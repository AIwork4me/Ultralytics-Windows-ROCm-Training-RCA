"""G2 runner — orchestrates the per-task lifecycle: main stage, resume stage,
then an in-process loaded-DLL probe for GPU provenance.

    python scripts/g2_runner.py --python <env-python> --task detect --data coco8.yaml \
        --weights yolo26n.pt --raw-dir ../raw [--workdir ..]
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
    ap.add_argument("--probe-script", default=str(
        Path(__file__).resolve().parent.parent.parent / "release-provenance" / "scripts" / "probe_loaded_miopen.py"))
    ap.add_argument("--lifecycle-script", default=str(
        Path(__file__).resolve().parent.parent / "tests" / "g2_lifecycle.py"))
    args = ap.parse_args()

    raw = Path(args.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    out = raw / f"g2_{args.task}_fp32.json"
    probe_out = raw / f"g2_{args.task}_loaddll.json"
    stages = [("main", []), ("resume", [])]
    for stage, _ in stages:
        cmd = [args.python, args.lifecycle_script,
               "--task", args.task, "--data", args.data,
               "--weights", args.weights, "--imgsz", str(args.imgsz),
               "--workers", str(args.workers), "--amp", args.amp,
               "--out", str(out), "--stage", stage]
        if args.model_yaml:
            cmd += ["--model-yaml", args.model_yaml]
        if args.infer_source:
            cmd += ["--infer-source", args.infer_source]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=3600)
        (raw / f"g2_{args.task}_{stage}.log").write_text(
            f"# exit={proc.returncode}\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n",
            encoding="utf-8")
        print(f"[{args.task}/{stage}] exit={proc.returncode} "
              f"tail={proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else '(empty)'}")
        if proc.returncode != 0:
            fail(f"stage {stage} of {args.task} failed (exit={proc.returncode}); "
                 f"see g2_{args.task}_{stage}.log")

    probe = subprocess.run([args.python, args.probe_script, "--out", str(probe_out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900)
    (raw / f"g2_{args.task}_probe.log").write_text(
        f"# exit={probe.returncode}\n{probe.stdout}\n{probe.stderr}", encoding="utf-8")
    if probe.returncode != 0:
        fail(f"loaded-DLL probe failed for {args.task}")

    result = json.loads(out.read_text(encoding="utf-8"))
    result["loaded_dll"] = json.loads(probe_out.read_text(encoding="utf-8"))["miopen_loaded"]
    result["runner_completed_utc"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    n_pass = sum(1 for t in result["tests"].values() if t["status"] == "PASS")
    print(f"VERDICT {args.task}: {n_pass}/{len(result['tests'])} PASS "
          f"miopen={result['loaded_dll']['sha256'][:12]}")


if __name__ == "__main__":
    main()
