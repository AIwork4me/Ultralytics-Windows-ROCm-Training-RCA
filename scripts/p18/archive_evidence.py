"""Archive P18 raw evidence into the RCA repo per its conventions.

Copies logs/JSONs to evidence/raw/p18/, appends entries to evidence/manifest.json
(path, timestamp UTC, command, sha256, size_bytes) matching the existing schema.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import shutil
from pathlib import Path

RCA = Path(r"C:\P18\rca")
DST = RCA / "evidence" / "raw" / "p18"
DST.mkdir(parents=True, exist_ok=True)

FILES = {
    "phase_a_gpu_basic.log": "python C:/P18/scratch/phase_a_gpu_basic.py",
    "phase_a4_runtime_identity.log": "inline psutil memory_maps probe",
    "phase_b1_check_amp.log": "python C:/P18/scratch/phase_b1_check_amp.py",
    "phase_b2_exception_boundary.log": "python C:/P18/scratch/phase_b2_exception_boundary.py",
    "phase_b3_train_amp.log": "python C:/P18/scratch/phase_b34_train.py --amp 1 --tag amp",
    "phase_b4_train_fp32.log": "python C:/P18/scratch/phase_b34_train.py --amp 0 --tag fp32",
    "phase_b5_test_amp.log": "python -m pytest tests/test_cuda.py::test_amp -v -s",
    "phase_c_device_discovery.log": "python C:/P18/scratch/phase_c_device_discovery.py",
    "phase_c7_cvd_0.log": "python C:/P18/scratch/phase_c7_cvd_probe.py (CUDA_VISIBLE_DEVICES=0)",
    "phase_c7_cvd_empty.log": "python C:/P18/scratch/phase_c7_cvd_probe.py (CUDA_VISIBLE_DEVICES=)",
    "phase_c7_cvd_1.log": "python C:/P18/scratch/phase_c7_cvd_probe.py (CUDA_VISIBLE_DEVICES=1)",
    "phase_c7_cvd_abc.log": "python C:/P18/scratch/phase_c7_cvd_probe.py (CUDA_VISIBLE_DEVICES=abc)",
    "phase_c8_pytest.log": "python -m pytest tests/test_cuda.py::test_amp tests/test_python.py::test_select_idle_gpu_fallback tests/test_python.py::test_select_device -v -s",
    "phase_d_combined.log": "python C:/P18/scratch/phase_d_combined.py",
    "phase_d9_resume.log": "python C:/P18/scratch/phase_d9_resume.py",
    "phase_f_stability.log": "python C:/P18/scratch/phase_f_stability.py",
    "pip_torch_install.log": "pip install torch[device-gfx1100]==2.12.0+rocm7.14.1 torchvision torchaudio (AMD index)",
    "pip_venv101.log": "10.1.0 stack install + no-shim BatchNorm test (miopenStatusUnknownError)",
}
SRC_LOGS = Path(r"C:\P18\logs")
SRC_ROOT = Path(r"C:\P18")
SRC_EV = Path(r"C:\P18\evidence")

entries = []
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
for name, cmd in FILES.items():
    src = SRC_LOGS / name if (SRC_LOGS / name).is_file() else SRC_ROOT / name
    if not src.is_file():
        raise SystemExit(f"missing log: {src}")
    dst = DST / name
    shutil.copy2(src, dst)
    data = dst.read_bytes()
    entries.append({
        "path": f"evidence/raw/p18/{name}",
        "timestamp": now,
        "command": cmd,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    })

EXTRA = {
    "P18_ENVIRONMENT_AND_PROVENANCE.json": "environment freeze (auto-generated)",
    "p18_pr27198_results.json": "P18 result JSON (auto-generated from logs)",
    "p18_pr27203_results.json": "P18 result JSON (auto-generated from logs)",
    "p18_combined_results.json": "P18 result JSON (auto-generated from logs)",
    "p18_pip_freeze.txt": "pip freeze of validation venv",
    "pr27198.diff": "gh pr diff 27198 (frozen head e5ac8593)",
    "pr27203.diff": "gh pr diff 27203 (frozen head 563ff46e)",
}
for name, cmd in EXTRA.items():
    src = SRC_EV / name
    if not src.is_file():
        raise SystemExit(f"missing evidence: {src}")
    dst = DST / name
    shutil.copy2(src, dst)
    data = dst.read_bytes()
    entries.append({
        "path": f"evidence/raw/p18/{name}",
        "timestamp": now,
        "command": cmd,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    })

manifest_path = RCA / "evidence" / "manifest.json"
raw = manifest_path.read_text(encoding="utf-8-sig")
manifest = json.loads(raw)
manifest.extend(entries)
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"archived {len(entries)} files; manifest now {len(manifest)} entries")
