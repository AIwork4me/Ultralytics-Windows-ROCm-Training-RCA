"""Phase 4 / Gates P51-P52 - runtime validation of the canonical MIOpen.dll.

Method (Phase-3 validated): temporarily swap the wheel's MIOpen.dll with
the canonical build (backup kept), run PyTorch with a probe that proves
via GetModuleFileNameW + SHA256 which MIOpen.dll is actually loaded, then
restore the pristine wheel DLL (hash-verified).

P52 regressions: GPU control, minimal BatchNorm train/eval/backward with
numerics vs CPU reference, finite-output checks.
"""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
EV = RCA / "evidence" / "phase4" / "windows_runtime"
PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe")

WHEEL_DLL = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"
                 r"\_rocm_sdk_libraries\bin\MIOpen.dll")
CANON_DLL = Y / "phase4_build" / "miopen" / "bin" / "MIOpen.dll"
WHEEL_SHA = "74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a"

PROBE = r"""
import ctypes, hashlib, json, sys
import torch, torch.nn as nn
# exercise an RTC-compiled op so MIOpen is actually loaded and used
m = nn.BatchNorm2d(8).cuda().train()
x = torch.randn(4, 8, 32, 32, device="cuda")
y = m(x)
torch.cuda.synchronize()
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
k32.GetModuleFileNameW.restype = ctypes.c_uint
h = k32.GetModuleHandleW("MIOpen.dll")
if not h:
    print(json.dumps({"loaded": False, "y_finite": bool(torch.isfinite(y).all())})); sys.exit(0)
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048)
path = buf.value if n else ""
sha = hashlib.sha256(open(path, "rb").read()).hexdigest() if path else None
print(json.dumps({"loaded": True, "path": path, "sha256": sha,
                  "y_finite": bool(torch.isfinite(y).all())}))
"""

BN_TEST = r"""
import json, torch, torch.nn as nn
torch.manual_seed(7)
m = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = m(x)
torch.cuda.synchronize()
xc = x.detach().cpu().double()
mc = nn.BatchNorm2d(16).double().train()
mc.weight.data = m.weight.data.detach().cpu().double()
mc.bias.data = m.bias.data.detach().cpu().double()
mc.running_mean.data = m.running_mean.data.detach().cpu().double()
mc.running_var.data = m.running_var.data.detach().cpu().double()
yc = mc(xc)
y_c = y.detach().cpu().double()
out = {
    "y_shape": list(y.shape),
    "y_finite": bool(torch.isfinite(y).all()),
    "max_abs_vs_cpu": float((y_c - yc).abs().max()),
    "running_stats_finite": bool(torch.isfinite(m.running_mean).all()
                                 and torch.isfinite(m.running_var).all()),
    "running_mean_changed": bool((m.running_mean != 0).any()),
    "eval_ok": None,
    "backward_finite": None,
}
m.eval()
with torch.no_grad():
    ye = m(x)
    torch.cuda.synchronize()
    out["eval_ok"] = bool(torch.isfinite(ye).all())
xg = x.clone().requires_grad_(True)
yg = m(xg)
(yg * yg).mean().backward()
torch.cuda.synchronize()
out["backward_finite"] = bool(torch.isfinite(xg.grad).all())
print(json.dumps(out))
"""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run_py(code: str, name: str) -> dict:
    p = subprocess.run([str(PY), "-c", code], capture_output=True, text=True,
                       timeout=900, cwd=str(Y))
    rec = {"name": name, "exit": p.returncode,
           "stdout": p.stdout[-6000:], "stderr": p.stderr[-8000:]}
    (EV / f"{name}.txt").write_text(
        f"exit={p.returncode}\n{p.stdout}\n{p.stderr}", encoding="utf-8")
    return rec


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    canon_sha = sha256(CANON_DLL)
    print("canonical dll:", CANON_DLL, canon_sha)

    if sha256(WHEEL_DLL) != WHEEL_SHA:
        print("WHEEL DLL NOT PRISTINE - refusing to swap")
        return 2
    backup = WHEEL_DLL.with_suffix(".dll.phase4bak")
    swapped = False
    record = {"schema": "phase4_runtime_binding_v1",
              "gate": "P51+P52(A-D)", "timestamp": datetime.now().isoformat(),
              "canonical_dll": str(CANON_DLL), "canonical_sha256": canon_sha,
              "wheel_dll": str(WHEEL_DLL), "wheel_sha256_expected": WHEEL_SHA}
    try:
        shutil.copy2(WHEEL_DLL, backup)
        shutil.copy2(CANON_DLL, WHEEL_DLL)
        swapped = True
        print("swapped; proving binding...")
        probe = run_py(PROBE, "binding_probe")
        loaded = None
        for line in probe["stdout"].splitlines():
            if line.startswith("{"):
                loaded = json.loads(line)
        record["binding_probe"] = loaded
        record["canonical_loaded"] = bool(
            loaded and loaded.get("sha256") == canon_sha)
        print("canonical loaded:", record["canonical_loaded"])

        if record["canonical_loaded"]:
            record["gpu_control"] = run_py(
                "import torch;print(torch.cuda.is_available(), "
                "torch.cuda.get_device_name(0))", "gpu_control")
            record["batchnorm"] = run_py(BN_TEST, "batchnorm_minimal")
    finally:
        if swapped:
            shutil.copy2(backup, WHEEL_DLL)
            backup.unlink()
            restored_sha = sha256(WHEEL_DLL)
            record["wheel_restored_sha256"] = restored_sha
            record["wheel_restored_ok"] = restored_sha == WHEEL_SHA
            print("wheel restored ok:", record["wheel_restored_ok"])
    (EV / "runtime_binding.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    ok = record.get("canonical_loaded") and record.get("wheel_restored_ok")
    print("P51:", "PASS" if record.get("canonical_loaded") else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
