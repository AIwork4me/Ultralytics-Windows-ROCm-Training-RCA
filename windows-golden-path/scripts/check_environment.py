# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Capture the R21 host environment baseline (mission §2) — R21_ENVIRONMENT_BASELINE.json.

Determines machine facts by measurement, not assumption: Windows build, GPU,
driver, python interpreters, MSVC toolchain presence, MIOpen caches, disk
space, and the AMD-relevant environment. Read-only: mutates nothing.
Safe to run in any Python (torch optional).

    python check_environment.py --out C:/RadeonYOLO/evidence/R21_ENVIRONMENT_BASELINE.json \
        [--venv-python C:/path/to/python.exe]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

RUN_ID = "R21-ENV-BASELINE"


def ps(cmd: str, timeout: int = 60) -> str:
    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                              capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:  # noqa: BLE001 - record, never crash the baseline
        return f"<error: {e}>"


def msvc_toolchain_facts() -> dict:
    """Host MSVC presence (no-STL negative control needs to know what exists)."""
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    vs = {}
    if vswhere.is_file():
        out = ps(f'& "{vswhere}" -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 '
                 "-property installationPath")
        vs["vc_tools_install_paths"] = [l for l in out.splitlines() if l.strip()] or []
    vs["VCToolsInstallDir_env"] = os.environ.get("VCToolsInstallDir")
    vs["INCLUDE_env_set"] = bool(os.environ.get("INCLUDE"))
    vs["cl_on_path"] = bool(ps("where.exe cl.exe 2>$null"))
    return vs


def miopen_cache_facts() -> dict:
    """Existing MIOpen caches (never deleted; cold tests use fresh identities)."""
    caches = {}
    for label, base in (("userprofile", Path(os.environ.get("USERPROFILE", "")) / ".cache" / "miopen"),
                        ("appdata", Path(os.environ.get("APPDATA", "")) / "miopen")):
        try:
            caches[label] = {"path": str(base), "exists": base.exists(),
                             "entries": len(list(base.iterdir())) if base.exists() else 0}
        except OSError:
            caches[label] = {"path": str(base), "exists": False}
    return caches


def python_inventory() -> list[dict]:
    """Known interpreters on this host (py launcher + known venvs)."""
    found = []
    for cand in (r"C:\P19\venv\Scripts\python.exe", r"C:\P18\venv\Scripts\python.exe",
                 sys.executable):
        p = Path(cand)
        if p.is_file():
            ver = subprocess.run([str(p), "-c", "import sys;print(sys.version.split()[0])"],
                                 capture_output=True, text=True, timeout=60).stdout.strip()
            found.append({"path": str(p), "version": ver})
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--venv-python", default=None,
                    help="optional target venv python to probe for stack facts")
    args = ap.parse_args()

    base = gp_lib.capture_environment("R21_ENVIRONMENT_BASELINE")
    base.update({
        "run_id": RUN_ID,
        "mission": "R21",
        "os_edition": ps("(Get-CimInstance Win32_OperatingSystem).Caption"),
        "free_disk_c_gb": ps("(Get-PSDrive C).Free / 1GB"),
        "running_gpu_processes": ps("Get-Process | Where-Object {$_.Name -match 'python|yolo'} | "
                                    "Select-Object Id,ProcessName | ConvertTo-Json -Compress"),
        "msvc": msvc_toolchain_facts(),
        "miopen_caches": miopen_cache_facts(),
        "python_interpreters": python_inventory(),
    })
    if args.venv_python:
        # stack facts measured in the target venv (torch import happens there)
        code = ("import json,sys;"
                "import torch;"
                "print(json.dumps({'torch': torch.__version__,"
                "'hip': torch.version.hip,"
                "'cuda_available': torch.cuda.is_available(),"
                "'device_count': torch.cuda.device_count(),"
                "'device_name': torch.cuda.get_device_name(0) if torch.cuda.device_count() else None}))")
        r = subprocess.run([args.venv_python, "-c", code], capture_output=True, text=True, timeout=300)
        try:
            base["target_venv_stack"] = json.loads(r.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            base["target_venv_stack"] = {"error": r.stderr[-500:]}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] baseline written: {out}")
    print(f"[OK] GPU: {base.get('gpu_name_cim')} driver {base.get('driver_version')} "
          f"gfx={base.get('gfx_target')} build {base.get('windows_build')}")


if __name__ == "__main__":
    main()
