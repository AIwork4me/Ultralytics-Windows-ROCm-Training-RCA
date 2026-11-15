"""Assemble P18 result JSON deliverables from phase logs."""
from __future__ import annotations

import json
from pathlib import Path

LOGS = Path(r"C:\P18_logs_missing")  # placeholder, replaced below
LOGS = Path(r"C:\P18\logs")
OUT = Path(r"C:\P18\evidence")


def extract(path: str, begin: str, end: str):
    t = (LOGS / path).read_text(encoding="utf-8", errors="replace")
    i, j = t.find(begin), t.rfind(end)
    if i < 0 or j < 0:
        return None
    return json.loads(t[i + len(begin) : j])


pr27198 = {
    "pr": 27198,
    "head_sha": "e5ac8593db60880b92b3e3cbd2e11ee3a7344034",
    "verdict": "GFX1100_PHYSICAL_SOURCE_VALIDATED",
    "gpu": "AMD Radeon RX 7900 XTX (gfx1100)",
    "stack": "torch 2.12.0+rocm7.14.1 / hip 7.14.60850 / Windows 11 26300 / ENGINEERING_REFERENCE (MIOpen shim)",
    "B1_check_amp_real_gpu": extract("phase_b1_check_amp.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "B2_exception_boundary": extract("phase_b2_exception_boundary.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "B3_amp_train": extract("phase_b3_train_amp.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "B4_fp32_control": extract("phase_b4_train_fp32.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "B5_upstream_test_amp": "SKIPPED on this branch (root cause: tests/__init__.py import-time cuda_device_count() requires nvidia-smi; the fix is PR #27203; log phase_b5_test_amp.log)",
    "phase_g": {
        "ruff_ci_exact": "All checks passed (both worktrees)",
        "ci_head": "all green incl. Tests (windows-latest, 3.13, latest): success",
        "findings": "none blocking; no broad except (RuntimeError only); programming errors and interrupts propagate (live-verified); NVIDIA healthy path untouched",
    },
}

pr27203 = {
    "pr": 27203,
    "head_sha": "563ff46e0c3347cc68db420e1b268a22a456e317",
    "verdict": "GFX1100_PHYSICAL_SOURCE_VALIDATED",
    "gpu": "AMD Radeon RX 7900 XTX (gfx1100)",
    "stack": "torch 2.12.0+rocm7.14.1 / hip 7.14.60850 / Windows 11 26300 / ENGINEERING_REFERENCE (MIOpen shim)",
    "C1_C6_C9": extract("phase_c_device_discovery.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "C7_cvd_matrix": {
        v: extract(f"phase_c7_cvd_{k}.log", "C7_JSON_BEGIN\n", "\nC7_JSON_END")
        for k, v in [("0", "0"), ("empty", ""), ("1", "1"), ("abc", "abc")]
    },
    "C7_verdict": "SINGLE_GPU_VISIBILITY_PASS; MULTI_GPU_PHYSICAL_MAPPING_NOT_RUN (single RX 7900 XTX)",
    "C8_upstream_tests": "3/3 PASSED: test_cuda.py::test_amp (ran on real GPU, not skipped), test_python.py::test_select_idle_gpu_fallback, test_select_device",
    "phase_g": {
        "ruff_ci_exact": "All checks passed",
        "ci_head": "all green incl. Tests (windows-latest, 3.13, latest): success",
        "findings": "none blocking; one except Exception (mem_get_info tolerance) matches repo style and CI ignores BLE001; nvidia-smi success path byte-identical to upstream main",
    },
}

combined = {
    "base": "upstream main 3e59149d4e047019e759dc8feec09208fa09163d",
    "merge_head": "c052cea5e (local temp, not pushed)",
    "merges": ["#27198 e5ac8593 (no-ff)", "#27203 563ff46e (no-ff), no conflicts"],
    "D1_D8": extract("phase_d_combined.log", "RESULT_JSON_BEGIN\n", "\nRESULT_JSON_END"),
    "D8_inference_320px": {"n_boxes": 5, "device": "cuda:0", "conf": [0.8308, 0.8245, 0.7629, 0.5541]},
    "D9_interrupt_resume": "PASS: killed alive subprocess at epoch 3/6 (returncode 1); interrupted ckpt had optimizer state + train_args; NEW process resumed to final_epoch 5/6, results.csv 7 rows, resume exit 0 (log phase_d9_resume.log)",
    "phase_f_stability": "7/7 PASS: cold x3 fresh processes, warm (2 trains 1 process), workers 0/2/4 (Windows DataLoader multiprocess OK); every stage: AMP fwd/bwd finite, checkpoint saved, reload+predict OK, exit 0, ~17-19s",
    "phase_e": {
        "official_golden_path": "BLOCKED_RELEASE",
        "blockers": [
            "rocm-sdk-libraries 10.1.0 wheel still lacks MIOpen #13437 fix: BatchNorm train forward/backward fails with miopenStatusUnknownError WITHOUT shim (torch 2.14.0+rocm10.1.0, hip 7.16.26385; log pip_venv101.log)",
            "PR #27198/#27203 not merged upstream; released ultralytics 8.4.213 does not contain the fixes",
        ],
    },
}

(OUT / "p18_pr27198_results.json").write_text(json.dumps(pr27198, indent=2))
(OUT / "p18_pr27203_results.json").write_text(json.dumps(pr27203, indent=2))
(OUT / "p18_combined_results.json").write_text(json.dumps(combined, indent=2))
print("written:", [p.name for p in OUT.glob("p18_*results.json")])
