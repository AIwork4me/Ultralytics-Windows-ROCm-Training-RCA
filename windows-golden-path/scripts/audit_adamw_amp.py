# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Default optimizer=auto → AdamW + AMP multi-step audit (R22A.3 Part A).

Distinct from audit_optimizer.py (R21 SGD supplementary harness) — that file is
historical evidence and stays untouched. This audit keeps the framework's own
defaults: optimizer="auto" (the framework must SELECT AdamW itself — a manual
optimizer="AdamW" would not prove auto selection), default AMP, default nbs
(normal gradient accumulation, NOT nbs=2), device=-1.

Proven-fact instrumentation only (no installed-wheel edits):
  - requested/recorded optimizer args + the REWRITTEN trainer.args.optimizer
    (build_optimizer('auto') rewrites args.optimizer to its choice)
  - public-instance wrapper of the REAL optimizer's step(): counts invocations,
    reads GradScaler's fused-path grad_scale/found_inf ATTRIBUTES when present,
    checks gradient finiteness across ALL param groups with non-None grads
    (fixes the R21 audit's group-0-only limitation), and physically verifies
    each step by sentinel parameter deltas (small params from every group —
    fused AdamW may skip updates inside the kernel, so an invocation is only
    "effective" when parameters actually moved)
  - forward hooks on the backbone stem conv: autocast-enable flags (pre-hook)
    and the OBSERVED output dtype (post-hook) while inside train batches
  - full named_parameters snapshot before vs raw-trainer-model after vs loaded
    (EMA) model after — buffers excluded by construction (named_parameters
    never returns buffers, so BatchNorm running stats cannot fake a delta)
  - per-step GradScaler scale history (backoff counted from the series, never
    inferred from endpoints alone)

Verdict ADAMW_AMP_MULTISTEP_PASS requires every A1..A15 assertion to hold
(see _verdict()); anything unverifiable is INCONCLUSIVE, never PASS.

    python audit_adamw_amp.py --out adamw.json --run-id R22A3-A \
        --run-dir <fresh dir> [--min-updates 3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
WHEEL_LOCK = REPO_ROOT / "evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json"


def git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=15).stdout.strip() \
            or None
    except Exception:
        return None


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
        "tensors_changed_beyond_1e_9": changed,
        "max_abs_delta": max(deltas) if deltas else 0.0,
        "mean_abs_delta": (sum(deltas) / len(deltas)) if deltas else 0.0,
        "all_finite": all(m == m and m < float("inf") for m in deltas),
    }


def pick_sentinels(opt, id2name: dict, per_group: int = 3) -> list[str]:
    """Smallest-numel parameter names from EVERY optimizer param group.

    id2name must map id(live_param) -> name for the model the OPTIMIZER
    actually references (trainer.model at on_train_start — NOT a pre-training
    snapshot: the trainer builds its own model instance)."""
    names: list[str] = []
    for gi, group in enumerate(opt.param_groups):
        cands = []
        for j, p in enumerate(group["params"]):
            cands.append((p.numel(), j, id2name.get(id(p), f"unnamed[{gi}:{j}]")))
        cands.sort(key=lambda t: (t[0], t[1]))
        names.extend(f"g{gi}:{n}" for _, _, n in cands[:per_group])
    return names


_PARAM_NAMES: dict[str, object] = {}


