# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""RX 9070 XT/gfx1201 physical preflight: NEVER emits PASS on CPU/fallback."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.metadata as metadata
import json
import platform
import sys
import traceback
from pathlib import Path

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--device-index", type=int, default=0)
    p.add_argument("--wheel-lock", required=True, help="Audited official nightly lock JSON; never use a historical gfx1100/1151 lock")
    a = p.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit("FAIL_CLOSED: refuse to overwrite existing physical preflight")
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": "r22a7-preflight-v1", "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "FAIL", "physical_gpu_identity_verified": False,
        "system": {"platform": platform.platform(), "python": sys.version,
                   "executable": sys.executable},
        "wheel_lock_path": str(Path(a.wheel_lock).resolve()),
        "wheel_lock_sha256": None, "device_index": a.device_index,
    }
    try:
        lock_path = Path(a.wheel_lock)
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        result["wheel_lock_sha256"] = sha(lock_path)
        if lock.get("gfx_target") != "gfx1201" or lock.get("channel") != "nightly":
            raise ValueError("LOCK_IDENTITY_MISMATCH: requires exact gfx1201/nightly package lock")
        result["lock_package_count"] = len(lock.get("packages", []))
        import torch
        import torchvision
        import ultralytics
        versions = {k: metadata.version(k) for k in ("torch", "torchvision", "ultralytics")}
        result["installed_versions"] = versions
        result["torch_version_hip"] = torch.version.hip
        result["torch_cuda_available"] = bool(torch.cuda.is_available())
        result["device_count"] = torch.cuda.device_count() if torch.cuda.is_available() else 0
        if not torch.cuda.is_available() or not (0 <= a.device_index < torch.cuda.device_count()):
            raise RuntimeError("NO_PHYSICAL_ROCM_GPU: torch.cuda unavailable or device index invalid")
        devices = []
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            devices.append({"index": i, "name": prop.name,
                            "gcn_arch_name": str(getattr(prop, "gcnArchName", "")),
                            "total_memory_bytes": prop.total_memory, "repr": str(prop)})
        result["devices"] = devices
        selected = devices[a.device_index]
        gfx = selected["gcn_arch_name"].lower()
        if "gfx1201" not in gfx or not ("9070" in selected["name"] and "xt" in selected["name"].lower()):
            raise RuntimeError("GPU_IDENTITY_MISMATCH: expected physical RX 9070 XT gfx1201")
        if not torch.version.hip:
            raise RuntimeError("NOT_ROCM_TORCH: torch.version.hip is absent")
        torch.cuda.set_device(a.device_index)
        x = torch.ones((96, 96), device=f"cuda:{a.device_index}", dtype=torch.float32, requires_grad=True)
        y = (x @ x).mean()
        y.backward()
        torch.cuda.synchronize(a.device_index)
        if x.device.type != "cuda" or x.grad is None or not bool(torch.isfinite(x.grad).all()):
            raise RuntimeError("GPU_AUTOGRAD_NOT_PROVEN")
        result["gpu_backward_scalar"] = float(y.detach().item())
        result["physical_gpu_identity_verified"] = True
        result["status"] = "PHYSICAL_GFX1201_PREFLIGHT_PASS"
    except Exception as e:
        result["error_type"] = type(e).__name__
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "out": str(out),
                      "gpu": result.get("devices"), "error": result.get("error")}, ensure_ascii=False))
    return 0 if result["physical_gpu_identity_verified"] else 2

if __name__ == "__main__":
    sys.exit(main())
