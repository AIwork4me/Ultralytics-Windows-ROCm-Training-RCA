# Runs in an isolated process; CUDA_VISIBLE_DEVICES=0 is set BEFORE torch import by the launcher.
import json, os, datetime
import torch
assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0", f"CVD must be 0, got {os.environ.get('CUDA_VISIBLE_DEVICES')}"
from ultralytics.utils.checks import cuda_is_available, cuda_device_count
from ultralytics.utils.torch_utils import parse_device
from ultralytics.utils.autodevice import GPUInfo

out = {"cwd_env_CVD": os.environ.get("CUDA_VISIBLE_DEVICES")}
out["visible_device_count"] = torch.cuda.device_count()
out["cuda_device_count"] = cuda_device_count()
out["cuda_is_available"] = cuda_is_available()
dev = parse_device("-1")
out["parse_device_-1"] = str(dev)
gi = GPUInfo()
sel = gi.select_idle_gpu(count=1, min_memory_fraction=0.2, min_util_fraction=0)
out["select_idle_gpu"] = sel
out["mem_get_info_0"] = [torch.cuda.mem_get_info(0)[0], torch.cuda.mem_get_info(0)[1]]
n = int(str(dev).replace("cuda:", "")) if "cuda" in str(dev) else int(dev)
t = torch.randn(64, 64, device=n)
torch.cuda.synchronize()
out["gpu_alloc_device"] = n
out["gpu_alloc_ok"] = bool(t.sum() == t.sum())
out["alloc_device_name"] = torch.cuda.get_device_name(n)
out["consistency"] = {
    "counts_agree": out["visible_device_count"] == out["cuda_device_count"],
    "parse_matches_physical": out["parse_device_-1"] in ("0", "cuda:0"),
    "selected_in_range": all(0 <= i < out["visible_device_count"] for i in sel),
}
out["timestamp"] = datetime.datetime.now().astimezone().isoformat()
json.dump(out, open("b6_cvd0_result.json", "w"), indent=2)
print(json.dumps(out, indent=2))
