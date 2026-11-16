# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""UNIFIED default optimizer=auto → AdamW + AMP audit (R22A.2 Part A /
R22A.3 Part A / R22A.4 §6 — ONE implementation, both gfx1100 and gfx1151,
no architecture-specific hardcoding).

Distinct from audit_optimizer.py (R21 SGD supplementary harness) — that file
is historical evidence and stays untouched. This audit keeps the framework's
own defaults: optimizer="auto" (the framework must SELECT AdamW itself — a
manual optimizer="AdamW" would not prove auto selection), default AMP,
default nbs (normal gradient accumulation, NOT nbs=2), device=-1.

Proven-fact instrumentation only (no installed-wheel edits):
  - requested/recorded optimizer args + the REWRITTEN trainer.args.optimizer
    (build_optimizer('auto') rewrites args.optimizer to its choice)
  - public-instance wrapper of the REAL optimizer's step(): counts invocations,
    reads GradScaler's fused-path grad_scale/found_inf ATTRIBUTES when present,
    checks gradient finiteness across ALL param groups with non-None grads,
    and physically verifies each step by sentinel parameter deltas (smallest
    params from every group — fused AdamW may skip updates inside the kernel,
    so an invocation is only "effective" when parameters actually moved; a
    Python-level optimizer.step call is NEVER sufficient update evidence)
  - forward hooks on the backbone stem conv: autocast-enable flags (pre-hook)
    and the OBSERVED output dtype histogram (post-hook) inside train batches
  - full named_parameters snapshot before vs raw-trainer-model after vs loaded
    (EMA) model after — buffers snapshotted separately and never counted as
    parameter-update evidence
  - per-step GradScaler scale history (backoff counted from the series, never
    inferred from endpoints alone)

Verdict ADAMW_AMP_MULTISTEP_PASS requires every contract check to hold
(evaluate_adamw_contract); anything unverifiable is INCONCLUSIVE, never PASS;
synthetic/fixture evidence and harness-forced optimizers are rejected
outright. Historical receipts (R22A.2 flat schema, R22A.3 nested schema) are
re-evaluated through explicit adapters — their JSON bytes are never rewritten.

    python audit_adamw_amp.py --out adamw.json --run-id R22A4-A \
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

MIN_UPDATES = 3
LOW_PRECISION_DTYPES = ("float16", "bfloat16", "torch.float16", "torch.bfloat16")


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
        "tensors_changed_beyond_1e-9": changed,
        "tensors_changed_beyond_1e_9": changed,
        "max_abs_delta": max(deltas) if deltas else 0.0,
        "mean_abs_delta": (sum(deltas) / len(deltas)) if deltas else 0.0,
        "all_finite": all(m == m and m < float("inf") for m in deltas),
    }


def changed_tensors(delta: dict) -> int:
    """Both historical key spellings are accepted (schema adapters)."""
    if not isinstance(delta, dict):
        return 0
    for k in ("tensors_changed_beyond_1e-9", "tensors_changed_beyond_1e_9"):
        if k in delta:
            return int(delta[k] or 0)
    return 0


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


# --- UNIFIED pure acceptance contract (R22A.4 §6, CPU-testable) --------------

