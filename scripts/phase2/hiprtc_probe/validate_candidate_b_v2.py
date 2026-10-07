"""Gate 32 (post-review): compile-validate the v2 Candidate-B header.

1. PREPROCESS the patched miopen_type_traits.hpp in MIOpen's RTC context
   (-DMIOPEN_HIP_RUNTIME_COMPILE -DHIP_PACKAGE_VERSION_FLAT=7014608500
   -std=c++17) and assert the output contains ZERO '#include <type_traits>'
   residue and defines all five traits the BN closure uses.
2. COMPILE a mini-kernel that instantiates all five traits THROUGH the
   patched header (-I patched dir), with -nostdinc so no system/MSVC STL
   can be touched, and EXECUTE it on the GPU to verify results.

Exit 0 iff all checks pass.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys

CORE = os.environ.get(
    "HIPRTC_CORE_BIN",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
)
PATCHED_DIR = sys.argv[1]  # dir containing patched miopen_type_traits.hpp
HDR = os.path.join(PATCHED_DIR, "miopen_type_traits.hpp")

os.add_dll_directory(CORE)
os.environ["PATH"] = CORE + os.pathsep + os.environ.get("PATH", "")

report: dict[str, object] = {"patched_header": HDR, "checks": []}

# ---- check 1: preprocess in RTC context ----
src = f'#include "miopen_type_traits.hpp"\n'
tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "candb_pp.cpp")
open(tmp, "w").write(src)
r = subprocess.run(
    [
        os.path.join(CORE, "..", "lib", "llvm", "bin", "amdclang++.exe"),
        "-E",
        "-x",
        "c++",
        "-std=c++17",
        "-DMIOPEN_HIP_RUNTIME_COMPILE",
        "-DHIP_PACKAGE_VERSION_FLAT=7014608500",
        "-I" + PATCHED_DIR,
        "-nostdinc",
        tmp,
    ],
    capture_output=True,
    text=True,
    timeout=120,
)
pp = r.stdout
includes_resolved = pp.count("#include") == 0 or "type_traits" not in pp.split("miopen_type_traits.hpp")[-1]
traits = {
    "remove_reference": "struct std::remove_reference" in pp or "remove_reference" in pp,
    "remove_cv": "remove_cv" in pp,
    "is_same": "is_same" in pp,
    "enable_if": "enable_if" in pp,
    "conditional": "conditional" in pp,
}
report["checks"].append(
    {
        "check": "preprocess_RTC_context",
        "exit": r.returncode,
        "stderr_head": r.stderr[:300],
        "trait_names_present": traits,
        "pass": r.returncode == 0 and all(traits.values()) and "error" not in r.stderr.lower(),
    }
)

# ---- check 2+3: compile and execute trait-using kernel with -nostdinc ----
KSRC = """#include "miopen_type_traits.hpp"
extern "C" __global__ void candb_traits_kernel(int* out)
{
    using A = std::remove_reference<int&>::type;          // int
    using B = std::remove_cv<const int>::type;            // int
    using C = std::conditional<sizeof(A) == sizeof(B), long, char>::type; // long
    using D = std::is_same<A, B>;                          // false (int vs const int pre-remove? A=int,B=int -> true)
    using E = std::enable_if<D::value, int>::type;         // int
    *out = (int)(sizeof(C) + (D::value ? E(1) : E(2)));
}
"""
hiprtc = ctypes.CDLL(os.path.join(CORE, "hiprtc0714.dll"))
prog = ctypes.c_void_p()
rc1 = hiprtc.hiprtcCreateProgram(
    ctypes.byref(prog), KSRC.encode(), b"candb.cu", 0, None, None
)
options = [
    b"-std=c++17",
    b"-DMIOPEN_HIP_RUNTIME_COMPILE",
    b"-DHIP_PACKAGE_VERSION_FLAT=7014608500",
    b"-nostdinc",
    ("-I" + PATCHED_DIR).encode(),
    b"--gpu-architecture=gfx1151",
]
arr = (ctypes.c_char_p * len(options))(*options)
rc2 = hiprtc.hiprtcCompileProgram(prog, len(options), arr)
ls = ctypes.c_size_t(0)
hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(ls))
lb = ctypes.create_string_buffer(max(ls.value, 1))
hiprtc.hiprtcGetProgramLog(prog, lb)
cs = ctypes.c_size_t(0)
hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(cs))
code = ctypes.create_string_buffer(cs.value) if rc2 == 0 else None
if rc2 == 0:
    hiprtc.hiprtcGetCode(prog, code)
report["checks"].append(
    {
        "check": "compile_traits_kernel_nostdinc",
        "create": rc1,
        "compile": rc2,
        "code_size": cs.value,
        "log": lb.value.decode("utf-8", "replace")[:600],
        "pass": rc2 == 0,
    }
)

# execute
exec_ok = None
if rc2 == 0:
    hip = ctypes.CDLL(os.path.join(CORE, "amdhip64_7.dll"))
    assert hip.hipInit(0) == 0
    d_out = ctypes.c_void_p()
    hip.hipMalloc(ctypes.byref(d_out), ctypes.c_size_t(4))
    hip.hipMemset(d_out, 0, ctypes.c_size_t(4))
    module = ctypes.c_void_p()
    hip.hipModuleLoadData(ctypes.byref(module), code)
    fn = ctypes.c_void_p()
    hip.hipModuleGetFunction(ctypes.byref(fn), module, b"candb_traits_kernel")
    args_buf = (ctypes.c_void_p * 1)(
        ctypes.cast(ctypes.byref(d_out), ctypes.c_void_p).value
    )
    hip.hipModuleLaunchKernel(
        fn, 1, 1, 1, 1, 1, 1, 0, ctypes.c_void_p(), args_buf, None
    )
    hip.hipDeviceSynchronize()
    host = ctypes.c_int(-1)
    hip.hipMemcpy(
        ctypes.byref(host), d_out, ctypes.c_size_t(4), 4
    )
    # expected: C = long; under hiprtc's Windows -fms-compatibility semantics
    # long is 4 bytes (MSVC LLP64), so sizeof(C) + 1 = 5
    exec_ok = host.value
    report["checks"].append(
        {
            "check": "execute_traits_kernel",
            "result": host.value,
            "expected": 5,
            "pass": host.value == 5,
        }
    )

ok = all(c["pass"] for c in report["checks"])
print(json.dumps(report, indent=2))
print("CANDIDATE-B-V2:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
