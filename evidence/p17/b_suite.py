import json, datetime
import torch
from ultralytics.utils.checks import cuda_is_available, cuda_device_count
from ultralytics.utils.torch_utils import parse_device
from ultralytics.utils.autodevice import GPUInfo

out = {"timestamp": datetime.datetime.now().astimezone().isoformat(), "head": "563ff46e0c3347cc68db420e1b268a22a456e317"}

# B1 HIP GPU visibility
out["B1"] = {
    "torch_cuda_is_available": torch.cuda.is_available(),
    "torch_cuda_device_count": torch.cuda.device_count(),
    "cuda_is_available": cuda_is_available(),
    "cuda_device_count": cuda_device_count(),
    "consistent": cuda_is_available() == torch.cuda.is_available() and cuda_device_count() == torch.cuda.device_count(),
}

# B2 NVML absence path
gi = GPUInfo()
out["B2"] = {"nvml_available": gi.nvml_available}
gi.refresh_stats()
out["B2"]["gpu_stats_empty_without_nvml"] = (not gi.gpu_stats)
# confirm no fake utilization: with nvml off, refresh_stats must not fabricate numbers
out["B2"]["no_fake_utilization"] = True if not gi.gpu_stats else all("utilization" not in g or g.get("utilization") is None for g in gi.gpu_stats)

# B3 auto selection device=-1
d1 = parse_device("-1")
d2 = parse_device("-1")
ok_alloc = False
try:
    if d1 not in ("cpu", None, ""):
        n = int(str(d1).replace("cuda:", "").split(":")[0]) if "cuda" in str(d1) else int(d1)
        t = torch.randn(64, 64, device=n)  # real GPU tensor allocation
        ok_alloc = bool(t.sum() == t.sum()); torch.cuda.synchronize()
except Exception as e:
    ok_alloc = f"alloc failed: {e}"
out["B3"] = {"parse_device_-1": str(d1), "idempotent": str(d1) == str(d2), "gpu_alloc_ok": ok_alloc}

# B4 idle memory threshold
sel = gi.select_idle_gpu(count=1, min_memory_fraction=0.2, min_util_fraction=0)
free, total = torch.cuda.mem_get_info(0)
out["B4"] = {
    "selected": sel,
    "mem_get_info_device0": {"free_bytes": free, "total_bytes": total, "free_fraction": round(free/total, 4)},
    "threshold_0_2": 0.2,
    "meets_threshold": free/total >= 0.2,
    "expected": [0] if free/total >= 0.2 else [],
    "matches_expected": sel == ([0] if free/total >= 0.2 else []),
}

# B5 unverifiable utilization
sel5 = gi.select_idle_gpu(count=1, min_util_fraction=0.3)
out["B5"] = {"selected": sel5, "expected": [], "matches_expected": sel5 == []}

# B7 restriction handling
out["B7"] = {
    "empty_indices": gi.select_idle_gpu(count=1, indices=[]),
    "nonexistent_99999": gi.select_idle_gpu(count=1, indices=[99999]),
    "duplicate_0_0": gi.select_idle_gpu(count=1, indices=[0, 0]),
}

json.dump(out, open("b_suite_result.json", "w"), indent=2)
print(json.dumps(out, indent=2))
