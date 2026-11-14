"""G3.5 — real AMP training verification: does GradScaler anneal and actually step?

Longer smoke (10 epochs) so GradScaler can halve its scale past the fp16
overflow band and execute real optimizer steps. Records per-step lr / scaled-
grad overflow / param delta, plus per-epoch fitness — proves (or refutes)
that AMP training on the official wheel actually updates weights.
"""
import json
import sys
from pathlib import Path

import torch
from ultralytics import YOLO

OUT = {"steps": [], "note": "", "environment": {}}


def probe(trainer):
    OUT["environment"] = {"torch": torch.__version__, "hip": torch.version.hip or "",
                          "device": torch.cuda.get_device_name(0),
                          "amp_effective": bool(trainer.amp),
                          "scaler_enabled": bool(getattr(trainer.scaler, "_enabled", False))}
    orig = trainer.optimizer_step

    def wrapped():
        overflow = False
        for p in trainer.model.parameters():
            if p.grad is not None and not torch.isfinite(p.grad).all():
                overflow = True
                break
        lr = float(trainer.optimizer.param_groups[0]["lr"])
        s0 = sum(float(p.detach().double().abs().sum()) for p in trainer.model.parameters())
        scale_before = float(trainer.scaler.get_scale())
        orig()
        s1 = sum(float(p.detach().double().abs().sum()) for p in trainer.model.parameters())
        OUT["steps"].append({
            "lr": lr, "scaled_grad_overflow": overflow,
            "scale_before": scale_before, "scale_after": float(trainer.scaler.get_scale()),
            "param_abs_sum_delta": s1 - s0,
            "stepped": abs(s1 - s0) > 0,
        })
        print(f"[step] lr={lr:.2e} overflow={overflow} scale {scale_before}->{trainer.scaler.get_scale()} delta={s1-s0:.6f}", flush=True)
    trainer.optimizer_step = wrapped


def epoch_end(trainer):
    print(f"[epoch {trainer.epoch}] fitness={trainer.fitness}", flush=True)
    OUT.setdefault("fitness_by_epoch", {})[str(trainer.epoch)] = float(trainer.fitness) if trainer.fitness is not None else None


model = YOLO("yolo26n.pt")
model.add_callback("on_train_start", probe)
model.add_callback("on_fit_epoch_end", epoch_end)
r = model.train(data="coco8.yaml", epochs=10, device=0, workers=0, amp=True,
                name="amp10", exist_ok=True, plots=False, seed=42)
OUT["note"] = "10-epoch AMP training on official wheel; steps with lr>0 and delta>0 prove real updates"
Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(OUT, indent=2))
n_stepped = sum(1 for s in OUT["steps"] if s["lr"] > 0 and s["stepped"])
print(f"SUMMARY: {n_stepped} real steps / {len(OUT['steps'])} total; final fitness={OUT['fitness_by_epoch'].get('9')}")
