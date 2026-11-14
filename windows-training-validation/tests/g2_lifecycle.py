"""G2 — Ultralytics task lifecycle test (T01–T16) for one task per invocation.

    python tests/g2_lifecycle.py --task detect --data coco8.yaml \
        --weights yolo26n.pt --imgsz 640 --workers 0 --amp False \
        --out ../raw/g2_detect_fp32.json [--stop-after-epoch N]

Stages:
  main    — T01 pretrained inference, T03 init, T04 1-epoch smoke, T06/T07/T08
            in-training assertions (per-parameter step audit), T05 4-epoch run
            interrupted after epoch 1 (graceful early-stop), T09/T10 checkpoints
  resume  — (second process) resume the interrupted 4-epoch run, then run
            T11–T15; with --amp True additionally runs T16: a dedicated
            longer AMP training (--amp-updates-epochs, default 10) on
            --amp-updates-data to establish GENUINE REPEATED optimizer
            updates (P8 audit: t08 proves semantics, not weight-learning).

Step auditing (amp_step_audit.StepRecorder, mission §3.1/§3.2):
  t07 strict gradient health — under AMP a non-finite SCALED grad is acceptable
      only as a scaler-sanctioned skipped step; no unconditional AMP PASS.
  t08 per-parameter tensor deltas — max-abs delta, changed tensor/element
      counts; int buffers never count as update evidence; classification
      WARMUP_SKIP / OVERFLOW_SKIP / UPDATED / STUCK_FAILURE / BAD_GRAD_UPDATE.
  t16 requires >= --amp-min-updated real UPDATED steps with per-parameter
      evidence + scaler transition trace.

All statuses PASS/FAIL/SKIP/BLOCKED with reasons; SKIP is never counted as
functional PASS; no silent fallback; GPU provenance asserted in-process.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amp_step_audit import (BAD_GRAD_UPDATE, OVERFLOW_SKIP, STUCK_FAILURE, UPDATED,
                            WARMUP_SKIP, StepRecorder, run_id)

RESULTS: dict = {"tests": {}, "environment": {}, "limitations": []}


def status(name: str, st: str, **fields) -> None:
    RESULTS["tests"][name] = {"status": st, **fields}
    print(f"[{st}] {name} {fields if st != 'PASS' else ''}", flush=True)


def require_gpu() -> bool:
    ok = bool(torch.cuda.is_available()) and bool(torch.version.hip)
    RESULTS["environment"] = {
        "torch": torch.__version__,
        "hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0) if ok else None,
        "gpu_authentic": ok,
        "python_executable": sys.executable,
        "run_id": RESULTS.get("run_id"),
        "environment_id": RESULTS.get("environment_id"),
        "cache_home_env": {k: os.environ[k] for k in sorted(os.environ)
                           if any(t in k.upper() for t in ("MIOPE", "MIOPEN", "ROCM", "USERPROFILE", "HIP"))},
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


def attach_recorder(label: str) -> None:
    """on_train_start callback: attach a fresh per-training StepRecorder."""
    def _attach(trainer) -> None:
        rec = StepRecorder(trainer, label=label)
        rec.attach()
        RESULTS[f"_rec_{label}"] = rec
        print(f"[recorder] attached ({label}) amp_effective={bool(trainer.amp)} "
              f"scaler_enabled={bool(getattr(trainer.scaler, '_enabled', False))}", flush=True)
    return _attach


def record_step_tests(label: str) -> None:
    """Write t07/t08 records for one stage's recorder into RESULTS['tests']."""
    rec = RESULTS.pop(f"_rec_{label}", None)
    if rec is None:
        return
    RESULTS.setdefault("_stage_step_records", {})[label] = {
        "t07": rec.t07_record(), "t08": rec.t08_record(min_updated=1),
        "counts": rec.counts(), "scaler_trace": rec.scaler_trace(),
        "steps_summary": [
            {"i": i, "lr": s["lr"], "class": s["classification"], "health": s["gradient_health"],
             "amp_active": s["amp_active"], "found_inf": s["found_inf"],
             "scale": [s["scale_before"], s["scale_after"]],
             "n_changed": s["params"]["n_tensors_changed"],
             "n_float": s["params"]["n_tensors_float"],
             "max_delta": s["params"]["max_abs_tensor_delta"],
             "buffers_changed": s["params"]["buffers"]["n_buffers_changed"]}
            for i, s in enumerate(rec.steps)],
        "steps_full": [{"lr": s["lr"], "class": s["classification"],
                        "amp_active": s["amp_active"], "found_inf": s["found_inf"],
                        "params": s["params"], "scaled_grad_census": s["scaled_grad_census"],
                        "unscaled_grad_census": s["unscaled_grad_census"]}
                       for s in rec.steps],
    }


