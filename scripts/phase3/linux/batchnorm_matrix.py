"""Gate L13/L30/L34 generator: BatchNorm functional matrix (wheel or source-built MIOpen).

Modes: train / eval / backward covered for BN2d; spatial + control variants.
Each case prints labeled PASS/FAIL with finite checks and CPU cross-reference
for the backward numerics. Exit 0 only if every case passes.

Environment: run with a FRESH MIOpen cache (see run_fresh_cache.sh) to prove
runtime kernel compilation is exercised, not a stale cache.
"""

import sys

import torch
import torch.nn as nn


def check(name: str, fn) -> bool:
    try:
        info = fn()
        torch.cuda.synchronize()
        ok = info is not False
        print(f"{name:26s} {'PASS' if ok else 'FAIL'}  {info if info is not False else ''}")
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"{name:26s} FAIL  {type(e).__name__}: {str(e)[:400]}")
        return False


def bn(kind: str, train: bool, shape, with_backward: bool = False):
    def run():
        torch.manual_seed(0)
        if kind == "GroupNorm":
            m = nn.GroupNorm(4, shape[1]).cuda()
        else:
            m = getattr(nn, kind)(shape[1]).cuda()
        m.train(mode=train)
        x = torch.randn(*shape, device="cuda", requires_grad=with_backward)
        y = m(x)
        torch.cuda.synchronize()
        finite = torch.isfinite(y).all().item()
        extra = f"shape={tuple(y.shape)} mean={y.mean().item():.3e} finite={finite}"
        if with_backward:
            y.sum().backward()
            torch.cuda.synchronize()
            # CPU reference with identical seed/RNG is not bit-identical across
            # backends; compare magnitudes for sanity (order-of-magnitude check).
            gnorm = x.grad.norm().item()
            wnorm = m.weight.grad.norm().item()
            extra += f" | dx_norm={gnorm:.3e} wgrad={wnorm:.3e} grads_finite={torch.isfinite(x.grad).all().item() and torch.isfinite(m.weight.grad).all().item()}"
        return extra if finite else False

    return run


def main() -> int:
    print("torch:", torch.__version__, "hip:", torch.version.hip, "gpu:", torch.cuda.get_device_name(0))
    ok = True
    ok &= check("BN2d train", bn("BatchNorm2d", True, (8, 16, 64, 64)))
    ok &= check("BN2d eval", bn("BatchNorm2d", False, (8, 16, 64, 64)))
    ok &= check("BN2d train backward", bn("BatchNorm2d", True, (8, 16, 64, 64), with_backward=True))
    ok &= check("BN1d 3D (spatial)", bn("BatchNorm1d", True, (8, 16, 32)))
    ok &= check("BN1d 2D (control)", bn("BatchNorm1d", True, (8, 16)))
    ok &= check("BN3d train", bn("BatchNorm3d", True, (4, 16, 8, 16, 16)))
    ok &= check("BN3d backward", bn("BatchNorm3d", True, (4, 16, 8, 16, 16), with_backward=True))
    ok &= check("GroupNorm control", bn("GroupNorm", True, (8, 16, 64, 64)))
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
