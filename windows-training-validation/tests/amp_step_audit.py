"""AMP/optimizer-step audit — per-parameter tensor-delta verification with
GradScaler instrumentation (P8-finding closure; mission §3.1/§3.2).

Replaces the old aggregate ``sum(abs(param))`` delta (which can conceal
tensor changes through cancellation and cannot identify skipped steps) with:

- actual per-tensor before/after snapshots -> max-abs tensor delta,
  count of changed tensors / elements (float64 math, snapshots discarded
  immediately — no long-term tensor retention)
- GradScaler instrumentation: scaled-grad finite/inf/nan census, unscale
  found_inf state, skip decision, scale transitions
- step classification distinguishing WARMUP_SKIP (lr==0), OVERFLOW_SKIP
  (scaler-handled inf/NaN), UPDATED, STUCK_FAILURE (lr>0, no overflow,
  params unchanged) and BAD_GRAD_UPDATE (step executed with non-finite grads)

Classification is a pure function of the observation dict (``classify_step``)
so adversarial tests can run on CPU without GPU or Ultralytics. StepRecorder
attaches to any trainer exposing the 8.4.182 call pattern
``optimizer_step() -> scaler.unscale_/clip/scaler.step/scaler.update`` (a
duck-typed mock is used in tests). Module importable without GPU.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

# ---- classification vocabulary -------------------------------------------------

WARMUP_SKIP = "WARMUP_SKIP"          # lr == 0: warmup schedule legitimately changes nothing
OVERFLOW_SKIP = "OVERFLOW_SKIP"      # GradScaler found inf/NaN -> skipped step + scale anneal (intended)
UPDATED = "UPDATED"                  # params actually changed (per-parameter evidence)
STUCK_FAILURE = "STUCK_FAILURE"      # lr > 0, no overflow, params unchanged -> real training failure
BAD_GRAD_UPDATE = "BAD_GRAD_UPDATE"  # step executed although grads were non-finite and unsanctioned
NO_GRAD = "NO_GRAD"                  # no gradients materialized at the step opportunity

# t07 (gradient health) verdicts
G_OK = "OK"                          # grads healthy (or scaler-sanctioned overflow skip)
G_OK_SKIP = "OK_SCALER_SKIP"         # non-finite scaled grads, but scaler flagged + skipped (intended)
G_FAIL = "FAIL"                      # unsanctioned non-finite grads


def classify_step(obs: dict) -> str:
    """Classify one optimizer-step opportunity from its observation record.

    Required keys: lr, stepped, amp_active, found_inf, unscaled_any_nonfinite.
    ``found_inf`` is the GradScaler's own authoritative overflow flag (read after
    ``scaler.unscale_``); a *valid* overflow skip exists only under an ACTIVE
    scaler — non-finite grads in FP32 (or without scaler sanction) are training
    failures, never "overflow skips".
    """
    stepped = bool(obs["stepped"])
    amp_overflow = bool(obs.get("amp_active")) and bool(obs["found_inf"])
    nonfinite = bool(obs.get("unscaled_any_nonfinite")) or bool(obs.get("scaled_any_nonfinite"))
    if not obs.get("has_grads", True):
        return NO_GRAD
    if stepped:
        # the scaler never lets sanctioned overflow reach the optimizer; stepping
        # through non-finite grads is an anomaly, not AMP semantics
        if nonfinite:
            return BAD_GRAD_UPDATE
        return UPDATED
    lr = float(obs["lr"])
    if lr == 0.0:
        return WARMUP_SKIP
    if amp_overflow:
        return OVERFLOW_SKIP
    return STUCK_FAILURE


def classify_gradient_health(obs: dict) -> str:
    """t07 per-step verdict. Under AMP, non-finite SCALED grads are the normal
    overflow signal and are acceptable ONLY when the scaler flagged them
    (found_inf) and skipped the step — never an unconditional PASS."""
    scaled_bad = bool(obs.get("scaled_any_nonfinite"))
    unscaled_bad = bool(obs.get("unscaled_any_nonfinite"))
    found_inf = bool(obs.get("found_inf"))
    if unscaled_bad and not found_inf:
        return G_FAIL  # FP32 NaN/Inf, or scaler failed to flag — real anomaly
    if scaled_bad and not unscaled_bad:
        return G_FAIL  # inconsistent state (cannot occur under real torch semantics)
    if scaled_bad and found_inf and not bool(obs.get("stepped")):
        return G_OK_SKIP  # scaler-handled overflow — separately classified event
    if scaled_bad or unscaled_bad:
        return G_FAIL  # non-finite grads neither sanctioned nor skipped
    return G_OK


def _grad_census(params) -> dict:
    n = finite = inf = nan = 0
    for p in params:
        if p.grad is None:
            continue
        n += 1
        g = p.grad.detach()
        if not torch.isfinite(g).all().item():
            if torch.isnan(g).any().item():
                nan += 1
            if torch.isinf(g).any().item():
                inf += 1
        else:
            finite += 1
    return {"n_params_with_grad": n, "n_finite": finite, "n_inf": inf, "n_nan": nan,
            "any_nonfinite": (inf + nan) > 0}


def _tensor_delta(cur: torch.Tensor, snap: torch.Tensor) -> tuple[float, bool, int]:
    """(max_abs_delta, changed, n_elems_changed) in float64; NaN delta counts as
    changed (a NaN parameter is the strongest possible update anomaly)."""
    d = (cur.double() - snap.double()).abs()
    has_nan = bool(torch.isnan(d).any().item())
    n_elems = int((d > 0).sum().item()) + (int(torch.isnan(d).sum().item()) if has_nan else 0)
    m = float(d.max().item()) if d.numel() else 0.0
    if has_nan:
        m = float("inf")
    changed = m > 0.0
    return m, changed, n_elems


def _param_delta_records(before: list, params, buffers_before=None, buffers=None) -> dict:
    """Per-tensor float64 deltas; snapshots discarded immediately after use.

    Trainable parameters are the update evidence. Non-trainable buffers (BN
    running_mean/running_var, num_batches_tracked) change on FORWARD passes,
    not optimizer steps — recorded separately for disclosure only and never
    counted as weight-update evidence (audit M5: fitness drift without weight
    updates is exactly this mechanism).
    """
    n_float = n_float_changed = 0
    n_int_changed = 0
    n_elems_changed = 0
    max_delta = 0.0
    per_tensor_max = []
    for snap, p in zip(before, params):
        cur = p.detach()
        if not cur.is_floating_point():
            if not torch.equal(snap, cur):
                n_int_changed += 1
            per_tensor_max.append(None)
            continue
        m, changed, n_elems = _tensor_delta(cur, snap)
        per_tensor_max.append(m)
        n_float += 1
        if changed:
            n_float_changed += 1
            n_elems_changed += n_elems
            max_delta = max(max_delta, m)
    buf = {"n_buffers": 0, "n_buffers_changed": 0, "max_abs_buffer_delta": 0.0,
           "n_buffers_int_changed": 0}
    if buffers_before is not None and buffers is not None:
        for snap_b, b in zip(buffers_before, buffers):
            cur = b.detach()
            buf["n_buffers"] += 1
            if not cur.is_floating_point():
                if not torch.equal(snap_b, cur):
                    buf["n_buffers_int_changed"] += 1
                continue
            m, changed, _ = _tensor_delta(cur, snap_b)
            if changed:
                buf["n_buffers_changed"] += 1
                buf["max_abs_buffer_delta"] = max(buf["max_abs_buffer_delta"], m)
    return {"n_tensors_float": n_float, "n_tensors_changed": n_float_changed,
            "n_elements_changed": n_elems_changed, "n_tensors_int_changed": n_int_changed,
            "max_abs_tensor_delta": max_delta, "per_tensor_max_abs_delta": per_tensor_max,
            "buffers": buf}


def _snap_params(params) -> list:
    return [p.detach().clone() for p in params]


class StepRecorder:
    """Attach to an ultralytics trainer (or duck-typed mock) and record every
    optimizer-step opportunity with per-parameter evidence + scaler state.

    Usage: ``rec = StepRecorder(trainer); rec.attach()`` before ``train()``.
    Verdicts: ``rec.t07_record(min_steps)`` / ``rec.t08_record(min_steps)``.
    """

    def __init__(self, trainer, label: str = ""):
        self.trainer = trainer
        self.label = label
        self.steps: list[dict] = []
        self._scale_transitions: list[dict] = []
        self._attached = False
        self._in_step = False

    # -- attach ---------------------------------------------------------------
    def attach(self) -> None:
        tr = self.trainer
        existing = getattr(tr, "_step_audit_recorder", None)
        if existing is self:
            return  # idempotent re-attach
        if existing is not None:
            raise RuntimeError("another StepRecorder is already attached to this trainer")
        orig_step = tr.optimizer_step
        scaler = getattr(tr, "scaler", None)

        if scaler is not None and not getattr(scaler, "_audit_wrapped", False):
            orig_scaler_step = scaler.step
            orig_scaler_update = scaler.update

            def scaler_step(optimizer, *a, **kw):
                # entered after scaler.unscale_: grads are in the UNSCALED domain.
                # torch>=2.4 exposes found_inf via the per-optimizer METHOD
                # scaler._found_inf_per_device(optimizer) -> {device: tensor}.
                # A probe error is recorded, never silently swallowed.
                try:
                    fid = scaler._found_inf_per_device(optimizer)
                    found_inf = any(float(v.item()) > 0 for v in fid.values())
                    fid_err = None
                except Exception as exc:  # noqa: BLE001 — surfaced in the record
                    found_inf, fid_err = False, f"{type(exc).__name__}: {exc}"
                unscaled = _grad_census(tr.model.parameters())
                self._last_scaler_step = {"found_inf": found_inf, "found_inf_probe_error": fid_err,
                                          "unscaled_grad_census": unscaled}
                return orig_scaler_step(optimizer, *a, **kw)

            def scaler_update(*a, **kw):
                s_before = float(scaler.get_scale())
                out = orig_scaler_update(*a, **kw)
                s_after = float(scaler.get_scale())
                if s_after != s_before:
                    self._scale_transitions.append({"before": s_before, "after": s_after})
                return out

            scaler.step = scaler_step
            scaler.update = scaler_update
            scaler._audit_wrapped = True  # idempotent across re-attach on same trainer
        self._orig_optimizer_step = orig_step

        def wrapped_optimizer_step():
            if self._in_step:  # re-entrancy guard
                return self._orig_optimizer_step()
            self._in_step = True
            try:
                lr = None
                try:
                    lr = float(tr.optimizer.param_groups[0]["lr"])
                except (AttributeError, KeyError, IndexError):
                    pass
                scaled = _grad_census(tr.model.parameters())
                amp_active = bool(getattr(tr, "amp", False)) and bool(
                    getattr(scaler, "_enabled", False)) if scaler is not None else False
                scale_before = float(scaler.get_scale()) if scaler is not None else None
                before = _snap_params(tr.model.parameters())
                buffers_before = [b.detach().clone() for b in tr.model.buffers()]
                self._last_scaler_step = None
                self._orig_optimizer_step()
                scale_after = float(scaler.get_scale()) if scaler is not None else None
                deltas = _param_delta_records(before, list(tr.model.parameters()),
                                              buffers_before, list(tr.model.buffers()))
                del before, buffers_before
                if self._last_scaler_step is not None:
                    found_inf = bool(self._last_scaler_step["found_inf"])
                    fid_err = self._last_scaler_step.get("found_inf_probe_error")
                    unscaled_census = self._last_scaler_step["unscaled_grad_census"]
                else:
                    # scaler.step not observed (test-only paths); raw backward
                    # grads are the unscaled-equivalent domain
                    found_inf, fid_err = False, None
                    unscaled_census = scaled
                # "stepped" = float parameters actually changed. int-only changes
                # (BN num_batches_tracked) are NOT weight-update evidence.
                stepped = deltas["n_tensors_changed"] > 0
                obs = {
                    "lr": lr if lr is not None else 0.0,
                    "amp_active": amp_active,
                    "scaled_grad_census": scaled,
                    "scaled_any_nonfinite": scaled["any_nonfinite"],
                    "found_inf": found_inf,
                    "found_inf_probe_error": fid_err,
                    "unscaled_grad_census": unscaled_census,
                    "unscaled_any_nonfinite": unscaled_census["any_nonfinite"],
                    "has_grads": scaled["n_params_with_grad"] > 0,
                    "stepped": stepped,
                    "params": deltas,
                    "scale_before": scale_before,
                    "scale_after": scale_after,
                }
                obs["classification"] = classify_step(obs)
                obs["gradient_health"] = classify_gradient_health(obs)
                self.steps.append(obs)
            finally:
                self._in_step = False
            return None

        tr.optimizer_step = wrapped_optimizer_step
        tr._step_audit_recorder = self
        self._attached = True

    # -- verdicts --------------------------------------------------------------
    def counts(self) -> dict:
        c = {"total": len(self.steps)}
        for k in (WARMUP_SKIP, OVERFLOW_SKIP, UPDATED, STUCK_FAILURE, BAD_GRAD_UPDATE, NO_GRAD):
            c[k] = sum(1 for s in self.steps if s["classification"] == k)
        return c

    def t07_record(self) -> dict:
        """Strict gradient-health verdict — no unconditional AMP PASS."""
        if not self.steps:
            return {"status": "SKIP", "reason": "no optimizer-step opportunity observed",
                    "steps": []}
        fails = [i for i, s in enumerate(self.steps) if s["gradient_health"] == G_FAIL]
        skips = sum(1 for s in self.steps if s["gradient_health"] == G_OK_SKIP)
        status = "FAIL" if fails else "PASS"
        return {"status": status,
                "n_steps": len(self.steps), "n_scaler_handled_overflow": skips,
                "failed_step_indices": fails,
                "note": ("scaled-domain grads are inspected pre-unscale; non-finite there is "
                         "acceptable only as a scaler-sanctioned skipped step (G_OK_SKIP)"),
                "step_health": [s["gradient_health"] for s in self.steps],
                "last_scaled_census": self.steps[-1]["scaled_grad_census"]}

    def t08_record(self, min_updated: int = 1) -> dict:
        """Optimizer-step verdict from per-parameter evidence.
        SKIP is reported honestly (e.g. all steps were warmup/overflow skips);
        it must never be counted as a functional PASS downstream."""
        if not self.steps:
            return {"status": "SKIP", "reason": "no optimizer-step opportunity observed",
                    "counts": self.counts()}
        c = self.counts()
        if c["STUCK_FAILURE"] or c["BAD_GRAD_UPDATE"]:
            bad = [i for i, s in enumerate(self.steps)
                   if s["classification"] in (STUCK_FAILURE, BAD_GRAD_UPDATE)]
            return {"status": "FAIL", "failed_step_indices": bad, "counts": c,
                    "reason": "real training failure: lr>0 steps without parameter change "
                              "(STUCK) or update executed with non-finite grads"}
        if c["UPDATED"] >= min_updated:
            upd = [s for s in self.steps if s["classification"] == UPDATED]
            first = upd[0]["params"]
            return {"status": "PASS", "counts": c, "min_updated_required": min_updated,
                    "first_updated_step": {k: first[k] for k in
                                           ("n_tensors_float", "n_tensors_changed",
                                            "n_elements_changed", "max_abs_tensor_delta")},
                    "max_abs_tensor_delta_all_updated":
                        max(s["params"]["max_abs_tensor_delta"] for s in upd),
                    "per_tensor_max_abs_delta_first_updated": first["per_tensor_max_abs_delta"],
                    "note": "per-parameter evidence; int tensors (num_batches_tracked) excluded"}
        if c["OVERFLOW_SKIP"] and c["UPDATED"] < min_updated:
            return {"status": "SKIP", "counts": c, "min_updated_required": min_updated,
                    "reason": f"all lr>0 steps were intended GradScaler overflow skips "
                              f"(n={c['OVERFLOW_SKIP']}); workload too short for the scaler "
                              f"to anneal past fp16 overflow on this stack — run the "
                              f"repeated-updates leg (t16) for real update evidence"}
        return {"status": "SKIP", "counts": c, "min_updated_required": min_updated,
                "reason": "only warmup (lr=0) steps observed"}

    def scaler_trace(self) -> dict:
        return {"scale_transitions": list(self._scale_transitions),
                "n_transitions": len(self._scale_transitions)}


# torch imported last so the classification helpers stay importable in
# torch-free lint contexts; tests and recorders require torch anyway.
import torch  # noqa: E402


def run_id() -> str:
    """Immutable per-run identifier (time-ordered prefix + short uuid)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"