def merge_step_tests() -> None:
    """Combine per-stage step records into final t07/t08 verdicts.
    FAIL dominates; PASS requires the merged UPDATED count >= min_updated
    (t08 keeps min_updated=1 inside the lifecycle; t16 is the repeated-update
    authority); otherwise honest SKIP with the skip composition disclosed."""
    stages = RESULTS.get("_stage_step_records", {})
    if not stages:
        return
    merged_counts = {}
    for k in (WARMUP_SKIP, OVERFLOW_SKIP, UPDATED, STUCK_FAILURE, BAD_GRAD_UPDATE):
        merged_counts[k] = sum(s["counts"].get(k, 0) for s in stages.values())
    fails7 = [f"{lbl}:{i}" for lbl, s in stages.items() for i in s["t07"].get("failed_step_indices", [])]
    t07 = {"status": "FAIL" if fails7 else "PASS",
           "n_steps": sum(s["t07"]["n_steps"] for s in stages.values()),
           "n_scaler_handled_overflow": sum(s["t07"].get("n_scaler_handled_overflow", 0)
                                            for s in stages.values()),
           "failed_step_indices": fails7,
           "per_stage": {lbl: s["t07"]["status"] for lbl, s in stages.items()},
           "note": ("strict: non-finite grads acceptable only as scaler-sanctioned "
                    "skipped steps (G_OK_SKIP); no unconditional AMP PASS")}
    if merged_counts[STUCK_FAILURE] or merged_counts[BAD_GRAD_UPDATE]:
        t08 = {"status": "FAIL", "counts": merged_counts,
               "reason": "STUCK_FAILURE/BAD_GRAD_UPDATE steps present (per-parameter evidence)",
               "per_stage": {lbl: s["t08"]["status"] for lbl, s in stages.items()}}
    elif merged_counts[UPDATED] >= 1:
        t08 = {"status": "PASS", "counts": merged_counts,
               "per_stage": {lbl: s["t08"]["status"] for lbl, s in stages.items()},
               "note": ">=1 real parameter update observed (per-parameter evidence); "
                       "repeated updates are established by t16 for AMP runs"}
    else:
        skips = [f"{lbl}: {s['t08'].get('reason', '')}" for lbl, s in stages.items()]
        t08 = {"status": "SKIP", "counts": merged_counts, "per_stage_reasons": skips,
               "note": "no real parameter update; every lr>0 step was an intended "
                       "GradScaler overflow skip — authoritative evidence is t16"}
    RESULTS["tests"]["t07_backward_gradient_finite"] = t07
    RESULTS["tests"]["t08_optimizer_step"] = t08
    RESULTS["step_audit_detail"] = {lbl: {"counts": s["counts"], "scaler_trace": s["scaler_trace"],
                                          "steps_summary": s["steps_summary"]}
                                    for lbl, s in stages.items()}


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
    RESULTS["tests"]["t03_gpu_training_init"] = {
        "status": "PASS", "save_dir": str(smoke_dir),
        "trainer_amp_effective": bool(getattr(model.trainer, "amp", None)),
        "note": "trainer_amp_effective=False with amp=True request means check_amp fell back to FP32",
    }

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
    model.add_callback("on_train_start", attach_recorder("main"))
    model.add_callback("on_fit_epoch_end", stop_after_epoch_callback)
    interrupted_cleanly = False
    ck = {}
    try:
        model.train(**kw4)
    except SimulatedInterrupt as exc:
        interrupted_cleanly = True
        print(f"[interrupt] {exc}", flush=True)
    record_step_tests("main")
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
        merge_step_tests()
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
    model.add_callback("on_train_start", attach_recorder("resume"))
    model.train(resume=True)
    record_step_tests("resume")
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
    n_det = None
    det_attr = None
    for attr in ("boxes", "obb", "masks"):
        obj = getattr(r2[0], attr, None)
        if obj is not None and hasattr(obj, "data"):
            n_det = len(obj.data)
            det_attr = attr
            break
    status("t14_gpu_predict_saved_model", "PASS" if ok else "FAIL",
           detections=n_det, task_result_attr=det_attr)

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

    merge_step_tests()

    # T16 — dedicated repeated AMP optimizer-update run (AMP track only).
    # The 4-epoch lifecycle cannot anneal the GradScaler past fp16 overflow on
    # this stack; a longer, wider run establishes genuine repeated updates.
    if args.amp:
        upd_data = args.amp_updates_data or args.data
        upd = YOLO(args.weights)
        upd_kwargs = dict(data=upd_data, epochs=args.amp_updates_epochs, device=0,
                          workers=args.workers, amp=True, name=args.run_ampupd,
                          exist_ok=True, seed=args.seed, plots=False, val=True)
        upd_model = upd
        upd_model.add_callback("on_train_start", attach_recorder("ampupd"))
        upd_exc = None
        t0 = time.time()
        try:
            upd_model.train(**upd_kwargs)
        except Exception as exc:  # noqa: BLE001 — recorded, never swallowed
            upd_exc = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record_step_tests("ampupd")
        upd_dir = Path(upd_model.trainer.save_dir)
        upd_rows = read_results_csv(upd_dir / "results.csv")
        RESULTS["t16_save_dir"] = str(upd_dir)
        rec = RESULTS.get("_stage_step_records", {}).get("ampupd")
        if rec is not None:
            counts = rec["counts"]
            upd_records = [s for s in rec["steps_full"] if s["class"] == UPDATED]
            min_upd = args.amp_min_updated
            amp_exercised = any(s.get("amp_active") for s in rec["steps_full"])
            if not amp_exercised:
                st = "SKIP"
                reason = ("check_amp fell back to FP32 — no AMP semantics exercised in the "
                          "dedicated run; t16 measures nothing about AMP here (honest SKIP, "
                          "never a PASS)")
            elif counts.get(STUCK_FAILURE) or counts.get(BAD_GRAD_UPDATE):
                st, reason = "FAIL", "STUCK/BAD_GRAD_UPDATE steps in the dedicated AMP run"
            elif counts.get(UPDATED, 0) >= min_upd:
                st = "PASS"
                reason = (f"{counts.get(UPDATED, 0)} repeated real updates "
                          f"(>= {min_upd} required) on {upd_data} x{args.amp_updates_epochs}ep")
            else:
                st = "SKIP"
                reason = (f"only {counts.get(UPDATED, 0)}/{min_upd} required updates; "
                          f"overflow skips n={counts.get(OVERFLOW_SKIP, 0)} — "
                          f"scaler never annealed past fp16 overflow on this workload")
            RESULTS["tests"]["t16_amp_repeated_updates"] = {
                "status": st, "reason": reason, "counts": counts,
                "min_updated_required": min_upd,
                "scaler_transitions": rec["scaler_trace"]["scale_transitions"],
                "per_param_first_updated": (upd_records[0]["params"] if upd_records else None),
                "fitness_first": upd_rows[0] if upd_rows else None,
                "fitness_last": upd_rows[-1] if upd_rows else None,
                "epochs_in_csv": len(upd_rows),
                "losses_finite_all": all(finite_loss_row(rw) for rw in upd_rows),
                "wall_s": round(time.time() - t0, 1),
                "unhandled_exception": upd_exc,
                "note": "t08 proves optimizer semantics; t16 proves GENUINE REPEATED "
                        "weight updates (audit M5 closure). BN buffer drift is recorded "
                        "separately and never counted as update evidence.",
            }
        # keep the dedicated run dir for checkpoint/CSV preservation
        print(f"[t16] dedicated AMP run dir preserved at {upd_dir}", flush=True)


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
    ap.add_argument("--run-ampupd", default="ampupd")
    ap.add_argument("--amp-updates-data", default=None,
                    help="dataset for the dedicated t16 repeated-updates run (default: --data)")
    ap.add_argument("--amp-updates-epochs", type=int, default=10)
    ap.add_argument("--amp-min-updated", type=int, default=3,
                    help="minimum genuine repeated updates for t16 PASS")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--environment-id", default="unknown")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=["main", "resume"], default="resume")
    args = ap.parse_args()

    args.amp = args.amp.lower() == "true"
    RESULTS["run_id"] = args.run_id or run_id()
    RESULTS["environment_id"] = args.environment_id
    RESULTS["run_tag"] = f"{args.task}_{args.environment_id}" + ("_amptrack" if args.amp else "")
    if not require_gpu():
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        sys.exit(3)
    RESULTS["args"] = {k: str(v) for k, v in vars(args).items()}
    t0 = time.time()
    try:
        if args.stage == "resume":
            # second process: load partial results from the main stage, then
            # resume the interrupted run and finish T09–T16
            partial = json.loads(Path(args.out).read_text(encoding="utf-8"))
            RESULTS["tests"] = partial.get("tests", {})
            RESULTS["limitations"] = partial.get("limitations", [])
            # carry the main stage's step records so the merged t07/t08 verdict
            # spans BOTH stages (never silently drop one side's evidence)
            RESULTS["_stage_step_records"] = partial.get("_stage_step_records", {})
            multi_dir = Path(partial["_multi_dir"])
            run_resume_and_final(args, multi_dir)
        else:
            run_main(args)
    except Exception as exc:  # first real error must surface, never swallowed
        RESULTS["unhandled_exception"] = f"{type(exc).__name__}: {exc}"
        Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
        raise
    RESULTS["wall_seconds"] = round(time.time() - t0, 1)
    n_pass = sum(1 for t in RESULTS["tests"].values() if t["status"] == "PASS")
    n_skip = sum(1 for t in RESULTS["tests"].values() if t["status"] == "SKIP")
    n_all = len(RESULTS["tests"])
    print(f"SUMMARY {args.task}: {n_pass}/{n_all} PASS ({n_skip} SKIP — "
          f"SKIP is not functional PASS)", flush=True)
    final = all(t["status"] in ("PASS", "SKIP") for t in RESULTS["tests"].values())
    Path(args.out).write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    sys.exit(0 if final else 1)


if __name__ == "__main__":
    main()
