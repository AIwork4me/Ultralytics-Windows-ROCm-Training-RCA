"""P19 Phase A: GPU pre-flight on PR #27203 HEAD d8fe65c8 (gfx1100).

Captures environment provenance + real GPU compute + PR-code device-detection results.
Outputs: C:/P19/logs/phase_a_gpu_preflight.log + C:/P19/evidence/P19_PHASE_A_ENV_GPU.json
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RESULT: dict = {"mission": "P19", "phase": "A", "captured_at": datetime.now(timezone.utc).isoformat()}

OUT_JSON = Path("C:/P19/evidence/P19_PHASE_A_ENV_GPU.json")
OUT_LOG = Path("C:/P19/logs/phase_a_gpu_preflight.log")


def log(msg: str = "") -> None:
    print(msg, flush=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_driver() -> dict:
    """Query Win32_VideoController for name + driver version."""
    try:
        ps = (
            "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM "
            "| ConvertTo-Json -Compress"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60
        ).stdout.strip()
        items = json.loads(out) if out else []
        if isinstance(items, dict):
            items = [items]
        return {"adapters": items}
    except Exception as e:  # noqa: BLE001
        return {"adapters": [], "error": repr(e)}


def capture_sac() -> dict:
    """Read Smart App Control policy state (1=On, 0=Off)."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\CI\Policy"
        )
        val, _ = winreg.QueryValueEx(key, "VerifiedAndReputablePolicyState")
        return {"VerifiedAndReputablePolicyState": val, "interpretation": "0=Off 1=On"}
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e)}


