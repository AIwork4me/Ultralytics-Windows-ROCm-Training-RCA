# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Real optimizer-update audit (mission §9) — supplementary harness, runs in target venv.

Design reused from the P19-proven phase_e2 harness, extended per R21:
  - named_parameters snapshot BEFORE training vs raw trainer model AFTER
    (on_train_end callback) AND post-train loaded (EMA) model
  - counted optimizer.step() via public-instance wrapper (no private torch APIs)
  - per-step GradScaler scale history (scale recorded around every step —
    skipped-step counts are NOT inferred from start/end scale alone)
  - autocast participation sampled per optimizer step via torch.is_autocast_enabled
  - explicit SGD + nbs=2 in THIS harness only (accumulate=1 → a step per batch);
    this is a SUPPLEMENTARY harness, not the standard CLI test — disclosed
  - BatchNorm running buffers are NOT counted as parameter updates

    python audit_optimizer.py --out audit.json --run-id R21-E [--data coco128.yaml]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402


def delta_report(before: dict, after: dict) -> dict:
    deltas, changed = [], 0
    for k, v0 in before.items():
        d = (after[k].detach().cpu() - v0.detach().cpu()).abs()
        m = float(d.max())
        deltas.append(m)
        if m > 1e-9:
            changed += 1
    return {
        "total_tensors": len(before),
        "tensors_changed_beyond_1e-9": changed,
        "max_abs_delta": max(deltas) if deltas else 0.0,
        "mean_abs_delta": (sum(deltas) / len(deltas)) if deltas else 0.0,
        "all_finite": all(m == m and m < float("inf") for m in deltas),
    }


def main() -> None:
    import torch
    import ultralytics
    from ultralytics import YOLO
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--run-dir", required=True, help="disposable run dir")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    model = YOLO("yolo26n.pt")
    params0 = {k: v.detach().cpu().clone() for k, v in model.model.named_parameters()}

    steps = {"n": 0}
    raw_snap: dict = {}
    scale_history: list[float] = []
    autocast_flags: list[bool] = []  # step-time samples sit OUTSIDE the autocast
    # region by design; true forward participation uses the forward-pre-hook
    autocast_fwd: list[bool] = []
    grad_finite_at_step: list[bool] = []

    def on_train_start(trainer):
        opt = trainer.optimizer
        orig = opt.step

        def counting_step(*a, **kw):
            if getattr(trainer, "scaler", None) is not None:
                scale_history.append(float(trainer.scaler.get_scale()))
            autocast_flags.append(bool(torch.is_autocast_enabled()))
            fin = all(bool(torch.isfinite(p.grad).all().item())
                      for p in opt.param_groups[0]["params"]
                      if p.grad is not None)
            grad_finite_at_step.append(fin)
            r = orig(*a, **kw)
            steps["n"] += 1
            return r

        opt.step = counting_step
        trainer._gp_opt_class = type(opt).__name__
        trainer._gp_opt_fused = bool(getattr(opt, "fused", False))

        def _fwd_hook(module, inputs):
            autocast_fwd.append(bool(torch.is_autocast_enabled()))
        trainer.model.register_forward_pre_hook(_fwd_hook)

    def on_train_end(trainer):
        raw_snap["params"] = {k: v.detach().cpu().clone()
                              for k, v in trainer.model.named_parameters()}

    model.add_callback("on_train_start", on_train_start)
    model.add_callback("on_train_end", on_train_end)

    model.train(
        data=args.data, epochs=args.epochs, imgsz=64, batch=2,
        nbs=2,               # accumulate = 1 → optimizer step every batch (harness choice)
        optimizer="SGD",      # explicit deterministic LR in THIS harness only
        lr0=0.01, device=0, workers=0,
        project=str(run_dir.parent), name=run_dir.name, exist_ok=True,
        verbose=True, seed=42,
    )

    trainer = model.trainer
    scaler_end = float(trainer.scaler.get_scale()) if getattr(trainer, "scaler", None) else None
    params_loaded = dict(model.model.named_parameters())
    raw_delta = delta_report(params0, raw_snap["params"]) if raw_snap else None
    loaded_delta = delta_report(params0, params_loaded)

    n_backoff = sum(1 for i in range(1, len(scale_history))
                    if scale_history[i] < scale_history[i - 1]) if scale_history else 0
    raw_ok = bool(raw_delta and raw_delta["tensors_changed_beyond_1e-9"] > 0
                  and raw_delta["all_finite"])
    verdict = "PASS" if (steps["n"] >= 1 and raw_ok) else "FAIL"

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
        "command": (f"python audit_optimizer.py --data {args.data} --epochs {args.epochs} "
                    "(SUPPLEMENTARY harness: SGD nbs=2 — not the standard CLI)"),
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": None if verdict == "PASS" else "INCONCLUSIVE",
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "harness_disclosure": "supplementary harness; optimizer/nbs differ from the standard CLI test",
        "harness_train_args": f"epochs={args.epochs}, imgsz=64, batch=2, nbs=2, optimizer=SGD, lr0=0.01, device=0",
        "ultralytics_version": im.version("ultralytics"),
        "ultralytics_file": ultralytics.__file__,
        "optimizer_step_count": steps["n"],
        "optimizer_class": getattr(trainer, "_gp_opt_class", type(trainer.optimizer).__name__),
        "optimizer_fused": bool(getattr(trainer, "_gp_opt_fused", False)),
        "amp_resolved": bool(trainer.args.amp),
        "autocast_participation": {"steps_sampled": len(autocast_flags),
                                   "steps_autocast_on": sum(autocast_flags),
                                   "note": "step-time samples sit outside the autocast "
                                           "region; see forward samples for true participation"},
        "autocast_forward_samples": {"forwards_sampled": len(autocast_fwd),
                                     "forwards_autocast_on": sum(autocast_fwd)},
        "grad_finite_at_step": {"steps": len(grad_finite_at_step),
                                "all_finite": all(grad_finite_at_step) if grad_finite_at_step else False},
        "gradscaler": {"present": scaler_end is not None,
                       "scale_history_len": len(scale_history),
                       "scale_first": scale_history[0] if scale_history else None,
                       "scale_end": scaler_end,
                       "scale_backoff_events_observed": n_backoff,
                       "note": "backoff events counted from per-step history, not inferred from endpoints"},
        "raw_trainer_model_delta": raw_delta,
        "loaded_model_delta": loaded_delta,
        "checkpoint": {"path": str(run_dir / "weights" / "last.pt"),
                       "exists": (run_dir / "weights" / "last.pt").exists()},
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(json.dumps({k: record[k] for k in
                      ("optimizer_step_count", "optimizer_class", "optimizer_fused", "amp_resolved",
                       "autocast_participation", "gradscaler", "raw_trainer_model_delta",
                       "checkpoint", "pass_fail_skip")}, indent=2))
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
