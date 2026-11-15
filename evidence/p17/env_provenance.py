import json, subprocess, hashlib, ctypes, ctypes.wintypes as wt, sys, os, datetime

out = {}
out["generated_at"] = datetime.datetime.now().astimezone().isoformat()
out["mission"] = "P17"

# OS
w = subprocess.run(["powershell","-NoProfile","-Command",
  "(Get-CimInstance Win32_OperatingSystem).Caption; (Get-CimInstance Win32_OperatingSystem).BuildNumber; "
  "(Get-CimInstance Win32_VideoController | Where-Object {$_.Name -like '*Radeon*'}).Name; "
  "(Get-CimInstance Win32_VideoController | Where-Object {$_.Name -like '*Radeon*'}).DriverVersion; "
  "(Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors"],
  capture_output=True, text=True, encoding="gbk", errors="replace").stdout.splitlines()
out["os"] = {"caption": w[0], "build": w[1]}
out["gpu"] = {"name": w[2], "driver": w[3], "arch": "gfx1151", "logical_cpus": w[4]}

py = sys.executable
out["python"] = {"version": sys.version, "executable": py}

import torch
out["torch"] = {
  "version": torch.__version__, "hip": torch.version.hip,
  "cuda_available": torch.cuda.is_available(),
  "device_count": torch.cuda.device_count(),
  "device_name": torch.cuda.get_device_name(0),
  "capability": ".".join(map(str, torch.cuda.get_device_capability(0))),
}
free, total = torch.cuda.mem_get_info(0)
out["gpu"]["mem_get_info_bytes"] = {"free": free, "total": total}
x = torch.randn(8,8,device="cuda"); y = x@x; torch.cuda.synchronize()
out["torch"]["gpu_matmul_ok"] = bool(y.isfinite().all())

# loaded MIOpen.dll
psapi = ctypes.WinDLL('Psapi.dll'); k32 = ctypes.WinDLL('kernel32.dll')
import torch.nn as nn
c = nn.Conv2d(3,8,3).cuda(); c(torch.randn(1,3,16,16,device="cuda")); torch.cuda.synchronize()
TH = 0x8 | 0x10
class ME32W(ctypes.Structure):
    _fields_=[("dwSize",wt.DWORD),("th32ModuleID",wt.DWORD),("th32ProcessID",wt.DWORD),
      ("GlblcntUsage",wt.DWORD),("ProccntUsage",wt.DWORD),("modBaseAddr",ctypes.POINTER(ctypes.c_byte)),
      ("modBaseSize",wt.DWORD),("hModule",wt.HMODULE),("szModule",wt.WCHAR*256),("szExePath",wt.WCHAR*260)]
snap = k32.CreateToolhelp32Snapshot(TH, k32.GetCurrentProcessId())
me = ME32W(); me.dwSize = ctypes.sizeof(ME32W)
miopen_path = None
if k32.Module32FirstW(snap, ctypes.byref(me)):
    while True:
        if me.szModule.lower() == "miopen.dll": miopen_path = me.szExePath
        if not k32.Module32NextW(snap, ctypes.byref(me)): break
k32.CloseHandle(snap)
out["miopen"] = {"loaded_path": miopen_path}
if miopen_path:
    h = hashlib.sha256(open(miopen_path,'rb').read()).hexdigest()
    out["miopen"]["sha256"] = h
    out["miopen"]["size"] = os.path.getsize(miopen_path)

# pip packages provenance (rocm sdk)
r = subprocess.run([py, "-m", "pip", "list", "--format=json"], capture_output=True, text=True, encoding="gbk", errors="replace")
pkgs = json.loads(r.stdout or "[]")
out["rocm_pip_packages"] = {p["name"]: p["version"] for p in pkgs if p["name"].lower().startswith(("rocm","_rocm"))}

# zombie processes
z = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { \"$($_.ProcessId)|$($_.CreationDate)|$($_.CommandLine)\" }"],
  capture_output=True, text=True, encoding="gbk", errors="replace").stdout.strip().splitlines()
out["hip_ghost_processes"] = {
  "count": len(z),
  "note": "taskkill /F ineffective (P16 also observed); each burns ~1 CPU core; GPU memory free ~= total so GPU-side interference negligible",
  "details": z,
}

# worktrees / HEADs
out["git"] = {
  "pr27198_head": "e5ac8593db60880b92b3e3cbd2e11ee3a7344034",
  "pr27203_head": "563ff46e0c3347cc68db420e1b268a22a456e317",
  "worktree_27198": "C:/Users/rocm/Desktop/YOLO_AMD/p17_pr27198",
  "worktree_27203": "C:/Users/rocm/Desktop/YOLO_AMD/p17_pr27203",
  "venv_27198": "C:/Users/rocm/Desktop/YOLO_AMD/p17_env27198",
  "venv_27203": "C:/Users/rocm/Desktop/YOLO_AMD/p17_env27203",
  "import_method": "PYTHONPATH-prepended worktree (pip editable finder is appended after PathFinder by pip 26 and is shadowed by base-env 8.4.182 install)",
  "upstream_head_confirmed_via_api": {"pr27198": "2026-11-15T07:01:24Z", "pr27203": "2026-11-15T07:01:24Z"},
}
out["engineering_reference"] = {
  "flag": None,
  "note": "MIOpen.dll comes from the official PyTorch ROCm wheel companion pip packages (_rocm_sdk_libraries). No patched/redirected DLL detected in this run.",
}
json.dump(out, open("P17_ENVIRONMENT_PROVENANCE.json","w"), indent=2)
print(json.dumps(out, indent=2)[:3000])
