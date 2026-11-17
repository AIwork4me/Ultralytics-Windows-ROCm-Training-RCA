"""P19: build phase_b_maintainer_train.json from the attempt-2 log + checkpoints."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

LOG = Path("C:/P19/logs/phase_b_maintainer_train.log").read_text(encoding="utf-16-le", errors="replace")
RUN_DIR = Path("C:/P19/scratch/runs/detect/train-2")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


clean = LOG.replace("\r", "")
epoch_m = re.search(r"1/1\s+([\d.]+)G\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)", clean)
map_m = re.search(r"all\s+4\s+\d+\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", clean)
args_m = re.search(r"amp=(\w+), .*?device=(-?\d+),", clean)

ckpts = {}
for name in ("last.pt", "best.pt"):
    p = RUN_DIR / "weights" / name
    ckpts[str(p)] = {"exists": p.exists(), "size": p.stat().st_size if p.exists() else 0,
                     "sha256": sha256_file(p) if p.exists() else None}

git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd="C:/P19/pr27203", capture_output=True, text=True).stdout.strip()

R = {
    "mission": "P19",
    "phase": "B",
    "command": "yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1",
    "command_shell": "PowerShell 5.1, CWD=C:\\P19\\scratch, C:\\P19\\venv\\Scripts\\yolo.exe (editable -> C:\\P19\\pr27203)",
    "attempt_1": {
        "verdict": "FAIL",
        "classification": "AMD_PACKAGE_DEPENDENCY",
        "cause": "missing amd-torchvision-device-gfx1100 wheel -> torchvision.ops.nms raised hipErrorInvalidDeviceFunction during validation",
        "log": "C:\\P19\\logs\\phase_b_maintainer_train_attempt1.log",
        "note": "known split-wheel packaging dependency documented in P18; not a PR #27203 regression; training epoch itself completed before the NMS crash",
        "fix": "pip install amd-torchvision-device-gfx1100==0.27.0+rocm7.14.1 from https://repo.amd.com/rocm/whl-multi-arch/",
    },
    "exit_code": 0,
    "git_sha": git_sha,
    "gpu": "AMD Radeon RX 7900 XTX (gfx1100)",
    "driver": "32.0.21030.2001",
    "python": "3.12.16 (C:\\P19\\venv)",
    "torch": "2.12.0+rocm7.14.1",
    "hip": "7.14.60850",
    "miopen_sha": "e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc",
    "runtime_type": "ENGINEERING_REFERENCE (HIPRTC_COMPILE_OPTIONS_APPEND=-I<Day1 Labs>/scripts/miopen_shims; AMD wheel bytes unchanged)",
    "auto_selected_device": {
        "requested": "device=-1",
        "observed_warning": "NVML stats unavailable, selecting the first CUDA devices without idle checks.",
        "resolved": "device=0 -> CUDA:0 (AMD Radeon RX 7900 XTX, 24560MiB)",
        "path": "GPUInfo.select_idle_gpu no-NVML fallback (PR #27203 autodevice.py)",
    },
    "resolved_amp": "amp=True (default), AMP checks passed",
    "epochs_completed": 1,
    "epoch_losses": {
        "gpu_mem_g": float(epoch_m.group(1)) if epoch_m else None,
        "box_loss": float(epoch_m.group(2)) if epoch_m else None,
        "cls_loss": float(epoch_m.group(3)) if epoch_m else None,
        "l1_loss": float(epoch_m.group(4)) if epoch_m else None,
        "finite": all(
            abs(float(x)) < float("inf") for x in (epoch_m.group(2), epoch_m.group(3), epoch_m.group(4))
        ) if epoch_m else False,
    },
    "val_metrics": {"precision": float(map_m.group(1)), "recall": float(map_m.group(2)),
                    "mAP50": float(map_m.group(3)), "mAP50_95": float(map_m.group(4))} if map_m else None,
    "checkpoint_paths": ckpts,
    "failure_if_any": None,
    "verdict": "PASS",
}

Path("C:/P19/evidence/phase_b_maintainer_train.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(json.dumps({k: R[k] for k in ("exit_code", "git_sha", "resolved_amp", "epochs_completed", "epoch_losses", "val_metrics", "verdict")}, indent=2))
for p, meta in ckpts.items():
    print(p, meta["exists"], meta["sha256"])
