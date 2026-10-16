"""Round-3 perf bench — BatchNorm forward/backward GPU latency (CUDA events).

Runs under whichever MIOpen.dll is swapped into the wheel dir; proves the
loaded module path in-process. Warmup 20, 100 timed iterations per shape/op,
reports median/P95/min/max in ms. Same seeds/tensors both variants.
"""
import ctypes
import json
import statistics
import sys

import torch
import torch.nn.functional as F

print("torch", torch.__version__, "| hip", torch.version.hip, "|", torch.cuda.get_device_name(0))
miopen = ctypes.CDLL("MIOpen.dll")
gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
path = ctypes.create_string_buffer(512)
gmfn(miopen._handle, path, 512)
print("MIOpen.dll loaded from:", path.value.decode(errors="replace"))

torch.manual_seed(0)
dev = torch.device("cuda")
shapes = [(20, 100, 35, 45), (32, 256, 56, 56), (64, 512, 28, 28)]
WARMUP, ITERS = 20, 100
results = {}

def timed(fn):
    for _ in range(WARMUP):
        fn()
    torch.cuda.synchronize()
    times = []
    for _ in range(ITERS):
        s = torch.cuda.Event(enable_timing=True); e = torch.cuda.Event(enable_timing=True)
        s.record(); fn(); e.record()
        torch.cuda.synchronize()
        times.append(s.elapsed_time(e))
    times.sort()
    return {
        "median_ms": statistics.median(times),
        "p95_ms": times[max(0, int(0.95 * len(times)) - 1)],
        "min_ms": times[0],
        "max_ms": times[-1],
        "n": len(times),
    }

for N, C, H, W in shapes:
    x = torch.randn(N, C, H, W, device=dev, dtype=torch.float32, generator=torch.Generator(device=dev).manual_seed(1234))
    w = torch.ones(C, device=dev, requires_grad=True)
    b = torch.zeros(C, device=dev, requires_grad=True)
    rm = torch.zeros(C, device=dev); rv = torch.ones(C, device=dev)
    xg = x.detach().clone().requires_grad_(True)

    def fwd():
        with torch.no_grad():
            F.batch_norm(x, rm, rv, w, b, training=True, momentum=0.1, eps=1e-5)

    y = F.batch_norm(xg, rm, rv, w, b, training=True, momentum=0.1, eps=1e-5)

    def bwd():
        torch.autograd.grad(y, [xg, w, b], grad_outputs=torch.ones_like(y), retain_graph=True)

    key = f"bn_fwd_{N}x{C}x{H}x{W}"
    results[key] = timed(fwd)
    key = f"bn_bwd_{N}x{C}x{H}x{W}"
    results[key] = timed(bwd)
    print(key, json.dumps(results[key]))

print("PERF_JSON", json.dumps(results))
sys.exit(0)