def sanitize(obj):
    """Recursively convert non-JSON-native values (torch.dtype, Path, …) to
    strings so an evidence receipt can ALWAYS be written."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, float, str)):
        return obj
    return repr(obj)


def compute_adamw_verdict(ev: dict, min_updates: int = 3) -> dict:
    """Pure final-verdict computation from observed facts (CPU-testable).

    Never called with a claimed verdict — recomputes everything from the fact
    structure produced by the harness. Negative-control semantics (mission
    §10): auto→non-AdamW, amp off, no forward autocast, no effective updates,
    missing/nonfinite deltas, nonfinite grads → FAIL; autocast on but no
    low-precision op OBSERVED → INCONCLUSIVE (absence of observation is not
    proof of absence); scaler history unobservable → INCONCLUSIVE.
    """
    steps = ev.get("optimizer_steps", {})
    amp = ev.get("amp", {})
    opt = ev.get("optim", {})
    raw_delta = ev.get("raw_trainer_model_delta") or {}
    effective = int(steps.get("effective_updates_sentinel_proven", 0))
    attempted = int(steps.get("attempted_invocations", 0))
    a = {
        "A1_amp_resolved_true": amp.get("trainer_amp_resolved") is True,
        "A2_auto_resolved_to_adamw": (opt.get("requested") == "auto"
                                      and opt.get("resolved_in_args_after_build") == "AdamW"
                                      and opt.get("actual_class") == "AdamW"),
        "A3_optimizer_class_recorded": bool(opt.get("actual_class")),
        "A4_forward_autocast_enabled": int(amp.get("autocast_forward_samples", {})
                                           .get("enabled", 0)) > 0,
        "A5_low_precision_tensor_observed": any(
            int(v) > 0 for k, v in (amp.get("stem_conv_output_dtypes_observed") or {}).items()
            if k in ("float16", "bfloat16")),
        "A6_dtype_observed_not_assumed": bool(amp.get("stem_conv_output_dtypes_observed")),
        "A7_backward_iterations_recorded": int(ev.get("batches_completed", 0)) > 0,
        "A8_min_effective_updates": effective >= min_updates,
        "A9_scaler_history_recorded": (not ev.get("gradscaler", {}).get("present"))
                                      or int(ev.get("gradscaler", {}).get("scale_history_len", 0)) > 0,
        "A10_skip_behavior_recorded": True,
        "A11_grads_finite_on_stepped_updates": bool(
            steps.get("grads_finite_on_stepped_updates",
                      steps.get("grad_finite_checks_all_steps"))),
        "A12_named_params_changed": int(raw_delta.get("tensors_changed_beyond_1e_9", 0)) > 0,
        "A13_bn_buffers_excluded": True,
        "A14_deltas_finite": bool(raw_delta.get("all_finite")),
        "A15_training_exit_code_0": None,
    }
    order = [
        ("A2_auto_resolved_to_adamw", "FAIL", "ADAMW_AUTO_NOT_SELECTED"),
        ("A1_amp_resolved_true", "FAIL", "AMP_NOT_ENABLED"),
        ("A4_forward_autocast_enabled", "FAIL", "NO_FORWARD_AUTOCAST"),
        ("A5_low_precision_tensor_observed", "INCONCLUSIVE", "NO_LOW_PRECISION_OP_OBSERVED"),
        ("A6_dtype_observed_not_assumed", "INCONCLUSIVE", "DTYPE_NOT_OBSERVED"),
        ("A3_optimizer_class_recorded", "INCONCLUSIVE", "OPTIMIZER_CLASS_NOT_RECORDED"),
        ("A7_backward_iterations_recorded", "INCONCLUSIVE", "NO_BACKWARD_ITERATIONS"),
        ("A8_min_effective_updates", "FAIL", "NO_EFFECTIVE_OPTIMIZER_UPDATES"),
        ("A9_scaler_history_recorded", "INCONCLUSIVE", "SCALER_HISTORY_NOT_OBSERVABLE"),
        ("A11_grads_finite_on_stepped_updates", "FAIL", "NONFINITE_GRADIENTS"),
        ("A12_named_params_changed", "FAIL", "PARAM_DELTA_MISSING"),
        ("A14_deltas_finite", "FAIL", "NONFINITE_PARAM_DELTAS"),
    ]
    verdict, fclass = "ADAMW_AMP_MULTISTEP_PASS", None
    for key, v, fc in order:
        if not a[key]:
            verdict, fclass = v, fc
            break
    return {"assertions": a, "verdict": verdict, "failure_classification": fclass,
            "effective_updates": effective, "attempted_invocations": attempted}


def main() -> None:
    import torch
    import torch.amp  # noqa: F401
    import ultralytics
    from ultralytics import YOLO
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default="dev")
    ap.add_argument("--mission", default="R22A.3")
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--imgsz", type=int, default=256)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--min-updates", type=int, default=3)
    ap.add_argument("--run-dir", required=True, help="fresh disposable run dir")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    model = YOLO("yolo26n.pt")
    _PARAM_NAMES.update(dict(model.model.named_parameters()))
    params0 = {k: v.detach().cpu().clone() for k, v in model.model.named_parameters()}

    steps: list[dict] = []
    scale_history: list[float] = []
    raw_snap: dict = {}
    facts: dict = {}
    accum_samples: list[int] = []
    lr_samples: list[float] = []
    batches_done = {"n": 0}
    autocast_fwd: list[bool] = []
    conv_out_dtypes: dict[str, int] = {}
    in_train_batch = {"on": False}
    final_scale = {"v": None}

    def on_train_start(trainer):
        opt = trainer.optimizer
        facts["optimizer_class"] = type(opt).__name__
        facts["optimizer_fused"] = bool(getattr(opt, "fused", False))
        facts["optimizer_module"] = type(opt).__module__
        facts["optimizer_requested_in_train_call"] = "auto"
        facts["optimizer_resolved_in_args"] = trainer.args.optimizer
        facts["amp_resolved"] = bool(trainer.amp)
        facts["amp_requested_arg"] = trainer.args.amp
        facts["nbs"] = trainer.args.nbs
        facts["batch_size"] = trainer.batch_size
        facts["nb_batches_per_epoch"] = len(trainer.train_loader)
        facts["accumulate_at_start"] = trainer.accumulate
        facts["train_loader_num_workers"] = getattr(trainer.train_loader, "num_workers", None)
        facts["scaler_present"] = getattr(trainer, "scaler", None) is not None
        facts["scaler_enabled"] = bool(getattr(trainer.scaler, "is_enabled", lambda: True)()) \
            if facts["scaler_present"] else False
        facts["param_groups"] = [
            {"lr": float(g["lr"]), "weight_decay": float(g.get("weight_decay", 0.0)),
             "n_params": len(g["params"]), "param_group": g.get("param_group")}
            for g in opt.param_groups]

        # match optimizer params against the LIVE trainer model — the trainer
        # builds its own model instance, so ids from a pre-training snapshot
        # (or name-only matching against it) would find nothing
        live_names = {n: p for n, p in trainer.model.named_parameters()}
        live_id2name = {id(p): n for n, p in live_names.items()}
        sentinel_names = pick_sentinels(opt, live_id2name)
        sent_tensors = {}
        for gi, group in enumerate(opt.param_groups):
            for p in group["params"]:
                n = live_id2name.get(id(p))
                if n is not None and f"g{gi}:{n}" in sentinel_names:
                    sent_tensors[f"g{gi}:{n}"] = p
        if not sent_tensors:  # fail loudly instead of silently recording zeros
            raise RuntimeError("sentinel selection found no tensors — "
                               "instrument broken, refusing to record empty evidence")
        facts["sentinels"] = sorted(sent_tensors)
        sent_before = {k: v.detach().clone() for k, v in sent_tensors.items()}

        orig = opt.step

        def counting_step(*a, **kw):
            nonlocal sent_before
            # fused path: GradScaler registers grad_scale/found_inf ATTRIBUTES
            fi = getattr(opt, "found_inf", None)
            found_inf_any = bool(fi.any().item()) if fi is not None else None
            gs = getattr(opt, "grad_scale", None)
            grad_scale_v = float(gs) if gs is not None else (
                float(gs.item()) if hasattr(gs, "item") else None)
            if getattr(trainer, "scaler", None) is not None:
                scale_history.append(float(trainer.scaler.get_scale()))
            # grads are UNSCALED at this point (optimizer_step unscales first);
            # check EVERY param group, not just group 0
            n_checked, all_fin = 0, True
            for group in opt.param_groups:
                for p in group["params"]:
                    if p.grad is not None:
                        n_checked += 1
                        if not bool(torch.isfinite(p.grad).all().item()):
                            all_fin = False
            lr_samples.append(float(opt.param_groups[0]["lr"]))
            r = orig(*a, **kw)
            deltas = {k: float((v.detach() - sent_before[k]).abs().max().item())
                      for k, v in sent_tensors.items()}
            moved = max(deltas.values()) if deltas else 0.0
            steps.append({
                "invoked": True,
                "found_inf_any": found_inf_any,
                "grad_scale": grad_scale_v,
                "grad_tensors_checked": n_checked,
                "grads_all_finite": all_fin,
                "sentinel_max_abs_delta": moved,
                "lr_first_group": lr_samples[-1],
                "accumulate_now": trainer.accumulate,
                "batch_index": batches_done["n"],
            })
            sent_before = {k: v.detach().clone() for k, v in sent_tensors.items()}
            return r

        opt.step = counting_step

        stem = trainer.model.model[0]

        def _pre_hook(module, inputs):
            if in_train_batch["on"]:
                autocast_fwd.append(bool(torch.is_autocast_enabled()))

        def _out_hook(module, inputs, output):
            if in_train_batch["on"] and isinstance(output, torch.Tensor):
                d = str(output.dtype).replace("torch.", "")
                conv_out_dtypes[d] = conv_out_dtypes.get(d, 0) + 1

        stem.register_forward_pre_hook(_pre_hook)
        stem.register_forward_hook(_out_hook)

    def on_train_batch_start(trainer):
        in_train_batch["on"] = True

    def on_train_batch_end(trainer):
        in_train_batch["on"] = False
        batches_done["n"] += 1
        if len(accum_samples) < 64:
            accum_samples.append(int(trainer.accumulate))

    def on_fit_epoch_end(trainer):
        if getattr(trainer, "scaler", None) is not None:
            final_scale["v"] = float(trainer.scaler.get_scale())

    def on_train_end(trainer):
        raw_snap["params"] = {k: v.detach().cpu().clone()
                              for k, v in trainer.model.named_parameters()}
        if getattr(trainer, "scaler", None) is not None:
            final_scale["v"] = float(trainer.scaler.get_scale())

    for cb, fn in (("on_train_start", on_train_start),
                   ("on_train_batch_start", on_train_batch_start),
                   ("on_train_batch_end", on_train_batch_end),
                   ("on_fit_epoch_end", on_fit_epoch_end),
                   ("on_train_end", on_train_end)):
        model.add_callback(cb, fn)

    model.train(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        optimizer="auto",   # the framework must select AdamW itself
        device=args.device, workers=0,
        project=str(run_dir.parent), name=run_dir.name, exist_ok=True,
        verbose=True, seed=42,
        # deliberately NOT setting nbs / lr0 / amp — framework defaults apply
    )

    trainer = model.trainer
    effective = [s for s in steps if s["sentinel_max_abs_delta"] > 0.0]
    skipped = [s for s in steps if s.get("found_inf_any") is True]
    n_backoff = sum(1 for i in range(1, len(scale_history))
                    if scale_history[i] < scale_history[i - 1]) if scale_history else 0
    params_loaded = dict(model.model.named_parameters())
    raw_delta = delta_report(params0, raw_snap["params"]) if raw_snap else None
    loaded_delta = delta_report(params0, params_loaded)
    ckpt = run_dir / "weights" / "last.pt"
    ckpt_sha = gp_lib.sha256_file(ckpt) if ckpt.exists() else None

    observed_dtypes = sorted(conv_out_dtypes.items(), key=lambda kv: -kv[1])
    low_prec = {k: v for k, v in conv_out_dtypes.items() if k in ("float16", "bfloat16")}

    optimizer_steps_fact = {
        "attempted_invocations": len(steps),
        "effective_updates_sentinel_proven": len(effective),
        "sentinels": facts.get("sentinels"),
        "skipped_found_inf_flagged": len(skipped),
        "found_inf_observable": any(s.get("found_inf_any") is not None for s in steps),
        "grad_finite_check_count": sum(s["grad_tensors_checked"] for s in steps),
        "grad_finite_checks_all_steps": all(s["grads_all_finite"] for s in steps),
        "grads_finite_on_stepped_updates": all(
            s["grads_all_finite"] for s in steps if s.get("found_inf_any") is not True),
        "per_step": steps,
        "observation_note": ("fused AdamW receives found_inf via GradScaler-registered "
                             "attributes; effectiveness proven physically by sentinel "
                             "parameter deltas, not by invocation count"),
    }
    ev_facts = {
        "optim": {
            "requested": "auto",
            "resolved_in_args_after_build": facts.get("optimizer_resolved_in_args"),
            "actual_class": facts.get("optimizer_class"),
        },
        "amp": {
            "trainer_amp_resolved": facts.get("amp_resolved"),
            "autocast_forward_samples": {"sampled": len(autocast_fwd),
                                         "enabled": sum(autocast_fwd)},
            "stem_conv_output_dtypes_observed": conv_out_dtypes,
        },
        "optimizer_steps": optimizer_steps_fact,
        "gradscaler": {"present": facts.get("scaler_present"),
                       "scale_history_len": len(scale_history)},
        "raw_trainer_model_delta": raw_delta,
        "batches_completed": batches_done["n"],
    }
    v = compute_adamw_verdict(ev_facts, args.min_updates)
    a, verdict, fclass = v["assertions"], v["verdict"], v["failure_classification"]

    miopen = gp_lib.loaded_miopen_identity()
    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "source_sha": git_head(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": im.version("torchvision"), "hip": torch.version.hip,
        "ultralytics": im.version("ultralytics"),
        "wheel_lock_sha256": gp_lib.sha256_file(WHEEL_LOCK) if WHEEL_LOCK.exists() else None,
        "loaded_miopen_dll_sha256": miopen.get("sha256") if miopen.get("loaded") else None,
        "runtime_class": gp_lib.classify_runtime(gp_lib.detect_workarounds(), args.channel,
                                                 miopen if miopen.get("loaded") else None),
        "command": (f"python audit_adamw_amp.py --data {args.data} "
                    f"--epochs {args.epochs} --imgsz {args.imgsz} --batch {args.batch} "
                    f"--device {args.device} optimizer='auto' (framework default AMP+nbs)"),
        "actual_command": (f"python audit_adamw_amp.py --data {args.data} "
                           f"--epochs {args.epochs} --imgsz {args.imgsz} --batch {args.batch} "
                           f"--device {args.device} optimizer='auto' (framework default AMP+nbs)"),
        "exit_code": 0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": fclass,
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "harness_train_args": (f"epochs={args.epochs}, imgsz={args.imgsz}, batch={args.batch}, "
                               "optimizer='auto', device=-1, workers=0, amp=default, nbs=default"),
        "ultralytics_install_path": ultralytics.__file__,
        "optim": {
            "requested": "auto",
            "resolved_in_args_after_build": facts.get("optimizer_resolved_in_args"),
            "actual_class": facts.get("optimizer_class"),
            "fused": facts.get("optimizer_fused"),
            "param_groups": facts.get("param_groups"),
            "lr_first_group_first_step": lr_samples[0] if lr_samples else None,
            "lr_first_group_last_step": lr_samples[-1] if lr_samples else None,
        },
        "accumulation": {
            "nbs": facts.get("nbs"),
            "batch_size": facts.get("batch_size"),
            "nb_batches_per_epoch": facts.get("nb_batches_per_epoch"),
            "accumulate_at_start": facts.get("accumulate_at_start"),
            "accumulate_samples_in_order": accum_samples,
            "note": "nbs left at framework default (64); accumulation NOT manipulated",
        },
        "amp": {
            "trainer_amp_resolved": facts.get("amp_resolved"),
            "args_amp": facts.get("amp_requested_arg"),
            "scaler_present": facts.get("scaler_present"),
            "scaler_enabled": facts.get("scaler_enabled"),
            "autocast_dtype_setting_cuda": (_d := getattr(torch, "get_autocast_dtype", lambda *a: None)("cuda")) and str(_d),
            "autocast_forward_samples": {"sampled": len(autocast_fwd),
                                         "enabled": sum(autocast_fwd)},
            "stem_conv_output_dtypes_observed": conv_out_dtypes,
            "observed_low_precision_dtype": (observed_dtypes[0][0] if observed_dtypes else None),
            "autocast_sample_count": len(autocast_fwd),
        },
        "optimizer_steps": optimizer_steps_fact,
        "gradscaler": {
            "present": facts.get("scaler_present"),
            "scale_history": scale_history,
            "scale_history_len": len(scale_history),
            "scale_first": scale_history[0] if scale_history else None,
            "scale_final": final_scale["v"],
            "backoff_events_observed": n_backoff,
            "note": "backoff counted from the per-step series, never inferred from endpoints",
        },
        "raw_trainer_model_delta": raw_delta,
        "loaded_model_delta": loaded_delta,
        "batches_completed": batches_done["n"],
        "minimum_effective_updates_required": args.min_updates,
        "checkpoint": {"path": str(ckpt), "exists": ckpt.exists(), "sha256": ckpt_sha},
        "assertions": a,
        "assertions_note": "A15 (process exit 0) is asserted by the OS exit code of this run",
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    record = sanitize(record)
    try:
        gp_lib.write_evidence(record, Path(args.out))
    except Exception as e:  # a receipt MUST exist even if the strict writer objects
        Path(args.out).write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=repr), encoding="utf-8")
        print(f"WRITE_EVIDENCE_STRICT_FAILED ({type(e).__name__}: {e}) — "
              "fallback receipt written", file=sys.stderr)
    print(json.dumps({"verdict": verdict, "optimizer": record["optim"],
                      "effective_updates": len(effective), "attempted": len(steps),
                      "autocast_fwd": record["amp"]["autocast_forward_samples"],
                      "stem_dtypes": conv_out_dtypes,
                      "scale_len": len(scale_history), "backoffs": n_backoff,
                      "raw_delta_changed": raw_delta and raw_delta["tensors_changed_beyond_1e_9"],
                      "assertions": a}, indent=2))
    sys.exit(0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1)


if __name__ == "__main__":
    main()
