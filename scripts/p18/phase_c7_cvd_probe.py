"""P18 Phase C7 child: CUDA_VISIBLE_DEVICES semantics on Windows HIP gfx1100.

Run in a FRESH python process with CUDA_VISIBLE_DEVICES set by the parent BEFORE
python starts. Records: torch visible count, logical id, parse_device('-1'),
select_idle_gpu(), mem_get_info, tensor allocation.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, r"C:\P18\pr27203")


def main() -> int:
    import torch
    import ultralytics.utils.checks as checks
    from ultralytics.utils.autodevice import GPUInfo
    from ultralytics.utils.torch_utils import parse_device

    out = {
        "cvd_env": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_version": torch.__version__,
        "hip": torch.version.hip,
    }
    out["torch_device_count"] = torch.cuda.device_count()
    out["torch_available"] = torch.cuda.is_available()
    if out["torch_device_count"]:
        out["device_name_0"] = torch.cuda.get_device_name(0)
        free, total = torch.cuda.mem_get_info(0)
        out["mem_get_info"] = {"free": free, "total": total, "free_frac": round(free / total, 4)}
        try:
            t = torch.ones(8, device="cuda:0")
            out["tensor_alloc"] = bool(t.is_cuda and t.sum().item() == 8)
        except Exception as e:  # noqa: BLE001
            out["tensor_alloc"] = f"FAIL {e}"
    out["checks_cuda_device_count"] = checks.cuda_device_count()
    out["checks_cuda_is_available"] = checks.cuda_is_available()
    try:
        out["parse_device_-1"] = str(parse_device("-1"))
    except Exception as e:  # noqa: BLE001
        out["parse_device_-1"] = f"RAISED {type(e).__name__}: {e}"
    try:
        out["select_idle_gpu"] = GPUInfo().select_idle_gpu(count=1, min_memory_fraction=0.2)
    except Exception as e:  # noqa: BLE001
        out["select_idle_gpu"] = f"RAISED {type(e).__name__}: {e}"
    print("C7_JSON_BEGIN")
    print(json.dumps(out, indent=2))
    print("C7_JSON_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
