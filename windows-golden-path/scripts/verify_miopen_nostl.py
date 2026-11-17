# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""MIOpen #13437 no-host-STL regression verifier (mission §6).

Implements the ACTUAL regression: BatchNorm2d(100) at the historically failing
shape (20, 100, 35, 45), forward + loss + backward + synchronize + finite
checks, in a child process where host MSVC STL headers are UNREACHABLE.

Technique (reused unchanged from P14/P16 RCA, validated in the C+D mission):
  VCToolsInstallDir -> empty scratch dir   (cl.exe STL include tree unreachable)
  INCLUDE = ""                             (no system include leakage)
  USERPROFILE -> fresh scratch home        (cold MIOpen cache per leg)
Only the CHILD process environment is modified — global toolchains untouched.

Legs (run each in a fresh process):
  --leg official     no HIPRTC shim  → expect the #3956 signature on pre-fix wheels
  --leg engineering  HIPRTC shim kept (from ambient env) → reference PASS

Classifications: OFFICIAL_PRE_FIX_EXPECTED_FAIL / ENGINEERING_REFERENCE_PASS /
OFFICIAL_CANDIDATE_PASS / OFFICIAL_STABLE_PASS / BLOCKED_ENVIRONMENT / INCONCLUSIVE.
A pre-fix leg that unexpectedly PASSES is reported (possible hidden host STL or
cached kernels) — never silently discarded.

    python verify_miopen_nostl.py --out result.json --run-id R21-D [--leg official]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

# The reproducer run inside the child process (kept as source so the exact
# bytes under test are visible in evidence; written to scratch at run time).
# R22A.5N.1 §6.4: the child ALSO reports the loaded MIOpen.dll identity from
# inside the executing process (parent-process capture alone is insufficient —
# the DLL that matters is the one the BatchNorm operation itself used).
REPRODUCER = r'''
import ctypes, hashlib, json, sys
from pathlib import Path
import torch
import torch.nn as nn


def miopen_identity():
    """In-process loaded MIOpen.dll identity. Captured PRE-OP as well: a
    pre-fix child dies inside the BatchNorm HIPRTC compile, so a post-op-only
    capture would never run on exactly the legs that must prove their DLL."""
    try:
        miopen = ctypes.CDLL("MIOpen.dll")
        gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
        gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        buf = ctypes.create_string_buffer(1024)
        gmfn(miopen._handle, buf, 1024)
        path = buf.value.decode(errors="replace")
        blob = Path(path).read_bytes()
        return {"loaded": True, "path": path,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
                "pr13437_marker_miopen_initializer_list":
                    blob.count(b"miopen_initializer_list")}
    except OSError as e:
        return {"loaded": False, "error": str(e)}


miopen_pre = miopen_identity()
print("BN_NOSTL_CHILD_MIOPEN_PRE " + json.dumps(miopen_pre))
try:
    torch.manual_seed(0)
    model = nn.BatchNorm2d(100).cuda()
    x = torch.randn(20, 100, 35, 45, device="cuda")
    y = model(x)
    loss = (y * y).mean()
    loss.backward()
    torch.cuda.synchronize()
except Exception:
    # the pre-fix legs die INSIDE the BatchNorm HIPRTC compile; capture the
    # loaded MIOpen identity at the moment of failure (torch has loaded it by
    # then — ctypes resolves the already-loaded module by name) BEFORE the
    # traceback unwinds, then let the failure propagate honestly
    miopen_fail = miopen_identity()
    print("BN_NOSTL_CHILD_MIOPEN_ATFAIL " + json.dumps(miopen_fail))
    raise
out_finite = bool(torch.isfinite(y).all().item())
grad_finite = bool(torch.isfinite(model.weight.grad).all().item()) and \
              bool(torch.isfinite(model.bias.grad).all().item())
miopen_post = miopen_identity()
print("BN_NOSTL_REPRO out_finite=%s grad_finite=%s loss=%.6f" %
      (out_finite, grad_finite, float(loss)))
print("BN_NOSTL_CHILD_MIOPEN " + json.dumps(
    {"pre_op": miopen_pre, "post_op": miopen_post}))
sys.exit(0 if (out_finite and grad_finite) else 1)
'''