def evaluate_adamw_contract(facts: dict, min_updates: int = MIN_UPDATES) -> dict:
    """Pure CPU-testable AdamW+AMP acceptance contract.

    Takes OBSERVED flat facts (never a serialized verdict) and returns the
    verdict with per-check reasons. Synthetic fixtures can never pass;
    a harness that forced an optimizer can never pass. Architecture-dependent
    measurement differences (6 vs 7 effective updates on gfx1100 vs gfx1151)
    are facts, not targets — nothing here hardcodes either GPU.
    """
    checks: list[dict] = []

    def check(name: str, ok, why: str) -> bool:
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
    resolved_in_args = facts.get("optimizer_resolved_in_args")
    resolved_note = str(facts.get("optimizer_resolution_note") or "")
    if not check("optimizer_resolved_adamw", opt == "AdamW",
                 (resolved_note
                  or f"args.optimizer rewritten to {resolved_in_args!r}"
                  if resolved_in_args else
                  f"resolved optimizer class={opt!r}")):
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
    per_step = facts.get("per_step_events") or facts.get("per_step") or []
    scaler_present = bool(facts.get("gradscaler_present"))
    found_inf_events = facts.get("found_inf_events")
    found_inf_events = int(found_inf_events) if found_inf_events is not None else None

    if confirmed is None:
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": "missing confirmed-update evidence — per-step parameter "
                          "deltas/checksums are required (wrapper calls alone prove nothing)",
                "checks": checks + [{"check": "confirmed_update_evidence", "ok": False,
                                     "detail": "confirmed_update_events not recorded"}]}
    if not per_step:
        return {"verdict": "ADAMW_AMP_FAIL",
                "reason": "aggregate counts without a per-step series cannot prove "
                          "effective updates",
                "checks": checks + [{"check": "per_step_series_present", "ok": False,
                                     "detail": "no per-step event series recorded"}]}
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
    # internal consistency: effective updates cannot exceed the non-skipped steps
    if found_inf_events is not None and per_step:
        n_steps = int(underlying or len(per_step))
        if confirmed > n_steps - found_inf_events:
            return {"verdict": "ADAMW_AMP_FAIL",
                    "reason": f"inconsistent step accounting: {confirmed} effective "
                              f"updates > {n_steps} steps − {found_inf_events} found_inf skips",
                    "checks": checks + [{"check": "step_accounting_consistent", "ok": False,
                                         "detail": f"effective={confirmed}, steps={n_steps}, "
                                                   f"found_inf_skips={found_inf_events}"}]}
    check("step_accounting_consistent", True,
          f"{confirmed} effective of {underlying or len(per_step)} step calls"
          + (f", {found_inf_events} found_inf skips observed" if found_inf_events else ""))

    if not check("min_updates", confirmed >= min_updates,
                 f"{confirmed} confirmed parameter-update events (sentinel/checksum "
                 f"deltas); {underlying} python-level step calls; {attempts} scaler "
                 f"attempts (minimum required: {min_updates})"):
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
    changed = changed_tensors(raw)
    if not check("nonzero_parameter_deltas", changed > 0,
                 f"{changed} parameter tensors changed beyond 1e-9"):
        buf = changed_tensors(facts.get("buffer_delta") or {})
        reason = ("only BatchNorm-style buffer changes observed (parameters unchanged)"
                  if buf > 0 else "no parameter tensor changes")
        return {"verdict": "ADAMW_AMP_FAIL", "reason": reason, "checks": checks}

    if not check("parameter_deltas_finite", bool(raw.get("all_finite")),
                 "max_abs_delta finite for every parameter tensor"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "nonfinite parameter deltas",
                "checks": checks}

    training_completed = facts.get("training_completed")
    if training_completed is None:
        training_completed = (facts.get("training_exit_code") == 0)
    if not check("training_completed", bool(training_completed),
                 "train() returned normally / process exit 0"):
        return {"verdict": "ADAMW_AMP_FAIL", "reason": "training did not complete",
                "checks": checks}

    return {"verdict": "ADAMW_AMP_MULTISTEP_PASS", "reason": "all Part A checks satisfied",
            "checks": checks}


# --- versioned adapters for the two historical receipt schemas ---------------

