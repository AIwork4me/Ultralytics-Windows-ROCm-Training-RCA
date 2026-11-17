# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N gfx1100 — build installed_manifest.json inside the mission venv.

Records the ACTUAL installed state for the PKG gate's installed-vs-lock diff:
every distribution (name==version), pip check output, gpu stack identity and
the installed (not yet loaded) MIOpen.dll bytes under _rocm_sdk_libraries.

    python scripts/r22a5n1100/build_installed_manifest.py --out manifest.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "windows-golden-path" / "scripts"))
import gp_lib  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import importlib.metadata as im
    import torch

    dists = sorted(f"{d.metadata['Name']}=={d.version}" for d in im.distributions())
    pip_check = subprocess.run([sys.executable, "-m", "pip", "check"],
                               capture_output=True, text=True, timeout=300)
    gpu_stack = {"torch": torch.__version__, "ultralytics": None,
                 "torchvision": None, "rocm_sdk_libraries": None,
                 "rocm_sdk_core": None}
    for d in im.distributions():
        n = gp_lib.dist_key(d.metadata["Name"] or "")
        for k in list(gpu_stack):
            if gp_lib.dist_key(k) == n and gpu_stack[k] is None:
                gpu_stack[k] = d.version

    installed_dll = None
    for d in im.distributions():
        if (d.metadata["Name"] or "").lower() == "rocm-sdk-libraries":
            f = Path(str(d.locate_file("_rocm_sdk_libraries/bin/MIOpen.dll")))
            if f.is_file():
                blob = f.read_bytes()
                installed_dll = {
                    "path": str(f), "sha256": hashlib.sha256(blob).hexdigest(),
                    "bytes": len(blob),
                    "pr13437_marker_miopen_initializer_list":
                        blob.count(b"miopen_initializer_list")}
            break

    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() else None
    out = Path(args.out)
    rec = {
        "run_id": "R22A5N-GFX1100-INSTALLED-MANIFEST",
        "mission": "R22A.5N gfx1100 Official Nightly Physical Prequalification",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "timestamp": gp_lib.now_utc(),
        "gpu_name": gpu_name,
        "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "torch": torch.__version__, "torchvision": gpu_stack["torchvision"],
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), "nightly",
            (gp_lib.loaded_miopen_identity() or None)),
        "command": f"python {Path(__file__).name} --out {args.out}",
        "exit_code": 0, "duration_s": 0.0,
        "pass_fail_skip": "PASS", "failure_classification": None,
        "raw_log_path": str(out),
        "python": sys.version.split()[0],
        "venv": sys.prefix,
        "gpu_stack": gpu_stack,
        "pip_check": (pip_check.stdout or "") + (pip_check.stderr or ""),
        "pip_check_exit": pip_check.returncode,
        "all_distributions": dists,
        "installed_miopen_dll": installed_dll,
        "torch_hip": torch.version.hip,
        "cuda_available": bool(torch.cuda.is_available()),
        "device_count": int(torch.cuda.device_count()),
        "gpu_name_0": gpu_name,
        "gfx_target": gp_lib.gfx_from_device_name(gpu_name or ""),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    gp_lib.write_evidence(rec, out)
    print(json.dumps({k: rec[k] for k in
                      ("gpu_stack", "pip_check_exit", "gfx_target",
                       "cuda_available", "device_count", "gpu_name_0")}, indent=2))
    print(f"distributions: {len(dists)}")
    print(f"[OK] {out}")


if __name__ == "__main__":
    main()
