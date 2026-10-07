"""Phase-3 Gate 58/59: compile the REAL upstream MIOpen BatchNorm kernel
from the patched rocm-libraries tree through the wheel's hiprtc —
-mirror of MIOpen BuildHip options- with -nostdinc (no host STL), the
exact condition of the Windows-wheel defect.

Also runs the BASELINE (pristine tree) negative control.

Usage:
  python compile_bn_patched_tree.py <kernels-dir> [--baseline] [--nostdinc]
Exit: 0 compile OK, 3 HIPRTC_ERROR_COMPILATION.
"""
from __future__ import annotations

import ctypes
import datetime
import hashlib
import json
import os
import subprocess
import sys

kern_dir = os.path.abspath(sys.argv[1])
baseline = "--baseline" in sys.argv
nostdinc = "--nostdinc" in sys.argv

core_bin = os.environ.get(
    "HIPRTC_CORE_BIN",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
)
os.add_dll_directory(core_bin)
os.environ["PATH"] = core_bin + os.pathsep + os.environ.get("PATH", "")
hiprtc = ctypes.CDLL(os.path.join(core_bin, "hiprtc0714.dll"))

src_name = "MIOpenBatchNormFwdTrainSpatial.cpp"
src_path = os.path.join(kern_dir, src_name)
src = open(src_path, encoding="utf-8", errors="replace").read()

options = [
    "-D__HIP_PLATFORM_AMD__=1",
    "-DMIOPEN_USE_FP16=0",
    "-DMIOPEN_USE_FP32=1",
    "-DMIOPEN_USE_FPMIX=0",
    "-DMIOPEN_USE_BFPMIX=0",
    "-DMIOPEN_LAYER_NCHW=1",
    "-DMIOPEN_LAYER_NHWC=0",
    "-DMIO_BN_VARIANT=0",
    "-DMIO_BN_GRP0=1024",
    "-DMIO_BN_GRP1=1",
    "-DMIO_BN_GRP2=1",
    "-DHIP_PACKAGE_VERSION_FLAT=7140060850",
    "-DMIOPEN_HIP_RUNTIME_COMPILE",
    "-Wno-cuda-compat",
    "-fno-gpu-rdc",
    "-O3",
    "-std=c++17",
    "--gpu-architecture=gfx1151",
    "-I" + kern_dir,
]
if nostdinc:
    options.append("-nostdinc")

prog = ctypes.c_void_p()
r_create = hiprtc.hiprtcCreateProgram(
    ctypes.byref(prog), src.encode(), src_name.encode(), 0, None, None)
arr = (ctypes.c_char_p * len(options))(*[o.encode() for o in options])
r_compile = hiprtc.hiprtcCompileProgram(prog, len(options), arr)
ls = ctypes.c_size_t(0)
hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(ls))
lb = ctypes.create_string_buffer(max(ls.value, 1))
hiprtc.hiprtcGetProgramLog(prog, lb)
cs = ctypes.c_size_t(0)
r_cs = hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(cs))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


tt = os.path.join(kern_dir, "miopen_type_traits.hpp")
uu = os.path.join(kern_dir, "miopen_utility.hpp")
print(json.dumps({
    "timestamp": datetime.datetime.now().isoformat(),
    "mode": ("baseline" if baseline else "patched") + ("+nostdinc" if nostdinc else "+default-env"),
    "kernels_dir": kern_dir,
    "type_traits_sha256": sha(tt) if os.path.exists(tt) else None,
    "utility_sha256": sha(uu) if os.path.exists(uu) else None,
    "freestanding_present": [f for f in os.listdir(kern_dir)
                             if f.startswith("miopen_freestanding")],
    "create": r_create,
    "compile": r_compile,
    "code_size": cs.value if r_compile == 0 else 0,
    "log": lb.value.decode("utf-8", "replace")[:20000],
}, indent=2))
sys.exit(0 if r_compile == 0 else 3)
