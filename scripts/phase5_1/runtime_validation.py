"""Phase 5.1 (P5.1-CANDIDATE-R1) - adapted from the validated Phase-5
script by mechanical path/identity substitution only (source tree, build
dir, evidence dir, schema/gate names). Logic unchanged.
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
EV = RCA / "evidence" / "phase5_1" / "runtime"
PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe")

WHEEL_DLL = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"
                 r"\_rocm_sdk_libraries\bin\MIOpen.dll")
P5_DLL = Y / "phase5_1_build" / "miopen" / "bin" / "MIOpen.dll"
WHEEL_SHA = "74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a"
MSVC_INC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207\include")

# Tolerances fixed before any run (Phase-4 reference: 6.845e-7 max_abs
# on BN output fp32-vs-cpu-fp64; bar relaxed one order for the different
# upstream BN kernel revision, still far below functional significance).
TOL = {"y_abs": 1e-5, "running_mean_abs": 1e-4, "running_var_rel": 1e-3,
       "dx_abs": 1e-5, "dw_abs": 1e-4, "db_abs": 1e-5}

PROBE = r"""
import ctypes, hashlib, json, sys
import torch, torch.nn as nn
m = nn.BatchNorm2d(8).cuda().train()
x = torch.randn(4, 8, 32, 32, device="cuda")
y = m(x)
torch.cuda.synchronize()
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
h = k32.GetModuleHandleW("MIOpen.dll")
if not h:
    print(json.dumps({"loaded": False})); sys.exit(0)
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048)
path = buf.value if n else ""
sha = hashlib.sha256(open(path, "rb").read()).hexdigest() if path else None
print(json.dumps({"loaded": True, "path": path, "sha256": sha,
                  "gpu": torch.cuda.get_device_name(0),
                  "torch": torch.__version__,
                  "y_finite": bool(torch.isfinite(y).all())}))
"""

NUMERICS = r"""
import ctypes, hashlib, json
import torch, torch.nn as nn
torch.manual_seed(20261008)
C, N, H, W = 16, 8, 64, 64
m = nn.BatchNorm2d(C).cuda().train()
x = torch.randn(N, C, H, W, device="cuda")
y = m(x)
xg = x.clone().requires_grad_(True)
yg = m(xg)
(yg * yg).mean().backward()
torch.cuda.synchronize()

# CPU fp64 reference with identical parameters/state AFTER the fwd pass
mcpu = nn.BatchNorm2d(C).double().train()
mcpu.weight.data = m.weight.data.detach().cpu().double()
mcpu.bias.data = m.bias.data.detach().cpu().double()
mcpu.running_mean.data = m.running_mean.data.detach().cpu().double()
mcpu.running_var.data = m.running_var.data.detach().cpu().double()
xc = x.detach().cpu().double()
yc = mcpu(xc)
xgc = xc.clone().requires_grad_(True)
ygc = mcpu(xgc)
(ygc * ygc).mean().backward()

y64 = y.detach().cpu().double()
dx64 = xg.grad.detach().cpu().double()
dxref = xgc.grad.detach().cpu().double()
dw64 = m.weight.grad.detach().cpu().double()
dwref = mcpu.weight.grad.detach().cpu().double()
db64 = m.bias.grad.detach().cpu().double()
dbref = mcpu.bias.grad.detach().cpu().double()
rm = m.running_mean.detach().cpu().double()
rv = m.running_var.detach().cpu().double()
# running stats REFERENCE recomputed from the actual input batch (fp64).
# The workload above performs TWO training forward passes (y and yg) with
# the same x, each updating running stats with momentum 0.1:
#   rm: 0 -> 0.1*b -> 0.9*(0.1*b) + 0.1*b = 0.19*b
#   rv: 1 -> 0.9*1+0.1*v -> 0.9*(0.9+0.1v) + 0.1*v = 0.81 + 0.19*v
flat = xc.transpose(1, 0).reshape(C, -1).double()
rm_ref = flat.mean(dim=1)
batch_var_unbiased = flat.var(dim=1, unbiased=True)
rm_expect = 0.19 * rm_ref
rv_expect = 0.81 + 0.19 * batch_var_unbiased

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
h = k32.GetModuleHandleW("MIOpen.dll")
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048) if h else 0
path = buf.value if n else ""
sha = hashlib.sha256(open(path, "rb").read()).hexdigest() if path else None

