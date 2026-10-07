"""Phase 5 supplement: standalone GPU Conv2d control (matrix case F in
isolation). Proves the MIOpen *convolution* runtime path compiles fine while
the BatchNorm path does not.
"""
import sys
import time

import torch
import torch.nn as nn

print(f"torch={torch.__version__} hip={torch.version.hip} "
      f"dev={torch.cuda.get_device_name(0)}")

conv = nn.Conv2d(16, 32, 3, padding=1).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")

t0 = time.perf_counter()
y = conv(x)
torch.cuda.synchronize()
t1 = time.perf_counter()

print(f"out shape={tuple(y.shape)} mean={y.mean().item():.6f} "
      f"isfinite={bool(torch.isfinite(y).all())}")
print(f"first-call wall time (incl. any kernel compile): {t1 - t0:.2f} s")
print("CONV_CONTROL: PASS")
sys.exit(0)
