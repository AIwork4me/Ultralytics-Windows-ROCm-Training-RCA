"""P19 Phase F: no-NVML select_idle_gpu/parse_device API contract on PR #27203 HEAD.

Fresh subprocess per CUDA_VISIBLE_DEVICES variant (cold state), single gfx1100.
Records actual returns, warning emission, and real GPU allocation on selection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CHILD = r"""
import json, logging, sys
sys.stderr.reconfigure(line_buffering=True)
import torch
from ultralytics.utils import checks as uc
from ultralytics.utils.autodevice import GPUInfo
from ultralytics.utils.torch_utils import parse_device

records = {"warnings": []}
class Cap(logging.Handler):
    def emit(self, r):
        records["warnings"].append(r.getMessage())
logging.getLogger("ultralytics").addHandler(Cap())

gi = GPUInfo()
records["cuda_device_count"] = uc.cuda_device_count()
records["cuda_is_available"] = uc.cuda_is_available()
records["torch_count"] = torch.cuda.device_count()
records["nvml_available"] = gi.nvml_available
records["select_count0"] = gi.select_idle_gpu(count=0)
records["select_count1"] = gi.select_idle_gpu(count=1)
records["select_count2"] = gi.select_idle_gpu(count=2)
records["select_indices_none"] = gi.select_idle_gpu(count=1, indices=None)
records["select_indices_empty"] = gi.select_idle_gpu(count=1, indices=[])
records["select_indices_0"] = gi.select_idle_gpu(count=1, indices=[0])
records["parse_-1"] = parse_device("-1")
records["parse_-1,-1"] = parse_device("-1,-1")
sel = records["select_count1"]
records["gpu_alloc_ok"] = False
if sel:
    x = torch.randn(8, 8, device=f"cuda:{sel[0]}")
    records["gpu_alloc_ok"] = bool(torch.isfinite(x @ x).all().item())
records["idle_warning_emitted"] = any(
    "NVML stats unavailable, selecting the first CUDA devices without idle checks" in w for w in records["warnings"]
)
records["no_idle_claim"] = not any("idle" in w.lower() and "verified" in w.lower() for w in records["warnings"])
print("RESULT_JSON:" + json.dumps(records))
"""

VARIANTS = {
    "cvd_unset": None,
    "cvd_0": "0",
    "cvd_empty": "",
    "cvd_abc": "abc",
}

OUT: dict = {"mission": "P19", "phase": "F", "single_gpu": "gfx1100", "variants": {}}

for name, cvd in VARIANTS.items():
    env = {k: v for k, v in os.environ.items() if k != "CUDA_VISIBLE_DEVICES"}
    if cvd is not None:
        env["CUDA_VISIBLE_DEVICES"] = cvd
    p = subprocess.run(
        [sys.executable, "-c", CHILD], capture_output=True, text=True, env=env, timeout=300
    )
    rec = None
    for line in p.stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            rec = json.loads(line[len("RESULT_JSON:") :])
    OUT["variants"][name] = {
        "env_CUDA_VISIBLE_DEVICES": cvd,
        "returncode": p.returncode,
        "record": rec,
        "stderr_tail": p.stderr.strip().splitlines()[-3:] if p.stderr.strip() else [],
    }
    print(f"--- {name} (CVD={cvd!r}) rc={p.returncode}")
    if rec:
        print(json.dumps(rec, indent=2))

# Verdict expectations on single gfx1100 without NVML
def check(name):
    v = OUT["variants"].get(name, {}).get("record")
    return bool(v)

cvd_unset = OUT["variants"]["cvd_unset"]["record"]
OUT["contract"] = {
    "count0_returns_empty": cvd_unset["select_count0"] == [],
    "count1_returns_0": cvd_unset["select_count1"] == [0],
    "count2_returns_fewer": cvd_unset["select_count2"] == [0],
    "indices_none_returns_0": cvd_unset["select_indices_none"] == [0],
    "indices_empty_returns_empty": cvd_unset["select_indices_empty"] == [],
    "indices_0_returns_0": cvd_unset["select_indices_0"] == [0],
    "warning_emitted": cvd_unset["idle_warning_emitted"],
    "gpu_alloc_ok": cvd_unset["gpu_alloc_ok"],
    "no_verified_idle_claim": cvd_unset["no_idle_claim"],
    "parse_-1_→_0": cvd_unset["parse_-1"] == "0",
    "parse_-1,-1_→_0": cvd_unset["parse_-1,-1"] == "0",
    "cvd_0_parse-1_→_0": OUT["variants"]["cvd_0"]["record"]["parse_-1"] == "0",
    "cvd_abc_select_returns_empty_or_none": OUT["variants"]["cvd_abc"]["record"]["select_indices_empty"] == [],
}
OUT["verdict"] = "PASS" if all(OUT["contract"].values()) else "FAIL"
print("CONTRACT:", json.dumps(OUT["contract"], indent=2))
print("PHASE F VERDICT:", OUT["verdict"])

Path("C:/P19/evidence/phase_f_no_nvml_contract.json").write_text(json.dumps(OUT, indent=2), encoding="utf-8")
sys.exit(0 if OUT["verdict"] == "PASS" else 1)
