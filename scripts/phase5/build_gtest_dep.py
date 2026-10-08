"""Phase 5 - build googletest v1.14.0 as a Windows CI-test dependency.

Upstream MIOpen CI uses the distro libgtest-dev; this machine has no
system GTest, so we build the same library with the validated clang
toolchain into phase5_deps/gtest_prefix.
"""
import os
import subprocess
import sys
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
DEPS = Y / "phase5_deps"
CORE = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core")
BUILDTOOLS = Y / "phase3_buildtools"
CMAKE = BUILDTOOLS / "Lib" / "site-packages" / "cmake" / "data" / "bin" / "cmake.exe"
NINJA = BUILDTOOLS / "Scripts" / "ninja.exe"
MSVC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207")
WINSDK = Path(r"C:\Program Files (x86)\Windows Kits\10")
SDKVER = "10.0.26100.0"
SRC = DEPS / "googletest-1.14.0"
BUILD = DEPS / "gtest_build"
PREFIX = DEPS / "gtest_prefix"


def env() -> dict:
    return {
        "PATH": os.pathsep.join([
            str(CORE / "bin"), str(CORE / "lib" / "llvm" / "bin"),
            str(BUILDTOOLS / "Scripts"), str(WINSDK / "bin" / SDKVER / "x64"),
            r"C:\Windows\System32", r"C:\Windows",
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
        ]),
        "SystemRoot": r"C:\Windows",
        "USERNAME": "rocm",
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
    }


def run(cmd):
    p = subprocess.run(cmd, env=env(), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(f"$ {' '.join(str(c) for c in cmd)}\n  exit={p.returncode}")
    if p.returncode != 0:
        print(p.stdout[-3000:], p.stderr[-3000:])
    return p.returncode


def main() -> int:
    rc = run([str(CMAKE), "-S", str(SRC), "-B", str(BUILD), "-G", "Ninja",
              f"-DCMAKE_MAKE_PROGRAM={NINJA}",
              "-DCMAKE_BUILD_TYPE=Release",
              f"-DCMAKE_C_COMPILER={CORE / 'lib' / 'llvm' / 'bin' / 'clang.exe'}",
              f"-DCMAKE_CXX_COMPILER={CORE / 'lib' / 'llvm' / 'bin' / 'clang++.exe'}",
              f"-DCMAKE_LINKER={CORE / 'lib' / 'llvm' / 'bin' / 'lld-link.exe'}",
              f"-DCMAKE_INSTALL_PREFIX={PREFIX}",
              "-Dgtest_force_shared_crt=ON",
              "-DINSTALL_GTEST=ON"])
    if rc:
        return rc
    rc = run([str(CMAKE), "--build", str(BUILD), "--target", "install"])
    if rc:
        return rc
    for probe in [PREFIX / "include" / "gtest" / "gtest.h",
                  PREFIX / "lib" / "gtest.lib",
                  PREFIX / "lib" / "gtest_main.lib"]:
        print(("OK  " if probe.exists() else "MISS"), probe)
    return 0 if all(p.exists() for p in [PREFIX / "include" / "gtest" / "gtest.h",
                                         PREFIX / "lib" / "gtest.lib",
                                         PREFIX / "lib" / "gtest_main.lib"]) else 1


if __name__ == "__main__":
    sys.exit(main())
