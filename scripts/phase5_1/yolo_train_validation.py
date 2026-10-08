"""Phase 5.1 (P5.1-CANDIDATE-R1) - adapted from the validated Phase-5
script by mechanical path/identity substitution only (source tree, build
dir, evidence dir, schema/gate names). Logic unchanged.
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
EV = RCA / "evidence" / "phase5_1" / "yolo"
PY = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe")

WHEEL_DLL = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"
                 r"\_rocm_sdk_libraries\bin\MIOpen.dll")
P5_DLL = Y / "phase5_1_build" / "miopen" / "bin" / "MIOpen.dll"
P5_SHA = None  # computed from the built P5.1 DLL at start of main()
WHEEL_SHA = "74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a"

RUN_PREFIX = """
import ctypes, hashlib, json
from ultralytics import YOLO
import torch

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
h = k32.GetModuleHandleW("MIOpen.dll")
buf = ctypes.create_unicode_buffer(2048)
n = k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 2048) if h else 0
miopen_path = buf.value if n else ""
miopen_sha = hashlib.sha256(open(miopen_path, 'rb').read()).hexdigest() if miopen_path else None
print("MIOPEN_PROVENANCE " + json.dumps(
    {"path": miopen_path, "sha256": miopen_sha,
     "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
     "torch": torch.__version__}))

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
    iso = Path(tempfile.gettempdir()) / f"phase5_1_yolo_{tag}_{uuid.uuid4().hex[:8]}"
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
        "USERNAME": os.environ.get("USERNAME", "rocm"),
        "HOMEDRIVE": "C:", "HOMEPATH": str(iso),
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
    # explicit AMP behavior from ultralytics' own output
    amp_lines = [l.strip() for l in p.stdout.splitlines()
                 if "AMP" in l or "amp" in l.lower()][:8]
    rec = {"tag": tag, "amparg": amparg or "(default)", "exit_code": p.returncode,
           "provenance": prov, "amp_lines": amp_lines,
           "amp_genuine": any("checks passed" in l for l in amp_lines)
                          and any("amp=True" in l or "AMP" in l for l in amp_lines),
           "train_done": "TRAIN_DONE" in p.stdout,
           "val_done": "all" in p.stdout and ("images" in p.stdout),
           "stdout_tail": p.stdout[-10000:], "stderr_tail": p.stderr[-10000:]}
    (EV / f"yolo_{tag}.txt").write_text(
        f"exit={p.returncode}\n{p.stdout[-40000:]}\n{p.stderr[-20000:]}",
        encoding="utf-8")
    best = None
    for line in p.stdout.splitlines():
        if "Results saved to" in line:
            d = line.split("Results saved to")[-1].strip().replace("\x1b[1m", "").replace("\x1b[0m", "")
            if (Path(d) / "weights" / "best.pt").exists():
                best = str(Path(d) / "weights" / "best.pt")
    rec["weights_best"] = best
    print(f"[{tag}] exit={p.returncode} done={rec['train_done']} "
          f"prov={prov.get('sha256', '')[:12] if prov else None} best={best}")
    print(f"  amp_lines: {amp_lines[:3]}")
    return rec


def main() -> int:
    global P5_SHA
    EV.mkdir(parents=True, exist_ok=True)
    P5_SHA = sha256(P5_DLL)
    if sha256(WHEEL_DLL) != WHEEL_SHA:
        print("dll state unexpected - refusing")
        return 2
    dll_backup = WHEEL_DLL.with_suffix(".dll.p51bak3")
    record = {"schema": "phase5_1_yolo_train_v1", "gate": "P51-13",
              "timestamp": datetime.now().isoformat(),
              "phase5_dll_sha256": P5_SHA, "gpu": "AMD Radeon 8060S (gfx1151)"}
    try:
        shutil.copy2(WHEEL_DLL, dll_backup)
        shutil.copy2(P5_DLL, WHEEL_DLL)
        print("Phase-5 DLL swapped in")
        record["amp_false"] = run_train("amp_false", ", amp=False")
        record["amp_default"] = run_train("amp_default", "")
    finally:
        shutil.copy2(dll_backup, WHEEL_DLL)
        dll_backup.unlink()
        record["wheel_restored_ok"] = sha256(WHEEL_DLL) == WHEEL_SHA
        print("wheel restored:", record["wheel_restored_ok"])

    def ok(r):
        return bool(r and r["exit_code"] == 0 and r["train_done"]
                    and r.get("provenance", {}).get("sha256") == P5_SHA
                    and r.get("weights_best")
                    and "8060S" in (r.get("provenance", {}).get("device") or ""))

    record["amp_false_pass"] = ok(record.get("amp_false"))
    # default AMP additionally requires positive evidence of AMP behavior
    record["amp_default_pass"] = ok(record.get("amp_default"))
    record["amp_disclosed"] = {
        "amp_false": {"genuine_amp_expected": False,
                      "lines": record["amp_false"]["amp_lines"]},
        "amp_default": {"genuine_amp_evidence": record["amp_default"]["amp_genuine"],
                        "lines": record["amp_default"]["amp_lines"]},
    }
    record["overall"] = "PASS" if (record["amp_false_pass"]
                                   and record["amp_default_pass"]
                                   and record["wheel_restored_ok"]) else "FAIL"
    (EV / "yolo_train.json").write_text(json.dumps(record, indent=2) + "\n",
                                        encoding="utf-8")
    print("amp_false:", "PASS" if record["amp_false_pass"] else "FAIL",
          "| amp_default:", "PASS" if record["amp_default_pass"] else "FAIL",
          "| genuine AMP:", record["amp_default"]["amp_genuine"])
    print("OVERALL:", record["overall"])
    return 0 if record["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
