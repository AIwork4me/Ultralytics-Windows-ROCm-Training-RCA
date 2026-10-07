"""Gate L16: determine WHICH STL HIPRTC actually resolves on Linux.

Two layers of evidence:
1. Driver-level: wheel amdclang++ verbose preprocessing probe → C++ include
   search paths (SUPPORTING evidence only).
2. HIPRTC-level: compile `#include <type_traits>` with clang's -H include
   trace passed through hiprtcCompileProgram options, and read the resolved
   header path back from the program log. This is DIRECT evidence of what
   HIPRTC resolves internally.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SP = Path(sys.prefix) / "lib" / "python3.13" / "site-packages"
CORE_LIB = SP / "_rocm_sdk_core" / "lib"
DEVEL_CLANG = SP / "_rocm_sdk_devel" / "lib" / "llvm" / "bin" / "amdclang++"
CORE_LLVM_INC = SP / "_rocm_sdk_core" / "lib" / "llvm" / "include" / "c++"

ARCH = "gfx1151"

SRC = "#include <type_traits>\n" '\nextern "C" __global__\n' "void probe(int* out)\n{\n    using T = std::remove_reference<int&>::type;\n    *out = (int)sizeof(T);\n}\n"


def driver_search_paths() -> dict:
    """amdclang++ -E -v on a .cu file: capture '#include <...>' search paths."""
    out = {}
    for label, extra in [
        ("host_cpp", []),  # host-style compile: g++-mode search list
        ("hip_offload", ["--offload-arch=gfx1151", "-x", "hip"]),
    ]:
        try:
            r = subprocess.run(
                [str(DEVEL_CLANG), "-E", "-v", *extra, "-"],
                input="#include <type_traits>\nint x;\n",
                capture_output=True, text=True, timeout=120,
            )
            err = r.stderr
            search = []
            grab = False
            for line in err.splitlines():
                if line.startswith("#include <"):
                    grab = True
                    continue
                if grab:
                    if line.strip() == "End of search list.":
                        grab = False
                    else:
                        search.append(line.strip())
            out[label] = {
                "returncode": r.returncode,
                "search_list": search,
                "stderr_tail": err[-2000:],
            }
        except Exception as e:  # noqa: BLE001
            out[label] = {"error": str(e)}
    return out


def hiprtc_include_trace() -> dict:
    """Compile with -H and read the include trace from the program log."""
    hiprtc = ctypes.CDLL(str(CORE_LIB / "libhiprtc.so.7"))
    prog = ctypes.c_void_p()
    r_create = hiprtc.hiprtcCreateProgram(
        ctypes.byref(prog), SRC.encode(), b"probe.cu", 0, None, None
    )
    if r_create != 0:
        return {"rtc_create": r_create}
    opts = [
        f"--gpu-architecture={ARCH}".encode(),
        b"-H",
    ]
    arr = (ctypes.c_char_p * len(opts))(*opts)
    r_compile = hiprtc.hiprtcCompileProgram(prog, len(opts), arr)
    log_size = ctypes.c_size_t(0)
    hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(log_size))
    buf = ctypes.create_string_buffer(max(log_size.value, 1))
    hiprtc.hiprtcGetProgramLog(prog, buf)
    log = buf.value.decode(errors="replace")
    hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))
    return {"rtc_compile": r_compile, "log": log}


def main() -> int:
    result = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "amdclang": str(DEVEL_CLANG),
        "wheel_libcxx": str(CORE_LLVM_INC),
        "wheel_libcxx_exists": CORE_LLVM_INC.is_dir(),
        "driver_probe": driver_search_paths(),
        "hiprtc_trace": hiprtc_include_trace(),
    }
    with open(
        Path(__file__).resolve().parents[3]
        / "evidence" / "phase3" / "raw" / "linux" / "hiprtc" / "which_stl.json",
        "w",
    ) as f:
        json.dump(result, f, indent=2)
    # human summary on stdout
    print("amdclang:", result["amdclang"])
    print("wheel libc++ dir exists:", result["wheel_libcxx_exists"], result["wheel_libcxx"])
    for mode, info in result["driver_probe"].items():
        print(f"\n--- driver search list ({mode}) rc={info.get('returncode')} ---")
        for p in info.get("search_list", []):
            print("  ", p)
    print("\n--- hiprtc -H trace (log excerpt) ---")
    print(result["hiprtc_trace"].get("log", "(empty)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
