"""P18 Phase D9: real training interruption + resume in a NEW process (gfx1100).

1. subprocess A: train 6 epochs (coco8, imgsz=64, workers=0, amp=True)
2. poll for first last.pt, wait 1.5s (mid-training), HARD-KILL A
3. record interrupted state (epoch inside last.pt, optimizer present)
4. subprocess B (new process): YOLO(last.pt).train(resume=True) -> completes
5. verify: final epoch reached, results.csv grows, resume flag true, exit 0
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RUN = Path("C:/P18/scratch/runs_d9")
PY = r"C:\P18\venv\Scripts\python.exe"
ENV = {**os.environ, "PYTHONPATH": r"C:\P18\combined", "HIPRTC_COMPILE_OPTIONS_APPEND": r"-IC:\Users\Rocm\Desktop\YOLO\YOLO26_ROCm_Day1_Labs\scripts\miopen_shims"}

TRAIN_A = r"""
import sys
from ultralytics import YOLO
m = YOLO('C:/P18/assets/yolo26n.pt')
m.train(data='C:/P18/assets/coco8.yaml', epochs=6, imgsz=64, batch=8, workers=0,
        device=0, amp=True, project='C:/P18/scratch', name='runs_d9', exist_ok=True,
        seed=42, save_period=1)
"""

RESUME_B = r"""
import json
import torch
from ultralytics import YOLO
last = 'C:/P18/scratch/runs_d9/weights/last.pt'
sd = torch.load(last, map_location='cpu', weights_only=False)
pre = {'epoch_in_ckpt': int(sd.get('epoch', -1)), 'has_optimizer': sd.get('optimizer') is not None,
       'best_fitness': float(sd.get('best_fitness', -1))}
m = YOLO(last)
m.train(resume=True)
t = m.trainer
post = {'final_epoch': int(t.epoch), 'epochs_arg': int(t.epochs)}
import csv
rows = list(csv.DictReader(open('C:/P18/scratch/runs_d9/results.csv')))
print('D9_JSON ' + json.dumps({'pre': pre, 'post': post, 'n_csv_rows': len(rows)}))
"""


def main() -> int:
    if RUN.exists():
        shutil.rmtree(RUN)

    out: dict = {"stage": "start"}

    # A: start training subprocess
    proc = subprocess.Popen([PY, "-c", TRAIN_A], cwd=r"C:\P18\combined", env=ENV,
                            stdout=open(r"C:\P18\logs\phase_d9_trainA.log", "w"), stderr=subprocess.STDOUT)
    last = RUN / "weights" / "last.pt"
    deadline = time.time() + 900
    first_seen = None
    while time.time() < deadline:
        if proc.poll() is not None:
            out["error"] = "subprocess A exited before interruption window"
            print(json.dumps(out))
            return 9
        if last.is_file():
            first_seen = time.time()
            break
        time.sleep(0.5)
    if first_seen is None:
        proc.kill()
        out["error"] = "no last.pt within deadline"
        print(json.dumps(out))
        return 9

    time.sleep(1.5)  # let it advance into a later epoch (still mid-run)
    was_alive = proc.poll() is None
    proc.kill()  # hard kill the training process
    proc.wait(timeout=60)
    out["interrupt"] = {"was_alive_at_kill": was_alive, "returncode": proc.returncode}

    # record interrupted checkpoint state
    import sys as _sys

    _sys.path.insert(0, r"C:\P18\combined")
    import torch

    sd = torch.load(last, map_location="cpu", weights_only=False)
    out["interrupted_ckpt"] = {
        "epoch": int(sd.get("epoch", -1)),
        "has_optimizer_state": sd.get("optimizer") is not None,
        "has_train_args": bool(sd.get("train_args")),
        "epochs_planned": int(sd.get("train_args", {}).get("epochs", -1)),
    }
    interrupted_epoch = out["interrupted_ckpt"]["epoch"]
    if not (0 <= interrupted_epoch < 6):
        out["error"] = f"interruption did not happen mid-run (epoch={interrupted_epoch})"
        print(json.dumps(out))
        return 9

    # B: resume in a NEW process
    res = subprocess.run([PY, "-c", RESUME_B], cwd=r"C:\P18\combined", env=ENV, capture_output=True, text=True, timeout=1800)
    out["resume_exit"] = res.returncode
    line = [l for l in res.stdout.splitlines() if l.startswith("D9_JSON")]
    if not line:
        out["resume_stdout_tail"] = res.stdout[-800:]
        out["resume_stderr_tail"] = res.stderr[-1500:]
        print(json.dumps(out, indent=2))
        return 9
    payload = json.loads(line[0][8:])
    out["resume"] = payload

    ok = (
        res.returncode == 0
        and payload["pre"]["has_optimizer"]
        and payload["post"]["final_epoch"] >= 5  # completed remaining epochs (0-indexed final = 5)
        and payload["n_csv_rows"] >= 6
    )
    out["D9_pass"] = ok
    print(json.dumps(out, indent=2))
    return 0 if ok else 9


if __name__ == "__main__":
    raise SystemExit(main())
