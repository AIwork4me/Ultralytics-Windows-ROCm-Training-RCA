"""Phase-3 Gate 57/59/63 workhorse: parameterized standalone HIPRTC canary.

Compiles (and optionally executes) HIP kernel sources through the wheel's
own hiprtc DLL via ctypes — no PyTorch, no MIOpen. Fixes Phase-2 Reviewer-C
finding B5 (hardcoded gfx1151/hiprtc0714.dll) by parameterizing
architecture, DLL, include dirs, defines, and -nostdinc.

Every invocation prints a JSON record with a provenance header (git HEAD of
the RCA repo, argv, DLL paths, SHA256s) so raw evidence is self-describing.

Usage examples:
  # compile+execute a freestanding-traits canary with no host STL:
  python hiprtc_canary.py --source canary_traits.hip --execute --expect 6 \
      --define MIOPEN_HIP_RUNTIME_COMPILE=1 --define HIP_PACKAGE_VERSION_FLAT=7140060850ULL \
      --include-dir <kernel include root> --nostdinc

  # header-availability probe (does <type_traits> resolve?):
  python hiprtc_canary.py --probe-include type_traits

Exit codes: 0 = compile(+execute) OK; 3 = HIPRTC_ERROR_COMPILATION;
4 = create failed; 5 = execution mismatch; 6 = runtime/load error.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import hashlib
import json
import os
import subprocess
import sys

PROBE_SRC_TEMPLATE = (
    "#include <{header}>\n"
    'extern "C" __global__\n'
    "void hiprtc_canary(int* out)\n{{\n    *out = 1;\n}}\n"
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo: str) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
            text=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def find_hiprtc_dll(core_bin: str) -> str:
    cands = sorted(f for f in os.listdir(core_bin)
                   if f.lower().startswith("hiprtc") and f.lower().endswith(".dll")
                   and "builtins" not in f.lower())
    if not cands:
        raise SystemExit(f"no hiprtc*.dll under {core_bin}")
    return os.path.join(core_bin, cands[0])


def find_hip_dll(core_bin: str) -> str:
    cands = sorted(f for f in os.listdir(core_bin)
                   if f.lower().startswith("amdhip64") and f.lower().endswith(".dll"))
    if not cands:
        raise SystemExit(f"no amdhip64*.dll under {core_bin}")
    return os.path.join(core_bin, cands[0])


def compile_source(hiprtc, src: str, name: str, options: list[str]) -> dict:
    prog = ctypes.c_void_p()
    src_b = src.encode()
    name_b = name.encode()
    r_create = hiprtc.hiprtcCreateProgram(
        ctypes.byref(prog), src_b, name_b, 0, None, None)
    if r_create != 0:
        return {"stage": "create", "rtc_result": r_create}

    opts = (ctypes.c_char_p * len(options))(*[o.encode() for o in options])
    r_compile = hiprtc.hiprtcCompileProgram(prog, len(options), opts)

    log_size = ctypes.c_size_t(0)
    hiprtc.hiprtcGetProgramLogSize(prog, ctypes.byref(log_size))
    log = ctypes.create_string_buffer(max(log_size.value, 1))
    hiprtc.hiprtcGetProgramLog(prog, log)

    code_size = ctypes.c_size_t(0)
    r_codesize = hiprtc.hiprtcGetCodeSize(prog, ctypes.byref(code_size))
    code = None
    if r_compile == 0 and r_codesize == 0 and code_size.value > 0:
        code = ctypes.create_string_buffer(code_size.value)
        if hiprtc.hiprtcGetCode(prog, code) != 0:
            code = None

    out = {
        "rtc_create": r_create,
        "rtc_compile": r_compile,
        "compile_result": ("HIPRTC_SUCCESS" if r_compile == 0
                           else f"HIPRTC_ERROR_COMPILATION({r_compile})"
                           if r_compile == 6 else f"HIPRTC_ERROR_{r_compile}"),
        "program_log": log.value.decode("utf-8", "replace"),
        "code_size": code_size.value if r_codesize == 0 else None,
        "_code_buf": code,
    }
    hiprtc.hiprtcDestroyProgram(ctypes.byref(prog))
    return out


def execute_code_object(hip, code_buf, kernel: str, expect: int) -> dict:
    if hip.hipInit(0) != 0:
        return {"exec": "hipInit failed"}
    dev = ctypes.c_int()
    hip.hipGetDevice(ctypes.byref(dev))
    d_out = ctypes.c_void_p()
    if hip.hipMalloc(ctypes.byref(d_out), ctypes.c_size_t(8)) != 0:
        return {"exec": "hipMalloc failed"}
    hip.hipMemset(d_out, 0, ctypes.c_size_t(8))
    module = ctypes.c_void_p()
    if hip.hipModuleLoadData(ctypes.byref(module), code_buf) != 0:
        return {"exec": "hipModuleLoadData failed"}
    fn = ctypes.c_void_p()
    if hip.hipModuleGetFunction(ctypes.byref(fn), module, kernel.encode()) != 0:
        return {"exec": f"hipModuleGetFunction({kernel}) failed"}
    args_buf = (ctypes.c_void_p * 1)(
        ctypes.cast(ctypes.byref(d_out), ctypes.c_void_p).value)
    if hip.hipModuleLaunchKernel(
            fn, 1, 1, 1, 1, 1, 1, 0, ctypes.c_void_p(), args_buf, None) != 0:
        return {"exec": "hipModuleLaunchKernel failed"}
    hip.hipDeviceSynchronize()
    host = ctypes.c_int64(-1)
    if hip.hipMemcpy(ctypes.byref(host), d_out, ctypes.c_size_t(8), 4) != 0:
        return {"exec": "hipMemcpy failed"}
    return {"exec": "PASS" if host.value == expect else
            f"MISMATCH(got {host.value}, want {expect})",
            "exec_value": host.value, "exec_expect": expect}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--core-bin", default=os.path.join(
        os.environ.get("ROCM_WHEEL_CORE",
                       r"C:\Users\rocm\miniconda3\envs\yolo_amd"),
        "Lib", "site-packages", "_rocm_sdk_core", "bin"))
    ap.add_argument("--arch", default=os.environ.get("HIPRTC_ARCH", "gfx1151"))
    ap.add_argument("--source", help="HIP C++ source file to compile")
    ap.add_argument("--probe-include", metavar="HEADER",
                    help="compile a trivial TU that only includes HEADER")
    ap.add_argument("--kernel", default="hiprtc_canary")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--expect", type=int, default=1)
    ap.add_argument("--include-dir", action="append", default=[])
    ap.add_argument("--define", action="append", default=[],
                    help="extra -D (raw, e.g. FOO=1)")
    ap.add_argument("--nostdinc", action="store_true")
    ap.add_argument("--extra-opt", action="append", default=[])
    ap.add_argument("--label", default="")
    ap.add_argument("--out-json", help="append JSON record to this file")
    args = ap.parse_args()

    if not args.source and not args.probe_include:
        ap.error("need --source or --probe-include")

    core_bin = os.path.abspath(args.core_bin)
    hiprtc_dll = find_hiprtc_dll(core_bin)
    hip_dll = find_hip_dll(core_bin)
    os.add_dll_directory(core_bin)
    os.environ["PATH"] = core_bin + os.pathsep + os.environ.get("PATH", "")
    hiprtc = ctypes.CDLL(hiprtc_dll)
    hip = ctypes.CDLL(hip_dll)

    maj, mnr = ctypes.c_int(), ctypes.c_int()
    hiprtc.hiprtcVersion(ctypes.byref(maj), ctypes.byref(mnr))

    if args.probe_include:
        src = PROBE_SRC_TEMPLATE.format(header=args.probe_include)
        name = f"probe_{args.probe_include.replace('/', '_')}.cu"
        sha = None
    else:
        with open(args.source, "r", encoding="utf-8") as f:
            src = f.read()
        name = os.path.basename(args.source)
        sha = sha256_file(args.source)

    options = [f"--gpu-architecture={args.arch}"]
    for d in args.include_dir:
        options.append(f"-I{os.path.abspath(d)}")
    for dfn in args.define:
        options.append(f"-D{dfn}")
    if args.nostdinc:
        options.append("-nostdinc")
    options.extend(args.extra_opt)

    res = compile_source(hiprtc, src, name, options)
    code_buf = res.pop("_code_buf", None)
    record = {
        "provenance": {
            "timestamp": datetime.datetime.now().isoformat(),
            "rca_git_head": git_head(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))),
            "argv": sys.argv[1:],
            "hiprtc_dll": hiprtc_dll,
            "hiprtc_dll_sha256": sha256_file(hiprtc_dll),
            "hip_dll": hip_dll,
            "hiprtc_version": f"{maj.value}.{mnr.value}",
            "source_sha256": sha,
        },
        "label": args.label or name,
        "options": options,
        **res,
    }

    exit_code = 0
    if res["rtc_compile"] != 0:
        exit_code = 3
    elif args.execute:
        if code_buf is None:
            record["exec"] = "no code object"
            exit_code = 6
        else:
            exec_res = execute_code_object(hip, code_buf, args.kernel, args.expect)
            record.update(exec_res)
            if exec_res.get("exec") != "PASS":
                exit_code = 5 if "MISMATCH" in exec_res.get("exec", "") else 6

    print(json.dumps(record, indent=2))
    if args.out_json:
        with open(args.out_json, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
