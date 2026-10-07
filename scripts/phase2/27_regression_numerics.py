"""Gate 34: numerical correctness of the (now passing) MIOpen BatchNorm path.

Compares GPU BatchNorm2d (train + eval) against CPU reference on controlled
input: forward output, running stats update, backward gradients. Reports
max_abs_error / mean_abs_error / relative error and finiteness checks.
Exit 0 iff all checks pass within tolerance.
"""

from __future__ import annotations

import json
import sys

import torch
import torch.nn as nn

torch.manual_seed(0)

results: dict[str, object] = {"device": None, "cases": []}


def stats(name, a, b, tol):
    diff = (a - b).abs()
    max_abs = float(diff.max())
    mean_abs = float(diff.mean())
    denom = b.abs().max().clamp_min(1e-12)
    rel = float((diff / denom).max())
    ok = max_abs <= tol and bool(torch.isfinite(a).all())
    return {
        "case": name,
        "max_abs_error": max_abs,
        "mean_abs_error": mean_abs,
        "max_relative_error": rel,
        "finite": bool(torch.isfinite(a).all()),
        "tolerance": tol,
        "pass": ok,
    }


def main() -> int:
    dev = "cuda"
    results["device"] = torch.cuda.get_device_name(0)

    # ---- train forward + running stats ----
    g = nn.BatchNorm2d(16).to(dev).train()
    c = nn.BatchNorm2d(16).train()
    c.load_state_dict(g.state_dict())
    x = torch.randn(8, 16, 64, 64)
    xg = x.to(dev).requires_grad_(True)
    xc = x.clone().requires_grad_(True)
    momentum, eps = g.momentum, g.eps

    rm0, rv0 = g.running_mean.clone(), g.running_var.clone()
    yg = g(xg)
    yc = c(xc)
    exp_rm = (1 - momentum) * rm0 + momentum * g.running_mean  # placeholder; recompute below
    # CPU reference running stats per PyTorch semantics
    unbiased_var = x.var(dim=(0, 2, 3), unbiased=True)
    biased_var = x.var(dim=(0, 2, 3), unbiased=False)
    mean = x.mean(dim=(0, 2, 3))
    exp_rm = (1 - momentum) * rm0.cpu() + momentum * mean
    exp_rv = (1 - momentum) * rv0.cpu() + momentum * unbiased_var
    n = x.numel() / x.shape[1]
    exp_y = (x - mean[None, :, None, None]) / torch.sqrt(
        biased_var[None, :, None, None] + eps
    ) * g.weight.cpu()[None, :, None, None] + g.bias.cpu()[None, :, None, None]

    results["cases"] += [
        stats("train_forward_out", yg.detach().cpu(), exp_y, 2e-4),
        stats("train_running_mean", g.running_mean.cpu(), exp_rm.cpu(), 1e-5),
        stats("train_running_var", g.running_var.cpu(), exp_rv.cpu(), 1e-3),
    ]

    # ---- backward ----
    go = torch.randn_like(yc)
    yg.backward(go.to(dev))
    yc.backward(go)
    results["cases"] += [
        stats("train_grad_input", xg.grad.detach().cpu(), xc.grad.detach(), 2e-4),
        {
            "case": "train_grad_weight_finite",
            "finite": bool(torch.isfinite(g.weight.grad).all()),
            "pass": bool(torch.isfinite(g.weight.grad).all()),
        },
        {
            "case": "train_grad_bias_finite",
            "finite": bool(torch.isfinite(g.bias.grad).all()),
            "pass": bool(torch.isfinite(g.bias.grad).all()),
        },
    ]

    # ---- eval forward (uses running stats; previously the InferSpatial failure) ----
    g.eval()
    with torch.no_grad():
        ye = g(xg.detach())
    with torch.no_grad():
        exp_ye = (x - g.running_mean.cpu()[None, :, None, None]) / torch.sqrt(
            g.running_var.cpu()[None, :, None, None] + eps
        ) * g.weight.cpu()[None, :, None, None] + g.bias.cpu()[None, :, None, None]
    results["cases"].append(stats("eval_forward_out", ye.cpu(), exp_ye, 2e-4))

    ok = all(c.get("pass", False) for c in results["cases"])
    print(json.dumps(results, indent=2))
    print("NUMERICS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
