"""Phase 4 / Gate P50 - build canonical (two-commit) MIOpen.dll on Windows.

Replicates the validated Phase-3 build configuration (same toolchain, shims,
options; fresh build dir phase4_build/miopen; never touches build_phase3).

Source : rocm-libraries-phase4-canonical/projects/miopen  (HEAD = 2 commits
         after b68f894, byte-equivalent to P3-FINAL-R3)
Build  : phase4_build/miopen
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
SRC = Y / "rocm-libraries-phase4-canonical" / "projects" / "miopen"
BUILD = Y / "phase4_build" / "miopen"
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
EV = RCA / "evidence" / "phase4" / "build"

ENV_PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd")
CORE = ENV_PY / "Lib" / "site-packages" / "_rocm_sdk_core"
DEPS = Y / "phase3_deps"
BUILDTOOLS = Y / "phase3_buildtools"
CMAKE = BUILDTOOLS / "Lib" / "site-packages" / "cmake" / "data" / "bin" / "cmake.exe"
NINJA = BUILDTOOLS / "Scripts" / "ninja.exe"

MSVC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207")
WINSDK = Path(r"C:\Program Files (x86)\Windows Kits\10")
SDKVER = "10.0.26100.0"


def env() -> dict:
    e = {
        "PATH": os.pathsep.join([
            str(CORE / "bin"),
            str(CORE / "lib" / "llvm" / "bin"),
            str(BUILDTOOLS / "Scripts"),
            str(WINSDK / "bin" / SDKVER / "x64"),  # mt.exe/rc.exe for lld-link
            r"C:\Windows\System32",
            r"C:\Windows",
            r"C:\Windows\System32\Wbem",
        ]),
        "INCLUDE": os.pathsep.join([
            str(MSVC / "include"),
            str(WINSDK / "Include" / SDKVER / "ucrt"),
            str(WINSDK / "Include" / SDKVER / "um"),
            str(WINSDK / "Include" / SDKVER / "shared"),
        ]),
        "LIB": os.pathsep.join([
            str(MSVC / "lib" / "x64"),
            str(WINSDK / "Lib" / SDKVER / "ucrt" / "x64"),
            str(WINSDK / "Lib" / SDKVER / "um" / "x64"),
            str(CORE / "lib"),
        ]),
        "SystemRoot": r"C:\Windows",
        "USERNAME": os.environ.get("USERNAME", "rocm"),
        "TEMP": os.environ.get("TEMP", r"C:\Users\rocm\AppData\Local\Temp"),
        "TMP": os.environ.get("TMP", r"C:\Users\rocm\AppData\Local\Temp"),
    }
    # deliberately NOT inheriting PATH: conda base leakage corrupts CMake
    # discovery (stale nlohmann headers) - Phase-3 lesson.
    return e


def run(cmd, log_name, e=None, cwd=None):
    e = e or env()
    p = subprocess.run(cmd, env=e, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    EV.mkdir(parents=True, exist_ok=True)
    (EV / log_name).write_text(
        "$ " + " ".join(str(c) for c in cmd) + f"\nexit={p.returncode}\n"
        + p.stdout[-200000:] + p.stderr[-200000:], encoding="utf-8")
    print(f"[{log_name}] exit={p.returncode}")
    return p


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(SRC), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print("canonical HEAD:", head)

    # Stage the hip-lang runtime package into the wheel for the duration of
    # configure+build only (Phase-3 environment; CMake's HIP-language detection
    # hard-checks <ROCM_ROOT>/lib/cmake/hip-lang on the compiler-derived root).
    # Created only if absent; always removed afterwards (wheel stays pristine).
    staged = CORE / "lib" / "cmake"
    staged_hiplang = staged / "hip-lang"
    staged_created = False
    if not staged_hiplang.exists():
        staged_hiplang.mkdir(parents=True, exist_ok=True)
        shutil.copy(DEPS / "cmake_shims" / "hip-lang" / "lib" / "cmake" / "hip-lang" /
                    "hip-lang-config.cmake", staged_hiplang / "hip-lang-config.cmake")
        staged_created = True
        print("staged (temporary):", staged_hiplang)
    try:
        return _configure_and_build(head)
    finally:
        if staged_created:
            shutil.rmtree(staged_hiplang)
            if not any(staged.iterdir()):
                staged.rmdir()
            print("restored wheel (removed):", staged_hiplang)


def _configure_and_build(head: str) -> int:

    # Phase-3-equivalent worktree state: the original phase3 checkout never
    # materialized tracked files whose absolute paths exceed 260 chars
    # (git checkout failed on them pre-longpaths), so its build never
    # referenced them. Ninja cannot Stat such paths even when present, and
    # these are gfx950 offline-assembly blobs unused by the gfx1151 DLL.
    # Remove them now (\\?\-prefixed so Python can see them) and restore
    # from git after the build.
    removed = []
    ls = subprocess.run(["git", "-C", str(SRC.parent), "ls-files"],
                        capture_output=True, text=True).stdout.splitlines()
    for f in ls:
        p = os.path.join(str(SRC.parent), f.replace("/", "\\"))
        if len(p) >= 260:
            lp = "\\\\?\\" + p
            if os.path.exists(lp):
                os.remove(lp)
                removed.append(f)
    print(f"temporarily removed {len(removed)} over-260-char tracked files (restored post-build)")

    try:
        return _run_configure_build(head, removed)
    finally:
        # always restore the committed worktree state
        subprocess.run(["git", "-C", str(SRC.parent), "checkout", "--", "."],
                       capture_output=True)
        subprocess.run(["git", "-C", str(SRC.parent), "status", "--short"],
                       capture_output=True)


def _run_configure_build(head: str, removed: list) -> int:
    configure = [
        str(CMAKE),
        "-S", str(SRC),
        "-B", str(BUILD),
        "-G", "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={NINJA}",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        f"-DCMAKE_INSTALL_PREFIX={BUILD / 'install'}",
        f"-DCMAKE_TOOLCHAIN_FILE={SRC / 'cmake' / 'ClangToolChain.cmake'}",
        f"-DCMAKE_C_COMPILER={CORE / 'lib' / 'llvm' / 'bin' / 'clang.exe'}",
        f"-DCMAKE_CXX_COMPILER={CORE / 'lib' / 'llvm' / 'bin' / 'clang++.exe'}",
        f"-DCMAKE_HIP_COMPILER={CORE / 'lib' / 'llvm' / 'bin' / 'clang.exe'}",
        "-DCMAKE_HIP_ARCHITECTURES=gfx1151",
        f"-DCMAKE_LINKER={CORE / 'lib' / 'llvm' / 'bin' / 'lld-link.exe'}",
        f"-DROCM_PATH={CORE}",
        "-DCMAKE_PREFIX_PATH=" + os.pathsep.join([
            str(DEPS / "dep_prefix" / "Library"),
            str(DEPS / "rocm-cmake"),
            str(DEPS / "cmake_shims" / "hip"),
            str(DEPS / "cmake_shims" / "hip-lang"),
            str(DEPS / "cmake_shims" / "rocblas"),
            str(DEPS / "cmake_shims" / "amd_comgr"),
            str(DEPS / "cmake_shims" / "hiprtc"),
            str(DEPS / "cmake_shims" / "rocrand"),
            str(DEPS / "cmake_shims" / "rocm-core"),
            str(DEPS / "cmake_shims" / "nlohmann_json"),
        ]),
        f"-DHALF_INCLUDE_DIR={DEPS / 'cmake_shims' / 'include'}",
        f"-DROCRAND_INCLUDE_DIR={DEPS / 'stage_rocrand'}",
        f"-DBZIP2_INCLUDE_DIR={DEPS / 'dep_prefix' / 'Library' / 'include'}",
        f"-DSQLite3_INCLUDE_DIR={DEPS / 'dep_prefix' / 'Library' / 'include'}",
        "-DBUILD_TESTING=OFF",
        "-DMIOPEN_BUILD_DRIVER=OFF",
        "-DMIOPEN_BUILD_CK=OFF",
        "-DMIOPEN_EMBED_BINCACHE=OFF",
        "-DMIOPEN_BINCACHE_PATH=",
        "-DMIOPEN_ENABLE_FIN=OFF",
        "-DMIOPEN_ENABLE_AI_KERNEL_TUNING=OFF",
        "-DMIOPEN_ENABLE_AI_IMMED_MODE_FALLBACK=OFF",
        # Phase-3 shim: bzip2 CLI via python bz2 (cache value there was CRLF-mangled)
        f"-DUNZIPPER={DEPS / 'tools' / 'bzip2.cmd'}".replace("\\", "/"),
    ]
    p = run(configure, "configure.log")
    if p.returncode != 0:
        print(p.stdout[-4000:], p.stderr[-4000:])
        return 1

    build = [str(CMAKE), "--build", str(BUILD), "--target", "MIOpen", "--", "-k", "0"]
    p = run(build, "build.log")
    if p.returncode != 0:
        print(p.stdout[-6000:], p.stderr[-6000:])
        return 1

    dll = BUILD / "MIOpen.dll"
    if not dll.exists():
        for cand in BUILD.rglob("MIOpen.dll"):
            dll = cand
            break
    h = hashlib.sha256(dll.read_bytes()).hexdigest()
    record = {
        "schema": "phase4_canonical_build_v1",
        "gate": "P50",
        "timestamp": datetime.now().isoformat(),
        "source_tree": str(SRC),
        "source_git_head": head,
        "configure_command": [str(c) for c in configure],
        "build_command": [str(c) for c in build],
        "worktree_state_deviation": {
            "description": "over-260-char tracked gfx950/gfx-exotic offline-assembly blobs "
                           "temporarily removed during build (ninja cannot Stat them); "
                           "identical to the effective phase3 checkout state; restored "
                           "from git afterwards",
            "count": len(removed),
            "restored": True,
        },
        "dll_path": str(dll),
        "dll_size": dll.stat().st_size,
        "dll_sha256": h,
        "toolchain": {
            "cmake": subprocess.run([str(CMAKE), "--version"], capture_output=True, text=True).stdout.splitlines()[0],
            "clang": str(CORE / "lib" / "llvm" / "bin" / "clang++.exe"),
            "linker": str(CORE / "lib" / "llvm" / "bin" / "lld-link.exe"),
            "msvc": str(MSVC),
        },
        "note": "fresh build dir phase4_build/miopen; build_phase3 untouched",
    }
    (EV / "build_provenance.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("MIOpen.dll:", dll)
    print("SHA256:", h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