out = {
  "miopen_path": path, "miopen_sha256": sha,
  "dtype": "float32 gpu vs float64 cpu", "shape": [N, C, H, W],
  "max_abs": {
    "y": float((y64 - yc).abs().max()),
    "dx": float((dx64 - dxref).abs().max()),
    "dw": float((dw64 - dwref).abs().max()),
    "db": float((db64 - dbref).abs().max()),
    "running_mean": float((rm - rm_expect).abs().max()),
    "running_var": float((rv - rv_expect).abs().max()),
  },
  "max_rel_where_meaningful": {
    "running_var": float(((rv - rv_expect).abs() / rv_expect.clamp(min=1e-6)).max()),
  },
  "finite": {
    "y": bool(torch.isfinite(y64).all()), "dx": bool(torch.isfinite(dx64).all()),
    "dw": bool(torch.isfinite(dw64).all()), "db": bool(torch.isfinite(db64).all()),
    "running_mean": bool(torch.isfinite(rm).all()),
    "running_var": bool(torch.isfinite(rv).all()),
  },
}
print(json.dumps(out))
"""

NOSTL_WORKLOAD = r"""
import ctypes, hashlib, json
import torch, torch.nn as nn
m = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = m(x)
xg = x.clone().requires_grad_(True)
yg = m(xg)
(yg * yg).mean().backward()
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
    "running_mean_changed": bool((m.running_mean != 0).any()),
}))
"""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run_py(code: str, name: str, env=None) -> dict:
    e = env or os.environ
    p = subprocess.run([str(PY), "-c", code], capture_output=True, text=True,
                       timeout=1200, cwd=str(Y), env=dict(e))
    rec = {"name": name, "exit": p.returncode,
           "stdout": p.stdout[-9000:], "stderr": p.stderr[-12000:]}
    (EV / f"{name}.txt").write_text(
        f"exit={p.returncode}\n{p.stdout}\n{p.stderr}", encoding="utf-8")
    return rec


def jline(rec):
    for line in reversed(rec["stdout"].splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    return None


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    if not P5_DLL.exists():
        for cand in (Y / "phase5_1_build" / "miopen").rglob("MIOpen.dll"):
            globals()["P5_DLL"] = cand
            break
    p5_sha = sha256(P5_DLL)
    print("phase5 dll:", P5_DLL, p5_sha)
    if sha256(WHEEL_DLL) != WHEEL_SHA:
        print("WHEEL DLL NOT PRISTINE - refusing")
        return 2

    record = {"schema": "phase5_1_runtime_validation_v1",
              "gate": "P51-10+11+12",
              "timestamp": datetime.now().isoformat(),
              "phase5_dll": str(P5_DLL), "phase5_dll_sha256": p5_sha,
              "wheel_dll": str(WHEEL_DLL), "wheel_sha_expected": WHEEL_SHA,
              "tolerances_fixed_before_run": TOL}
    ok = True
    dll_backup = WHEEL_DLL.with_suffix(".dll.p51bak")
    try:
        shutil.copy2(WHEEL_DLL, dll_backup)
        shutil.copy2(P5_DLL, WHEEL_DLL)

        # ---- P51-10 provenance ----
        probe = run_py(PROBE, "binding_probe")
        loaded = jline(probe)
        record["provenance"] = loaded
        record["phase5_canonical_miopen_loaded"] = bool(
            loaded and loaded.get("sha256") == p5_sha)
        print("P51-10 loaded proven:", record["phase5_canonical_miopen_loaded"])
        ok = ok and record["phase5_canonical_miopen_loaded"]

        # ---- P51-12 numerics (same swapped DLL) ----
        num = run_py(NUMERICS, "numerics_batchnorm")
        r = jline(num)
        record["numerics"] = r
        if r:
            ma = r["max_abs"]
            checks = {
                "y": ma["y"] <= TOL["y_abs"],
                "dx": ma["dx"] <= TOL["dx_abs"],
                "dw": ma["dw"] <= TOL["dw_abs"],
                "db": ma["db"] <= TOL["db_abs"],
                "running_mean": ma["running_mean"] <= TOL["running_mean_abs"],
                "running_var_rel": r["max_rel_where_meaningful"]["running_var"] <= TOL["running_var_rel"],
                "all_finite": all(r["finite"].values()),
                "provenance_inside_process": r.get("miopen_sha256") == p5_sha,
            }
            record["numerics_checks"] = checks
            print("P51-12 numerics:", checks)
            ok = ok and all(checks.values())
        else:
            record["numerics_checks"] = {"parse": False}
            ok = False
    finally:
        shutil.copy2(dll_backup, WHEEL_DLL)
        dll_backup.unlink()
        record["wheel_restored_ok"] = sha256(WHEEL_DLL) == WHEEL_SHA
        print("wheel restored:", record["wheel_restored_ok"])
        ok = ok and record["wheel_restored_ok"]

    (EV / "dll_provenance.json").write_text(
        json.dumps({k: record[k] for k in
                    ["schema", "gate", "timestamp", "phase5_dll",
                     "phase5_dll_sha256", "provenance",
                     "phase5_canonical_miopen_loaded", "wheel_dll",
                     "wheel_sha_expected", "wheel_restored_ok"]},
                   indent=2) + "\n", encoding="utf-8")

    # ---- P51-11 no-STL (separate swap cycle, reversible MSVC rename) ----
    if not MSVC_INC.exists():
        print("MSVC include tree missing - cannot isolate")
        record["nostl"] = {"error": "msvc include missing"}
        ok = False
    else:
        iso = Path(tempfile.gettempdir()) / f"phase5_1_iso_nostl_{uuid.uuid4().hex[:8]}"
        (iso / "AppData" / "Local").mkdir(parents=True)
        (iso / "tmp").mkdir()
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ["SYSTEMROOT"],
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", "C:"),
            "USERPROFILE": str(iso),
            "LOCALAPPDATA": str(iso / "AppData" / "Local"),
            "TEMP": str(iso / "tmp"), "TMP": str(iso / "tmp"),
            "COMSPEC": os.environ.get("COMSPEC", r"C:\Windows\system32\cmd.exe"),
            "PYTHONPATH": "",
        }
        for v in ("INCLUDE", "LIB", "ROCM_PATH", "MIOPEN_FIND_MODE",
                  "MIOPEN_USER_CACHE_PATH", "MIOPEN_USER_DB_PATH",
                  "AMD_COMGR_CACHE", "CPATH", "C_INCLUDE_PATH",
                  "CPLUS_INCLUDE_PATH"):
            env.pop(v, None)
        inc_backup = MSVC_INC.with_name("include.p51bak")
        dll_backup2 = WHEEL_DLL.with_suffix(".dll.p51bak2")
        nostl = {"gate": "P51-11", "fresh_profile": str(iso),
                 "env_scrubbed": ["INCLUDE", "LIB", "ROCM_PATH", "CPATH",
                                  "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH",
                                  "AMD_COMGR_CACHE", "MIOPEN_USER_CACHE_PATH",
                                  "MIOPEN_USER_DB_PATH"]}
        try:
            shutil.copy2(WHEEL_DLL, dll_backup2)
            shutil.copy2(P5_DLL, WHEEL_DLL)
            MSVC_INC.rename(inc_backup)
            assert not MSVC_INC.exists()
            print("isolated: DLL swapped, MSVC include renamed, fresh profile")
            w = run_py(NOSTL_WORKLOAD, "nostl_workload", env=env)
            r = jline(w) or {}
            nostl.update({"exit_code": w["exit"], "result": r,
                          "stdout": w["stdout"][-4000:],
                          "stderr": w["stderr"][-9000:]})
            nostl["checks"] = {
                "exit_zero": w["exit"] == 0,
                "provenance": r.get("miopen_sha256") == p5_sha,
                "y_finite": r.get("y_finite"),
                "grad_finite": r.get("grad_finite"),
                "running_stats_finite": r.get("running_stats_finite"),
                "running_mean_changed": r.get("running_mean_changed"),
            }
            print("P51-11 no-STL:", nostl["checks"])
            ok = ok and all(nostl["checks"].values())
        finally:
            if inc_backup.exists():
                inc_backup.rename(MSVC_INC)
            if dll_backup2.exists():
                shutil.copy2(dll_backup2, WHEEL_DLL)
                dll_backup2.unlink()
            nostl["msvc_include_restored"] = MSVC_INC.exists()
            nostl["wheel_restored_ok"] = sha256(WHEEL_DLL) == WHEEL_SHA
            shutil.rmtree(iso, ignore_errors=True)
            print("restored: msvc", nostl["msvc_include_restored"],
                  "wheel", nostl["wheel_restored_ok"])
            ok = ok and nostl["msvc_include_restored"] and nostl["wheel_restored_ok"]
        record["nostl"] = nostl
        (EV / "nostl_validation.json").write_text(
            json.dumps(nostl, indent=2) + "\n", encoding="utf-8")

    record["overall"] = "PASS" if ok else "FAIL"
    (EV / "runtime_validation.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("OVERALL:", record["overall"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
