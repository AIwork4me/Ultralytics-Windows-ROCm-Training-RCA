"""Gate 24/30 supplement: does hiprtcCompileProgram honor include-path
options? Tests -I<dir>, --include-path=<dir> (nvrtc-style), and
-isystem<dir> against a directory containing a fake 'stl_hdr.h', using a
source that #includes it. Establishes whether ANY caller-side option could
have supplied the missing STL path (Candidate A feasibility).
"""

from __future__ import annotations

import ctypes
import json
import os
import tempfile

core_bin = os.environ.get(
    "HIPRTC_CORE_BIN",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
)
os.add_dll_directory(core_bin)
os.environ["PATH"] = core_bin + os.pathsep + os.environ.get("PATH", "")
hiprtc = ctypes.CDLL(os.path.join(core_bin, "hiprtc0714.dll"))

tmp = tempfile.mkdtemp(prefix="hiprtc_incopts_")
hdr = os.path.join(tmp, "stl_hdr.h")
with open(hdr, "w") as f:
    f.write("#define STI_HDR_VALUE 7\n")

SRC = (
    "#include <stl_hdr.h>\n"
    "extern \"C\" __global__ void k(int* out) { *out = STI_HDR_VALUE; }\n"
)

results = []
for label, opts in [
    ("dash-I", [b"-I" + tmp.encode()]),
    ("include-path", [b"--include-path=" + tmp.encode()]),
    ("isystem", [b"-isystem" + tmp.encode()]),
]:
    prog = ctypes.c_void_p()
    r_create = hiprtc.hiprtcCreateProgram(
        ctypes.byref(prog), SRC.encode(), b"probe.cu", 0, None, None
    )
    arr = (ctypes.c_char_p * len(opts))(*opts)
    r_compile = hiprtc.hiprtcCompileProgram(prog, len(opts), arr)
    ls = ctypes.c_size_t(0)
    hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(ls))
    lb = ctypes.create_string_buffer(max(ls.value, 1))
    hiprtc.hiprtcGetProgramLog(prog, lb)
    cs = ctypes.c_size_t(0)
    hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(cs))
    results.append(
        {
            "option_style": label,
            "create": r_create,
            "compile": r_compile,
            "code_size": cs.value if r_compile == 0 else 0,
            "log": lb.value.decode("utf-8", "replace")[:400],
        }
    )
    hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))

print(json.dumps({"fake_include_dir": tmp, "results": results}, indent=2))