def main() -> int:
    log(f"=== P19 PHASE A GPU PRE-FLIGHT {RESULT['captured_at']} ===")

    # --- 1. OS / driver / security -------------------------------------------------
    RESULT["os"] = {
        "windows": platform.platform(),
        "version": platform.version(),
        "machine": platform.machine(),
    }
    RESULT["driver"] = capture_driver()
    RESULT["smart_app_control"] = capture_sac()
    log(f"OS: {RESULT['os']['version']}")
    log(f"Adapters: {json.dumps(RESULT['driver'].get('adapters', []), ensure_ascii=False)}")
    log(f"SAC: {json.dumps(RESULT['smart_app_control'])}")

    # --- 2. Python / torch stack ----------------------------------------------------
    import torch

    RESULT["python"] = {"executable": sys.executable, "version": sys.version}
    props = torch.cuda.get_device_properties(0)
    free_b, total_b = torch.cuda.mem_get_info(0)
    RESULT["torch"] = {
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "cuda": torch.version.cuda,
        "is_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "get_device_name_0": torch.cuda.get_device_name(0),
        "device_0": {
            "name": props.name,
            "gcn_arch_name": getattr(props, "gcnArchName", None),
            "multi_processor_count": props.multi_processor_count,
            "total_memory": props.total_memory,
        },
        "mem_get_info_0": {"free": free_b, "total": total_b},
    }
    log(f"torch={torch.__version__} hip={torch.version.hip} avail={torch.cuda.is_available()}")
    log(f"gpu0={torch.cuda.get_device_name(0)} arch={getattr(props, 'gcnArchName', None)}")
    log(f"mem free={free_b / 2**30:.2f}GiB total={total_b / 2**30:.2f}GiB")

    # --- 3. Real GPU compute: fp32/fp16 matmul + conv + backward + optimizer ---------
    torch.manual_seed(42)
    dev = "cuda:0"
    lin = torch.nn.Linear(256, 256).to(dev)
    conv = torch.nn.Conv2d(3, 8, 3).to(dev)
    opt = torch.optim.SGD(list(lin.parameters()) + list(conv.parameters()), lr=0.1)
    w_before = lin.weight.detach().clone()
    for amp_flag in (False, True):
        x1 = torch.randn(64, 256, device=dev)
        x2 = torch.randn(2, 3, 32, 32, device=dev)
        with torch.autocast("cuda", dtype=torch.float16, enabled=amp_flag):
            y = lin(x1).pow(2).mean() + conv(x2).pow(2).mean()
        y.backward()
        opt.step()
        opt.zero_grad()
        RESULT.setdefault("gpu_compute", {})[f"{'amp' if amp_flag else 'fp32'}"] = {
            "loss": float(y.detach()),
            "finite": bool(torch.isfinite(y).item()),
        }
        log(f"compute {'amp' if amp_flag else 'fp32'}: loss={float(y.detach()):.6f} finite={bool(torch.isfinite(y).item())}")
    w_after = lin.weight.detach()
    RESULT["gpu_compute"]["optimizer_step_changed_weights"] = bool((w_after - w_before).abs().max().item() > 0)
    log(f"optimizer_step_changed_weights={RESULT['gpu_compute']['optimizer_step_changed_weights']}")

    # --- 4. MIOpen.dll provenance via loaded modules ---------------------------------
    try:
        import psutil

        maps = psutil.Process().memory_maps()
        miopen = [m.path for m in maps if "miopen.dll" in m.path.lower()]
        RESULT["miopen"] = {
            "loaded_paths": sorted(set(miopen)),
            "sha256": {p: sha256_file(p) for p in sorted(set(miopen))},
        }
        log(f"miopen.dll: {RESULT['miopen']['loaded_paths']}")
        for p, h in RESULT["miopen"]["sha256"].items():
            log(f"  sha256 {h}")
    except Exception as e:  # noqa: BLE001
        RESULT["miopen"] = {"error": repr(e)}
        log(f"miopen provenance error: {e!r}")

    # --- 5. nvidia-smi / NVML availability -------------------------------------------
    try:
        subprocess.run(["nvidia-smi"], capture_output=True, timeout=15, check=True)
        RESULT["nvidia_smi"] = "PRESENT"
    except FileNotFoundError:
        RESULT["nvidia_smi"] = "FileNotFoundError (not installed)"
    except Exception as e:  # noqa: BLE001
        RESULT["nvidia_smi"] = repr(e)
    log(f"nvidia-smi: {RESULT['nvidia_smi']}")

    # --- 6. Ultralytics PR-code device detection (the code under validation) ----------
    import ultralytics

    from ultralytics.utils import checks as ul_checks
    from ultralytics.utils.autodevice import GPUInfo

    def git_sha() -> str:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd="C:/P19/pr27203", capture_output=True, text=True, timeout=30
            ).stdout.strip()
        )

    gi = GPUInfo()
    RESULT["ultralytics"] = {
        "__file__": ultralytics.__file__,
        "__version__": ultralytics.__version__,
        "git_head": git_sha(),
        "cuda_is_available": ul_checks.cuda_is_available(),
        "cuda_device_count": ul_checks.cuda_device_count(),
        "torch_device_count": torch.cuda.device_count(),
        "checks_match_torch": ul_checks.cuda_device_count() == torch.cuda.device_count(),
        "gpuinfo": {
            "nvml_available": gi.nvml_available,
            "gpu_stats_len": len(gi.gpu_stats),
            "select_idle_gpu_count1": gi.select_idle_gpu(count=1),
            "select_idle_gpu_count2": gi.select_idle_gpu(count=2),
            "select_idle_gpu_indices_empty": gi.select_idle_gpu(count=1, indices=[]),
            "select_idle_gpu_indices_0": gi.select_idle_gpu(count=1, indices=[0]),
        },
    }
    u = RESULT["ultralytics"]
    log(f"ultralytics {u['__version__']} from {u['__file__']}")
    log(f"git HEAD {u['git_head']}")
    log(f"cuda_is_available={u['cuda_is_available']} cuda_device_count={u['cuda_device_count']} (torch={u['torch_device_count']})")
    log(f"GPUInfo nvml_available={u['gpuinfo']['nvml_available']} gpu_stats={u['gpuinfo']['gpu_stats_len']}")
    log(f"select_idle_gpu: count1={u['gpuinfo']['select_idle_gpu_count1']} count2={u['gpuinfo']['select_idle_gpu_count2']} "
        f"indices[]={u['gpuinfo']['select_idle_gpu_indices_empty']} indices[0]={u['gpuinfo']['select_idle_gpu_indices_0']}")

    # --- 7. Runtime env --------------------------------------------------------------
    RESULT["runtime_env"] = {
        "HIPRTC_COMPILE_OPTIONS_APPEND": os.environ.get("HIPRTC_COMPILE_OPTIONS_APPEND", ""),
        "MIOPEN_USER_CACHE_PATH": os.environ.get("MIOPEN_USER_CACHE_PATH", "<default>"),
        "MIOPEN_SYSTEM_CACHE_PATH": os.environ.get("MIOPEN_SYSTEM_CACHE_PATH", "<default>"),
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
        "runtime_type": "ENGINEERING_REFERENCE (MIOpen freestanding-header shim via HIPRTC_COMPILE_OPTIONS_APPEND; AMD wheel bytes unchanged)",
    }
    log(f"HIPRTC_COMPILE_OPTIONS_APPEND={RESULT['runtime_env']['HIPRTC_COMPILE_OPTIONS_APPEND']!r}")
    log(f"CUDA_VISIBLE_DEVICES={RESULT['runtime_env']['CUDA_VISIBLE_DEVICES']!r}")
    log(f"runtime_type={RESULT['runtime_env']['runtime_type']}")

    # --- 8. Verdict -------------------------------------------------------------------
    errs = []
    if not torch.cuda.is_available():
        errs.append("cuda unavailable")
    if "7900 XTX" not in torch.cuda.get_device_name(0):
        errs.append("gpu name mismatch")
    if not RESULT["gpu_compute"]["optimizer_step_changed_weights"]:
        errs.append("optimizer did not update weights")
    if not u["cuda_is_available"] or u["cuda_device_count"] != 1:
        errs.append("ultralytics checks mismatch")
    if u["__file__"].replace("\\", "/").lower() != "c:/p19/pr27203/ultralytics/__init__.py":
        errs.append("import path is not the PR worktree")
    if u["git_head"] != "d8fe65c8c1052cb4305f3cec1be9cb909538dcf1":
        errs.append("git head drift")
    if u["gpuinfo"]["select_idle_gpu_count1"] != [0]:
        errs.append("select_idle_gpu(count=1) != [0]")
    RESULT["verdict"] = "PASS" if not errs else f"FAIL: {errs}"
    log(f"PHASE A VERDICT: {RESULT['verdict']}")

    OUT_JSON.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"wrote {OUT_JSON}")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
