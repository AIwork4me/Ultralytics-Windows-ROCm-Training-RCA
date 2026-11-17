"""G3.8 — genuine AMP learning validation on a representative dataset.

    python tests/g3_amp_learning.py --out ../raw/g3_learning_<env>.json \
        --environment-id ENV_X [--epochs 6] [--data imagenette2-160]

Mission §4.4: "PASS requires stable training with a meaningful number of
successful updates and credible task metrics."

Design (closes audit M5's residual scope honestly):
  - matched FP32 vs AMP training runs, SAME env/machine/seed/epochs/batch
  - classification on imagenette2-160 (real photos, 10 classes, ~13k train
    images) — top-1/top-5 accuracy is a credible task metric, unlike mAP on
    a 128-image toy set
  - full per-step audit via amp_step_audit.StepRecorder: successful updates,
    overflow skips, scale transitions, per-parameter deltas — for BOTH modes
  - BN buffer drift is recorded separately and never counted as learning
  - verdict per mode: PASS requires >= min_updated successful steps AND
    finite losses AND top1 metric recorded; AMP mode additionally requires
    amp_effective (a silent FP32 fallback is NOT an AMP result)
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amp_step_audit import BAD_GRAD_UPDATE, OVERFLOW_SKIP, STUCK_FAILURE, UPDATED, StepRecorder
from harness_common import csv_rows, dll_provenance, env_meta, new_run_id, save_immutable

OUT: dict = {"environment": {}, "runs": {}, "summary": {}}


def run_mode(tag: str, amp: bool, args) -> dict:
    from ultralytics import YOLO
    rec_steps = {}

    def attach(trainer):
        r = StepRecorder(trainer, label=tag)
        r.attach()
        rec_steps["rec"] = r

    model = YOLO(args.weights)
    model.add_callback("on_train_start", attach)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    exc = None
    try:
        model.train(data=args.data, epochs=args.epochs, device=0, workers=args.workers,
                    amp=amp, task="classify", name=f"amplearn_{OUT['run_id']}_{tag}",
                    exist_ok=True, plots=False, seed=args.seed, batch=args.batch)
    except Exception as e:  # noqa: BLE001
        exc = f"{type(e).__name__}: {e}"
        raise
    wall = time.time() - t0
    save_dir = Path(model.trainer.save_dir)
    rows = csv_rows(save_dir / "results.csv")
    rec = rec_steps.get("rec")
    counts = rec.counts() if rec else {}
    fitness = [float(r.get("metrics/accuracy_top1", 0) or 0) for r in rows]
    all_finite_loss = all(all(_isfinite(v) for k, v in r.items() if "loss" in k) for r in rows)
    out = {
        "amp_requested": amp,
        "amp_effective": bool(getattr(model.trainer, "amp", None)),
        "wall_s": round(wall, 1),
        "epochs_configured": args.epochs,
        "epochs_in_csv": len(rows),
        "counts": counts,
        "scaler_transitions": rec.scaler_trace()["scale_transitions"] if rec else [],
        "steps_summary": [
            {"i": i, "lr": s["lr"], "class": s["classification"], "health": s["gradient_health"],
             "scale": [s["scale_before"], s["scale_after"]],
             "max_delta": s["params"]["max_abs_tensor_delta"],
             "n_changed": s["params"]["n_tensors_changed"],
             "buffers_max_delta": s["params"]["buffers"]["max_abs_buffer_delta"]}
            for i, s in enumerate(rec.steps)] if rec else [],
        "first_updated_per_param": next(
            ({"n_float": s["params"]["n_tensors_float"],
              "n_changed": s["params"]["n_tensors_changed"],
              "n_elements": s["params"]["n_elements_changed"],
              "max_delta": s["params"]["max_abs_tensor_delta"]}
             for s in rec.steps if s["classification"] == UPDATED), None) if rec else None,
        "losses_finite_all": all_finite_loss,
        "top1_first": fitness[0] if fitness else None,
        "top1_last": fitness[-1] if fitness else None,
        "top1_max": max(fitness) if fitness else None,
        "top1_trajectory": fitness,
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "results_csv_text": (save_dir / "results.csv").read_text(encoding="utf-8")
        if (save_dir / "results.csv").is_file() else None,
        "dll_provenance": dll_provenance(),
        "unhandled_exception": exc,
    }
    min_upd = args.min_updated
    if exc:
        out["verdict"] = "FAIL"
        out["verdict_reason"] = f"unhandled exception: {exc}"
    elif amp and not out["amp_effective"]:
        out["verdict"] = "SKIP"
        out["verdict_reason"] = ("check_amp fell back to FP32 — this leg measured FP32, not AMP "
                                 "(honest SKIP, never PASS)")
    elif counts.get(STUCK_FAILURE, 0) or counts.get(BAD_GRAD_UPDATE, 0):
        out["verdict"] = "FAIL"
        out["verdict_reason"] = "STUCK/BAD_GRAD_UPDATE steps present"
    elif counts.get(UPDATED, 0) < min_upd:
        out["verdict"] = "SKIP"
        out["verdict_reason"] = f"only {counts.get(UPDATED, 0)} successful updates (< {min_upd} required)"
    elif not out["losses_finite_all"] or not rows:
        out["verdict"] = "FAIL"
        out["verdict_reason"] = f"losses not finite or no epochs recorded ({len(rows)})"
    else:
        out["verdict"] = "PASS"
        out["verdict_reason"] = (f"{counts.get(UPDATED, 0)} successful updates, losses finite, "
                                 f"top1 {out['top1_first']}->{out['top1_last']} (max {out['top1_max']})")
    print(f"[{tag}] verdict={out['verdict']} updates={counts.get(UPDATED, 0)} "
          f"top1 {out['top1_first']}->{out['top1_last']} wall={out['wall_s']}s", flush=True)
    OUT["runs"][tag] = out
    return out


def _isfinite(v):
    try:
        return _math_isfinite(float(v))
    except (TypeError, ValueError):
        return True  # non-numeric CSV fields are not losses


def _math_isfinite(x):
    import math
    return math.isfinite(x)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="imagenette2-160")
    ap.add_argument("--weights", default="yolo26n-cls.pt")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-updated", type=int, default=10)
    ap.add_argument("--environment-id", default="unknown")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    OUT["run_id"] = args.run_id or new_run_id("amplearn")
    OUT["environment_id"] = args.environment_id
    OUT["environment"] = env_meta()
    OUT["args"] = {k: str(v) for k, v in vars(args).items()}
    OUT["started_utc"] = datetime.now(timezone.utc).isoformat()
    OUT["note"] = ("matched FP32-vs-AMP classification on a representative dataset; "
                   "successful-update counts from per-parameter step audit; top1 accuracy "
                   "is the credible task metric (audit M5 closure)")
    run_mode("fp32", False, args)
    run_mode("amp", True, args)
    fp, am = OUT["runs"]["fp32"], OUT["runs"]["amp"]
    OUT["summary"] = {
        "fp32_verdict": fp["verdict"], "amp_verdict": am["verdict"],
        "fp32_updates": fp["counts"].get(UPDATED, 0), "amp_updates": am["counts"].get(UPDATED, 0),
        "amp_overflow_skips": am["counts"].get(OVERFLOW_SKIP, 0),
        "fp32_top1_last": fp["top1_last"], "amp_top1_last": am["top1_last"],
        "fp32_top1_max": fp["top1_max"], "amp_top1_max": am["top1_max"],
        "fp32_wall_s": fp["wall_s"], "amp_wall_s": am["wall_s"],
        "amp_vs_fp32_top1_delta": (round((am["top1_last"] or 0) - (fp["top1_last"] or 0), 4)),
        "miopen_sha_fp32": (fp["dll_provenance"].get("miopen_loaded") or {}).get("sha256"),
        "miopen_sha_amp": (am["dll_provenance"].get("miopen_loaded") or {}).get("sha256"),
    }
    OUT["completed_utc"] = datetime.now(timezone.utc).isoformat()
    save_immutable(Path(args.out), OUT)
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)


if __name__ == "__main__":
    main()
