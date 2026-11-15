"""Archive P19 raw evidence into the RCA repo per its conventions.

Copies logs/JSONs to evidence/raw/p19/, appends entries to evidence/manifest.json
(path, timestamp UTC, command, sha256, size_bytes) matching the existing schema.
Also emits merged environment.json / baseline_vs_pr.json / SHA256SUMS.txt.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import shutil
from pathlib import Path

RCA = Path(r"C:\P18\rca")
DST = RCA / "evidence" / "raw" / "p19"
DST.mkdir(parents=True, exist_ok=True)

SRC_LOGS = Path(r"C:\P19\logs")
SRC_EV = Path(r"C:\P19\evidence")


def utf8_of(p: Path) -> Path:
    """PS 5.1 redirect writes UTF-16LE; provide UTF-8 copies for readability."""
    out = SRC_LOGS / (p.stem + "_utf8.log")
    if not out.is_file():
        out.write_text(p.read_text(encoding="utf-16-le", errors="replace"), encoding="utf-8")
    return out


FILES = {
    # environment / preflight
    "environment.json": "merged P19 environment + runtime provenance (this script)",
    "runtime_provenance.json": "merged P19 runtime provenance (this script)",
    "P19_PHASE_A_ENV_GPU.json": "python C:/P19/scratch/phase_a_gpu_preflight.py",
    "phase_a_gpu_preflight.log": "python C:/P19/scratch/phase_a_gpu_preflight.py",
    "p19_pip_freeze.txt": "pip freeze (P19 venv, after amd-torchvision-device-gfx1100 install)",
    "pip_torch_install.log": "pip install torch/torchvision/torchaudio + device wheels (AMD multi-arch index)",
    # maintainer command 1
    "phase_b_maintainer_train.log": "yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1 (UTF-8 copy of PS redirect; attempt 2, exit 0)",
    "phase_b_maintainer_train_attempt1.log": "attempt 1 (exit 1): torchvision.ops.nms hipErrorInvalidDeviceFunction - missing amd-torchvision-device-gfx1100 wheel (AMD_PACKAGE_DEPENDENCY, not PR regression)",
    "phase_b_maintainer_train.json": "structured Phase B evidence",
    # maintainer command 2
    "phase_c_full_test_cuda.log": "pytest tests/test_cuda.py (UTF-8 copy of PS redirect; 8 passed/1 failed/1 skipped, exit 1)",
    "phase_c_targeted_diagnostics.log": "pytest tests/test_cuda.py::test_checks + ::test_train_cold_process_nonzero_device -v -rs",
    "phase_c_full_test_cuda.json": "structured Phase C evidence with failure classifications",
    # A/B + contract + optimizer
    "baseline_vs_pr.json": "Phase D A/B: upstream main 3e59149d vs PR d8fe65c8 on identical host",
    "phase_d_leg_main.json": "python C:/P19/scratch/phase_d_baseline_probe.py main (PYTHONPATH=C:/P19/baseline-main)",
    "phase_d_leg_pr.json": "python C:/P19/scratch/phase_d_baseline_probe.py pr",
    "phase_f_no_nvml_contract.json": "python C:/P19/scratch/phase_f_no_nvml_contract.py (subprocess CVD matrix)",
    "phase_f_no_nvml_contract.log": "python C:/P19/scratch/phase_f_no_nvml_contract.py",
    "phase_e_optimizer.log": "python C:/P19/scratch/phase_e_optimizer_evidence.py (v1: INCONCLUSIVE by design analysis)",
    "phase_e2_optimizer.log": "python C:/P19/scratch/phase_e2_optimizer_evidence.py (v2: 11 steps, 355/366 tensors changed)",
    "phase_e2_optimizer_evidence.json": "structured Phase E2 evidence",
    # frozen upstream inputs
    "pr27203_d8fe65c.diff": "gh api pulls/27203 (diff) at frozen head",
    "test_cuda.py.frozen": "tests/test_cuda.py @ d8fe65c8 (gh api contents)",
    "AGENTS_md.frozen": "AGENTS.md @ d8fe65c8 (gh api contents)",
    "ci_status_frozen_head.log": "gh pr checks 27203 @ d8fe65c8",
}

COPY_MAP: dict[str, Path] = {
    "P19_PHASE_A_ENV_GPU.json": SRC_EV / "P19_PHASE_A_ENV_GPU.json",
    "phase_a_gpu_preflight.log": SRC_LOGS / "phase_a_gpu_preflight.log",
    "p19_pip_freeze.txt": SRC_EV / "p19_pip_freeze.txt",
    "pip_torch_install.log": SRC_LOGS / "pip_torch_install.log",
    "phase_b_maintainer_train.log": utf8_of(SRC_LOGS / "phase_b_maintainer_train.log"),
    "phase_b_maintainer_train_attempt1.log": utf8_of(SRC_LOGS / "phase_b_maintainer_train_attempt1.log"),
    "phase_b_maintainer_train.json": SRC_EV / "phase_b_maintainer_train.json",
    "phase_c_full_test_cuda.log": SRC_LOGS / "phase_c_full_test_cuda_utf8.log",
    "phase_c_targeted_diagnostics.log": SRC_LOGS / "phase_c_targeted_diagnostics.log",
    "phase_c_full_test_cuda.json": SRC_EV / "phase_c_full_test_cuda.json",
    "phase_d_leg_main.json": SRC_EV / "phase_d_leg_main.json",
    "phase_d_leg_pr.json": SRC_EV / "phase_d_leg_pr.json",
    "phase_f_no_nvml_contract.json": SRC_EV / "phase_f_no_nvml_contract.json",
    "phase_f_no_nvml_contract.log": SRC_LOGS / "phase_f_no_nvml_contract.log",
    "phase_e_optimizer.log": SRC_LOGS / "phase_e_optimizer.log",
    "phase_e2_optimizer.log": SRC_LOGS / "phase_e2_optimizer.log",
    "phase_e2_optimizer_evidence.json": SRC_EV / "phase_e2_optimizer_evidence.json",
    "pr27203_d8fe65c.diff": SRC_EV / "pr27203_d8fe65c.diff",
    "test_cuda.py.frozen": SRC_EV / "test_cuda.py.frozen",
    "AGENTS_md.frozen": SRC_EV / "AGENTS_md.frozen",
}


def write_merged() -> None:
    a = json.loads((SRC_EV / "P19_PHASE_A_ENV_GPU.json").read_text(encoding="utf-8"))
    env = {
        "mission": "P19",
        "purpose": "Maintainer-requested validation of Ultralytics PR #27203 @ d8fe65c8 on Windows gfx1100",
        "maintainer_request": {
            "comment": "https://github.com/ultralytics/ultralytics/pull/27203#issuecomment-6893882839",
            "user": "glenn-jocher",
            "at": "2026-11-15T11:51:03Z",
            "commands": [
                "yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1",
                "pytest tests/test_cuda.py",
            ],
        },
        "pr": {"head": "d8fe65c8c1052cb4305f3cec1be9cb909538dcf1", "state": "OPEN/MERGEABLE", "files": 2,
               "diff": "+12/-12 vs main (3e59149d4 at test time)"},
        "os": a["os"],
        "driver": a["driver"],
        "smart_app_control": a["smart_app_control"],
        "gpu": a["torch"]["device_0"],
        "python": a["python"],
        "torch": a["torch"],
        "miopen": a["miopen"],
        "nvidia_smi": a["nvidia_smi"],
        "runtime_env": a["runtime_env"],
        "phase_a_verdict": a["verdict"],
    }
    (DST / "environment.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")

    prov = {
        "runtime_type": "ENGINEERING_REFERENCE",
        "definition": "AMD wheel bytes unchanged; HIPRTC_COMPILE_OPTIONS_APPEND points at local freestanding STL header shims required by MIOpen BatchNorm HIPRTC paths (ROCm/rocm-libraries#13437 / #15862 not yet in Windows wheels)",
        "hiprtc_append": a["runtime_env"]["HIPRTC_COMPILE_OPTIONS_APPEND"],
        "miopen_dll_sha256": a["miopen"]["sha256"],
        "torch_stack": {k: a["torch"][k] for k in ("torch", "hip")},
        "device_wheels": ["amd-torch-device-gfx1100 2.12.0+rocm7.14.1", "amd-torch-device-gfx110x 2.12.0+rocm7.14.1",
                          "amd-torchvision-device-gfx1100 0.27.0+rocm7.14.1"],
        "torchvision_wheel_note": "attempt 1 failed with hipErrorInvalidDeviceFunction in torchvision.ops.nms until amd-torchvision-device-gfx1100 was installed; known split-wheel dependency (P18), not PR-related",
        "official_release_status": "NOT official clean-install acceptance; ROCm 10.1.0 wheels still lack the MIOpen fix",
    }
    (DST / "runtime_provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")

    main_j = json.loads((SRC_EV / "phase_d_leg_main.json").read_text(encoding="utf-8"))
    pr_j = json.loads((SRC_EV / "phase_d_leg_pr.json").read_text(encoding="utf-8"))
    merged = {
        "mission": "P19", "phase": "D",
        "same_host_stack": "identical Windows/driver/torch/HIP/model/dataset/commands; only the ultralytics checkout differs",
        "leg_main": main_j,
        "leg_pr": pr_j,
        "conclusion": "main cannot see the AMD GPU through nvidia-smi-only counting (cuda_device_count=0, select_idle_gpu=[], parse_device('-1')='' -> CPU); PR d8fe65c8 detects and selects the real gfx1100 (count=1, [0], '0'), un-skipping the CUDA test suite",
    }
    (DST / "baseline_vs_pr.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


write_merged()

# capture CI status snapshot
ci_log = DST / "ci_status_frozen_head.log"
if not ci_log.is_file():
    import subprocess

    out = subprocess.run(
        ["gh", "pr", "checks", "27203", "--repo", "ultralytics/ultralytics"],
        capture_output=True, text=True, timeout=180,
    )
    ci_log.write_text(out.stdout + out.stderr, encoding="utf-8")
COPY_MAP["ci_status_frozen_head.log"] = ci_log

manifest_path = RCA / "evidence" / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
existing = {e["path"] for e in manifest}

now = datetime.datetime.now(datetime.timezone.utc).isoformat()
for name, cmd in FILES.items():
    src = COPY_MAP.get(name, DST / name)
    if not src.is_file():
        raise SystemExit(f"missing file: {name} -> {src}")
    dst = DST / name
    if src != dst:
        shutil.copy2(src, dst)
    data = dst.read_bytes()
    rel = f"evidence/raw/p19/{name}"
    if rel not in existing:
        manifest.append({
            "path": rel,
            "timestamp": now,
            "command": cmd,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        })

manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

# dir-local checksums
sums = []
for p in sorted(DST.iterdir()):
    if p.is_file() and p.name != "SHA256SUMS.txt":
        sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(DST / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

print(f"archived {len(FILES)} files to {DST}; manifest now {len(manifest)} entries")
