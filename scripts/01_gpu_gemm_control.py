"""Phase 1: positive GPU control — real GEMM on the ROCm device.

Falsifies H1 ("PyTorch ROCm GPU compute is generally broken").
PASS: op executes on cuda:0, torch.version.hip non-null, no CPU fallback.
"""
import sys
import time

import torch

print(f"torch.__version__ = {torch.__version__}")
print(f"torch.version.hip = {torch.version.hip}")
print(f"device_count = {torch.cuda.device_count()}")
print(f"device(0) = {torch.cuda.get_device_name(0)}")

assert torch.version.hip is not None, "torch.version.hip is null (not a ROCm build)"
assert torch.cuda.is_available(), "cuda (HIP) not available"

x = torch.randn(4096, 4096, device="cuda")
print(f"\ninput: shape={tuple(x.shape)} dtype={x.dtype} device={x.device}")

t0 = time.perf_counter()
y = x @ x
torch.cuda.synchronize()
t1 = time.perf_counter()

print(f"output: shape={tuple(y.shape)} dtype={y.dtype} device={y.device}")
print(f"mean={y.mean().item():.6f}  sum={y.sum().item():.6e}")
print(f"wall time incl. compile/first-call: {t1 - t0:.3f} s")

# checksum via CPU transfer — proves a real round trip
cpu_sum = y.cpu().sum().item()
print(f"cpu-side checksum sum={cpu_sum:.6e}")
print(f"isfinite={bool(torch.isfinite(y).all().item())}")

if str(y.device) != "cuda:0":
    print("FAIL: result not on cuda:0")
    sys.exit(2)

print("\nPHASE1_GEMM: PASS")
