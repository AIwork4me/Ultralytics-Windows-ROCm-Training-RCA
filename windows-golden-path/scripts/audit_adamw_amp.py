# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""DEFAULT optimizer=auto → AdamW + AMP audit (mission R22A.2 Part A).

Unlike audit_optimizer.py (frozen historical test: forces SGD, nbs=2,
workers=0), THIS harness must NOT force any optimizer: it requests the
Ultralytics DEFAULT `optimizer="auto"` and PASSES only if the real trainer
resolves it to torch.optim.AdamW and actually trains with AMP:

  - requested/resolved optimizer class + per-group lr/weight_decay recorded
  - normal nbs behaviour retained (NO nbs=2 forcing); effective gradient
    accumulation recorded as observed
  - real autocast participation inside forward (forward-pre-hook samples)
  - actual dtype of an eligible op under autocast (Conv2d output dtype)
  - attempted GradScaler steps counted SEPARATELY from underlying
    optimizer.step invocations (a scaler call that skipped step is never
    counted as an update — mission A12)
  - finite-gradient check across ALL param groups with non-None grads
  - named_parameters() before vs raw trainer model after; BatchNorm
    running-stat buffers snapshotted SEPARATELY and never counted as
    parameter-update evidence (mission A11)
  - >=3 confirmed optimizer update events required (mission A3)

    python audit_adamw_amp.py --out adamw.json --run-id R22A2-A \
        --run-dir <dir> [--data coco128.yaml]
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

MIN_UPDATES = 3


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


