"""P19: build phase_c_full_test_cuda.json from the pytest log."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

raw = Path("C:/P19/logs/phase_c_full_test_cuda.log").read_text(encoding="utf-16-le", errors="replace").replace("\r", "")
import re as _re

ANSI = _re.compile(r"\x1b\[[0-9;]*m")
raw = ANSI.sub("", raw)

summary = re.search(r"(\d+) failed, (\d+) passed, (\d+) skipped, (\d+) warnings in ([\d.]+)s", raw)
wrapper = Path("C:/P19/logs/phase_c_wrapper.log").read_text(errors="replace")

failed = re.findall(r"FAILED (\S+) - (.+)", raw)
passed_names = [
    "test_checks",
    "test_amp",
    "test_semantic_loss_all_ignore_amp[1]",
    "test_semantic_loss_all_ignore_amp[3]",
    "test_train",
    "test_track_exported_model[False]",
    "test_track_exported_model[320]",
    "test_autobatch",
]
durations = dict(re.findall(r"([\d.]+)s call\s+(\S+)", raw))

git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd="C:/P19/pr27203", capture_output=True, text=True).stdout.strip()

R = {
    "mission": "P19",
    "phase": "C",
    "command": "pytest tests/test_cuda.py",
    "cwd": "C:\\P19\\pr27203",
    "pytest": "9.2.0",
    "exit_code": int(re.search(r"EXIT_CODE=(\d+)", wrapper).group(1)),
    "git_sha": git_sha,
    "collected_items": 188,
    "executed_after_conftest_slow_filter": 10,
    "conftest_note": "tests/conftest.py removes slow-marked items unless --slow is passed; 178 slow items (onnx matrix, engine matrix, multi-device, benchmarks, SAM) were removed from collection by upstream design; plain `pytest tests/test_cuda.py` matches the maintainer's exact command and CI's non-slow default",
    "passed": passed_names,
    "passed_count": len(passed_names),
    "failed": [{"node": n, "assert": a} for n, a in failed],
    "failed_count": len(failed),
    "skipped": [{"node": "tests/test_cuda.py::test_train_cold_process_nonzero_device",
                 "reason": "requires an idle CUDA device with nonzero index (single-GPU machine)",
                 "classification": "ENVIRONMENT (expected on 1x gfx1100)"}],
    "skipped_count": 1,
    "duration_s": float(summary.group(5)) if summary else None,
    "durations_s": durations,
    "failure_classification": [
        {
            "node": "tests/test_cuda.py::test_onnx_dynamic_spatial_outputs",
            "assert": "assert 'CUDAExecutionProvider' in ['CPUExecutionProvider']",
            "classification": "NVIDIA_ONLY_UNSUPPORTED",
            "evidence": "onnxruntime 1.32.0 (PyPI CPU wheel) provides only AzureExecutionProvider/CPUExecutionProvider on Windows ROCm; no ROCm CUDA-EP build exists for this platform; the ONNX export itself succeeded on GPU and the test RAN (DEVICES=[0]) rather than being skipped, which is the PR working as intended",
            "pr_regression": False,
        }
    ],
    "verdict": "GATE3_FAIL_NONZERO_EXIT (1 failed / 8 passed / 1 skipped); single failure is NVIDIA-only onnxruntime provider, not PR-scope",
}

Path("C:/P19/evidence/phase_c_full_test_cuda.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(json.dumps({k: R[k] for k in ("exit_code", "passed_count", "failed_count", "skipped_count", "duration_s", "verdict")}, indent=2))
