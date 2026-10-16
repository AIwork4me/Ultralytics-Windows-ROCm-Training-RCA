"""Round-3 perf bench v2 — preloads a specific MIOpen.dll build (no wheel swap).
Usage: perf_bn2.py <abs-path-to-MIOpen.dll> <label>
"""
import ctypes
import hashlib
import json
import os
import statistics
import sys

DLL = sys.argv[1]
for d in [os.path.dirname(DLL),
          r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_libraries\bin",
          r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin",
          r"C:\Users\rocm\Desktop\YOLO_AMD\phase3_deps\dep_prefix\Library\bin"]:
    os.add_dll_directory(d)
with open(DLL, "rb") as f:
    print("preloading", DLL, "sha256", hashlib.sha256(f.read()).hexdigest()[:16])
miopen = ctypes.CDLL(DLL, mode=ctypes.RTLD_GLOBAL)
gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
path = ctypes.create_string_buffer(512)
gmfn(miopen._handle, path, 512)
print("MIOpen.dll loaded from:", path.value.decode(errors="replace"))

import torch
import torch.nn.functional as F

# Force a MIOpen call so torch resolves its MIOpen binding, then prove the
# process-wide "MIOpen.dll" module is the preloaded one.
_ = torch.nn.functional.batch_norm(
    torch.randn(2, 4, 8, 8, device="cuda"), torch.zeros(4, device="cuda"),
    torch.ones(4, device="cuda"), torch.ones(4, device="cuda"),
    torch.zeros(4, device="cuda"), training=True)
check = ctypes.CDLL("MIOpen.dll")
p2 = ctypes.create_string_buffer(512)
gmfn(check._handle, p2, 512)
print("post-torch bare-name MIOpen.dll:", p2.value.decode(errors="replace"),
      "| same handle as preload:", check._handle == miopen._handle)

print("torch", torch.__version__, "| hip", torch.version.hip, "|", torch.cuda.get_device_name(0))
torch.manual_seed(0)
dev = torch.device("cuda")
shapes = [(20, 100, 35, 45), (32, 256, 56, 56), (64, 512, 28, 28)]
WARMUP, ITERS = 30, 200
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
        "median_ms": round(statistics.median(times), 5),
        "p95_ms": round(times[max(0, int(0.95 * len(times)) - 1)], 5),
        "min_ms": round(times[0], 5),
        "max_ms": round(times[-1], 5),
        "n": len(times),
    }

for N, C, H, W in shapes:
    x = torch.randn(N, C, H, W, device=dev, dtype=torch.float32,
                    generator=torch.Generator(device=dev).manual_seed(1234))
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

    results[f"bn_fwd_{N}x{C}x{H}x{W}"] = timed(fwd)
    results[f"bn_bwd_{N}x{C}x{H}x{W}"] = timed(bwd)
    print(f"bn_{N}x{C}x{H}x{W} done", flush=True)

print("PERF_JSON", json.dumps(results))
sys.exit(0)
