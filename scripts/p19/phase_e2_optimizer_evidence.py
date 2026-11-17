"""P19 Phase E (v2): earn and prove real optimizer updates on PR #27203 HEAD.

v1 was INCONCLUSIVE: optimizer=auto -> AdamW(lr=1.19e-4) + accumulate=ceil(64/2)=32
with 16 total batches -> no effective update window; post-train model is EMA-loaded.
v2 uses an explicit SGD/lr0 and nbs=2 (accumulate=1) in this disposable harness
(kept clearly separate from the maintainer's exact command), and snapshots BOTH the
raw trainer model (on_train_end callback) and the post-train loaded (EMA) model.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import torch

RUN_DIR = Path("C:/P19/scratch/runs_e2")
if RUN_DIR.exists():
    shutil.rmtree(RUN_DIR)

R: dict = {"mission": "P19", "phase": "E2", "harness": "disposable RCA (no upstream source changes)",
           "v1_result": "INCONCLUSIVE (auto AdamW lr=1.19e-4, accumulate=32, 16 batches, zero param delta)"}

import ultralytics
from ultralytics import YOLO

R["ultralytics_file"] = ultralytics.__file__

model = YOLO("C:/P19/scratch/yolo26n.pt")
params0 = {k: v.detach().clone() for k, v in model.model.named_parameters()}

step_count = {"n": 0}
raw_snap: dict = {}
scaler_info: dict = {}


def on_train_start(trainer):
    opt = trainer.optimizer
    orig = opt.step

    def counting_step(*a, **kw):
        step_count["n"] += 1
        return orig(*a, **kw)

    opt.step = counting_step
    if getattr(trainer, "scaler", None) is not None:
        scaler_info["scale_at_start"] = float(trainer.scaler.get_scale())


def on_train_end(trainer):
    raw_snap["params"] = {k: v.detach().cpu().clone() for k, v in trainer.model.named_parameters()}


model.add_callback("on_train_start", on_train_start)
model.add_callback("on_train_end", on_train_end)

model.train(
    data="coco8.yaml",
    epochs=8,
    imgsz=64,
    batch=2,
    nbs=2,            # accumulate = 1 -> optimizer step every batch
    optimizer="SGD",  # explicit, deterministic LR in harness
    lr0=0.01,
    device=0,
    workers=0,
    project=str(RUN_DIR.parent),
    name=RUN_DIR.name,
    exist_ok=True,
    verbose=True,
    seed=42,
)
R["harness_train_args"] = "epochs=8, imgsz=64, batch=2, nbs=2, optimizer=SGD, lr0=0.01, device=0"


def delta_report(before: dict, after: dict) -> dict:
    deltas = []
    changed = 0
    for k, v0 in before.items():
        d = (after[k] - v0).abs()
        m = float(d.max())
        deltas.append(m)
        if m > 1e-9:
            changed += 1
    return {
        "total_tensors": len(before),
        "tensors_changed_beyond_1e-9": changed,
        "max_abs_delta": max(deltas),
        "mean_abs_delta": sum(deltas) / len(deltas),
        "all_finite": all(m == m and m < float("inf") for m in deltas),
    }


trainer = model.trainer
if getattr(trainer, "scaler", None) is not None:
    scaler_info["scale_at_end"] = float(trainer.scaler.get_scale())
R["scaler"] = scaler_info
R["optimizer_step_count"] = step_count["n"]
R["amp_resolved"] = bool(trainer.args.amp)

params_loaded = dict(model.model.named_parameters())  # post-train loaded (EMA) weights
R["raw_trainer_model_delta"] = delta_report(params0, raw_snap["params"]) if raw_snap else None
R["loaded_model_delta"] = delta_report(params0, params_loaded)

ck = RUN_DIR / "weights" / "last.pt"
R["checkpoint"] = {"path": str(ck), "exists": ck.exists(), "size": ck.stat().st_size if ck.exists() else 0}

raw_ok = R["raw_trainer_model_delta"] and R["raw_trainer_model_delta"]["tensors_changed_beyond_1e-9"] > 0 and R["raw_trainer_model_delta"]["all_finite"]
R["verdict"] = "PASS" if (R["optimizer_step_count"] >= 1 and raw_ok) else "FAIL"

Path("C:/P19/evidence/phase_e2_optimizer_evidence.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(json.dumps({k: R[k] for k in ("optimizer_step_count", "amp_resolved", "scaler", "raw_trainer_model_delta", "loaded_model_delta", "checkpoint", "verdict")}, indent=2))
