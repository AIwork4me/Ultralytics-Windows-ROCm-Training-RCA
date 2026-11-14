"""G2 runner — orchestrates the per-task lifecycle: main stage, resume stage,
then an in-process loaded-DLL probe for GPU provenance.

Every invocation gets an immutable run_id; all outputs are keyed by
task_tag_runid so no run can overwrite another (mission §3.4):

    <raw-dir>/g2_{task}_{tag}_{run_id}.json
    <raw-dir>/g2_{task}_{tag}_{run_id}_{stage}.log
    <raw-dir>/g2_{task}_{tag}_{run_id}_probe.log
    <raw-dir>/g2_{task}_{tag}_{run_id}_loaddll.json

    python scripts/g2_runner.py --python <env-python> --task detect \
        --data coco8.yaml --weights yolo26n.pt --raw-dir ../raw \
        [--tag fp32] [--environment-id ENV_A_official] [--run-id <id>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def fail(msg: str) -> None:
    print(f"G2-RUNNER-FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--model-yaml", default=None)
    ap.add_argument("--infer-source", default=None)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--amp", default="False")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--tag", default="fp32", help="run tag (fp32 | amptrack | ...)")
    ap.add_argument("--environment-id", default="unknown",
                    help="declared environment identity, verified against in-process probe")
    ap.add_argument("--run-id", default=None, help="immutable run id (default: generated)")
    ap.add_argument("--lifecycle-args", default=None,
                    help="extra args passed to g2_lifecycle.py verbatim, e.g. "
                         "'--amp-updates-data coco128.yaml --amp-updates-epochs 10'")
    ap.add_argument("--probe-script", default=str(
        Path(__file__).resolve().parent.parent.parent / "release-provenance" / "scripts" / "probe_loaded_miopen.py"))
    ap.add_argument("--lifecycle-script", default=str(
        Path(__file__).resolve().parent.parent / "tests" / "g2_lifecycle.py"))
    args = ap.parse_args()

    raw = Path(args.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    rid = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"g2_{args.task}_{args.tag}_{rid}"
    out = raw / f"{base}.json"
    probe_out = raw / f"{base}_loaddll.json"
    for p in (out, probe_out):
        if p.exists():
            fail(f"immutable-output violation: {p.name} already exists — "
                 f"no run may overwrite a previous result; pass a new --run-id")

    header = (f"# run_id={rid} task={args.task} tag={args.tag} "
              f"environment_id={args.environment_id} amp={args.amp} "
              f"python={args.python} started_utc={datetime.now(timezone.utc).isoformat()}\n")

    stages = [("main", []), ("resume", [])]
    for stage, _ in stages:
        cmd = [args.python, args.lifecycle_script,
               "--task", args.task, "--data", args.data,
               "--weights", args.weights, "--imgsz", str(args.imgsz),
               "--workers", str(args.workers), "--amp", args.amp,
               "--run-id", rid, "--environment-id", args.environment_id,
               "--out", str(out), "--stage", stage]
        if args.model_yaml:
            cmd += ["--model-yaml", args.model_yaml]
        if args.infer_source:
            cmd += ["--infer-source", args.infer_source]
        if args.lifecycle_args:
            cmd += args.lifecycle_args.split()
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=7200)
        (raw / f"{base}_{stage}.log").write_text(
            header + f"# exit={proc.returncode}\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n",
            encoding="utf-8")
        print(f"[{args.task}/{stage}] exit={proc.returncode} "
              f"tail={proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else '(empty)'}")
        if proc.returncode != 0:
            fail(f"stage {stage} of {args.task} failed (exit={proc.returncode}); "
                 f"see {base}_{stage}.log")

    probe = subprocess.run([args.python, args.probe_script, "--out", str(probe_out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900)
    (raw / f"{base}_probe.log").write_text(
        header + f"# exit={probe.returncode}\n{probe.stdout}\n{probe.stderr}", encoding="utf-8")
    if probe.returncode != 0:
        fail(f"loaded-DLL probe failed for {args.task}")

    result = json.loads(out.read_text(encoding="utf-8"))
    miopen = json.loads(probe_out.read_text(encoding="utf-8"))["miopen_loaded"]
    result["loaded_dll"] = miopen
    result["runner_completed_utc"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    n_pass = sum(1 for t in result["tests"].values() if t["status"] == "PASS")
    n_skip = sum(1 for t in result["tests"].values() if t["status"] == "SKIP")
    print(f"VERDICT {args.task}: {n_pass}/{len(result['tests'])} PASS ({n_skip} SKIP, "
          f"SKIP≠PASS) miopen={miopen['sha256'][:12]} run_id={rid}")


if __name__ == "__main__":
    main()
