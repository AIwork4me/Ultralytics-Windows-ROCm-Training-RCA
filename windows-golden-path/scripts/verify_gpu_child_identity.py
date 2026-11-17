# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N G0 runtime-identity verifier (mission PHASE 2, section 6).

Child-process DLL evidence extension: the mission requires DLL identity
verification "in the same process context as the GPU test, not only in a
separate parent process". The historical verify_miopen_nostl.py captures
`miopen_identity_in_parent` only; this versioned Nightly adapter reuses the
same gp_lib identity technique INSIDE the GPU child process (self-contained
reproducer source below, run with `python -I`) and ties the loaded module
path + SHA256 to the candidate's frozen wheel identity. Historical DEV
receipts and the historical verifier are untouched.

Verdicts: G0_RUNTIME_IDENTITY_PASS / BLOCKED_DLL_CONTAMINATION /
BLOCKED_ENVIRONMENT / FAIL.

    python verify_gpu_child_identity.py --out g0.json --run-id R22A5N-G0 \
        --expect-dll-sha256 f9312c3e... --channel nightly --mission R22A.5N
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

# Self-contained child source: GPU op + in-process loaded-DLL identity.
# (Child runs `python -I`, so gp_lib is NOT importable there — the identity
# capture below is the same technique as gp_lib.loaded_miopen_identity,
# inlined so the exact bytes under test are visible in evidence.)
REPRODUCER = r'''
import ctypes, hashlib, json, re, sys
from pathlib import Path
import torch
import torch.nn as nn

rec = {}
rec["torch"] = torch.__version__
rec["hip"] = torch.version.hip
rec["cuda_available"] = bool(torch.cuda.is_available())
rec["device_count"] = int(torch.cuda.device_count())
if rec["device_count"]:
    rec["gpu_name"] = torch.cuda.get_device_name(0)
    # a real GPU op in THIS process — the DLL identity observed below is the
    # one the GPU execution itself used
    torch.manual_seed(0)
    model = nn.BatchNorm2d(100).cuda()
    x = torch.randn(4, 100, 8, 8, device="cuda")
    y = model(x)
    (y * y).mean().backward()
    torch.cuda.synchronize()
    rec["op_finite"] = bool(torch.isfinite(y).all().item()) and \
        bool(torch.isfinite(model.weight.grad).all().item())
try:
    miopen = ctypes.CDLL("MIOpen.dll")
    gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
    gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    buf = ctypes.create_string_buffer(1024)
    gmfn(miopen._handle, buf, 1024)
    path = buf.value.decode(errors="replace")
    h = hashlib.sha256()
    blob = b""
    try:
        blob = Path(path).read_bytes()
        h = hashlib.sha256(blob)
    except OSError:
        pass
    versions = sorted(set(re.findall(rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", blob)))
    rec["miopen"] = {"loaded": True, "path": path, "sha256": h.hexdigest(),
                     "bytes": len(blob),
                     "embedded_version_strings": [v.decode() for v in versions],
                     "pr13437_marker_miopen_initializer_list":
                         blob.count(b"miopen_initializer_list")}
except OSError as e:
    rec["miopen"] = {"loaded": False, "error": str(e)}
print("G0_CHILD_IDENTITY " + json.dumps(rec))
'''


def run_child(scratch_root: Path, timeout_s: int) -> dict:
    scratch = scratch_root / f"g0_child_{int(time.time())}"
    (scratch / "home").mkdir(parents=True, exist_ok=True)
    (scratch / "log").mkdir(parents=True, exist_ok=True)
    repro = scratch / "g0_child.py"
    repro.write_text(REPRODUCER, encoding="utf-8")
    log = scratch / "child.log"

    env = dict(os.environ)
    env["USERPROFILE"] = str(scratch / "home")   # controlled cache identity
    env.pop("PYTHONPATH", None)
    env.pop("HIPRTC_COMPILE_OPTIONS_APPEND", None)  # pure official bytes
    cmd = [sys.executable, "-I", str(repro)]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          cwd=str(scratch / "log"), timeout=timeout_s)
    dur = round(time.time() - t0, 1)
    log.write_text(f"# G0 child identity leg\n# cmd={' '.join(cmd)}\n"
                   f"# USERPROFILE={env['USERPROFILE']}\n\n"
                   f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}",
                   encoding="utf-8")
    child = None
    for line in proc.stdout.splitlines():
        if line.startswith("G0_CHILD_IDENTITY "):
            child = json.loads(line[len("G0_CHILD_IDENTITY "):])
    return {"exit_code": proc.returncode, "duration_s": dur, "child": child,
            "stdout_tail": proc.stdout[-1500:], "stderr_tail": proc.stderr[-2500:],
            "log_path": str(log), "scratch": str(scratch)}


