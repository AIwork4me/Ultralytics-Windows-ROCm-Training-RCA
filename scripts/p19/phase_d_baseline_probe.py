"""P19 Phase D leg A/B: device-detection probe against a chosen checkout.

Usage: python phase_d_baseline_probe.py main|pr
Leg main -> C:/P19/baseline-main (upstream main, no PR) via PYTHONPATH.
No GPU kernels are executed; only device-count/selection logic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

LEG = sys.argv[1] if len(sys.argv) > 1 else "main"
R: dict = {"leg": LEG}

import ultralytics

R["ultralytics_file"] = ultralytics.__file__
R["git_head"] = (
    subprocess.run(["git", "rev-parse", "HEAD"], cwd="C:/P19/baseline-main" if LEG == "main" else "C:/P19/pr27203",
                   capture_output=True, text=True).stdout.strip()
)

import torch

from ultralytics.utils import checks as ul_checks
from ultralytics.utils.autodevice import GPUInfo

R["torch_device_count"] = torch.cuda.device_count()
R["torch_is_available"] = torch.cuda.is_available()
R["cuda_device_count()"] = ul_checks.cuda_device_count()
R["cuda_is_available()"] = ul_checks.cuda_is_available()

gi = GPUInfo()
R["nvml_available"] = gi.nvml_available
R["select_idle_gpu(count=1)"] = gi.select_idle_gpu(count=1)

from ultralytics.utils.torch_utils import parse_device

R["parse_device('-1')"] = parse_device("-1")

# test_cuda.py DEVICES emulation (conftest-style)
devices = []
try:
    gpu_info = GPUInfo()
    frac = float(os.environ.get("YOLO_AUTODEVICE_FRACTION_FREE", 0.3))
    if idle := gpu_info.select_idle_gpu(count=2, min_memory_fraction=frac, min_util_fraction=frac):
        devices = idle
except Exception as e:  # noqa: BLE001
    R["devices_emulation_error"] = repr(e)
R["test_cuda_DEVICES"] = devices
R["test_checks_would_pass"] = (torch.cuda.device_count() == R["cuda_device_count()"]) and (
    torch.cuda.is_available() == R["cuda_is_available()"]
)

print(json.dumps(R, indent=2))
with open(f"C:/P19/evidence/phase_d_leg_{LEG}.json", "w", encoding="utf-8") as f:
    json.dump(R, f, indent=2)
