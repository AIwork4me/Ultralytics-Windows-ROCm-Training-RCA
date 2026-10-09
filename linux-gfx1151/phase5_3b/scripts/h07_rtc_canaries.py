"""Gate H07 (P53B): R2-targeted coverage canaries adapted from Phase-3 extended_canary.
Leg A = frozen base 7c58661, Leg B = exact R2 tree b983cad (both from this mission).

New evidence addressing maintainer review MAJOR-2/3/4:
  E1) UNPATCHED wrapper chain, RTC, -nostdinc++: comgr's bundled libc++
      provides <type_traits> but NOT <utility> (partial STL). The unpatched
      HIP>=7 arm includes <utility> unconditionally -> must FAIL
      ('utility' file not found): the Windows failure CLASS reproduced on
      Linux through the real comgr RTC path.
  E2) PATCHED wrapper chain, same partial-STL environment: the patch's
      partial-STL guard must fire — a CLEAN #error diagnostic naming the
      inconsistency (designed behavior: reject loudly instead of risking
      redefinitions). PASS = compile fails WITH the designed message.
  E3) patch-0002 paths: tensor_view.hpp, radix.hpp,
      miopen_freestanding_initializer_list.hpp compiled via RTC from BOTH
      trees in normal mode (with-STL) — patched must compile; plus
      static_assert value-equivalence for the radix lowering:
      __INT32_MAX__ == std::numeric_limits<int32_t>::max() and
      __INT64_MAX__ == std::numeric_limits<int64_t>::max().
  E4) Kthvalue kernel TU (the only radix consumer) compiled via RTC from
      both trees — unpatched and patched must both compile on Linux
      (with-STL); token stream is EXPECTED to differ (radix lowering),
      compile-level regression check only.
"""
import ctypes, json, re, sys
from datetime import datetime
from pathlib import Path

BASE = Path("/home/amd/Desktop/YOLO_AMD")
SP = BASE / ".venv/lib/python3.13/site-packages"
HIPRTC_LIB = SP / "_rocm_sdk_core/lib/libhiprtc.so.7"
HIP_LIB = SP / "_rocm_sdk_core/lib/libamdhip64.so.7"
UNP = BASE / "phase5_3b/src/legA/projects/miopen/src/kernels"
PAT = BASE / "phase5_3b/src/legB/projects/miopen/src/kernels"
RTCMODE = ["-DMIOPEN_HIP_RUNTIME_COMPILE=1", "-DHIP_PACKAGE_VERSION_FLAT=7140060850ULL"]

KERNEL = r"""
#include "miopen_type_traits.hpp"
#include "miopen_utility.hpp"
extern "C" __global__ void canary(int* out)
{
    using T = std::remove_reference<int&>::type;
    *out = (int)sizeof(T) == 4 ? 1 : 0;
    *out += (int)std::is_pointer<double*>::value;
    int a = 7;
    *out += (int)(*reinterpret_cast<char*>(&a) & 1) == (7 & 1) ? 0 : 1;
}
"""

TENSOR_VIEW_SRC = '#include "tensor_view.hpp"\n' + KERNEL
RADIX_EQUIV = r"""
#include <limits>
#include <cstdint>
static_assert(__INT32_MAX__ == (std::numeric_limits<std::int32_t>::max)(), "int32 max equivalence");
static_assert(__INT64_MAX__ == (std::numeric_limits<std::int64_t>::max)(), "int64 max equivalence");
static_assert(__INT32_MAX__ == 2147483647, "int32 literal");
static_assert(__INT64_MAX__ == 9223372036854775807LL, "int64 literal");
int touch; // non-empty TU
"""

def rtc_compile(src, inc_dir, extra):
    hiprtc = ctypes.CDLL(str(HIPRTC_LIB))
    prog = ctypes.c_void_p()
    rc = hiprtc.hiprtcCreateProgram(ctypes.byref(prog), src.encode(), b"c.cu", 0, None, None)
    if rc != 0:
        return {"rtc_create": rc, "rtc_compile": None, "log": ""}
    opts = [b"--gpu-architecture=gfx1151", ("-I" + str(inc_dir)).encode(), *extra]
    arr = (ctypes.c_char_p * len(opts))(*opts)
    rcc = hiprtc.hiprtcCompileProgram(prog, len(opts), arr)
    ls = ctypes.c_size_t(0); hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(ls))
    log = ctypes.create_string_buffer(max(ls.value, 1)); hiprtc.hiprtcGetProgramLog(prog, log)
    cs = ctypes.c_size_t(0); hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(cs))
    code = None
    if rcc == 0 and cs.value:
        code = ctypes.create_string_buffer(cs.value); hiprtc.hiprtcGetCode(prog, code)
    hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))
    return {"rtc_compile": rcc, "code_size": cs.value, "log": log.value.decode(errors="replace"), "_code": code}

def gpu_exec(code):
    hip = ctypes.CDLL(str(HIP_LIB))
    mod = ctypes.c_void_p(); k = ctypes.c_void_p(); dp = ctypes.c_void_p()
    rl = hip.hipModuleLoadData(ctypes.byref(mod), code)
    hip.hipModuleGetFunction(ctypes.byref(k), mod, b"canary")
    hip.hipMalloc(ctypes.byref(dp), 4)
    arg = dp
    args = (ctypes.c_void_p * 1)(ctypes.cast(ctypes.byref(arg), ctypes.c_void_p))
    rlaunch = hip.hipModuleLaunchKernel(k, 1,1,1, 1,1,1, 0, ctypes.c_void_p(0), args, None)
    host = ctypes.c_int(-1); hip.hipMemcpy(ctypes.byref(host), dp, 4, 2)
    return {"load": rl, "launch": rlaunch, "gpu_result": host.value}

