"""Phase 4 / Gate P52(E) - YOLO26n training on GPU with the canonical MIOpen.dll.

Swap in the canonical DLL (wheel backed up), run ultralytics training in a
FRESH user-profile env (fresh MIOpen kernel cache => real RTC compiles),
first with amp=False then with default AMP; restore afterwards. Provenance
probe inside the same run: loaded MIOpen.dll path + SHA256.
"""
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

RUN_PREFIX = """
import ctypes, hashlib, json
from ultralytics import YOLO
import torch

# provenance BEFORE heavy work: which MIOpen.dll is loaded right now
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
h = k32.GetModuleHandleW("MIOpen.dll")
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048) if h else 0
miopen_path = buf.value if n else ""
miopen_sha = hashlib.sha256(open(miopen_path, 'rb').read()).hexdigest() if miopen_path else None
print("MIOPEN_PROVENANCE " + json.dumps(
    {"path": miopen_path, "sha256": miopen_sha,
     "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))

model = YOLO(r"C:\\Users\\rocm\\Desktop\\YOLO_AMD\\yolo26n.pt")
results = model.train(data="coco8.yaml", epochs=1, imgsz=640, device=0,
                      workers=0%AMPARG%)
print("TRAIN_DONE")
"""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run_train(tag: str, amparg: str) -> dict:
    iso = Path(tempfile.gettempdir()) / f"phase4_yolo_{tag}_{uuid.uuid4().hex[:8]}"
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
        "USERNAME": os.environ.get("USERNAME", "rocm"),
        "HOMEDRIVE": "C:",
        "HOMEPATH": str(iso),
        "WORLD_SIZE": "1",
    }
    for v in ("INCLUDE", "LIB", "ROCM_PATH", "MIOPEN_FIND_MODE",
              "MIOPEN_USER_CACHE_PATH", "MIOPEN_USER_DB_PATH", "AMD_COMGR_CACHE",
              "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH"):
        env.pop(v, None)
    code = RUN_PREFIX.replace("%AMPARG%", amparg)
    p = subprocess.run([str(PY), "-c", code], env=env, capture_output=True,
                       text=True, timeout=3600, cwd=str(Y))
    shutil.rmtree(iso, ignore_errors=True)
    prov = None
    for line in p.stdout.splitlines():
        if line.startswith("MIOPEN_PROVENANCE "):
            prov = json.loads(line[len("MIOPEN_PROVENANCE "):])
    rec = {"tag": tag, "amparg": amparg, "exit_code": p.returncode,
           "provenance": prov,
           "train_done": "TRAIN_DONE" in p.stdout,
           "stdout_tail": p.stdout[-8000:], "stderr_tail": p.stderr[-10000:]}
    (EV / f"yolo_{tag}.txt").write_text(
        f"exit={p.returncode}\n{p.stdout[-30000:]}\n{p.stderr[-20000:]}",
        encoding="utf-8")
    # best.pt/last.pt: find the run dir named in the training log
    best = None
    for line in p.stdout.splitlines():
        if "Results saved to" in line:
            d = line.split("Results saved to")[-1].strip().replace("\x1b[1m", "").replace("\x1b[0m", "")
            if (Path(d) / "weights" / "best.pt").exists():
                best = str(Path(d) / "weights" / "best.pt")
    rec["weights_best"] = best
    print(f"[{tag}] exit={p.returncode} train_done={rec['train_done']} "
          f"prov_sha={prov.get('sha256') if prov else None} best={best}")
    return rec


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    if sha256(CANON_DLL) != CANON_SHA or sha256(WHEEL_DLL) != WHEEL_SHA:
        print("dll state unexpected - refusing")
        return 2
    dll_backup = WHEEL_DLL.with_suffix(".dll.phase4bak3")
    record = {"schema": "phase4_yolo_train_v1", "gate": "P52E",
              "timestamp": datetime.now().isoformat()}
    try:
        shutil.copy2(WHEEL_DLL, dll_backup)
        shutil.copy2(CANON_DLL, WHEEL_DLL)
        print("canonical DLL swapped in")
        record["amp_false"] = run_train("amp_false", ", amp=False")
        record["amp_default"] = run_train("amp_default", "")  # library default AMP
    finally:
        shutil.copy2(dll_backup, WHEEL_DLL)
        dll_backup.unlink()
        record["wheel_restored_ok"] = sha256(WHEEL_DLL) == WHEEL_SHA
        print("wheel restored:", record["wheel_restored_ok"])

    def ok(r):
        return bool(r and r["exit_code"] == 0 and r["train_done"]
                    and r.get("provenance", {}) and
                    r["provenance"].get("sha256") == CANON_SHA and r["weights_best"])

    record["amp_false_ok"] = ok(record.get("amp_false"))
    record["amp_default_ok"] = ok(record.get("amp_default"))
    record["overall"] = "PASS" if (record["amp_false_ok"] and record["wheel_restored_ok"]) else "FAIL"
    (EV / "yolo_train.json").write_text(json.dumps(record, indent=2) + "\n",
                                        encoding="utf-8")
    print("P52E YOLO train (amp=False):", "PASS" if record["amp_false_ok"] else "FAIL")
    print("P52E YOLO train (amp=default):", "PASS" if record["amp_default_ok"] else "FAIL")
    return 0 if record["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
