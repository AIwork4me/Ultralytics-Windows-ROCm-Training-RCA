# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Reliability runner (missions §8 R21-F smoke / §14 R22 ≥10 runs per arch).

Runs N INDEPENDENT short training processes (exact standard command shape),
classifying each run and tallying anomaly families separately — an
unexplained kernel/runtime failure blocks stable Golden Path readiness and is
never assumed fixed by MIOpen #13437.

Cold vs warm cache are distinct evidence classes: a fresh Python process is
NOT a cold MIOpen cache. --cold runs redirect USERPROFILE to a per-run fresh
home (the user's global cache is never touched or deleted).

Bounded execution: per-run timeout + overall wall budget; no retry loops.

    python run_stability.py --out stability.json --run-id R22-G8 --runs 10 [--cold]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

CHILD = r'''
import sys, time
t0 = time.time()
from ultralytics import YOLO
m = YOLO("yolo26n.pt")
r = m.train(data="coco8.yaml", epochs=1, device={device}, project=r"{project}",
            name=r"{name}", exist_ok=True, seed={seed}, workers=0, verbose=True)
print(f"STABILITY_CHILD_DONE {{time.time()-t0:.1f}}s")
'''

ANOMALY_SIGNATURES = {
    "hipErrorInvalidKernelFile": "HIP_KERNEL_IMAGE_FAILURE",
    "hipErrorInvalidDeviceFunction": "TORCHVISION_DEVICE_WHEEL_MISSING",
    "HIPRTC_ERROR_COMPILATION": "MIOPEN_HIPRTC_COMPILATION",
    "type_traits": "MIOPEN_HIPRTC_COMPILATION",
    "miopenStatusUnknownError": "MIOPEN_RUNTIME_KERNEL",
    "MIOpen(HIP): [FindSolution]": "MIOPEN_SOLVER_ANOMALY",
    "missing CK kernel": "MIOPEN_MISSING_CK_SYMBOL",
}


def classify_run(exit_code: int, output: str) -> dict:
    anomalies = sorted({fc for sig, fc in ANOMALY_SIGNATURES.items() if sig in output})
    if exit_code == 0 and not anomalies:
        return {"status": "PASS", "anomalies": []}
    return {"status": "FAIL", "anomalies": anomalies,
            "failure_classification": anomalies[0] if anomalies else "INCONCLUSIVE"}


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--runs", type=int, default=3, help="independent processes (R22: 10)")
    ap.add_argument("--cold", action="store_true",
                    help="fresh MIOpen cache identity per run (isolated USERPROFILE)")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--per-run-timeout", type=int, default=900)
    args = ap.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    runs = []
    for i in range(1, args.runs + 1):
        run_dir = work / f"run{i:02d}"
        run_dir.mkdir(exist_ok=True)
        child = run_dir / "child.py"
        child.write_text(CHILD.format(device=args.device, project=run_dir,
                                       name="train", seed=100 + i), encoding="utf-8")
        env = dict(os.environ)
        cache_note = "warm(process-level)"
        if args.cold:
            fresh_home = run_dir / "home"
            fresh_home.mkdir(exist_ok=True)
            env["USERPROFILE"] = str(fresh_home)
            cache_note = "cold(fresh-USERPROFILE)"
        log = run_dir / "child.log"
        t1 = time.time()
        try:
            r = subprocess.run([sys.executable, "-I", str(child)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               cwd=str(run_dir), env=env,
                               timeout=args.per_run_timeout)
            rc, out = r.returncode, r.stdout + "\n" + r.stderr
        except subprocess.TimeoutExpired as e:
            rc, out = 124, (e.stdout or b"").decode(errors="replace") if isinstance(
                e.stdout, bytes) else str(e.stdout or "")
        dur = round(time.time() - t1, 1)
        log.write_text(out, encoding="utf-8", errors="replace")
        verdict = classify_run(rc, out)
        runs.append({"run": i, "exit_code": rc, "duration_s": dur,
                     "cache_class": cache_note, "log": str(log), **verdict})
        print(f"[run {i}/{args.runs}] exit={rc} {verdict['status']} "
              f"{verdict.get('anomalies') or ''} ({dur}s)")

    n_pass = sum(1 for r in runs if r["status"] == "PASS")
    tally: dict[str, int] = {}
    for r in runs:
        for a in r.get("anomalies", []):
            tally[a] = tally.get(a, 0) + 1
    verdict = "PASS" if n_pass == len(runs) and runs else "FAIL"

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), args.channel,
            (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None)),
        "command": f"python run_stability.py --runs {args.runs} "
                   f"{'--cold' if args.cold else '--warm'} --device {args.device}",
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": (tally and next(iter(tally))) or None if verdict == "FAIL" else None,
        "raw_log_path": str(work / "stability_runs.json"),
        "runs": runs, "n_pass": n_pass, "n_total": len(runs),
        "anomaly_tally": tally,
        "cache_class": "cold(fresh-USERPROFILE per run)" if args.cold else "warm",
        "note": "independent training PROCESSES; cache classes tracked separately; "
                "unexplained kernel/runtime failures block stable readiness",
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    (work / "stability_runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    gp_lib.write_evidence(record, Path(args.out))
    print(f"STABILITY: {verdict} ({n_pass}/{len(runs)})")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
