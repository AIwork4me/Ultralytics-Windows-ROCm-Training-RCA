"""Phase 5 / Gates P5-06+P5-07 - real CMake/CTest integration of the HIPRTC
self-containment regression test.

Configures the ACTUAL MIOpen source tree (Phase-5 candidate worktree,
frozen develop base + source-fix commits + CI test commit) with
BUILD_TESTING=ON using the validated Phase-3/4 shim toolchain, builds ONLY
the test_hiprtc_selfcontained target, and runs it through CTest.

Source : rocm-libraries-phase5-candidate/projects/miopen
Build  : phase5_build/ci_test (fresh; phase4_build untouched)
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
BUILD = Y / "phase5_build" / "ci_test"
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
EV = RCA / "evidence" / "phase5" / "ci"

ENV_PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd")
CORE = ENV_PY / "Lib" / "site-packages" / "_rocm_sdk_core"
DEPS = Y / "phase3_deps"
BUILDTOOLS = Y / "phase3_buildtools"
CMAKE = BUILDTOOLS / "Lib" / "site-packages" / "cmake" / "data" / "bin" / "cmake.exe"
NINJA = BUILDTOOLS / "Scripts" / "ninja.exe"
CTEST = BUILDTOOLS / "Lib" / "site-packages" / "cmake" / "data" / "bin" / "ctest.exe"

MSVC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207")
WINSDK = Path(r"C:\Program Files (x86)\Windows Kits\10")
SDKVER = "10.0.26100.0"


def env() -> dict:
    e = {
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
    return e  # deliberately NOT inheriting PATH (conda base leakage)


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
    print("candidate HEAD:", head)

    # temporary hip-lang staging in the wheel (Phase-3 method, restored in finally)
    staged = CORE / "lib" / "cmake"
    staged_hiplang = staged / "hip-lang"
    staged_created = False
    if not staged_hiplang.exists():
        staged_hiplang.mkdir(parents=True, exist_ok=True)
        shutil.copy(DEPS / "cmake_shims" / "hip-lang" / "lib" / "cmake" / "hip-lang" /
                    "hip-lang-config.cmake", staged_hiplang / "hip-lang-config.cmake")
        staged_created = True
        print("staged (temporary):", staged_hiplang)

    # over-260-char tracked blobs break ninja Stat (Phase-3 lesson)
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
            "-DBUILD_TESTING=ON",          # <-- the point of this gate
            # GTest in CONFIG mode: the gtest subdir links GTest::gmock,
            # which MODULE-mode FindGTest does not provide. Upstream CI
            # installs distro libgtest-dev (config package); this Windows
            # machine uses phase5_deps/gtest_prefix built with the same
            # clang toolchain.
            f"-DGTest_DIR={Y / 'phase5_deps' / 'gtest_prefix' / 'lib' / 'cmake' / 'GTest'}",
            "-DMIOPEN_BUILD_DRIVER=OFF",
            "-DMIOPEN_BUILD_CK=OFF",
            # CI-test-focused configure: without an installed CK package the
            # CK-header gtests cannot link; upstream documents that the host
            # configures cleanly with this OFF (flag gates only the per-arch
            # CK plugin build and CK-header-dependent gtests - see the
            # ROCM-27359 comment in projects/miopen/CMakeLists.txt).
            "-DMIOPEN_USE_COMPOSABLEKERNEL=OFF",
            "-DMIOPEN_EMBED_BINCACHE=OFF",
            "-DMIOPEN_BINCACHE_PATH=",
            "-DMIOPEN_ENABLE_FIN=OFF",
            "-DMIOPEN_ENABLE_AI_KERNEL_TUNING=OFF",
            "-DMIOPEN_ENABLE_AI_IMMED_MODE_FALLBACK=OFF",
            f"-DUNZIPPER={DEPS / 'tools' / 'bzip2.cmd'}".replace("\\", "/"),
        ]
        p = run(configure, "ci_configure.log")
        if p.returncode != 0:
            print(p.stdout[-4000:], p.stderr[-4000:])
            return 1

        build = [str(CMAKE), "--build", str(BUILD),
                 "--target", "test_hiprtc_selfcontained", "--", "-k", "0"]
        p = run(build, "ci_build_target.log")
        if p.returncode != 0:
            print(p.stdout[-4000:], p.stderr[-4000:])
            return 1

        disc = run([str(CTEST), "-N", "-R", "test_hiprtc_selfcontained",
                    "--test-dir", str(BUILD)], "ci_ctest_discovery.log")
        run([str(CTEST), "-N", "--test-dir", str(BUILD)], "ci_ctest_all_tests.log")

        test_env = dict(env())
        # the test binary needs hiprtc DLL on PATH at runtime
        test_env["PATH"] = os.pathsep.join([
            str(CORE / "bin"), test_env["PATH"]])
        exec_run = run([str(CTEST), "-R", "^test_hiprtc_selfcontained$",
                        "--output-on-failure", "--test-dir", str(BUILD)],
                       "ci_ctest_run.log", e=test_env)

        # capture binary hash
        exe = BUILD / "test_hiprtc_selfcontained.exe"
        exe_sha = hashlib.sha256(exe.read_bytes()).hexdigest() if exe.exists() else None

        record = {
            "schema": "phase5_ci_integration_v1",
            "gate": "P5-06+P5-07",
            "timestamp": datetime.now().isoformat(),
            "source_tree": str(SRC),
            "source_git_head": head,
            "build_dir": str(BUILD),
            "configure": {"cmd": "BUILD_TESTING=ON (see ci_configure.log)",
                          "exit": 0},
            "build_target": {"target": "test_hiprtc_selfcontained", "exit": 0},
            "ctest_discovery": {"exit": disc.returncode},
            "ctest_run": {"exit": exec_run.returncode},
            "test_exe": str(exe) if exe.exists() else None,
            "test_exe_sha256": exe_sha,
            "over260_files_removed": len(removed),
            "hip_lang_staging": "temporary; removed after",
        }
        (EV / "ci_integration.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print("record written:", EV / "ci_integration.json")
        return exec_run.returncode
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