def evaluate_adamw_contract(facts: dict) -> dict:
    """Pure CPU-testable acceptance contract (mission §5 / §9).

    Takes OBSERVED facts (never a serialized verdict) and returns the verdict
    with per-check reasons. Synthetic fixtures can never pass: harness_fixture
    or missing GPU identity is rejected outright.
    """
    checks: list[dict] = []

    def check(name: str, ok: bool, why: str) -> bool:
        checks.append({"check": name, "ok": bool(ok), "detail": why})
        return bool(ok)

    synthetic = bool(facts.get("harness_fixture")) or not facts.get("gpu_name") \
        or not facts.get("gfx_target")
    if not check("physical_gpu_identity", not synthetic,
                 "synthetic/fixture evidence can never earn a physical PASS" if synthetic
                 else f"{facts.get('gpu_name')} / {facts.get('gfx_target')}"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "synthetic evidence rejected",
                "checks": checks}

    opt = str(facts.get("optimizer_class") or "")
    requested = str(facts.get("optimizer_requested") or "")
    if not check("optimizer_requested_auto", requested == "auto",
                 f"requested={requested!r} (harness must not force an optimizer)"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "harness forced an optimizer",
                "checks": checks}
    resolved_note = str(facts.get("optimizer_resolution_note") or "")
    if not check("optimizer_resolved_adamw", opt == "AdamW",
                 resolved_note or f"resolved optimizer class={opt!r}"):
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": f"optimizer=auto resolved to {opt!r}, not AdamW",
                "checks": checks}

    if not check("amp_resolved", bool(facts.get("amp_resolved")),
                 f"trainer amp={facts.get('amp_resolved')!r}"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "AMP not resolved on",
                "checks": checks}

    fwd_on = int(facts.get("autocast_forward_on") or 0)
    if not check("forward_autocast_active", fwd_on > 0,
                 f"{fwd_on} forward samples with autocast enabled"):
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": "AMP checks passed but autocast never active in forward",
                "checks": checks}

    lowp = int(facts.get("low_precision_op_samples") or 0)
    if lowp <= 0:
        # autocast active but no lower-precision operator evidence observed
        checks.append({"check": "low_precision_operator_evidence", "ok": False,
                       "detail": "no eligible op observed at lower precision"})
        return {"verdict": "ADAMW_AMP_INCONCLUSIVE",
                "reason": "autocast active but no lower-precision operator evidence",
                "checks": checks}

    confirmed = facts.get("confirmed_update_events")
    confirmed = int(confirmed) if confirmed is not None else None
    attempts = int(facts.get("scaler_step_attempts") or 0)
    underlying = int(facts.get("optimizer_steps_underlying") or 0)
    scaler_present = bool(facts.get("gradscaler_present"))
    if confirmed is None:
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": "missing confirmed-update evidence — per-step parameter "
                          "checksums are required (wrapper calls alone prove nothing)",
                "checks": checks + [{"check": "confirmed_update_evidence", "ok": False,
                                     "detail": "confirmed_update_events not recorded"}]}
    if confirmed <= 0:
        if scaler_present and attempts > 0:
            return {"verdict": "ADAMW_AMP_FAIL",
                    "reason": "GradScaler active but every step skipped — zero real optimizer updates",
                    "checks": checks + [{"check": "real_optimizer_updates", "ok": False,
                                         "detail": f"{attempts} scaler attempts "
                                                   f"({underlying} python-level step calls), "
                                                   "0 confirmed parameter updates"}]}
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "missing optimizer step evidence",
                "checks": checks + [{"check": "real_optimizer_updates", "ok": False,
                                     "detail": "no step observations recorded"}]}
    if not check("min_updates", confirmed >= MIN_UPDATES,
                 f"{confirmed} confirmed parameter-update events (checksum deltas); "
                 f"{underlying} python-level step calls; {attempts} scaler attempts"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "insufficient optimizer updates",
                "checks": checks}

    if not check("grads_finite_all_groups",
                 bool(facts.get("grads_finite_at_confirmed_updates")),
                 "finite grads at every CONFIRMED update across all groups "
                 "(skipped nonfinite steps recorded separately — they are the "
                 "GradScaler working as designed, not failures)"):
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": "nonfinite gradients at a confirmed update in at least "
                          "one parameter group",
                "checks": checks}

    raw = facts.get("raw_trainer_model_delta") or {}
    changed = int(raw.get("tensors_changed_beyond_1e-9") or 0)
    if not check("nonzero_parameter_deltas", changed > 0,
                 f"{changed} parameter tensors changed beyond 1e-9"):
        buf = int((facts.get("buffer_delta") or {}).get("tensors_changed_beyond_1e-9") or 0)
        reason = ("only BatchNorm-style buffer changes observed (parameters unchanged)"
                  if buf > 0 else "no parameter tensor changes")
        return {"verdict": "ADAMW_AMP_FAIL", "reason": reason, "checks": checks}

    if not check("parameter_deltas_finite", bool(raw.get("all_finite")),
                 "max_abs_delta finite for every parameter tensor"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "nonfinite parameter deltas",
                "checks": checks}

    if not check("training_completed", bool(facts.get("training_completed")),
                 "train() returned normally"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "training did not complete",
                "checks": checks}

    return {"verdict": "ADAMW_AMP_MULTISTEP_PASS", "reason": "all Part A checks satisfied",
            "checks": checks}


