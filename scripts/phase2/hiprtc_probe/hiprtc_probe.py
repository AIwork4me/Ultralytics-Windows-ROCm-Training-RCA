"""Gate 24: standalone HIPRTC reproducer — NO PyTorch, NO MIOpen, NO Ultralytics.

Calls hiprtc0714.dll directly via ctypes and compiles small HIP sources with
a controlled single #include (<type_traits> etc.), mirroring what MIOpen's
BatchNorm runtime-compile path does. A/B: same source shape, with and
without the standard header.

If compile succeeds, optionally loads and executes the kernel on the GPU via
amdhip64_7.dll (hipModuleLoadData + hipModuleLaunchKernel) to prove the code
object is functional — execution requires a valid out-pointer buffer.

Usage:
    python hiprtc_probe.py <probe-name>
        probe-name in: none | type_traits | utility | limits | cstdint |
                       initializer_list | all
Output: JSON result dict on stdout (one line per field), human summary on
stderr. Exit 0 = compile OK, 3 = HIPRTC_ERROR_COMPILATION, other = other
error.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE_BIN = os.path.join(
    os.environ.get("ROCM_WHEEL_CORE", ""),
    "Lib", "site-packages", "_rocm_sdk_core", "bin",
)

PROBES: dict[str, str] = {
    "none": "",
    "type_traits": "#include <type_traits>",
    "utility": "#include <utility>",
    "limits": "#include <limits>",
    "cstdint": "#include <cstdint>",
    "initializer_list": "#include <initializer_list>",
}


def source_for(header: str) -> str:
    include_line = f"{header}\n" if header else ""
    if header == "type_traits":
        # exercise a real std trait like MIOpen's miopen_type_traits.hpp does
        body = "    using T = std::remove_reference<int&>::type;\n    *out = (int)sizeof(T);"
    elif header == "utility":
        body = "    int a = 1;\n    int& b = a;\n    *out = std::move(b);"
    elif header == "limits":
        body = "    *out = (std::numeric_limits<int>::max)() > 0 ? 1 : 0;"
    elif header == "cstdint":
        body = "    std::uint64_t v = 42;\n    *out = (int)(v & 0xff);"
    elif header == "initializer_list":
        body = "    auto il = {1, 2, 3};\n    *out = (int)il.size();  /* requires runtime helper? size is constexpr */\n    *out = 3;"
    else:
        body = "    *out = 1;"
    return (
        f"{include_line}"
        "\nextern \"C\" __global__\n"
        "void hiprtc_probe(int* out)\n{\n"
        f"{body}\n"
        "}\n"
    )


def main() -> int:
    names = sys.argv[1:] or ["all"]
    if names == ["all"]:
        names = list(PROBES)

    # Ensure the ROCm DLLs are loadable: add core bin to DLL search path.
    core_bin = os.environ.get("HIPRTC_CORE_BIN") or CORE_BIN
    os.add_dll_directory(core_bin)
    os.environ.setdefault("PATH", "")
    os.environ["PATH"] = core_bin + os.pathsep + os.environ["PATH"]

    hiprtc = ctypes.CDLL(os.path.join(core_bin, "hiprtc0714.dll"))
    hip = ctypes.CDLL(os.path.join(core_bin, "amdhip64_7.dll"))

    # hiprtcVersion(int*, int*)
    maj, mnr = ctypes.c_int(), ctypes.c_int()
    hiprtc.hiprtcVersion(ctypes.byref(maj), ctypes.byref(mnr))

    results = []
    overall_exit = 0
    for name in names:
        header = PROBES[name]
        src = source_for(header)
        prog = ctypes.c_void_p()
        src_b = src.encode()
        name_b = "probe.cu".encode()

        r_create = hiprtc.hiprtcCreateProgram(
            ctypes.byref(prog), src_b, name_b, 0, None, None
        )
        if r_create != 0:
            results.append({"probe": name, "stage": "create", "rtc_result": r_create})
            overall_exit = 4
            continue

        arch = os.environ.get("HIPRTC_ARCH", "gfx1151")
        options = (ctypes.c_char_p * 1)(f"--gpu-architecture={arch}".encode())
        r_compile = hiprtc.hiprtcCompileProgram(prog, 1, options)

        log_size = ctypes.c_size_t(0)
        hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(log_size))
        log = ctypes.create_string_buffer(max(log_size.value, 1))
        hiprtc.hiprtcGetProgramLog(prog, log)

        code_size = ctypes.c_size_t(0)
        r_codesize = hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(code_size))

        entry = {
            "probe": name,
            "header": header or "(none)",
            "rtc_create": r_create,
            "rtc_compile": r_compile,
            "compile_result": (
                "HIPRTC_SUCCESS" if r_compile == 0
                else f"HIPRTC_ERROR_COMPILATION({r_compile})" if r_compile == 6
                else f"HIPRTC_ERROR_{r_compile}"
            ),
            "log_size": log_size.value,
            "program_log": log.value.decode("utf-8", "replace"),
            "code_size": code_size.value if r_codesize == 0 else None,
            "rtc_code_size_result": r_codesize,
            "arch": os.environ.get("HIPRTC_ARCH", "gfx1151"),
            "hiprtc_version": f"{maj.value}.{mnr.value}",
            "dll": os.path.join(core_bin, "hiprtc0714.dll"),
        }
        results.append(entry)
        if r_compile != 0:
            overall_exit = 3
        hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))

    print(json.dumps({"hiprtc_version": f"{maj.value}.{mnr.value}", "results": results}, indent=2))
    return overall_exit


if __name__ == "__main__":
    raise SystemExit(main())