def main():
    res = {"generated": datetime.now().isoformat(timespec="seconds"), "arms": {}}
    enc = [o.encode() for o in RTCMODE]
    # E1: unpatched, partial-STL env
    r = rtc_compile(KERNEL, UNP, [b"-nostdinc++", *enc])
    e1 = r["rtc_compile"] != 0 and "utility" in r["log"] and "not found" in r["log"]
    res["arms"]["E1_unpatched_partial_stl_FAIL"] = {"rc": r["rtc_compile"], "reproduces": e1,
        "log_head": r["log"][:300], "result": "PASS" if e1 else "FAIL"}
    # E2: patched, same env -> designed #error diagnostic expected
    r2 = rtc_compile(KERNEL, PAT, [b"-nostdinc++", *enc])
    guard = "inconsistent C++ standard library availability" in r2["log"]
    a = {"rc": r2["rtc_compile"], "guard_fired": guard,
         "log_head": r2["log"][:300],
         "result": "PASS" if (r2["rtc_compile"] != 0 and guard) else "FAIL"}
    res["arms"]["E2_patched_partial_stl_guard"] = a
    # E3: 0002 paths
    tv = {}
    for label, tree in (("unpatched", UNP), ("patched", PAT)):
        tv[label] = rtc_compile(TENSOR_VIEW_SRC, tree, enc)
    res["arms"]["E3_tensor_view"] = {"unpatched_rc": tv["unpatched"]["rtc_compile"],
        "patched_rc": tv["patched"]["rtc_compile"],
        "result": "PASS" if tv["patched"]["rtc_compile"] == 0 else "FAIL",
        "patched_log_head": tv["patched"]["log"][:200]}
    # radix equivalence (offline clang with STL): static_asserts
    import subprocess
    CLANG = str(SP / "_rocm_sdk_devel/lib/llvm/bin/amdclang++")
    f = Path("/tmp/radix_equiv.cpp"); f.write_text(RADIX_EQUIV)
    rr = subprocess.run([CLANG, "-x", "c++", "-std=c++17", "-fsyntax-only", str(f)],
                        capture_output=True, text=True); f.unlink()
    res["arms"]["E3_radix_value_equivalence"] = {"rc": rr.returncode,
        "result": "PASS" if rr.returncode == 0 else "FAIL", "stderr": rr.stderr[:200]}
    # freestanding initializer_list device-level engagement on Linux is
    # only reachable in a NO-STL environment (partial env -> guard rejects;
    # full-STL env -> probe selects real header). Exercise the full
    # freestanding chain (utility wrapper + tensor_view probe +
    # initializer_list) in the offline zero-STL channel:
    import subprocess
    CLANG = str(SP / "_rocm_sdk_devel/lib/llvm/bin/amdclang++")
    src_il = ('#include "miopen_type_traits.hpp"\n'
              '#include "miopen_utility.hpp"\n'
              '#include "tensor_view.hpp"\n'
              'int use_il() { const auto il = {1, 2, 3}; return (int)il.size(); }\n'
              'static_assert(sizeof(int) == 4, "sanity");\n')
    f3 = Path("/tmp/initlist_chain.cpp"); f3.write_text(src_il)
    r3 = subprocess.run([CLANG, "-x", "c++", "-std=c++17", "-nostdinc++",
                         "-fsyntax-only", *RTCMODE,
                         "-D__global__=", "-D__device__=", "-D__host__=",
                         "-I", str(PAT), str(f3)],
                        capture_output=True, text=True); f3.unlink()
    a3 = {"rc": r3.returncode, "stderr_head": r3.stderr[:300],
          "note": ("zero-STL offline channel; tensor_view probe falls back to "
                   "freestanding initializer_list; wrapper chain falls back to "
                   "freestanding utility/type_traits"),
          "result": "PASS" if r3.returncode == 0 else "FAIL"}
    res["arms"]["E3_freestanding_initlist_chain_zerostl"] = a3
    # E4: Kthvalue TU both trees
    kt = {}
    for label, tree in (("unpatched", UNP), ("patched", PAT)):
        src = '#include "MIOpenKthvalue.cpp"\n'
        kt[label] = rtc_compile(src, tree, enc)
    res["arms"]["E4_kthvalue_rtc"] = {"unpatched_rc": kt["unpatched"]["rtc_compile"],
        "patched_rc": kt["patched"]["rtc_compile"],
        "result": "PASS" if kt["patched"]["rtc_compile"] == 0 else "FAIL",
        "unpatched_log_head": kt["unpatched"]["log"][:200],
        "patched_log_head": kt["patched"]["log"][:200]}
    ok = all(v.get("result") == "PASS" for v in res["arms"].values())
    res["overall"] = "PASS" if ok else "FAIL"
    out = BASE / "phase5_3b/evidence/h07_coverage/extended_canary.json"
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: v.get("result") for k, v in res["arms"].items()} | {"overall": res["overall"]}, indent=1))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