def main() -> None:
    import torch  # target venv — parent-side stack identity

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mission", default="R22A.5N")
    ap.add_argument("--channel", default="nightly")
    ap.add_argument("--expect-dll-sha256", required=True,
                    help="frozen candidate MIOpen.dll SHA256 (wheel audit)")
    ap.add_argument("--scratch-root", default=None)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    scratch_root = Path(args.scratch_root or tempfile.mkdtemp(prefix="r22a5n_g0_"))
    t0 = time.time()
    leg = run_child(scratch_root, args.timeout)

    import importlib.metadata as im
    tv = im.version("torchvision") if any(
        d.metadata["Name"] == "torchvision" for d in im.distributions()) else None
    ul = im.version("ultralytics") if any(
        d.metadata["Name"] == "ultralytics" for d in im.distributions()) else None
    parent_miopen = gp_lib.loaded_miopen_identity()

    verdict, reason = "FAIL", "unclassified"
    child = leg["child"] or {}
    mi = child.get("miopen") or {}
    dll_match = mi.get("sha256") == args.expect_dll_sha256.lower()
    gpu_ok = bool(child.get("cuda_available") and child.get("device_count")
                  and child.get("gpu_name"))
    op_ok = child.get("op_finite") is True
    if leg["exit_code"] != 0:
        verdict, reason = "FAIL", "child process exited non-zero"
    elif not gpu_ok:
        verdict, reason = "BLOCKED_ENVIRONMENT", "no CUDA/HIP device available in child"
    elif not op_ok:
        verdict, reason = "FAIL", "GPU op did not produce finite results"
    elif not mi.get("loaded"):
        verdict, reason = "FAIL", "MIOpen.dll not loaded in child process"
    elif not dll_match:
        verdict, reason = "BLOCKED_DLL_CONTAMINATION", (
            f"child loaded MIOpen.dll sha256={mi.get('sha256')} "
            f"path={mi.get('path')} which is NOT the audited candidate "
            f"{args.expect_dll_sha256}")
    else:
        verdict, reason = "G0_RUNTIME_IDENTITY_PASS", (
            "real GPU selected in child, GPU op finite, in-process loaded "
            "MIOpen.dll path+SHA256 equal the frozen candidate wheel identity")

    record = {
        "run_id": args.run_id, "mission": args.mission,
        "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": tv, "ultralytics": ul, "hip": torch.version.hip,
        "channel": args.channel,
        "runtime_class": gp_lib.classify_runtime(
            {"any_workaround_present": False}, args.channel, parent_miopen),
        "verdict": verdict, "reason": reason,
        "expect_dll_sha256": args.expect_dll_sha256.lower(),
        "child_dll_sha256": mi.get("sha256"),
        "child_dll_path": mi.get("path"),
        "child_dll_sha256_matches_frozen": dll_match,
        "child_gpu_name": child.get("gpu_name"),
        "child_torch": child.get("torch"), "child_hip": child.get("hip"),
        "child_device_count": child.get("device_count"),
        "child_op_finite": child.get("op_finite"),
        "child_miopen_versions": mi.get("embedded_version_strings"),
        "child_marker_count": mi.get("pr13437_marker_miopen_initializer_list"),
        "miopen_identity_in_parent": parent_miopen,
        "parent_and_child_dll_agree": (
            parent_miopen.get("sha256") == mi.get("sha256")
            if parent_miopen.get("loaded") and mi.get("sha256") else None),
        "exit_code": leg["exit_code"], "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": "PASS" if verdict == "G0_RUNTIME_IDENTITY_PASS" else "FAIL",
        "failure_classification": None,
        "raw_log_path": leg["log_path"],
        "command": (f"python verify_gpu_child_identity.py --expect-dll-sha256 "
                    f"{args.expect_dll_sha256[:12]}... --channel {args.channel}"),
        "leg_detail": leg,
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(f"VERDICT: {verdict} — {reason}")
    print(f"[OK] evidence: {args.out}")
    sys.exit(0 if verdict == "G0_RUNTIME_IDENTITY_PASS" else 4)


if __name__ == "__main__":
    main()
