"""Gate 32 Candidate B: compile the REAL extracted MIOpen BatchNorm kernel
(MIOpenBatchNormFwdTrainSpatial.cpp + its extracted include tree) through
hiprtc with options mirroring MIOpen's BuildHip — with a patched
miopen_type_traits.hpp whose no-STL shim is restored for runtime-compile
mode. Proves the MIOpen-source-level fix compiles the actual kernel.

Usage: python hiprtc_compile_bnsources.py <kernel-dir> [--baseline]
  --baseline : compile the UNPATCHED tree (expected FAIL: type_traits)
"""

from __future__ import annotations

import ctypes
import json
import os
import sys

kern_dir = sys.argv[1]
baseline = "--baseline" in sys.argv

core_bin = os.environ.get(
    "HIPRTC_CORE_BIN",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
)
os.add_dll_directory(core_bin)
os.environ["PATH"] = core_bin + os.pathsep + os.environ.get("PATH", "")
hiprtc = ctypes.CDLL(os.path.join(core_bin, "hiprtc0714.dll"))

src_path = os.path.join(kern_dir, "MIOpenBatchNormFwdTrainSpatial.cpp")
src = open(src_path, encoding="utf-8", errors="replace").read()

# Mirror MIOpen BuildHip options (comgr.cpp develop; wheel 3.5.2 rockrel)
options = [
    b"-D__HIP_PLATFORM_AMD__=1",
    b"-DMIOPEN_USE_FP16=0",
    b"-DMIOPEN_USE_FP32=1",
    b"-DMIOPEN_USE_FPMIX=0",
    b"-DMIOPEN_USE_BFPMIX=0",
    b"-DMIOPEN_LAYER_NCHW=1",
    b"-DMIOPEN_LAYER_NHWC=0",
    b"-DHIP_PACKAGE_VERSION_FLAT=7014608500",  # 7.14.60850
    b"-DMIOPEN_HIP_RUNTIME_COMPILE",
    b"-Wno-cuda-compat",
    b"-fno-gpu-rdc",
    b"-O3",
    b"-std=c++17",
    b"--gpu-architecture=gfx1151",
    ("-I" + os.path.join(kern_dir, "include")).encode(),
]

prog = ctypes.c_void_p()
r_create = hiprtc.hiprtcCreateProgram(
    ctypes.byref(prog), src.encode(), b"MIOpenBatchNormFwdTrainSpatial.cpp", 0, None, None
)
arr = (ctypes.c_char_p * len(options))(*options)
r_compile = hiprtc.hiprtcCompileProgram(prog, len(options), arr)
ls = ctypes.c_size_t(0)
hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(ls))
lb = ctypes.create_string_buffer(max(ls.value, 1))
hiprtc.hiprtcGetProgramLog(prog, lb)
cs = ctypes.c_size_t(0)
r_cs = hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(cs))

print(
    json.dumps(
        {
            "mode": "baseline(unpatched)" if baseline else "candidateB(patched)",
            "kernel_dir": kern_dir,
            "create": r_create,
            "compile": r_compile,
            "code_size": cs.value if r_compile == 0 else 0,
            "log": lb.value.decode("utf-8", "replace")[:20000],
        },
        indent=2,
    )
)
sys.exit(0 if r_compile == 0 else 3)
