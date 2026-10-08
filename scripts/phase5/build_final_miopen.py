"""Phase 5 / Gate P5-09 - build the final MIOpen.dll from the Phase-5
candidate.

Same validated Windows recipe as Phase-4's canonical build (toolchain,
shims, options; fresh build dir phase5_build/miopen; never touches
build_phase3 or phase4_build). Source: rocm-libraries-phase5-candidate
(3 commits over frozen develop 7c58661).
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
SRC = Y / "rocm-libraries-phase5-candidate" / "projects" / "miopen"
BUILD = Y / "phase5_build" / "miopen"
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
EV = RCA / "evidence" / "phase5" / "build"

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
    return {
        "PATH": os.pathsep.join([
            str(CORE / "bin"),
            str(CORE / "lib" / "llvm" / "bin"),
            str(BUILDTOOLS / "Scripts"),
            str(WINSDK / "bin" / SDKVER / "x64"),
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


def run(cmd, log_name, e=None):
    e = e or env()
    p = subprocess.run(cmd, env=e, cwd=None, capture_output=True, text=True,
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
    dirty = subprocess.run(["git", "-C", str(SRC), "status", "--short"],
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        print("REFUSING: candidate worktree dirty:\n", dirty)
        return 2
    print("candidate HEAD:", head)

    staged = CORE / "lib" / "cmake"
    staged_hiplang = staged / "hip-lang"
    staged_created = False
    if not staged_hiplang.exists():
        staged_hiplang.mkdir(parents=True, exist_ok=True)
        shutil.copy(DEPS / "cmake_shims" / "hip-lang" / "lib" / "cmake" / "hip-lang" /
                    "hip-lang-config.cmake", staged_hiplang / "hip-lang-config.cmake")
        staged_created = True
        print("staged (temporary):", staged_hiplang)

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
    print(f"temporarily removed {len(removed)} over-260-char tracked files")

    try:
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
            "schema": "phase5_final_build_v1",
            "gate": "P5-09",
            "timestamp": datetime.now().isoformat(),
            "source_tree": str(SRC),
            "source_git_head": head,
            "configure_command": [str(c) for c in configure],
            "build_command": [str(c) for c in build],
            "over260_files_removed": len(removed),
            "dll_path": str(dll),
            "dll_size": dll.stat().st_size,
            "dll_sha256": h,
            "toolchain": {
                "cmake": subprocess.run([str(CMAKE), "--version"], capture_output=True,
                                        text=True).stdout.splitlines()[0],
                "clang": str(CORE / "lib" / "llvm" / "bin" / "clang++.exe"),
                "linker": str(CORE / "lib" / "llvm" / "bin" / "lld-link.exe"),
                "msvc": str(MSVC),
            },
            "note": "fresh build dir phase5_build/miopen; build_phase3 and phase4_build untouched",
        }
        (EV / "build_provenance.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print("MIOpen.dll:", dll)
        print("SHA256:", h)
        return 0
    finally:
        subprocess.run(["git", "-C", str(SRC.parent), "checkout", "--", "."],
                       capture_output=True)
        if staged_created:
            shutil.rmtree(staged_hiplang)
            if not any(staged.iterdir()):
                staged.rmdir()
            print("restored wheel (removed):", staged_hiplang)


if __name__ == "__main__":
    sys.exit(main())
