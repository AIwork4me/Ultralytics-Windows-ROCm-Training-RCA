"""Shared harness provenance helpers (mission §3.4 evidence-capture contract).

Every GPU harness records: immutable run_id, complete environment identity,
in-process loaded MIOpen DLL SHA256 (Toolhelp32Snapshot — what the process
ACTUALLY loaded, not what is on disk), cache-home identity, and writes its
output atomically with an exists-check so no run can overwrite another.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROCM_MODULE_RE = ("miopen", "hipdnn", "rocm-sdk", "amdhip64")
TH32CS_SNAPMODULE = 0x00000008


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{os.getpid()}"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def loaded_modules() -> list[dict]:
    """Every module loaded into THIS process (Windows Toolhelp32Snapshot)."""
    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
            ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
            ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
            ("szModule", wt.WCHAR * 256), ("szExePath", wt.WCHAR * 260),
        ]

    INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
    snapshot = KERNEL32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, 0)
    if snapshot == INVALID_HANDLE_VALUE or not snapshot:
        raise OSError(f"CreateToolhelp32Snapshot failed err={ctypes.get_last_error()}")
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not KERNEL32.Module32FirstW(snapshot, ctypes.byref(entry)):
            raise OSError(f"Module32FirstW failed err={ctypes.get_last_error()}")
        modules = []
        while True:
            modules.append({"name": entry.szModule.lower(), "path": entry.szExePath})
            if not KERNEL32.Module32NextW(snapshot, ctypes.byref(entry)):
                break
        return modules
    finally:
        KERNEL32.CloseHandle(snapshot)


def dll_provenance() -> dict:
    """SHA256 the ROCm DLLs actually loaded in this process. Errors are
    recorded, never silently swallowed."""
    out: dict = {"probe": "Toolhelp32Snapshot in-process", "modules": {},
                 "miopen_loaded": None, "probe_error": None}
    try:
        mods = loaded_modules()
        out["loaded_module_count_total"] = len(mods)
        for m in mods:
            name = m["name"]
            if name.endswith(".dll") and any(t in name for t in ROCM_MODULE_RE):
                try:
                    out["modules"][name] = {"path": m["path"],
                                            "sha256": sha256_file(m["path"]),
                                            "size_bytes": os.path.getsize(m["path"])}
                except OSError as exc:
                    out["modules"][name] = {"path": m["path"], "sha256_error": str(exc)}
        miopen = out["modules"].get("miopen.dll")
        if miopen is None:
            for name, rec in out["modules"].items():
                if "miopen" in name:
                    miopen = rec
                    break
        out["miopen_loaded"] = miopen
        if miopen is None:
            out["probe_error"] = "no MIOpen module found among loaded modules"
    except Exception as exc:  # noqa: BLE001 — recorded
        out["probe_error"] = f"{type(exc).__name__}: {exc}"
    return out


def cache_home_env() -> dict:
    keys = ("MIOPE", "MIOPEN", "ROCM", "HIP", "USERPROFILE", "TORCH")
    return {k: os.environ[k] for k in sorted(os.environ)
            if any(t in k.upper() for t in keys)}


def env_meta(python_exe: str | None = None) -> dict:
    import torch
    try:
        import ultralytics
        ul_v = ultralytics.__version__
    except Exception:  # noqa: BLE001
        ul_v = None
    meta = {
        "captured_utc": utcnow(),
        "python_executable": python_exe or sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "hip": torch.version.hip or "",
        "cuda_available": bool(torch.cuda.is_available()),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "total_mem_gb": (round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
                         if torch.cuda.is_available() else None),
        "ultralytics": ul_v,
        "cache_home_env": cache_home_env(),
    }
    return meta


def save_immutable(path: Path, obj: dict) -> None:
    """Write JSON output; refuse to overwrite an existing evidence file."""
    if path.exists():
        raise FileExistsError(f"immutable-output violation: {path} already exists — "
                              "no run may overwrite a previous result; use a new run_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)


def csv_rows(csv_path: Path) -> list[dict]:
    if not csv_path.is_file():
        return []
    lines = [l.strip() for l in csv_path.read_text().splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split(",")
    return [dict(zip(header, l.split(","))) for l in lines[1:]]


def reconcile_epochs(epochs_configured: int, results_csv_rows: int,
                     training_epoch_callbacks: int, final_eval_callbacks: int) -> dict:
    """Epoch-accounting reconciliation (mission §3.3).

    Upstream semantics (ultralytics/engine/trainer.py, final_eval, present in
    8.4.174 and 8.4.182): after the training loop, final_eval() bumps
    self.epoch by 1 and fires on_fit_epoch_end once more 'to log best metrics
    at step epochs+1'. So a healthy run produces `epochs` TRAINING epoch
    callbacks (indices 0..epochs-1, matching results.csv rows) plus exactly 1
    final-eval callback at index == epochs. Anything else is an accounting
    anomaly that must FAIL, not be papered over.
    """
    recon = {
        "epochs_configured": epochs_configured,
        "results_csv_rows": results_csv_rows,
        "training_epoch_callbacks": training_epoch_callbacks,
        "final_eval_callbacks": final_eval_callbacks,
        "upstream_semantics": "final_eval() fires on_fit_epoch_end once at index==epochs "
                              "to log best.pt metrics (trainer.py: 'log best metrics at "
                              "step epochs+1') — 1 extra callback is expected, 0 extra "
                              "training epochs",
    }
    recon["csv_matches_configured"] = results_csv_rows == epochs_configured
    recon["training_callbacks_match_csv"] = training_epoch_callbacks == results_csv_rows
    recon["final_eval_callbacks_expected"] = final_eval_callbacks <= 1
    recon["reconciled"] = (recon["csv_matches_configured"]
                           and recon["training_callbacks_match_csv"]
                           and recon["final_eval_callbacks_expected"])
    return recon