def flat_facts_from_r22a2_record(rec: dict) -> dict:
    """Adapter: R22A.2 (gfx1100) flat receipt → unified flat facts.

    Every mapping is provenance-preserving; nothing is invented. Where the
    schema did not record a fact the field is left ABSENT so the contract
    treats it as unverifiable rather than optimistically true.
    """
    tc = rec.get("training_counts") or {}
    amp = rec.get("amp") or {}
    lpe = rec.get("low_precision_evidence") or {}
    opt = rec.get("optimizer") or {}
    per_step = tc.get("per_step_events") or []
    return {
        "gpu_name": rec.get("gpu_name"),
        "gfx_target": rec.get("gfx_target"),
        "harness_fixture": rec.get("harness_fixture"),
        "optimizer_requested": opt.get("requested"),
        "optimizer_class": opt.get("resolved_class"),
        "optimizer_resolved_in_args": opt.get("trainer_args_optimizer_after_resolution"),
        "optimizer_resolution_note": (opt or {}).get("resolution_note"),
        "amp_resolved": amp.get("resolved"),
        "autocast_forward_on": tc.get("forward_autocast_on"),
        "autocast_forward_samples": tc.get("forward_samples"),
        "low_precision_op_samples": lpe.get("samples_low_precision"),
        "low_precision_dtype": amp.get("autocast_dtype_observed"),
        "optimizer_steps_underlying": tc.get("optimizer_steps_underlying"),
        "scaler_step_attempts": tc.get("scaler_step_attempts"),
        "confirmed_update_events": tc.get("confirmed_update_events"),
        "per_step_events": per_step,
        "gradscaler_present": (rec.get("gradscaler") or {}).get("present"),
        "grads_finite_at_confirmed_updates": tc.get("grads_finite_at_confirmed_updates"),
        "raw_trainer_model_delta": rec.get("raw_trainer_model_delta"),
        "buffer_delta": rec.get("buffer_delta"),
        # schema recorded exit code 0 + post-training delta receipts; the
        # receipt itself documents train() returning normally
        "training_exit_code": rec.get("exit_code"),
        "_adapter": "r22a2-flat-v1",
    }


def flat_facts_from_r22a3_record(rec: dict) -> dict:
    """Adapter: R22A.3 (gfx1151) nested receipt → unified flat facts."""
    optim = rec.get("optim") or {}
    amp = rec.get("amp") or {}
    steps = rec.get("optimizer_steps") or {}
    dtypes = amp.get("stem_conv_output_dtypes_observed") or {}
    lowp = sum(int(v) for k, v in dtypes.items()
               if k in LOW_PRECISION_DTYPES)
    lowp_dtype = next((k for k, v in sorted(dtypes.items(), key=lambda kv: -kv[1])
                       if k in LOW_PRECISION_DTYPES), None)
    return {
        "gpu_name": rec.get("gpu_name"),
        "gfx_target": rec.get("gfx_target"),
        "harness_fixture": rec.get("harness_fixture"),
        "optimizer_requested": optim.get("requested"),
        "optimizer_class": optim.get("actual_class"),
        "optimizer_resolved_in_args": optim.get("resolved_in_args_after_build"),
        "amp_resolved": amp.get("trainer_amp_resolved"),
        "autocast_forward_on": (amp.get("autocast_forward_samples") or {}).get("enabled"),
        "autocast_forward_samples": (amp.get("autocast_forward_samples") or {}).get("sampled"),
        "low_precision_op_samples": lowp,
        "low_precision_dtype": lowp_dtype,
        "optimizer_steps_underlying": steps.get("attempted_invocations"),
        # this schema counts python-level step calls; scaler-attempt granularity
        # is not separately recorded (scale_history_len equals the step count)
        "scaler_step_attempts": steps.get("attempted_invocations"),
        "confirmed_update_events": steps.get("effective_updates_sentinel_proven"),
        "per_step_events": steps.get("per_step"),
        "found_inf_events": steps.get("skipped_found_inf_flagged"),
        "gradscaler_present": (rec.get("gradscaler") or {}).get("present"),
        "grads_finite_at_confirmed_updates": steps.get("grads_finite_on_stepped_updates"),
        "raw_trainer_model_delta": rec.get("raw_trainer_model_delta"),
        "training_exit_code": rec.get("exit_code"),
        "_adapter": "r22a3-nested-v1",
    }


