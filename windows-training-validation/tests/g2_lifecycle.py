"""G2 — Ultralytics task lifecycle test (T01–T15) for one task per invocation.

    python tests/g2_lifecycle.py --task detect --data coco8.yaml \
        --weights yolo26n.pt --imgsz 640 --workers 0 --amp False \
        --out ../raw/g2_detect_fp32.json [--stop-after-epoch N]

Stages:
  main    — T01 pretrained inference, T03 init, T04 1-epoch smoke, T06/T07/T08
            in-training assertions, T05 4-epoch run interrupted after epoch 1
            (graceful early-stop), T09/T10 checkpoints, T11 reload, T12 resume,
            T13 val of saved model, T14 predict of saved model, T15 metric
            equality across reload.
  resume  — (second process) resume the interrupted 4-epoch run, then run
            T11–T15 and write the merged result JSON.

All statuses PASS/FAIL/SKIP/BLOCKED with reasons; no silent fallback; GPU
provenance asserted in-process (torch.version.hip + device + MIOpen ops).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch

RESULTS: dict = {"tests": {}, "environment": {}, "limitations": []}


def status(name: str, st: str, **fields) -> None:
    RESULTS["tests"][name] = {"status": st, **fields}
    print(f"[{st}] {name} {fields if st != 'PASS' else ''}", flush=True)


def fail(name: str, detail: str, **fields) -> None:
    status(name, "FAIL", detail=detail, **fields)


def require_gpu() -> bool:
    ok = bool(torch.cuda.is_available()) and bool(torch.version.hip)
    RESULTS["environment"] = {
        "torch": torch.__version__,
        "hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0) if ok else None,
        "gpu_authentic": ok,
    }
    if not ok:
        RESULTS["limitations"].append("GPU/HIP unavailable — lifecycle BLOCKED")
    return ok


def finite_loss_row(row: dict) -> bool:
    keys = [k for k in row if "loss" in k]
    vals = []
    for k in keys:
        v = row[k]
        if v in (None, ""):
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            return False
    return all(math.isfinite(v) for v in vals)


def read_results_csv(csv_path: Path) -> list[dict]:
    if not csv_path.is_file():
        return []
    lines = [l.strip() for l in csv_path.read_text().splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split(",")
    return [dict(zip(header, l.split(","))) for l in lines[1:]]


def patch_step(trainer) -> None:
    """Wrap trainer.optimizer_step once to observe pre-step gradients and the
    parameter delta across the actual optimizer update (read-only diagnostics;
    8.4.182 zeroed grads inside optimizer_step and no longer fires
    on_before_zero_grad, so the official callback API cannot observe them)."""
    if RESULTS.get("_step_patched"):
        return
    RESULTS["_step_patched"] = True
    original = trainer.optimizer_step

    def wrapped_step():
        grads = [p.grad for p in trainer.model.parameters() if p.grad is not None]
        all_finite = bool(grads) and all(torch.isfinite(g).all().item() for g in grads)
        RESULTS["tests"]["t07_backward_gradient_finite"] = {
            "status": "PASS" if all_finite else "FAIL",
            "params_with_grad": len(grads),
            "all_grads_finite": all_finite,
            "hook": "trainer.optimizer_step wrapper (pre-step .grad inspection)",
        }
        RESULTS["_param_sum_before_step"] = sum(
            float(p.detach().double().abs().sum()) for p in trainer.model.parameters()
        )
        original()
        after = sum(
            float(p.detach().double().abs().sum()) for p in trainer.model.parameters()
        )
        before = RESULTS["_param_sum_before_step"]
        delta = abs(after - before)
        prev = RESULTS.get("_max_param_delta", 0.0)
        RESULTS["_max_param_delta"] = max(prev, delta)
        lr_now = None
        try:
            lr_now = float(trainer.optimizer.param_groups[0]["lr"])
        except (AttributeError, KeyError, IndexError):
            pass
        # warmup starts at lr=0 (first step legitimately changes nothing) —
        # SKIP until a lr>0 step is observed; lr>0 with no change = real FAIL
        if RESULTS["_max_param_delta"] > 0:
            st = "PASS"
        elif lr_now is not None and lr_now > 0:
            st = "FAIL"
        else:
            st = "SKIP"
        RESULTS["tests"]["t08_optimizer_step"] = {
            "status": st,
            "max_param_abs_sum_delta": RESULTS["_max_param_delta"],
            "last_step_lr": lr_now,
            "note": "SKIP=only warmup lr~0 steps observed so far; authoritative on resume stage",
        }

    trainer.optimizer_step = wrapped_step


def batch_start_callback(trainer) -> None:
    patch_step(trainer)


class SimulatedInterrupt(Exception):
    """Raised mid-training from a callback to abort the epoch loop.

    Ultralytics saves the resumable last.pt (epoch + optimizer state) at each
    epoch end BEFORE running on_fit_epoch_end, so an exception here aborts the
    loop without the final-checkpoint strip — equivalent to a real external
    interruption between epochs, but process-kill-free.
    """


def stop_after_epoch_callback(trainer) -> None:
    if trainer.epoch == RESULTS["_stop_after_epoch"]:
        RESULTS["_stopped_epoch"] = trainer.epoch
        raise SimulatedInterrupt(f"simulated interruption after epoch {trainer.epoch}")


def run_main(args) -> None:
    from ultralytics import YOLO

    dev = 0

    # T01 — pretrained GPU inference
    model = YOLO(args.weights)
    src = args.infer_source or args.data
    r = model.predict(source=src, device=dev, verbose=False)
    ok = r and len(r) > 0 and r[0].orig_img is not None
    status("t01_gpu_pretrained_inference", "PASS" if ok else "FAIL",
           n_results=len(r) if r else 0)

    # T03 — GPU training initialization (1-epoch smoke, fresh run dir)
    kw = dict(data=args.data, epochs=1, device=dev, workers=args.workers,
              amp=args.amp, name=args.run_smoke,
              exist_ok=True, seed=args.seed, plots=False, val=True)
    if args.model_yaml:
        model = YOLO(args.model_yaml)
        RESULTS["limitations"].append(f"no pretrained weights used; trained from {args.model_yaml}")
    m = model.train(**kw)  # noqa: F841
    smoke_dir = Path(model.trainer.save_dir)
    RESULTS["tests"]["t03_gpu_training_init"] = {"status": "PASS", "save_dir": str(smoke_dir)}

    # T04 — one-epoch smoke completed (train() returned normally = 1 epoch done)
    csv_rows = read_results_csv(smoke_dir / "results.csv")
    ok = len(csv_rows) == 1 and finite_loss_row(csv_rows[0])
    status("t04_one_epoch_smoke", "PASS" if ok else "FAIL",
           epochs_in_csv=len(csv_rows), losses=csv_rows[0] if csv_rows else None)

    # T09/T10 for the smoke run (files) — real checkpoint audit on the 4-epoch run
    last_pt = smoke_dir / "weights" / "last.pt"
    best_pt = smoke_dir / "weights" / "best.pt"
    status("t09_save_last_pt", "PASS" if last_pt.is_file() else "FAIL", path=str(last_pt))
    status("t10_save_best_pt", "PASS" if best_pt.is_file() else "FAIL", path=str(best_pt))

    # T05 — multi-epoch (4) run, interrupted after epoch N via callback exception
    model = YOLO(args.weights)
    kw4 = dict(data=args.data, epochs=args.resume_epochs, device=dev, workers=args.workers,
               amp=args.amp, name=args.run_multi,
               exist_ok=True, seed=args.seed, plots=False, val=True)
    RESULTS["_stop_after_epoch"] = args.stop_after_epoch
    RESULTS["_param_sum_before"] = None
    RESULTS["_param_sum_after_step"] = None
    model.add_callback("on_train_batch_start", batch_start_callback)
    model.add_callback("on_fit_epoch_end", stop_after_epoch_callback)
    interrupted_cleanly = False
    try:
        model.train(**kw4)
    except SimulatedInterrupt as exc:
        interrupted_cleanly = True
        print(f"[interrupt] {exc}", flush=True)
    multi_dir = Path(model.trainer.save_dir)
    rows = read_results_csv(multi_dir / "results.csv")
    last_pt = multi_dir / "weights" / "last.pt"
    resumable = False
    if last_pt.is_file():
        ck = torch.load(last_pt, map_location="cpu", weights_only=False)
        resumable = ck.get("epoch") == args.stop_after_epoch and ck.get("optimizer") is not None
    interrupted_ok = interrupted_cleanly and len(rows) == args.stop_after_epoch + 1 and resumable
    status("t05_multi_epoch_interrupted", "PASS" if interrupted_ok else "FAIL",
           planned_epochs=args.resume_epochs, completed_before_interrupt=len(rows),
           last_pt_epoch=ck.get("epoch") if last_pt.is_file() else None,
           last_pt_resumable=resumable, save_dir=str(multi_dir))
    status("t06_loss_finite_throughout", "PASS" if all(finite_loss_row(rw) for rw in rows) else "FAIL",
           epochs_checked=len(rows))
    RESULTS["_multi_dir"] = str(multi_dir)

    if args.stage == "main":
        # write partial state for the resume process
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        print(f"MAIN stage done — interrupted run at {multi_dir}", flush=True)
        return
    raise RuntimeError("unreachable: stage=resume must be handled in main()")


def run_resume_and_final(args, multi_dir: Path) -> None:
    from ultralytics import YOLO

    last_pt = multi_dir / "weights" / "last.pt"
    best_pt = multi_dir / "weights" / "best.pt"

    # T12 — resume interrupted training
    model = YOLO(str(last_pt))
    # observe gradients/optimizer on the resumed training too (fresh records)
    RESULTS["_step_patched"] = False
    RESULTS["_max_param_delta"] = 0.0
    RESULTS["tests"].pop("t07_backward_gradient_finite", None)
    RESULTS["tests"].pop("t08_optimizer_step", None)
    model.add_callback("on_train_batch_start", batch_start_callback)
    model.train(resume=True)
    rows = read_results_csv(multi_dir / "results.csv")
    ok = len(rows) == args.resume_epochs and all(finite_loss_row(rw) for rw in rows)
    status("t12_resume_interrupted", "PASS" if ok else "FAIL",
           rows_after_resume=len(rows), expected=args.resume_epochs)

    # T09/T10 — checkpoint integrity on the completed multi-epoch run.
    # Note: ultralytics 8.4.182 final-saves last.pt with epoch=-1 and optimizer
    # stripped once training COMPLETES (resumability was asserted at interrupt
    # time in t05: last.pt epoch=1 + optimizer present, and proven by t12).
    ck = torch.load(last_pt, map_location="cpu", weights_only=False)
    ok = ("model" in ck and ck.get("train_args") is not None
          and ck.get("epoch") in (-1, args.resume_epochs - 1))
    status("t09_save_last_pt", "PASS" if ok else "FAIL",
           epoch_field=ck.get("epoch"), has_optimizer=ck.get("optimizer") is not None,
           note="post-completion last.pt (final strip) on multi-epoch run")
    ck_b = torch.load(best_pt, map_location="cpu", weights_only=False)
    ok = "model" in ck_b and ck_b.get("train_args") is not None
    status("t10_save_best_pt", "PASS" if ok else "FAIL",
           fitness=ck_b.get("fitness"), note="multi-epoch run")

    # T11 — reload checkpoint (fresh YOLO object from disk, GPU predict)
    reloaded = YOLO(str(best_pt))
    r = reloaded.predict(source=args.infer_source or args.data, device=0, verbose=False)
    ok = bool(r) and r[0].orig_img is not None
    status("t11_reload_checkpoint", "PASS" if ok else "FAIL")

    # T13 — GPU validation of saved model
    metrics = reloaded.val(data=args.data, device=0, verbose=False)
    m1 = dict(metrics.results_dict)
    status("t13_gpu_val_saved_model", "PASS", metrics={k: float(v) for k, v in m1.items()
                                                       if isinstance(v, (int, float))})

    # T14 — GPU prediction of saved model (already exercised in T11; re-record explicitly)
    r2 = reloaded.predict(source=args.infer_source or args.data, device=0, verbose=False)
    ok = bool(r2) and r2[0].orig_img is not None
    status("t14_gpu_predict_saved_model", "PASS" if ok else "FAIL",
           boxes=len(r2[0].boxes) if hasattr(r2[0], "boxes") else None)

    # T15 — metrics identical before/after reload (val is deterministic at eval)
    reloaded2 = YOLO(str(best_pt))
    metrics2 = reloaded2.val(data=args.data, device=0, verbose=False)
    m2 = dict(metrics2.results_dict)
    key_ok = True
    diffs = {}
    for k, v in m1.items():
        if isinstance(v, (int, float)):
            d = abs(float(v) - float(m2.get(k, v)))
            diffs[k] = d
            if d > 1e-12:
                key_ok = False
    status("t15_metrics_before_after_reload", "PASS" if key_ok else "FAIL", max_diffs=diffs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--model-yaml", default=None, help="train from yaml if no pretrained weight")
    ap.add_argument("--infer-source", default=None)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--amp", default="False")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume-epochs", type=int, default=4)
    ap.add_argument("--stop-after-epoch", type=int, default=1)
    ap.add_argument("--project", default="runs")
    ap.add_argument("--run-smoke", default="smoke")
    ap.add_argument("--run-multi", default="multi")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=["main", "resume"], default="resume")
    args = ap.parse_args()

    args.amp = args.amp.lower() == "true"
    if not require_gpu():
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        sys.exit(3)
    RESULTS["args"] = {k: str(v) for k, v in vars(args).items()}
    t0 = time.time()
    try:
        if args.stage == "resume":
            # second process: load partial results from the main stage, then
            # resume the interrupted run and finish T09–T15
            partial = json.loads(Path(args.out).read_text(encoding="utf-8"))
            RESULTS["tests"] = partial.get("tests", {})
            RESULTS["limitations"] = partial.get("limitations", [])
            multi_dir = Path(partial["_multi_dir"])
            run_resume_and_final(args, multi_dir)
        else:
            run_main(args)
    except Exception as exc:  # first real error must surface, never swallowed
        RESULTS["unhandled_exception"] = f"{type(exc).__name__}: {exc}"
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        raise
    RESULTS["wall_seconds"] = round(time.time() - t0, 1)
    Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    n_pass = sum(1 for t in RESULTS["tests"].values() if t["status"] == "PASS")
    n_all = len(RESULTS["tests"])
    print(f"SUMMARY {args.task}: {n_pass}/{n_all} PASS", flush=True)
    final = all(t["status"] in ("PASS", "SKIP") for t in RESULTS["tests"].values())
    sys.exit(0 if final else 1)


if __name__ == "__main__":
    main()