def main() -> None:
    import torch
    import torch.nn as nn
    import ultralytics
    from ultralytics import YOLO
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default="dev", help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R22A2")
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--imgsz", type=int, default=256)
    ap.add_argument("--workers", type=int, default=0, help="Part A isolates AdamW+AMP from worker behavior (mission §3)")
    ap.add_argument("--run-dir", required=True, help="disposable run dir")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    model = YOLO("yolo26n.pt")
    params0 = {k: v.detach().cpu().clone() for k, v in model.model.named_parameters()}
    buffers0 = {k: v.detach().cpu().clone() for k, v in model.model.named_buffers()}

    steps = {"underlying": 0, "scaler_attempts": 0, "confirmed": 0}
    step_events: list[dict] = []
    raw_snap: dict = {}
    scale_history: list[float] = []
    lr_at_step: list[float] = []
    autocast_fwd: list[bool] = []
    conv_dtypes: list[str] = []
    grads_finite_flags: list[bool] = []
    backward_count = {"n": 0}

    def param_checksum(model) -> float:
        return float(sum(p.detach().double().sum().item() for p in model.parameters()))

    def on_train_start(trainer):
        opt = trainer.optimizer
        orig = opt.step

        def counting_step(*a, **kw):
            # Python-level optimizer.step invocation. With a FUSED optimizer
            # under GradScaler, scaler.step invokes this on EVERY attempt and
            # the inf/skip decision happens INSIDE the fused kernel — so the
            # definitive update evidence is the parameter checksum delta,
            # never the wrapper call itself (mission A12).
            fin = True
            n_nonfinite = 0
            for group in opt.param_groups:
                for p in group["params"]:
                    if p.grad is not None and not bool(torch.isfinite(p.grad).all()):
                        fin = False
                        n_nonfinite += 1
            grads_finite_flags.append(fin)
            lr_at_step.append(float(group0_lr(opt)))
            scale = None
            if getattr(trainer, "scaler", None) is not None:
                scale = float(trainer.scaler.get_scale())
                scale_history.append(scale)
            pre = param_checksum(trainer.model)
            r = orig(*a, **kw)
            post = param_checksum(trainer.model)
            changed = pre != post
            if changed:
                steps["confirmed"] += 1
            steps["underlying"] += 1
            step_events.append({
                "step": steps["underlying"],
                "lr": lr_at_step[-1],
                "scaler_scale": scale,
                "pre_step_grads_finite": fin,
                "nonfinite_grad_tensors": n_nonfinite,
                "param_checksum_changed": changed,
            })
            return r

        opt.step = counting_step
        trainer._gp_opt_class = type(opt).__name__
        # NOTE: build_optimizer has ALREADY overwritten trainer.args.optimizer
        # with the resolved name when optimizer=auto; the REQUESTED value comes
        # from the harness train_kwargs (captured after train_kwargs below)
        trainer._gp_args_optimizer_at_start = str(trainer.args.optimizer)
        trainer._gp_opt_fused = bool(any(bool(g.get("fused"))
                                         for g in opt.param_groups))
        trainer._gp_opt_groups = [{
            "lr": g.get("lr"), "weight_decay": g.get("weight_decay"),
            "betas": [float(b) for b in g["betas"]] if "betas" in g else None,
            "n_params": len(g["params"]),
            "param_group": g.get("param_group"),
        } for g in opt.param_groups]
        trainer._gp_auto_note = (
            f"optimizer=auto resolved to {type(opt).__name__} "
            f"(8.4.x iterations heuristic: >10000 → MuSGD else AdamW)")

        scaler = getattr(trainer, "scaler", None)
        if scaler is not None and hasattr(scaler, "step"):
            orig_scaler = scaler.step

            def counting_scaler_step(*a, **kw):
                steps["scaler_attempts"] += 1
                return orig_scaler(*a, **kw)
            scaler.step = counting_scaler_step

        def _fwd_pre_hook(module, inputs):
            autocast_fwd.append(bool(torch.is_autocast_enabled()))
        trainer.model.register_forward_pre_hook(_fwd_pre_hook)

        # actual dtype of an eligible op under autocast (Conv2d output)
        for m in trainer.model.modules():
            if isinstance(m, nn.Conv2d):
                def _conv_out_hook(module, inputs, output):
                    conv_dtypes.append(str(output.dtype))
                m.register_forward_hook(_conv_out_hook)
                break

        first_param = next(trainer.model.parameters())

        def _grad_hook(grad):
            backward_count["n"] += 1
        first_param.register_hook(_grad_hook)

    def group0_lr(opt) -> float:
        return float(opt.param_groups[0]["lr"]) if opt.param_groups else float("nan")

    def on_train_end(trainer):
        raw_snap["params"] = {k: v.detach().cpu().clone()
                              for k, v in trainer.model.named_parameters()}
        raw_snap["buffers"] = {k: v.detach().cpu().clone()
                               for k, v in trainer.model.named_buffers()}
        raw_snap["accumulate"] = int(trainer.accumulate)
        raw_snap["amp"] = bool(trainer.amp)
        raw_snap["nbs"] = int(trainer.args.nbs)
        raw_snap["scaler_enabled"] = bool(trainer.scaler.is_enabled()) \
            if getattr(trainer, "scaler", None) is not None else False

    model.add_callback("on_train_start", on_train_start)
    model.add_callback("on_train_end", on_train_end)

    train_kwargs = dict(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        optimizer="auto",  # the Ultralytics DEFAULT — the trainer resolves it itself
        device=-1, workers=args.workers,
        project=str(run_dir.parent), name=run_dir.name, exist_ok=True,
        verbose=True, seed=42,
    )
    model.train(**train_kwargs)
    training_completed = True

    trainer = model.trainer
    params_loaded = dict(model.model.named_parameters())
    buffers_loaded = dict(model.model.named_buffers())
    raw_delta = delta_report(params0, raw_snap["params"]) if raw_snap else {}
    loaded_delta = delta_report(params0, params_loaded)
    buffer_delta = delta_report(buffers0, raw_snap["buffers"]) if raw_snap else {}

    n_backoff = sum(1 for i in range(1, len(scale_history))
                    if scale_history[i] < scale_history[i - 1]) if scale_history else 0
    lowp_dtypes = sorted(set(conv_dtypes) - {"torch.float32"})
    lowp_samples = sum(1 for d in conv_dtypes if d != "torch.float32")
    # confirmed update events = steps whose parameter checksum CHANGED; grads
    # "across observed updates" (mission §5) = finite at every CONFIRMED step.
    # Skipped steps (fused inf-guard) legitimately carry nonfinite grads —
    # that is precisely what GradScaler exists for; they are recorded, not
    # counted as failures unless EVERY step was skipped.
    confirmed_events = [e for e in step_events if e["param_checksum_changed"]]
    grads_finite_at_confirmed = (all(e["pre_step_grads_finite"]
                                     for e in confirmed_events)
                                 if confirmed_events else False)

    facts = {
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "optimizer_requested": str(train_kwargs.get("optimizer")),
        "optimizer_class": getattr(trainer, "_gp_opt_class", type(trainer.optimizer).__name__),
        "optimizer_resolution_note": facts_note if (facts_note := getattr(trainer, "_gp_auto_note", None)) else None,
        "optimizer_fused": bool(getattr(trainer, "_gp_opt_fused", False)),
        "amp_resolved": bool(getattr(trainer, "amp", False)),
        "autocast_forward_on": sum(autocast_fwd),
        "autocast_forward_samples": len(autocast_fwd),
        "conv_output_dtypes_observed": sorted(set(conv_dtypes)),
        "low_precision_dtype": lowp_dtypes[0] if lowp_dtypes else None,
        "low_precision_op_samples": lowp_samples,
        "optimizer_steps_underlying": steps["underlying"],
        "confirmed_update_events": steps["confirmed"],
        "scaler_step_attempts": steps["scaler_attempts"],
        "gradscaler_present": getattr(trainer, "scaler", None) is not None,
        "grads_finite_all_steps": all(grads_finite_flags) if grads_finite_flags else False,
        "grads_finite_at_confirmed_updates": grads_finite_at_confirmed,
        "raw_trainer_model_delta": raw_delta,
        "buffer_delta": buffer_delta,
        "training_completed": training_completed,
    }
    facts["gfx_target"] = gp_lib.gfx_from_device_name(facts["gpu_name"] or "")
    contract = evaluate_adamw_contract(facts)
    verdict = contract["verdict"]

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": facts["gpu_name"],
        "gfx_target": facts["gfx_target"], "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), args.channel,
            (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None)),
        "command": (f"python audit_adamw_amp.py --data {args.data} --epochs {args.epochs} "
                    f"--batch {args.batch} --imgsz {args.imgsz} (optimizer=auto, default nbs)"),
        "exit_code": 0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": "PASS" if verdict == "ADAMW_AMP_MULTISTEP_PASS" else (
            "INCONCLUSIVE" if verdict.endswith("INCONCLUSIVE") else "FAIL"),
        "failure_classification": None if verdict == "ADAMW_AMP_MULTISTEP_PASS" else "INCONCLUSIVE",
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "harness_disclosure": "Part A supplemental harness: optimizer=auto (NOT forced), "
                              "normal nbs retained, workers=0 to isolate AdamW+AMP from "
                              "Windows worker behavior",
        "harness_train_args": (f"epochs={args.epochs}, imgsz={args.imgsz}, batch={args.batch}, "
                               f"optimizer=auto, device=-1, workers={args.workers}"),
        "ultralytics_version": im.version("ultralytics"),
        "ultralytics_file": ultralytics.__file__,
        "optimizer": {
            "requested": facts["optimizer_requested"],
            "resolved_class": facts["optimizer_class"],
            "trainer_args_optimizer_after_resolution": getattr(
                trainer, "_gp_args_optimizer_at_start", None),
            "resolution_note": facts["optimizer_resolution_note"],
            "fused": facts["optimizer_fused"],
            "param_groups": getattr(trainer, "_gp_opt_groups", None),
        },
        "gradient_accumulation": {
            "nbs_requested": raw_snap.get("nbs"),
            "effective_accumulate": raw_snap.get("accumulate"),
            "note": "normal Ultralytics nbs default retained — NOT forced to step every batch",
        },
        "amp": {
            "resolved": facts["amp_resolved"],
            "scaler_present": facts["gradscaler_present"],
            "scaler_enabled": raw_snap.get("scaler_enabled"),
            "autocast_dtype_observed": facts["low_precision_dtype"],
            "conv_output_dtypes": facts["conv_output_dtypes_observed"],
        },
        "training_counts": {
            "forward_samples": len(autocast_fwd),
            "forward_autocast_on": sum(autocast_fwd),
            "backward_iterations": backward_count["n"],
            "scaler_step_attempts": steps["scaler_attempts"],
            "optimizer_steps_underlying": steps["underlying"],
            "confirmed_update_events": steps["confirmed"],
            "grads_finite_all_steps": facts["grads_finite_all_steps"],
            "grads_finite_at_confirmed_updates": facts["grads_finite_at_confirmed_updates"],
            "per_step_events": step_events,
            "step_event_semantics": "param_checksum_changed is the definitive update "
                                    "evidence; with fused AdamW under GradScaler the "
                                    "python-level step call runs on every scaler "
                                    "attempt and the inf skip happens inside the "
                                    "fused kernel (mission A12)",
        },
        "low_precision_evidence": {
            "conv_output_dtypes": facts["conv_output_dtypes_observed"],
            "samples_low_precision": facts["low_precision_op_samples"],
            "samples_total": len(conv_dtypes),
            "note": "observed dtype reported — no assumed FP16/BF16 label",
        },
        "gradscaler": {
            "present": facts["gradscaler_present"],
            "scale_history_len": len(scale_history),
            "scale_first": scale_history[0] if scale_history else None,
            "scale_history": scale_history,
            "scale_backoff_events_observed": n_backoff,
            "note": "backoff events counted from per-attempt history, not inferred "
                    "from endpoints; scale decrease alone is not failure evidence",
        },
        "raw_trainer_model_delta": raw_delta,
        "loaded_model_delta": loaded_delta,
        "buffer_delta_note": "named_buffers (incl. BatchNorm running stats) tracked "
                             "separately and NEVER counted as parameter updates",
        "buffer_delta": buffer_delta,
        "checkpoint": {"path": str(run_dir / "weights" / "last.pt"),
                       "exists": (run_dir / "weights" / "last.pt").exists()},
        "contract": contract,
    }
    gp_lib.write_evidence(record, Path(args.out))
    print(json.dumps({"verdict": verdict, "reason": contract["reason"],
                      "checks_ok": sum(1 for c in contract["checks"] if c["ok"]),
                      "checks_total": len(contract["checks"]),
                      "optimizer_class": facts["optimizer_class"],
                      "optimizer_fused": facts["optimizer_fused"],
                      "amp_resolved": facts["amp_resolved"],
                      "autocast_dtype_observed": facts["low_precision_dtype"],
                      "optimizer_steps_underlying": steps["underlying"],
                      "confirmed_update_events": steps["confirmed"],
                      "scaler_step_attempts": steps["scaler_attempts"],
                      "scaler_backoffs": n_backoff,
                      "accumulate": raw_snap.get("accumulate"),
                      "params_changed": (raw_delta or {}).get("tensors_changed_beyond_1e-9"),
                      "max_abs_delta": (raw_delta or {}).get("max_abs_delta"),
                      "grads_finite_at_confirmed_updates": facts["grads_finite_at_confirmed_updates"]},
                     indent=2))
    sys.exit(0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1)


if __name__ == "__main__":
    main()
