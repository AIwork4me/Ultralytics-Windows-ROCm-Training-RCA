"""Adversarial CPU tests for amp_step_audit (mission §3.1/§3.2 item 5).

Runs WITHOUT GPU and WITHOUT Ultralytics: a duck-typed mock trainer replicates
the 8.4.182 call pattern ``optimizer_step() -> scaler.unscale_/clip/
scaler.step/scaler.update`` with real torch.amp.GradScaler semantics on CPU.

    python tests/test_amp_step_audit_cpu.py [--verbose]

Proves the instrumentation independently:
  - per-parameter deltas catch aggregate-cancellation the old sum(|p|) check
    concealed (the t08 rewrite justification)
  - int-only tensor changes (BN num_batches_tracked) never count as updates
  - overflow skips / warmup skips / stuck steps / bad-grad updates are each
    classified exactly, and every misbehaving scenario FAILs or is SKIPped
    honestly (never PASS)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amp_step_audit import (BAD_GRAD_UPDATE, NO_GRAD, OVERFLOW_SKIP, STUCK_FAILURE,
                            UPDATED, WARMUP_SKIP, StepRecorder, classify_step)

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


class MockTrainer:
    """Replicates BaseTrainer.optimizer_step (8.4.182) call pattern."""

    def __init__(self, model: torch.nn.Module, lr: float = 0.1, amp: bool = False,
                 ignore_scaler: bool = False, noop_optimizer: bool = False,
                 custom_step=None):
        self.model = model
        self.amp = amp
        self.scaler = torch.amp.GradScaler("cpu", enabled=amp)
        self.optimizer = torch.optim.SGD(model.parameters(), lr=lr)
        self.ignore_scaler = ignore_scaler      # steps even when scaler would skip
        self.noop_optimizer = noop_optimizer    # never touches params (STUCK sim)
        self.custom_step = custom_step          # fn(model) called in-lieu of opt step
        self.optimizer_step_calls = 0

    def optimizer_step(self):
        self.optimizer_step_calls += 1
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
        if self.ignore_scaler:
            self.optimizer.step()
        elif self.noop_optimizer:
            pass
        elif self.custom_step is not None:
            self.custom_step(self.model)
        else:
            self.scaler.step(self.optimizer)
        self.scaler.update()
        self.optimizer.zero_grad()


def run_steps(tr: MockTrainer, rec: StepRecorder, n: int, loss_fn, plant_inf_at=None):
    rec.attach()
    torch.manual_seed(0)
    for i in range(n):
        loss = loss_fn(tr.model)
        if tr.amp:
            # real GradScaler requires scaler.scale() before backward
            tr.scaler.scale(loss).backward()
        else:
            loss.backward()
        if plant_inf_at is not None and i in plant_inf_at:
            with torch.no_grad():
                list(tr.model.parameters())[0].grad[0] = float("inf")
        tr.optimizer_step()


def linear_loss(model):
    x = torch.ones(2, 4)
    return model(x).square().mean()


# ---------------------------------------------------------------- pure classify
def test_pure_classification():
    base = {"lr": 0.01, "stepped": False, "amp_active": True, "found_inf": True,
            "scaled_any_nonfinite": True, "unscaled_any_nonfinite": True, "has_grads": True}
    check("classify: AMP found_inf skip -> OVERFLOW_SKIP",
          classify_step(base) == OVERFLOW_SKIP)
    check("classify: AMP found_inf with lr=0 -> WARMUP_SKIP",
          classify_step({**base, "lr": 0.0}) == WARMUP_SKIP)
    check("classify: clean step -> UPDATED",
          classify_step({**base, "stepped": True, "found_inf": False,
                         "scaled_any_nonfinite": False,
                         "unscaled_any_nonfinite": False}) == UPDATED)
    check("classify: FP32 NaN grads (no scaler) not stepped -> STUCK_FAILURE",
          classify_step({**base, "amp_active": False, "found_inf": False,
                         "scaled_any_nonfinite": True,
                         "unscaled_any_nonfinite": True}) == STUCK_FAILURE)
    check("classify: stepped through NaN grads -> BAD_GRAD_UPDATE",
          classify_step({**base, "amp_active": False, "found_inf": False, "stepped": True,
                         "scaled_any_nonfinite": True,
                         "unscaled_any_nonfinite": True}) == BAD_GRAD_UPDATE)
    check("classify: no grads -> NO_GRAD",
          classify_step({**base, "has_grads": False}) == NO_GRAD)
    check("classify: AMP overflow without amp_active flag -> STUCK_FAILURE (conservative)",
          classify_step({**base, "amp_active": False}) == STUCK_FAILURE)


# ---------------------------------------------------------------- fp32 healthy
def test_fp32_repeated_updates():
    torch.manual_seed(1)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.1, amp=False)
    rec = StepRecorder(tr, "fp32")
    run_steps(tr, rec, 5, linear_loss)
    r8 = rec.t08_record(min_updated=3)
    check("fp32: t08 PASS with 5 repeated updates", r8["status"] == "PASS"
          and r8["counts"][UPDATED] == 5, str(r8))
    check("fp32: every float tensor changed each step",
          all(s["params"]["n_tensors_changed"] == s["params"]["n_tensors_float"]
              for s in rec.steps))
    check("fp32: per-parameter max delta > 0 recorded",
          r8["max_abs_tensor_delta_all_updated"] > 0)
    r7 = rec.t07_record()
    check("fp32: t07 strict PASS", r7["status"] == "PASS", str(r7))


# ------------------------------------------------- aggregate-cancellation trap
def test_cancellation_concealment():
    """Old harness measured sum(|p|) before/after: engineered cancellation keeps
    that aggregate EXACTLY constant while two tensors really changed — the old
    t08 would have reported no update; per-parameter evidence catches it."""
    torch.manual_seed(2)
    m = torch.nn.Linear(4, 4)
    with torch.no_grad():
        m.weight.fill_(1.0)
        m.bias.fill_(1.0)

    def cancel(model):
        with torch.no_grad():
            model.weight[0, 0] += 0.5   # |w| sum +0.5
            model.bias[0] -= 0.5        # |b| sum -0.5 -> total unchanged
        return None

    tr = MockTrainer(m, lr=0.1, custom_step=cancel)
    rec = StepRecorder(tr, "cancel")
    run_steps(tr, rec, 1, linear_loss)
    agg = sum(float(p.detach().abs().sum()) for p in m.parameters())
    s = rec.steps[0]
    check("cancellation: aggregate sum(|p|) delta == 0 (old method blind)",
          abs(agg - 20.0) < 1e-6, f"agg={agg}")
    check("cancellation: per-parameter evidence catches both tensors",
          s["stepped"] and s["classification"] == UPDATED
          and s["params"]["n_tensors_changed"] == 2
          and s["params"]["max_abs_tensor_delta"] == 0.5, str(s["params"]))
    check("cancellation: t08 PASS on per-parameter evidence",
          rec.t08_record(min_updated=1)["status"] == "PASS")


# ------------------------------------------------------- int-tensor not update
def test_int_only_change_not_an_update():
    torch.manual_seed(3)
    m = torch.nn.Sequential(torch.nn.BatchNorm1d(4), torch.nn.Linear(4, 4))
    m.train()
    x = torch.randn(8, 4)

    def bump_int(model):
        with torch.no_grad():
            model[0].num_batches_tracked += 1   # int tensor only
        return None

    tr = MockTrainer(m, lr=0.1, custom_step=bump_int)
    rec = StepRecorder(tr, "intonly")
    run_steps(tr, rec, 2, lambda mm: mm(x).square().mean())
    s = rec.steps[0]
    check("int-only: not counted as weight update",
          not s["stepped"] and s["classification"] == STUCK_FAILURE, str(s["classification"]))
    check("int-only: buffer (num_batches_tracked) change disclosed separately, never update evidence",
          s["params"]["buffers"]["n_buffers_int_changed"] >= 1
          and s["params"]["n_tensors_changed"] == 0, str(s["params"]["buffers"]))
    check("int-only: t08 FAILs (real training failure, not PASS/SKIP)",
          rec.t08_record(min_updated=1)["status"] == "FAIL")


# ------------------------------------------------------------------ warmup
def test_warmup_lr0():
    torch.manual_seed(4)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.0, amp=False)
    rec = StepRecorder(tr, "warmup")
    run_steps(tr, rec, 3, linear_loss)
    r8 = rec.t08_record(min_updated=1)
    check("warmup: SKIP (never PASS)", r8["status"] == "SKIP", str(r8))
    check("warmup: all steps WARMUP_SKIP",
          r8["counts"][WARMUP_SKIP] == 3 and r8["counts"][UPDATED] == 0)


# ------------------------------------------------------- AMP overflow handling
def test_amp_overflow_then_updates():
    torch.manual_seed(5)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.1, amp=True)
    rec = StepRecorder(tr, "amp")
    run_steps(tr, rec, 6, linear_loss, plant_inf_at={0, 1, 2})
    c = rec.counts()
    check("amp: planted inf -> 3 OVERFLOW_SKIP with real GradScaler",
          c[OVERFLOW_SKIP] == 3, str(c))
    check("amp: 3 real UPDATED steps after anneal", c[UPDATED] == 3)
    check("amp: scale halved at each overflow (transition trace)",
          len(rec.scaler_trace()["scale_transitions"]) == 3
          and rec.scaler_trace()["scale_transitions"][0]["after"]
          < rec.scaler_trace()["scale_transitions"][0]["before"],
          str(rec.scaler_trace()))
    r7 = rec.t07_record()
    check("amp: t07 PASS with scaler-handled overflow classified separately",
          r7["status"] == "PASS" and r7["n_scaler_handled_overflow"] == 3, str(r7))
    r8 = rec.t08_record(min_updated=3)
    check("amp: t08 PASS requires >=3 repeated updates", r8["status"] == "PASS")
    r8b = rec.t08_record(min_updated=10)
    check("amp: t08 honest SKIP when updates < min and skips were intended",
          r8b["status"] == "SKIP" and "overflow" in r8b["reason"], str(r8b))


def test_amp_all_overflow_no_update():
    torch.manual_seed(6)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.1, amp=True)
    rec = StepRecorder(tr, "ampoverflow")
    run_steps(tr, rec, 4, linear_loss, plant_inf_at={0, 1, 2, 3})
    r8 = rec.t08_record(min_updated=3)
    check("amp all-skip: honest SKIP, UPDATED count 0, never PASS",
          r8["status"] == "SKIP" and r8["counts"][UPDATED] == 0, str(r8))
    # the historical t08 FAIL signature (aggregate delta 0.0 @ lr>0) is now an
    # intended skip, and the intended-skip count is explicit
    check("amp all-skip: overflow skip count explicit", r8["counts"][OVERFLOW_SKIP] == 4)


# --------------------------------------------------------------------- stuck
def test_stuck_failure():
    torch.manual_seed(7)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.01, noop_optimizer=True)
    rec = StepRecorder(tr, "stuck")
    run_steps(tr, rec, 3, linear_loss)
    r8 = rec.t08_record(min_updated=1)
    check("stuck: t08 FAIL (real failure, not SKIP/PASS)",
          r8["status"] == "FAIL" and r8["counts"][STUCK_FAILURE] == 3, str(r8))
    check("stuck: lr>0 disclosed", all(s["lr"] > 0 for s in rec.steps))


# ------------------------------------------------------- bad-grad update (AMP)
def test_bad_grad_update():
    torch.manual_seed(8)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.1, amp=True, ignore_scaler=True)
    rec = StepRecorder(tr, "badgrad")
    run_steps(tr, rec, 2, linear_loss, plant_inf_at={0})
    s = rec.steps[0]
    check("bad-grad: stepping through overflow -> BAD_GRAD_UPDATE",
          s["classification"] == BAD_GRAD_UPDATE, s["classification"])
    check("bad-grad: t07 FAIL (no unconditional AMP gradient PASS)",
          rec.t07_record()["status"] == "FAIL")
    check("bad-grad: t08 FAIL", rec.t08_record(min_updated=1)["status"] == "FAIL")


# ------------------------------------------------------------ re-attach guard
def test_reattach_guard():
    torch.manual_seed(9)
    m = torch.nn.Linear(4, 4)
    tr = MockTrainer(m, lr=0.1)
    r1 = StepRecorder(tr)
    r1.attach()
    try:
        StepRecorder(tr).attach()
        check("re-attach: second recorder rejected", False)
    except RuntimeError:
        check("re-attach: second recorder rejected", True)
    r1.attach()  # idempotent
    check("re-attach: idempotent same-recorder attach OK", True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    for fn in (test_pure_classification, test_fp32_repeated_updates,
               test_cancellation_concealment, test_int_only_change_not_an_update,
               test_warmup_lr0, test_amp_overflow_then_updates,
               test_amp_all_overflow_no_update, test_stuck_failure,
               test_bad_grad_update, test_reattach_guard):
        print(f"--- {fn.__name__}")
        fn()
    print(f"SUMMARY {PASS}/{PASS + FAIL} checks PASS")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
