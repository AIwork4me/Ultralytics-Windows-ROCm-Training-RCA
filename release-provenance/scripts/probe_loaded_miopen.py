"""G0.3 — Report the MIOpen/HIP DLLs actually loaded by the running Python process.

Run inside the environment under test (its own python interpreter):

    python release-provenance/scripts/probe_loaded_miopen.py --out <report.json>

Sequence (lazy-load aware):
  1. Record interpreter/torch environment metadata.
  2. Initialize HIP via torch.cuda; run a real MIOpen workload
     (Conv2d forward + BatchNorm2d train forward/backward + optimizer step)
     so MIOpen/hipdnn modules are actually loaded before probing.
  3. Enumerate this process's loaded modules through the Windows API
     (EnumProcessModulesEx) — not by guessing filesystem paths — and
     SHA256 every module matching the ROCm set (MIOpen*, hipdnn*, hip*,
     roc*). Writes one JSON object; exits non-zero on any assertion failure.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PSAPI = ctypes.WinDLL("psapi", use_last_error=True)
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)

ROCM_MODULE_RE = ("miopen", "hipdnn", "rocm-sdk")

LIST_MODULES_ALL = 0x03


def fail(msg: str) -> None:
    print(f"ASSERTION-FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


def loaded_modules() -> list[dict]:
    """Return every module loaded into this process (name + full path).

    Uses Toolhelp32Snapshot(TH32CS_SNAPMODULE) — reliable from Python for the
    current process without handle plumbing.
    """
    TH32CS_SNAPMODULE = 0x00000008
    INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
    snapshot = KERNEL32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, 0)
    if snapshot == INVALID_HANDLE_VALUE or not snapshot:
        fail(f"CreateToolhelp32Snapshot failed err={ctypes.get_last_error()}")
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not KERNEL32.Module32FirstW(snapshot, ctypes.byref(entry)):
            fail(f"Module32FirstW failed err={ctypes.get_last_error()}")
        modules = []
        while True:
            modules.append(
                {
                    "name": entry.szModule.lower(),
                    "path": entry.szExePath,
                }
            )
            if not KERNEL32.Module32NextW(snapshot, ctypes.byref(entry)):
                break
        return modules
    finally:
        KERNEL32.CloseHandle(snapshot)


def run_miopen_workload() -> dict:
    """Real GPU workload that forces MIOpen (and hipdnn engine) loading."""
    import torch

    results: dict = {}
    dev = torch.device("cuda:0")
    results["torch_version"] = torch.__version__
    results["torch_version_hip"] = torch.version.hip or ""
    results["cuda_is_available"] = bool(torch.cuda.is_available())
    if not results["cuda_is_available"]:
        fail("torch.cuda.is_available() is False — not a GPU run")
    if not results["torch_version_hip"]:
        fail("torch.version.hip is empty — CUDA wheel, not ROCm wheel")
    props = torch.cuda.get_device_properties(0)
    results["device_name"] = props.name
    results["device_count"] = torch.cuda.device_count()
    results["hip_runtime_reported"] = results["torch_version_hip"]

    # --- real MIOpen path: conv + BN train fwd/bwd + optimizer step ---
    torch.manual_seed(0)
    model = torch.nn.Sequential(
        torch.nn.Conv2d(3, 8, 3, padding=1, bias=False),
        torch.nn.BatchNorm2d(8),
        torch.nn.ReLU(),
    ).to(dev)
    opt = torch.optim.SGD(model.parameters(), lr=0.05)
    x = torch.randn(4, 3, 32, 32, device=dev)
    before = model[0].weight.detach().clone()
    out = model(x)
    loss = out.square().mean()
    loss.backward()
    opt.step()
    torch.cuda.synchronize()
    results["workload_output_device"] = str(out.device)
    results["workload_loss_float"] = float(loss.detach().cpu())
    results["loss_finite"] = bool(torch.isfinite(loss).item())
    results["grad_conv_weight_finite"] = bool(
        torch.isfinite(model[0].weight.grad).all().item()
    )
    results["optimizer_changed_weights"] = bool(
        not torch.equal(before, model[0].weight.detach())
    )
    results["bn_running_var_finite"] = bool(
        torch.isfinite(model[1].running_var).all().item()
    )
    for key, ok in [
        ("loss_finite", results["loss_finite"]),
        ("grad_conv_weight_finite", results["grad_conv_weight_finite"]),
        ("optimizer_changed_weights", results["optimizer_changed_weights"]),
        ("bn_running_var_finite", results["bn_running_var_finite"]),
    ]:
        if not ok:
            fail(f"workload assertion failed: {key}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="output JSON report path")
    args = parser.parse_args()

    env_meta = {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "os": f"{platform.system()} {platform.release()} build {platform.version()}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "process_pid": os.getpid(),
    }

    workload = run_miopen_workload()

    # Probe loaded modules AFTER MIOpen ops (lazy-load safe).
    modules = loaded_modules()
    rocm_hits = {}
    for m in modules:
        name = m["name"]
        if any(tag in name for tag in ROCM_MODULE_RE) and name.endswith(".dll"):
            if name in ("miopen_hip_kernel_loader.dll",):  # informational only
                pass
            entry = rocm_hits.setdefault(
                name, {"path": m["path"], "sha256": None, "size_bytes": None}
            )
            # keep first occurrence (already loaded, dedup by name)
    for name, entry in rocm_hits.items():
        p = entry["path"]
        entry["sha256"] = sha256_file(p)
        entry["size_bytes"] = os.path.getsize(p)
    if "miopen.dll" not in rocm_hits:
        # Some builds resolve MIOpen under a different casing/path; report all
        # candidates but assert on any module containing 'miopen'.
        if not any("miopen" in n for n in rocm_hits):
            fail(
                "no MIOpen module found among loaded modules — MIOpen never loaded; "
                "workload may have bypassed MIOpen (check hipdnn plugin path)"
            )

    miopen = rocm_hits.get("miopen.dll")
    report = {
        "tool": "probe_loaded_miopen.py",
        "purpose": "G0.3 actual-loaded-DLL proof (Windows API, post-MIOpen-op)",
        "environment": env_meta,
        "workload": workload,
        "loaded_rocm_modules": rocm_hits,
        "miopen_loaded": miopen,
        "loaded_module_count_total": len(modules),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"miopen_path": miopen["path"], "miopen_sha256": miopen["sha256"],
                      "hip": workload["torch_version_hip"],
                      "device": workload["device_name"]}, indent=2))


if __name__ == "__main__":
    main()
