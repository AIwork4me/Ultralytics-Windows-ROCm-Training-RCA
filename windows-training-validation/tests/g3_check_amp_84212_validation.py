"""G3.9 — validate the NEW upstream check_amp (8.4.197+, PR #26967) on gfx1151.

    python tests/g3_check_amp_84212_validation.py --out ../raw/g3_checkamp84212_<env>.json \
        --python <env-python> --environment-id ENV_X --ultralytics-src <clone-path>

Upstream redesigned check_amp in 8.4.197 (commit 1e4d3d2, PR #26967): untrained
YOLO26n from YAML, per-layer Conv2d/Attention recomputation under AMP from each
layer's own FP32 input, relative norm tolerance (<=5%), NaN/inf fail by
comparison semantics. Our PR-C targeted the old amp_allclose (removed) — this
harness decides whether the new check resolves the cache-state-dependent
false failure on Windows ROCm (gfx1151), including the historical
warm-training-context state that failed 0/5 at 0.7606 px on 8.4.182.

The 8.4.212 source tree is injected via PYTHONPATH (site-packages keeps 8.4.182
pristine); the run records which version was actually imported.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

INNER = r'''
import json, logging, sys
import torch
sys.path.insert(0, r"__ULTRALYTICS_SRC__")
import ultralytics
from ultralytics.utils.checks import check_amp

res = {"ultralytics_imported": ultralytics.__version__,
       "ultralytics_file": ultralytics.__file__,
       "torch": torch.__version__, "hip": torch.version.hip or "",
       "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}

if len(sys.argv) > 2 and sys.argv[2] == "warm":
    # build the TRAINING-CONTEXT cache first (historical FAIL state for 8.4.182)
    from ultralytics import YOLO
    tr = YOLO(r"__WEIGHTS__")
    tr.train(data="coco8.yaml", epochs=1, device=0, workers=0, amp=True,
             name="warmctx_84212", exist_ok=True, plots=False, seed=42)
    res["warm_training_amp_effective"] = bool(getattr(tr.trainer, "amp", None))

from ultralytics import YOLO
m = YOLO(r"__WEIGHTS__").model.cuda()
caps = []

class H(logging.Handler):
    def emit(self, record):
        caps.append(record.getMessage())

h = H()
logging.getLogger().addHandler(h)
ul = logging.getLogger("ultralytics")
ul.addHandler(h)
try:
    verdict = bool(check_amp(m))
finally:
    logging.getLogger().removeHandler(h)
    ul.removeHandler(h)
res["check_amp_verdict"] = verdict
res["log_lines"] = [l for l in caps if "AMP" in l][-6:]
print("RESULT_JSON:" + json.dumps(res))
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--environment-id", required=True)
    ap.add_argument("--ultralytics-src", required=True)
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    OUT = {"environment_id": args.environment_id,
           "run_id": args.run_id or f"g3c84_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
           "ultralytics_src": args.ultralytics_src,
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "modes": {}, "summary": {}}

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from harness_common import dll_provenance, save_immutable

    inner = Path(tempfile.mkdtemp(prefix="g3c84_")) / "inner.py"
    src = INNER.replace("__ULTRALYTICS_SRC__", args.ultralytics_src).replace("__WEIGHTS__", args.weights)
    inner.write_text(src, encoding="utf-8")

    for mode in ("default", "warm"):
        env = os.environ.copy()
        env["PYTHONPATH"] = args.ultralytics_src
        env.pop("MIOPEN_USER_DB_PATH", None)
        # stream stdout/stderr to files: long hiprtc compilation phases on
        # Windows ROCm stay visible instead of vanishing into a capture pipe
        out_log = inner.parent / f"mode_{mode}.out.log"
        err_log = inner.parent / f"mode_{mode}.err.log"
        t0 = datetime.now(timezone.utc)
        with open(out_log, "w", encoding="utf-8") as fo, open(err_log, "w", encoding="utf-8") as fe:
            try:
                p = subprocess.run([args.python, "-u", str(inner), args.weights,
                                    "warm" if mode == "warm" else "plain"],
                                   stdout=fo, stderr=fe, timeout=7200, env=env,
                                   cwd=str(inner.parent))
                rc, timed_out = p.returncode, False
            except subprocess.TimeoutExpired:
                rc, timed_out = "TIMEOUT", True
        rec = {"exit": rc, "timed_out": timed_out,
               "wall_s": round((datetime.now(timezone.utc) - t0).total_seconds(), 1),
               "out_log": str(out_log), "err_log": str(err_log)}
        try:
            out_text = out_log.read_text(encoding="utf-8", errors="replace")
            for line in out_text.splitlines():
                if line.startswith("RESULT_JSON:"):
                    rec.update(json.loads(line[len("RESULT_JSON:"):]))
        except OSError:
            pass
        if "check_amp_verdict" not in rec:
            try:
                rec["stderr_tail"] = err_log.read_text(encoding="utf-8", errors="replace")[-2000:]
                rec["stdout_tail"] = out_text[-1000:]
            except OSError:
                pass
        OUT["modes"][mode] = rec
        print(f"[{mode}] verdict={rec.get('check_amp_verdict')} exit={rc} "
              f"wall={rec['wall_s']}s ul={rec.get('ultralytics_imported')} "
              f"amp_eff={rec.get('warm_training_amp_effective')}", flush=True)

    vals = {m: r.get("check_amp_verdict") for m, r in OUT["modes"].items()}
    imported = {r.get("ultralytics_imported") for r in OUT["modes"].values()}
    OUT["summary"] = {
        "verdicts": vals,
        "all_pass": all(v is True for v in vals.values()) and len(vals) == 2,
        "ultralytics_imported": sorted(imported),
        "dll_provenance": dll_provenance(),
        "note": ("modes: default USERPROFILE cache, warm-training context (1-epoch AMP "
                 "training before the check — the 8.4.182-era FAIL state)"),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    save_immutable(Path(args.out), OUT)
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)


if __name__ == "__main__":
    main()