def run_leg(leg: str, scratch_root: Path, timeout_s: int) -> dict:
    scratch = scratch_root / f"nostl_{leg}_{int(time.time())}"
    (scratch / "fakevc").mkdir(parents=True, exist_ok=True)
    (scratch / "home").mkdir(parents=True, exist_ok=True)
    (scratch / "log").mkdir(parents=True, exist_ok=True)
    repro = scratch / "bn_repro.py"
    repro.write_text(REPRODUCER, encoding="utf-8")
    log = scratch / "leg.log"

    env = dict(os.environ)
    env["USERPROFILE"] = str(scratch / "home")          # cold MIOpen cache identity
    env["MIOPEN_LOG_LEVEL"] = "4"
    env["VCToolsInstallDir"] = str(scratch / "fakevc")  # hide host MSVC STL
    env["INCLUDE"] = ""
    env.pop("PYTHONPATH", None)
    if leg == "official":
        env.pop("HIPRTC_COMPILE_OPTIONS_APPEND", None)  # NO shim: pure official bytes
    # leg == "engineering": keep ambient HIPRTC shim (disclosed workaround)

    cmd = [sys.executable, "-I", str(repro)]
    t0 = time.time()
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=env, cwd=str(scratch / "log"))
    child_pid = popen.pid
    try:
        so, se = popen.communicate(timeout=timeout_s)
        rc = popen.returncode
    except subprocess.TimeoutExpired:
        popen.kill()
        so, se = popen.communicate()
        rc = popen.returncode
    dur = round(time.time() - t0, 1)
    class _Proc:  # minimal shim preserving the historical downstream shape
        pass
    proc = _Proc()
    proc.returncode, proc.stdout, proc.stderr = rc, so, se
    log.write_text(f"# leg={leg}\n# cmd={' '.join(cmd)}\n"
                   f"# VCToolsInstallDir={env['VCToolsInstallDir']}\n"
                   f"# INCLUDE={env['INCLUDE']!r}\n"
                   f"# USERPROFILE={env['USERPROFILE']}\n"
                   f"# HIPRTC_COMPILE_OPTIONS_APPEND={env.get('HIPRTC_COMPILE_OPTIONS_APPEND')}\n\n"
                   f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}",
                   encoding="utf-8")
    child_miopen = pre = post = at_fail = None
    for line in proc.stdout.splitlines():
        try:
            if line.startswith("BN_NOSTL_CHILD_MIOPEN_PRE "):
                pre = json.loads(line[len("BN_NOSTL_CHILD_MIOPEN_PRE "):])
            elif line.startswith("BN_NOSTL_CHILD_MIOPEN_ATFAIL "):
                at_fail = json.loads(line[len("BN_NOSTL_CHILD_MIOPEN_ATFAIL "):])
            elif line.startswith("BN_NOSTL_CHILD_MIOPEN "):
                rec = json.loads(line[len("BN_NOSTL_CHILD_MIOPEN "):])
                pre = rec.get("pre_op") or pre
                post = rec.get("post_op")
        except ValueError:
            pass
    # authoritative in-child identity: post-op (op succeeded) → at-failure
    # (pre-fix legs die inside the BN HIPRTC compile; MIOpen is loaded by
    # then) → pre-op import-time attempt
    child_miopen = next((x for x in (post, at_fail, pre)
                         if (x or {}).get("loaded")), None)
    return {"leg": leg, "exit_code": proc.returncode, "duration_s": dur,
            "pid": child_pid, "child_miopen": child_miopen,
            "child_miopen_pre_op": pre, "child_miopen_at_failure": at_fail,
            "child_miopen_post_op": post,
            "stdout_tail": proc.stdout[-1500:], "stderr_tail": proc.stderr[-2500:],
            "log_path": str(log), "scratch": str(scratch)}


def classify(leg: str, exit_code: int, stderr: str, expect: str) -> tuple[str, str]:
    """(classification, failure_class) for one leg."""
    fc = gp_lib.classify_nostl_failure(stderr)
    if exit_code == 0:
        if leg == "engineering":
            return "ENGINEERING_REFERENCE_PASS", None
        if expect == "FAIL":
            return "INCONCLUSIVE", None  # pre-fix wheel unexpectedly passed — investigate
        return ("OFFICIAL_CANDIDATE_PASS" if expect == "CANDIDATE"
                else "OFFICIAL_STABLE_PASS"), None
    # non-zero exit
    if leg == "official" and expect == "FAIL" and fc == "MIOPEN_HIPRTC_COMPILATION":
        return "OFFICIAL_PRE_FIX_EXPECTED_FAIL", fc
    if leg == "engineering":
        return "INCONCLUSIVE", fc
    return "INCONCLUSIVE", fc


def main() -> None:
    import torch  # target venv; records provenance of the stack under test

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--leg", choices=["official", "engineering"], required=True)
    ap.add_argument("--expect", choices=["FAIL", "CANDIDATE", "STABLE"], default="FAIL",
                    help="official-leg expectation for the wheel under test")
    ap.add_argument("--channel", default=None,
                    help="stack channel (runtime classification of the official leg)")
    ap.add_argument("--scratch-root", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    scratch_root = Path(args.scratch_root or tempfile.mkdtemp(prefix="r21_nostl_"))
    t0 = time.time()
    leg = run_leg(args.leg, scratch_root, args.timeout)
    classification, failure_class = classify(args.leg, leg["exit_code"],
                                             leg["stderr_tail"], args.expect)
    ambient_shim = os.environ.get("HIPRTC_COMPILE_OPTIONS_APPEND")
    miopen_ident = gp_lib.loaded_miopen_identity()
    import importlib.metadata as im

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": ("ENGINEERING_REFERENCE" if args.leg == "engineering"
                          or ambient_shim
                          else gp_lib.classify_runtime(
                              {"any_workaround_present": False},  # child env: shim popped
                              args.channel, miopen_ident)),
        "command": f"python verify_miopen_nostl.py --leg {args.leg} --expect {args.expect}",
        "exit_code": leg["exit_code"], "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": ("PASS" if classification.endswith("_PASS")
                           else "EXPECTED_FAIL" if classification ==
                           "OFFICIAL_PRE_FIX_EXPECTED_FAIL" else "FAIL"),
        "failure_classification": failure_class,
        "raw_log_path": leg["log_path"],
        "classification": classification,
        "leg_detail": leg,
        "ambient_hiprtc_shim": ambient_shim,
        "reproducer_shape": [20, 100, 35, 45],
        "reproducer_op": "nn.BatchNorm2d(100) forward+backward",
        "expectation": args.expect,
        "miopen_identity_in_parent": miopen_ident,
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(f"CLASSIFICATION: {classification} (exit={leg['exit_code']}, "
          f"failure_class={failure_class})")
    print(f"[OK] evidence: {args.out}")


if __name__ == "__main__":
    main()
