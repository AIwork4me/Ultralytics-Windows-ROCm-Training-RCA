"""Gate L15: standalone HIPRTC header matrix on Linux — NO PyTorch, NO MIOpen, NO Ultralytics.

Port of the Phase-2 Windows probe (scripts/phase2/hiprtc_probe/hiprtc_probe.py)
to Linux wheel layout. Loads the wheel's libhiprtc.so via ctypes and compiles
small HIP sources with a controlled single #include (<type_traits> etc.),
mirroring what MIOpen's BatchNorm runtime-compile path does.

The 'none' control is additionally EXECUTED on the GPU via libamdhip64
(hipModuleLoadData + hipModuleLaunchKernel) to prove the code object is
functional, not merely compilable.

Usage:
    python hiprtc_probe_linux.py [none|type_traits|utility|limits|cstdint|initializer_list|all|exec]

Output: JSON on stdout. Exit 0 = all compile OK, 3 = any compile failure.
"""

from __future__ import annotations

import ctypes
import json
import sys
from datetime import datetime
from pathlib import Path

SP = Path(sys.prefix) / "lib" / "python3.13" / "site-packages"
CORE_LIB = SP / "_rocm_sdk_core" / "lib"

PROBES: dict[str, str] = {
    "none": "",
    "type_traits": "#include <type_traits>",
    "utility": "#include <utility>",
    "limits": "#include <limits>",
    "cstdint": "#include <cstdint>",
    "initializer_list": "#include <initializer_list>",
}

ARCH = "gfx1151"


def source_for(name: str) -> str:
    """Build probe source for probe NAME; each header's body really uses the std facility."""
    header = PROBES[name]
    include_line = f"{header}\n" if header else ""
    if name == "type_traits":
        body = "    using T = std::remove_reference<int&>::type;\n    *out = (int)sizeof(T);"
    elif name == "utility":
        body = "    int a = 1;\n    int& b = a;\n    *out = std::move(b);"
    elif name == "limits":
        body = "    *out = (std::numeric_limits<int>::max)() > 0 ? 1 : 0;"
    elif name == "cstdint":
        body = "    std::uint64_t v = 42;\n    *out = (int)(v & 0xff);"
    elif name == "initializer_list":
        body = "    auto il = {1, 2, 3};\n    *out = (int)il.size();\n    *out = 3;"
    else:
        body = "    *out = 1;"
    return (
        f"{include_line}"
        '\nextern "C" __global__\n'
        "void hiprtc_probe(int* out)\n{\n"
        f"{body}\n"
        "}\n"
    )


def run_compile(hiprtc, name: str) -> dict:
    header = PROBES[name]
    src = source_for(name)
    prog = ctypes.c_void_p()
    src_b = src.encode()
    name_b = "probe.cu".encode()

    entry = {
        "probe": name,
        "header": header or "(none)",
        "source": src,
        "arch": ARCH,
    }

    r_create = hiprtc.hiprtcCreateProgram(ctypes.byref(prog), src_b, name_b, 0, None, None)
    entry["rtc_create"] = r_create
    if r_create != 0:
        entry["stage"] = "create"
        entry["result"] = "FAIL"
        return entry

    options = (ctypes.c_char_p * 1)(f"--gpu-architecture={ARCH}".encode())
    r_compile = hiprtc.hiprtcCompileProgram(prog, 1, options)

    log_size = ctypes.c_size_t(0)
    hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(log_size))
    log = ctypes.create_string_buffer(max(log_size.value, 1))
    hiprtc.hiprtcGetProgramLog(prog, log)
    entry["log"] = log.value.decode(errors="replace")

    code_size = ctypes.c_size_t(0)
    r_codesize = hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(code_size))
    entry["rtc_compile"] = r_compile
    entry["rtc_codesize"] = r_codesize
    entry["code_size"] = code_size.value
    entry["result"] = "PASS" if r_compile == 0 and r_codesize == 0 else "FAIL"
    if entry["result"] == "PASS":
        code = ctypes.create_string_buffer(code_size.value)
        hiprtc.hiprtcGetCode(prog, code)
        entry["_code"] = code.raw[: code_size.value]
    hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))
    return entry


def run_exec(hip, code_bytes: bytes) -> dict:
    """Execute the 'none' probe code object on the GPU."""
    out = {
        "moduleLoadData": None,
        "malloc": None,
        "launch": None,
        "memcpyDtoH": None,
        "gpu_result": None,
    }
    module = ctypes.c_void_p()
    r = hip.hipModuleLoadData(ctypes.byref(module), code_bytes)
    out["moduleLoadData"] = r
    if r != 0:
        out["result"] = "FAIL"
        return out
    kernel = ctypes.c_void_p()
    r = hip.hipModuleGetFunction(
        ctypes.byref(kernel), module, b"hiprtc_probe"
    )
    out["moduleGetFunction"] = r
    if r != 0:
        out["result"] = "FAIL"
        return out
    dptr = ctypes.c_void_p()
    r = hip.hipMalloc(ctypes.byref(dptr), ctypes.sizeof(ctypes.c_int))
    out["malloc"] = r
    arg = dptr
    args = (ctypes.c_void_p * 1)(ctypes.cast(ctypes.byref(arg), ctypes.c_void_p))
    r = hip.hipModuleLaunchKernel(
        kernel,
        1, 1, 1,  # grid
        1, 1, 1,  # block
        0, ctypes.c_void_p(0), args, None,
    )
    out["launch"] = r
    host = ctypes.c_int(-1)
    r = hip.hipMemcpy(
        ctypes.byref(host), dptr, ctypes.sizeof(ctypes.c_int), 2  # hipMemcpyDeviceToHost
    )
    out["memcpyDtoH"] = r
    out["gpu_result"] = host.value
    out["result"] = "PASS" if r == 0 and host.value == 1 else "FAIL"
    return out


def main() -> int:
    names = sys.argv[1:] or ["all"]
    if names == ["all"]:
        names = list(PROBES)

    hiprtc_path = str(CORE_LIB / "libhiprtc.so.7")
    hip_path = str(CORE_LIB / "libamdhip64.so.7")
    hiprtc = ctypes.CDLL(hiprtc_path)
    hip = ctypes.CDLL(hip_path)

    maj, mnr = ctypes.c_int(), ctypes.c_int()
    hiprtc.hiprtcVersion(ctypes.byref(maj), ctypes.byref(mnr))

    results = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "hiprtc_library": hiprtc_path,
        "hip_library": hip_path,
        "hiprtc_version": f"{maj.value}.{mnr.value}",
        "arch": ARCH,
        "probes": [],
        "exec_control": None,
    }
    overall = 0
    for name in names:
        entry = run_compile(hiprtc, name)
        results["probes"].append(entry)
        if entry["result"] != "PASS":
            overall = 3

    # GPU execution control on the 'none' probe (and any compiled probe)
    if "none" in names or "all" in names:
        for entry in results["probes"]:
            if entry.get("probe") == "none" and entry.get("result") == "PASS":
                results["exec_control"] = run_exec(hip, entry.pop("_code"))
                break

    # strip raw code buffers from the other entries
    for entry in results["probes"]:
        entry.pop("_code", None)

    print(json.dumps(results, indent=2))
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
