"""Gate L11 generator: positive GPU compute control (4096^3 GEMM).

Prints labeled values and exits 0 only on success. Re-runnable evidence
generator for evidence/phase3/raw/linux/baseline/gemm.txt.
"""

import sys
import time

import torch


def main() -> int:
    print("start:", time.strftime("%Y-%m-%dT%H:%M:%S"))
    print("torch:", torch.__version__, "hip:", torch.version.hip)
    x = torch.randn(4096, 4096, device="cuda")
    y = x @ x
    torch.cuda.synchronize()
    print("device:", y.device)
    print("shape:", tuple(y.shape))
    print("mean: ", y.mean().item())
    print("finite:", torch.isfinite(y).all().item())
    print("PASS" if y.device.type == "cuda" and torch.isfinite(y).all() else "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
