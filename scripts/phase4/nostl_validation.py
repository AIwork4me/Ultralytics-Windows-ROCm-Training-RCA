"""Phase 4 / Gate P52(C) - no-host-STL validation of the canonical MIOpen.dll.

Phase-3 isolation procedure: swap in the canonical DLL (wheel backed up),
make the MSVC include tree unreachable (rename), run a BatchNorm train
workload under a FRESH user profile (redirected USERPROFILE/LOCALAPPDATA =>
fresh MIOpen user kernel DB + comgr cache) so the RTC compile actually
happens, then restore everything (hash-verified). Proves the no-STL
condition via the include dir being renamed, and the DLL binding in the
same process.
"""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
EV = RCA / "evidence" / "phase4" / "windows_runtime"
PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe")

WHEEL_DLL = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"
                 r"\_rocm_sdk_libraries\bin\MIOpen.dll")
CANON_DLL = Y / "phase4_build" / "miopen" / "bin" / "MIOpen.dll"
CANON_SHA = "b32d6310817a225ff81cfe8de3dfe2a0d5c525caa845bad1f4d2304abc6aa721"
WHEEL_SHA = "74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a"
MSVC_INC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207\include")

WORKLOAD = r"""
import ctypes, hashlib, json
import torch, torch.nn as nn
m = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = m(x)
xg = x.clone().requires_grad_(True)
yg = m(xg)
(yg*yg).mean().backward()
torch.cuda.synchronize()
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
h = k32.GetModuleHandleW("MIOpen.dll")
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048) if h else 0
path = buf.value if n else ""
sha = hashlib.sha256(open(path, "rb").read()).hexdigest() if path else None
print(json.dumps({
    "miopen_path": path, "miopen_sha256": sha,
    "y_finite": bool(torch.isfinite(y).all()),
    "grad_finite": bool(torch.isfinite(xg.grad).all()),
    "running_stats_finite": bool(torch.isfinite(m.running_mean).all()
                                 and torch.isfinite(m.running_var).all()),
}))
"""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    record = {"schema": "phase4_nostl_validation_v1", "gate": "P52C",
              "timestamp": datetime.now().isoformat(),
              "canonical_sha256_expected": CANON_SHA}
    if sha256(CANON_DLL) != CANON_SHA:
        print("canonical dll hash mismatch")
        return 2
    if sha256(WHEEL_DLL) != WHEEL_SHA:
        print("wheel dll not pristine - refusing")
        return 2
    if not MSVC_INC.exists():
        print("MSVC include tree missing")
        return 2

    iso = Path(tempfile.gettempdir()) / f"phase4_iso_nostl_{uuid.uuid4().hex[:8]}"
    (iso / "AppData" / "Local").mkdir(parents=True)
    (iso / "tmp").mkdir()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ["SYSTEMROOT"],
        "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", "C:"),
        "USERPROFILE": str(iso),
        "LOCALAPPDATA": str(iso / "AppData" / "Local"),
        "TEMP": str(iso / "tmp"),
        "TMP": str(iso / "tmp"),
        "COMSPEC": os.environ.get("COMSPEC", r"C:\Windows\system32\cmd.exe"),
        "PYTHONPATH": "",
    }
    for v in ("INCLUDE", "LIB", "ROCM_PATH", "MIOPEN_FIND_MODE",
              "MIOPEN_USER_CACHE_PATH", "MIOPEN_USER_DB_PATH", "AMD_COMGR_CACHE",
              "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH"):
        env.pop(v, None)

    dll_backup = WHEEL_DLL.with_suffix(".dll.phase4bak2")
    inc_backup = MSVC_INC.with_name("include.phase4bak")
    try:
        shutil.copy2(WHEEL_DLL, dll_backup)
        shutil.copy2(CANON_DLL, WHEEL_DLL)
        MSVC_INC.rename(inc_backup)
        assert not MSVC_INC.exists(), "MSVC include still reachable - rename failed"
        print("isolated: canonical DLL swapped, MSVC include renamed, fresh profile")
        p = subprocess.run([str(PY), "-c", WORKLOAD], env=env,
                           capture_output=True, text=True, timeout=1200, cwd=str(Y))
        record.update({
            "exit_code": p.returncode,
            "stdout": p.stdout[-8000:],
            "stderr": p.stderr[-12000:],
            "msvc_include_renamed": True,
            "fresh_profile": str(iso),
            "env_scrubbed": ["INCLUDE", "LIB", "ROCM_PATH", "CPATH",
                             "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH",
                             "AMD_COMGR_CACHE", "MIOPEN_USER_CACHE_PATH"],
        })
        print("exit:", p.returncode)
        print(p.stdout[-1500:])
        print(p.stderr[-2500:])
    finally:
        # restore everything regardless of outcome
        if inc_backup.exists():
            inc_backup.rename(MSVC_INC)
        if dll_backup.exists():
            shutil.copy2(dll_backup, WHEEL_DLL)
            dll_backup.unlink()
        record["msvc_include_restored"] = MSVC_INC.exists()
        record["wheel_restored_ok"] = sha256(WHEEL_DLL) == WHEEL_SHA
        shutil.rmtree(iso, ignore_errors=True)
        print("restored: msvc_include", record["msvc_include_restored"],
              "wheel", record["wheel_restored_ok"])

    result = None
    for line in record["stdout"].splitlines():
        if line.startswith("{"):
            result = json.loads(line)
    record["result"] = result
    ok = bool(p.returncode == 0 and result
              and result.get("miopen_sha256") == CANON_SHA
              and result.get("y_finite") and result.get("grad_finite")
              and result.get("running_stats_finite")
              and record["msvc_include_restored"] and record["wheel_restored_ok"])
    record["overall"] = "PASS" if ok else "FAIL"
    (EV / "nostl_validation.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("P52C no-STL validation:", record["overall"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
