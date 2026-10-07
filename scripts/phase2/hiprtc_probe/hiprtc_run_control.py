"""Gate 24 supplement: compile the NO-include control via HIPRTC, load the
code object with amdhip64_7.dll (hipModuleLoadData), launch it, and verify
the kernel writes the expected value. Proves the standalone path compiles
AND executes correctly when no standard header is involved.
"""

from __future__ import annotations

import ctypes
import os
import sys

core_bin = os.environ.get(
    "HIPRTC_CORE_BIN",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
)
os.add_dll_directory(core_bin)
os.environ["PATH"] = core_bin + os.pathsep + os.environ.get("PATH", "")

hiprtc = ctypes.CDLL(os.path.join(core_bin, "hiprtc0714.dll"))
hip = ctypes.CDLL(os.path.join(core_bin, "amdhip64_7.dll"))

SRC = (
    "extern \"C\" __global__\n"
    "void hiprtc_control(int* out)\n{\n    *out = 42;\n}\n"
)

# compile
prog = ctypes.c_void_p()
src_b = SRC.encode()
assert hiprtc.hiprtcCreateProgram(ctypes.byref(prog), src_b, b"control.cu", 0, None, None) == 0
options = (ctypes.c_char_p * 1)(b"--gpu-architecture=gfx1151")
rc = hiprtc.hiprtcCompileProgram(prog, 1, options)
assert rc == 0, f"compile failed rc={rc}"
size = ctypes.c_size_t(0)
hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(size))
buf = ctypes.create_string_buffer(size.value)
assert hiprtc.hiprtcGetCode(prog, buf) == 0
print(f"compiled code object: {size.value} bytes")

# init runtime, alloc, load, launch
assert hip.hipInit(0) == 0
dev = ctypes.c_int()
hip.hipGetDevice(ctypes.byref(dev))
out = ctypes.c_int(-1)
d_out = ctypes.c_void_p()
assert hip.hipMalloc(ctypes.byref(d_out), ctypes.c_size_t(4)) == 0
hip.hipMemset(d_out, 0, ctypes.c_size_t(4))

module = ctypes.c_void_p()
assert hip.hipModuleLoadData(ctypes.byref(module), buf) == 0
fn = ctypes.c_void_p()
assert hip.hipModuleGetFunction(ctypes.byref(fn), module, b"hiprtc_control") == 0

args_buf = (ctypes.c_void_p * 1)(ctypes.cast(ctypes.byref(d_out), ctypes.c_void_p).value)
assert hip.hipModuleLaunchKernel(
    fn, 1, 1, 1, 1, 1, 1, 0, ctypes.c_void_p(), args_buf, None
) == 0
hip.hipDeviceSynchronize()

host = ctypes.c_int(-1)
assert hip.hipMemcpy(
    ctypes.byref(host), d_out, ctypes.c_size_t(4), 4  # kind=4 hipMemcpyDeviceToHost
) == 0
print(f"kernel result: out = {host.value} (expected 42)")
print("STANDALONE-HIPRTC-EXEC:", "PASS" if host.value == 42 else "FAIL")
sys.exit(0 if host.value == 42 else 5)
