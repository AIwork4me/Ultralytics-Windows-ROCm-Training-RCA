"""P19 Phase E: supplementary optimizer-update evidence on PR #27203 HEAD.

SEPARATE from the maintainer's exact 1-epoch command (which has a single batch:
4 images / batch 16 -> 1 step per 4 accumulated batches -> likely 0 optimizer
steps by design). Here: enough batches to guarantee real optimizer updates.

Measures named_parameters only (no buffers), optimizer step count (callback
wrapper, no upstream source mutation), GradScaler scale, finite losses.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import torch

RUN_DIR = Path("C:/P19/scratch/runs_e")
if RUN_DIR.exists():
    shutil.rmtree(RUN_DIR)

R: dict = {"mission": "P19", "phase": "E", "harness": "disposable RCA (no upstream source changes)"}

import ultralytics
from ultralytics import YOLO

R["ultralytics_file"] = ultralytics.__file__

model = YOLO("C:/P19/scratch/yolo26n.pt")
params0 = {k: v.detach().clone() for k, v in model.model.named_parameters()}

step_count = {"n": 0}
scaler_info: dict = {}


def on_train_start(trainer):
    """Wrap optimizer.step to count real steps; capture scaler state."""
    opt = trainer.optimizer
    orig = opt.step

    def counting_step(*a, **kw):
        step_count["n"] += 1
        return orig(*a, **kw)

    opt.step = counting_step
    if getattr(trainer, "scaler", None) is not None:
        scaler_info["scale_at_start"] = float(trainer.scaler.get_scale())


model.add_callback("on_train_start", on_train_start)

results = model.train(
    data="coco8.yaml",
    epochs=8,          # 8 epochs x 2 batches/epoch = 16 batches -> >=4 optimizer steps at nbs=64,batch=2
    imgsz=64,
    batch=2,
    device=0,          # explicit GPU (this harness does not test selection)
    workers=0,
    project=str(RUN_DIR.parent),
    name=RUN_DIR.name,
    exist_ok=True,
    verbose=True,
    seed=42,
)
R["command_equiv"] = "YOLO('yolo26n.pt').train(data='coco8.yaml', epochs=8, imgsz=64, batch=2, device=0)"

trainer = model.trainer
if getattr(trainer, "scaler", None) is not None:
    scaler_info["scale_at_end"] = float(trainer.scaler.get_scale())
R["scaler"] = scaler_info
R["optimizer_step_count"] = step_count["n"]
R["amp_resolved"] = bool(trainer.args.amp) if hasattr(trainer, "args") else None

params1 = dict(model.model.named_parameters())
deltas = []
changed = 0
trainable = 0
for k, v0 in params0.items():
    v1 = params1[k]
    if v1.requires_grad:
        trainable += 1
    d = (v1.detach() - v0).abs()
    m = float(d.max())
    deltas.append(m)
    if m > 1e-9:
        changed += 1
R["named_parameters"] = {
    "total_tensors": len(params0),
    "trainable_tensors": trainable,
    "tensors_changed_beyond_1e-9": changed,
    "max_abs_delta": max(deltas),
    "mean_abs_delta": sum(deltas) / len(deltas),
}
R["all_finite_deltas"] = all(m == m and m < float("inf") for m in deltas)

# checkpoint produced by harness run
ck = RUN_DIR / "weights" / "last.pt"
R["checkpoint"] = {"path": str(ck), "exists": ck.exists(), "size": ck.stat().st_size if ck.exists() else 0}

R["verdict"] = (
    "PASS"
    if R["optimizer_step_count"] >= 1 and changed > 0 and R["all_finite_deltas"]
    else "INCONCLUSIVE"
)

Path("C:/P19/evidence/phase_e_optimizer_evidence.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(json.dumps({k: R[k] for k in ("optimizer_step_count", "amp_resolved", "scaler", "named_parameters", "all_finite_deltas", "checkpoint", "verdict")}, indent=2))
