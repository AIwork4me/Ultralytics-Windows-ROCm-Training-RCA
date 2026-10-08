"""Phase 4 / Gates P48-P49: build the standalone hiprtc_selfcontained CI
test binary on Windows with the validated wheel toolchain (AMD clang
msvc-triple + wheel hiprtc import lib + MSVC/WinSDK link environment).

Same environment discipline as Phase 3: absolute paths only, no conda
base leakage.
"""
import os
import subprocess
import sys

SP = r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"
CORE = SP + r"\_rocm_sdk_core"
CLANG = CORE + r"\lib\llvm\bin\clang++.exe"
MSVC = r"C:\BuildTools\VC\Tools\MSVC\14.44.35207"
WINSDK = r"C:\Program Files (x86)\Windows Kits\10"
SDKVER = "10.0.26100.0"

SRC = r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA\patches\phase4\ci_test_proposal\hiprtc_selfcontained.cpp"
OUTDIR = r"C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\ci-test"
OUT = OUTDIR + r"\hiprtc_selfcontained.exe"

env = dict(os.environ)
inc = [
    CORE + "\\include",
    MSVC + "\\include",
    WINSDK + "\\Include\\" + SDKVER + "\\ucrt",
    WINSDK + "\\Include\\" + SDKVER + "\\um",
    WINSDK + "\\Include\\" + SDKVER + "\\shared",
]
lib = [
    MSVC + "\\lib\\x64",
    WINSDK + "\\Lib\\" + SDKVER + "\\ucrt\\x64",
    WINSDK + "\\Lib\\" + SDKVER + "\\um\\x64",
    CORE + "\\lib",
]
env["INCLUDE"] = ";".join(inc)
env["LIB"] = ";".join(lib)
env["PATH"] = CORE + r"\bin" + os.pathsep + env.get("PATH", "")

os.makedirs(OUTDIR, exist_ok=True)
cmd = [
    CLANG,
    "-target", "x86_64-pc-windows-msvc",
    "-std=c++17", "-O2", "-Wall",
    "-D__HIP_PLATFORM_AMD__=1",
    "-I" + CORE + "\\include",
    SRC,
    CORE + "\\lib\\hiprtc.lib",
    "-o", OUT,
]
print(" ".join(cmd))
r = subprocess.run(cmd, env=env, capture_output=True, text=True)
print("exit:", r.returncode)
print(r.stdout[-4000:])
print(r.stderr[-8000:])
sys.exit(r.returncode)