def compute_adamw_verdict(ev: dict, min_updates: int = MIN_UPDATES) -> dict:
    """DEPRECATED compat wrapper (R22A.3 name) — adapts the nested fact
    structure to the unified flat contract. Assertions view preserved for
    historical consumers; the unified contract is the authority."""
    facts = flat_facts_from_r22a3_record(ev) if "optim" in ev or "optimizer_steps" in ev \
        else dict(ev)
    out = evaluate_adamw_contract(facts, min_updates)
    assertions = {c["check"]: c["ok"] for c in out["checks"]}
    out["assertions"] = assertions
    out["effective_updates"] = facts.get("confirmed_update_events")
    out["attempted_invocations"] = facts.get("optimizer_steps_underlying")
    out["failure_classification"] = None if out["verdict"] == "ADAMW_AMP_MULTISTEP_PASS" \
        else out["reason"]
    return out


def main() -> None:
    import torch
    import torch.amp  # noqa: F401
    import torch.nn as nn
    import ultralytics
    from ultralytics import YOLO
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default="dev")
    ap.add_argument("--mission", default="R22A.4")
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--imgsz", type=int, default=256)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--workers", type=int, default=0,
                    help="Part A isolates AdamW+AMP from worker behavior (mission §3)")
    ap.add_argument("--min-updates", type=int, default=3)
    ap.add_argument("--run-dir", required=True, help="fresh disposable run dir")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    model = YOLO("yolo26n.pt")
    params0 = {k: v.detach().cpu().clone() for k, v in model.model.named_parameters()}
    buffers0 = {k: v.detach().cpu().clone() for k, v in model.model.named_buffers()}

    steps: list[dict] = []
    scale_history: list[float] = []
    raw_snap: dict = {}
    facts: dict = {}
    lr_samples: list[float] = []
    batches_done = {"n": 0}
    autocast_fwd: list[bool] = []
    conv_out_dtypes: dict[str, int] = {}
    in_train_batch = {"on": False}
    final_scale = {"v": None}

    def on_train_start(trainer):
        opt = trainer.optimizer
        facts["optimizer_class"] = type(opt).__name__
        facts["optimizer_fused"] = bool(any(bool(g.get("fused"))
                                            for g in opt.param_groups))
        facts["optimizer_module"] = type(opt).__module__
        facts["optimizer_requested_in_train_call"] = "auto"  # from train_kwargs below
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
                "param_checksum_changed": moved > 0.0,
                "lr_first_group": lr_samples[-1],
                "accumulate_now": trainer.accumulate,
                "batch_index": batches_done["n"],
            })
            sent_before = {k: v.detach().clone() for k, v in sent_tensors.items()}
            return r

        opt.step = counting_step

        # autocast participation inside forward + dtype of an eligible op
        # (stem conv) — observed, never assumed (train-batch-gated)
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

        for m in trainer.model.modules():
            if isinstance(m, nn.Conv2d):
                def _conv_out_hook(module, inputs, output):
                    if in_train_batch["on"] and isinstance(output, torch.Tensor):
                        d = str(output.dtype).replace("torch.", "")
                        conv_out_dtypes[d] = conv_out_dtypes.get(d, 0) + 1
                m.register_forward_hook(_conv_out_hook)
                break

    def on_train_batch_start(trainer):
        in_train_batch["on"] = True

    def on_train_batch_end(trainer):
        in_train_batch["on"] = False
        batches_done["n"] += 1

    def on_train_end(trainer):
        raw_snap["params"] = {k: v.detach().cpu().clone()
                              for k, v in trainer.model.named_parameters()}
        raw_snap["buffers"] = {k: v.detach().cpu().clone()
                               for k, v in trainer.model.named_buffers()}
        raw_snap["accumulate"] = int(trainer.accumulate)
        raw_snap["nbs"] = int(trainer.args.nbs)
        if getattr(trainer, "scaler", None) is not None:
            final_scale["v"] = float(trainer.scaler.get_scale())

    for cb, fn in (("on_train_start", on_train_start),
                   ("on_train_batch_start", on_train_batch_start),
                   ("on_train_batch_end", on_train_batch_end),
                   ("on_train_end", on_train_end)):
        model.add_callback(cb, fn)

    train_kwargs = dict(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        # the framework must select the optimizer itself (never forced)
        optimizer="auto",
        device=args.device, workers=args.workers,
        project=str(run_dir.parent), name=run_dir.name, exist_ok=True,
        verbose=True, seed=42,
    )
    # deliberately NOT setting nbs / lr0 / amp — framework defaults apply
    model.train(**train_kwargs)
    training_completed = True

    trainer = model.trainer
    effective = [s for s in steps if s["sentinel_max_abs_delta"] > 0.0]
    skipped = [s for s in steps if s.get("found_inf_any") is True]
    n_backoff = sum(1 for i in range(1, len(scale_history))
                    if scale_history[i] < scale_history[i - 1]) if scale_history else 0
    params_loaded = dict(model.model.named_parameters())
    raw_delta = delta_report(params0, raw_snap["params"]) if raw_snap else {}
    loaded_delta = delta_report(params0, params_loaded)
    buffer_delta = delta_report(buffers0, raw_snap.get("buffers") or {}) if raw_snap else {}
    ckpt = run_dir / "weights" / "last.pt"
    ckpt_sha = gp_lib.sha256_file(ckpt) if ckpt.exists() else None

    low_prec = {k: v for k, v in conv_out_dtypes.items() if k in LOW_PRECISION_DTYPES}
    lowp_samples = sum(low_prec.values())

    flat_facts = {
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "optimizer_requested": str(train_kwargs.get("optimizer")),
        "optimizer_class": facts.get("optimizer_class"),
        "optimizer_resolved_in_args": facts.get("optimizer_resolved_in_args"),
        "optimizer_resolution_note": (
            f"optimizer=auto resolved to {facts.get('optimizer_class')} "
            f"(8.4.x iterations heuristic: >10000 → MuSGD else AdamW)"),
        "amp_resolved": facts.get("amp_resolved"),
        "autocast_forward_on": sum(autocast_fwd),
        "autocast_forward_samples": len(autocast_fwd),
        "low_precision_op_samples": lowp_samples,
        "low_precision_dtype": next(iter(sorted(low_prec.items(), key=lambda kv: -kv[1])), (None,))[0],
        "optimizer_steps_underlying": len(steps),
        "scaler_step_attempts": len(steps),
        "confirmed_update_events": len(effective),
        "per_step_events": steps,
        "found_inf_events": len(skipped),
        "gradscaler_present": facts.get("scaler_present"),
        "grads_finite_at_confirmed_updates": (
            all(s["grads_all_finite"] for s in steps if s.get("found_inf_any") is not True)
            if steps else False),
        "raw_trainer_model_delta": raw_delta,
        "buffer_delta": buffer_delta,
        "training_completed": training_completed,
    }
    flat_facts["gfx_target"] = gp_lib.gfx_from_device_name(flat_facts["gpu_name"] or "")
    contract = evaluate_adamw_contract(flat_facts)
    verdict = contract["verdict"]

    miopen = gp_lib.loaded_miopen_identity()
    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "source_sha": git_head(),
        "gpu_name": flat_facts["gpu_name"],
        "gfx_target": flat_facts["gfx_target"], "windows_build": gp_lib.windows_build(),
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
        "exit_code": 0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": None if verdict == "ADAMW_AMP_MULTISTEP_PASS"
        else contract["reason"],
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "harness_train_args": (f"epochs={args.epochs}, imgsz={args.imgsz}, batch={args.batch}, "
                               f"optimizer='auto', device={args.device}, workers={args.workers}, "
                               "amp=default, nbs=default"),
        "harness_disclosure": "unified Part A supplemental harness: optimizer=auto (NOT "
                              "forced), normal nbs retained, workers=0 to isolate AdamW+AMP "
                              "from Windows worker behavior",
        "ultralytics_install_path": ultralytics.__file__,
        "optimizer": {
            "requested": flat_facts["optimizer_requested"],
            "resolved_class": facts.get("optimizer_class"),
            "trainer_args_optimizer_after_resolution": facts.get("optimizer_resolved_in_args"),
            "resolution_note": flat_facts["optimizer_resolution_note"],
            "fused": facts.get("optimizer_fused"),
            "param_groups": facts.get("param_groups"),
        },
        "gradient_accumulation": {
            "nbs": facts.get("nbs"),
            "batch_size": facts.get("batch_size"),
            "nb_batches_per_epoch": facts.get("nb_batches_per_epoch"),
            "accumulate_at_start": facts.get("accumulate_at_start"),
            "note": "normal Ultralytics nbs default retained — NOT forced to step every batch",
        },
        "amp": {
            "resolved": facts.get("amp_resolved"),
            "scaler_present": facts.get("scaler_present"),
            "scaler_enabled": facts.get("scaler_enabled"),
            "autocast_dtype_observed": flat_facts["low_precision_dtype"],
            "stem_conv_output_dtypes_observed": conv_out_dtypes,
            "autocast_forward_samples": {"sampled": len(autocast_fwd),
                                         "enabled": sum(autocast_fwd)},
        },
        "low_precision_evidence": {
            "conv_output_dtypes": dict(sorted(conv_out_dtypes.items())),
            "samples_low_precision": lowp_samples,
            "samples_total": sum(conv_out_dtypes.values()),
            "note": "observed dtype reported — no assumed FP16/BF16 label",
        },
        "training_counts": {
            "forward_samples": len(autocast_fwd),
            "forward_autocast_on": sum(autocast_fwd),
            "batches_completed": batches_done["n"],
            "scaler_step_attempts": len(steps),
            "optimizer_steps_underlying": len(steps),
            "confirmed_update_events": len(effective),
            "skipped_found_inf_flagged": len(skipped),
            "grads_finite_on_stepped_updates": flat_facts["grads_finite_at_confirmed_updates"],
            "per_step_events": steps,
            "step_event_semantics": "sentinel_max_abs_delta > 0 is the definitive update "
                                    "evidence; with fused AdamW under GradScaler the "
                                    "python-level step call runs on every scaler attempt "
                                    "and the inf skip happens inside the fused kernel",
        },
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
        "buffer_delta": buffer_delta,
        "buffer_delta_note": "named_buffers (incl. BatchNorm running stats) tracked "
                             "separately and NEVER counted as parameter updates",
        "minimum_effective_updates_required": args.min_updates,
        "checkpoint": {"path": str(ckpt), "exists": ckpt.exists(), "sha256": ckpt_sha},
        "contract": contract,
    }
    record = sanitize(record)
    try:
        gp_lib.write_evidence(record, Path(args.out))
    except Exception as e:  # a receipt MUST exist even if the strict writer objects
        Path(args.out).write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=repr), encoding="utf-8")
        print(f"WRITE_EVIDENCE_STRICT_FAILED ({type(e).__name__}: {e}) — "
              "fallback receipt written", file=sys.stderr)
    print(json.dumps({"verdict": verdict, "reason": contract["reason"],
                      "checks_ok": sum(1 for c in contract["checks"] if c["ok"]),
                      "checks_total": len(contract["checks"]),
                      "optimizer_class": facts.get("optimizer_class"),
                      "optimizer_fused": facts.get("optimizer_fused"),
                      "amp_resolved": facts.get("amp_resolved"),
                      "autocast_dtype_observed": flat_facts["low_precision_dtype"],
                      "optimizer_steps_underlying": len(steps),
                      "confirmed_update_events": len(effective),
                      "skipped_found_inf": len(skipped),
                      "scaler_backoffs": n_backoff,
                      "raw_delta_changed": changed_tensors(raw_delta),
                      "grads_finite_at_confirmed_updates":
                          flat_facts["grads_finite_at_confirmed_updates"]},
                     indent=2))
    sys.exit(0 if verdict == "ADAMW_AMP_MULTISTEP_PASS" else 1)


if __name__ == "__main__":
    main()
