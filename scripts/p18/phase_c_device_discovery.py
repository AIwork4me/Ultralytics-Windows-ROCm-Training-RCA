"""P18 Phase C: device discovery & idle-GPU selection of PR #27203 on real gfx1100.

C1 cuda_is_available/cuda_device_count vs torch
C2 nvml_available
C3 parse_device("-1")
C4 select_idle_gpu memory gate (real measurement vs mem_get_info)
C5 select_idle_gpu min_util_fraction>0 without NVML -> [] + warning
C6 indices semantics: [] / [0] / [0,0] / [99999]; None vs [] differ
C7 (separate subprocess script) CUDA_VISIBLE_DEVICES=0 set before torch import
C9 fake-nvidia-smi success path (contract test, NOT NVIDIA hardware PASS)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile

RESULTS: dict = {"cases": {}, "provenance": {}}
CAPTURED: list[str] = []


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records: list[tuple[int, str]] = []

    def emit(self, record):
        self.records.append((record.levelno, record.getMessage()))


def check(cid: str, ok: bool, detail):
    RESULTS["cases"][cid] = {"pass": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {json.dumps(detail, default=str)[:220]}")
    return bool(ok)


def with_captured_logger(fn):
    import ultralytics.utils.autodevice as autodevice

    cap = Capture()
    autodevice.LOGGER.addHandler(cap)
    try:
        val = fn()
        return val, cap.records
    finally:
        autodevice.LOGGER.removeHandler(cap)


def main() -> int:
    import torch
    import ultralytics
    import ultralytics.utils.checks as checks
    from ultralytics.utils.autodevice import GPUInfo
    from ultralytics.utils.torch_utils import parse_device

    RESULTS["provenance"] = {
        "ultralytics_file": ultralytics.__file__,
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "device": torch.cuda.get_device_name(0),
    }
    assert "pr27203" in ultralytics.__file__.replace("\\", "/").lower(), ultralytics.__file__

    ok = True

    # C1 CUDA/HIP availability via PR functions
    ok &= check(
        "C1_availability",
        torch.cuda.is_available() and checks.cuda_is_available() and checks.cuda_device_count() == torch.cuda.device_count(),
        {
            "torch_cuda_is_available": torch.cuda.is_available(),
            "ultralytics_cuda_is_available": checks.cuda_is_available(),
            "ultralytics_cuda_device_count": checks.cuda_device_count(),
            "torch_device_count": torch.cuda.device_count(),
        },
    )

    # C2 NVML availability
    gi = GPUInfo()
    ok &= check("C2_nvml", gi.nvml_available is False, {"nvml_available": gi.nvml_available, "expect": False})

    # C3 parse_device("-1")
    d1 = parse_device("-1")
    d2 = parse_device("-1")
    alloc_ok = False
    try:
        t = torch.zeros(4, device=int(d1) if str(d1).isdigit() else 0)
        alloc_ok = bool(t.is_cuda and (t == 0).all().item())
    except Exception as e:  # noqa: BLE001
        alloc_ok = f"ALLOC_FAIL {e}"
    vis_before = os.environ.get("CUDA_VISIBLE_DEVICES")
    ok &= check(
        "C3_parse_device_-1",
        str(d1).isdigit() and 0 <= int(d1) < torch.cuda.device_count() and d1 == d2 and alloc_ok is True and vis_before == os.environ.get("CUDA_VISIBLE_DEVICES"),
        {"parse_-1": str(d1), "parse_-1_again": str(d2), "idempotent": d1 == d2, "tensor_alloc_cuda": alloc_ok, "cvd_unchanged": os.environ.get("CUDA_VISIBLE_DEVICES")},
    )

    # C4 memory gate measured for real
    free, total = torch.cuda.mem_get_info(0)
    sel4, logs4 = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1, min_memory_fraction=0.2, min_util_fraction=0))
    sel = sel4[0] if sel4 else None
    free2, total2 = torch.cuda.mem_get_info(0)
    ok &= check(
        "C4_memory_gate",
        sel == 0 and total > 20 * 2**30 and free / total >= 0.2 and total2 == total,
        {
            "selected": sel,
            "mem_free_frac": round(free / total, 4),
            "total_bytes": total,
            "stable_total": total2 == total,
            "logs": [m[:100] for _, m in logs4],
        },
    )

    # C5 unmeasurable utilization -> [] + truthful warning
    sel5, logs5 = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1, min_util_fraction=0.3))
    warn_msgs = [m for lv, m in logs5 if "NVML" in m or "utilization" in m.lower()]
    ok &= check(
        "C5_unmeasurable_util",
        sel5 == [] and len(warn_msgs) >= 1,
        {"selected": sel5, "warnings": [m[:140] for m in warn_msgs]},
    )

    # C6 indices semantics
    r_empty, _ = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1, indices=[]))
    r_zero, _ = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1, indices=[0], min_memory_fraction=0.0))
    r_dup, _ = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=2, indices=[0, 0]))
    r_oob, _ = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1, indices=[99999]))
    r_none, _ = with_captured_logger(lambda: GPUInfo().select_idle_gpu(count=1))
    ok &= check(
        "C6_indices",
        r_empty == [] and r_zero == [0] and r_dup == [0] and r_oob == [] and r_none == [0],
        {"indices=[]": r_empty, "indices=[0]": r_zero, "indices=[0,0] count=2": r_dup, "indices=[99999]": r_oob, "indices=None": r_none, "none_vs_empty_differ": r_none != r_empty},
    )

    # C9 nvidia-smi success path contract. CreateProcess cannot exec a fake .bat/.txt as
    # nvidia-smi.exe, so the success branch is exercised by patching subprocess.check_output
    # in a child process (code-level contract injection). The failure branch (nvidia-smi
    # absent) is exercised FOR REAL. Neither is an NVIDIA hardware PASS.
    code_fake = (
        "import sys; sys.path.insert(0, r'C:\\P18\\pr27203');"
        "import subprocess;"
        "orig = subprocess.check_output;"
        "subprocess.check_output = lambda cmd, **k: '2\\n' if cmd and cmd[0] == 'nvidia-smi' else orig(cmd, **k);"
        "import ultralytics.utils.checks as checks;"
        "print('patched_smi_count', checks.cuda_device_count())"
    )
    child_fake = subprocess.run([sys.executable, "-c", code_fake], capture_output=True, text=True)
    code_real = (
        "import sys; sys.path.insert(0, r'C:\\P18\\pr27203');"
        "import ultralytics.utils.checks as checks;"
        "print('no_smi_count', checks.cuda_device_count())"
    )
    child_real = subprocess.run([sys.executable, "-c", code_real], capture_output=True, text=True)
    fake_line = [l for l in child_fake.stdout.splitlines() if l.startswith("patched_smi_count")]
    real_line = [l for l in child_real.stdout.splitlines() if l.startswith("no_smi_count")]
    fake_count = int(fake_line[0].split()[1]) if fake_line else None
    real_count = int(real_line[0].split()[1]) if real_line else None
    ok &= check(
        "C9_nvidia_smi_contract",
        fake_count == 2 and real_count == torch.cuda.device_count(),
        {
            "patched_smi_success_branch_returns_2": fake_count,
            "real_no_smi_fallback_returns_torch_count": real_count,
            "torch_count": torch.cuda.device_count(),
            "note": "success branch via subprocess.check_output patch in child (contract injection); failure branch is REAL on this AMD host; NOT an NVIDIA hardware PASS",
        },
    )

    RESULTS["all_pass"] = ok
    print("RESULT_JSON_BEGIN")
    print(json.dumps(RESULTS, indent=2, default=str))
    print("RESULT_JSON_END")
    return 0 if ok else 6


if __name__ == "__main__":
    raise SystemExit(main())
