"""P18 Phase F: Windows stability on real gfx1100 (combined tree).

Cold start x3 (fresh processes), warm start (2 trains one process), workers
0/2/4 short trains, AMP fwd/bwd, tensor alloc, checkpoint save/load, resource
release between runs. Each stage reports pass/fail; driver aggregates.
Usage: python phase_f_stability.py --stage {cold|warm|workers|cycle} [--workers N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PY = r"C:\P18\venv\Scripts\python.exe"
ENV = {
    **__import__("os").environ,
    "PYTHONPATH": r"C:\P18\combined",
    "HIPRTC_COMPILE_OPTIONS_APPEND": r"-IC:\Users\Rocm\Desktop\YOLO\YOLO26_ROCm_Day1_Labs\scripts\miopen_shims",
}

CHILD = r"""
import json, sys, time
from pathlib import Path
import torch
import ultralytics
from ultralytics import YOLO
stage = sys.argv[1]
out = {'stage': stage, 'file': ultralytics.__file__}
t0 = time.time()
# GPU tensor alloc + AMP fwd/bwd sanity
x = torch.randn(8,3,64,64,device='cuda:0')
with torch.autocast('cuda', dtype=torch.float16):
    c = torch.nn.Conv2d(3,8,3,padding=1).to('cuda:0')
    y = c(x); loss = y.float().pow(2).mean()
loss.backward(); torch.cuda.synchronize()
out['amp_fwd_bwd'] = bool(torch.isfinite(y).all()) and bool(torch.isfinite(c.weight.grad).all())
free, total = torch.cuda.mem_get_info(0)
out['mem_after_alloc'] = {'free_gb': round(free/2**30,2), 'total_gb': round(total/2**30,2)}
import shutil, os
rd = f'C:/P18/scratch/runs_f_{stage}'
if os.path.exists(rd): shutil.rmtree(rd)
kw = dict(data='C:/P18/assets/coco8.yaml', epochs=1, imgsz=64, batch=8,
          device=0, amp=True, project='C:/P18/scratch', name=f'runs_f_{stage}',
          exist_ok=True, seed=42, verbose=False)
w = int(sys.argv[2]) if len(sys.argv) > 2 else 0
m = YOLO('C:/P18/assets/yolo26n.pt')
m.train(workers=w, **kw)
last = Path(rd)/'weights'/'last.pt'
out['ckpt_saved'] = last.is_file()
# checkpoint save/load cycle
if last.is_file():
    m2 = YOLO(str(last))
    _ = m2.predict(source='C:/P18/combined/ultralytics/assets/bus.jpg', imgsz=320, device=0, verbose=False)
    out['ckpt_reload_predict'] = True
free2, _ = torch.cuda.mem_get_info(0)
out['mem_released_gb'] = round((free2-free)/2**30, 2)
out['total_s'] = round(time.time()-t0, 1)
print('F_JSON ' + json.dumps(out))
"""


def run_child(stage: str, workers: str = "0", timeout: int = 1200):
    r = subprocess.run([PY, "-c", CHILD, stage, workers], cwd=r"C:\P18\combined", env=ENV, capture_output=True, text=True, timeout=timeout)
    line = [l for l in r.stdout.splitlines() if l.startswith("F_JSON")]
    if not line:
        return {"stage": stage, "crash": True, "rc": r.returncode, "tail": (r.stdout + r.stderr)[-600:]}
    d = json.loads(line[0][6:])
    d["rc"] = r.returncode
    d["crash"] = False
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="all")
    args = ap.parse_args()
    results = []

    # cold starts: 3 fresh processes (each a new interpreter = cold)
    for i in range(3):
        results.append(run_child(f"cold{i}"))
    # warm start: same process trains twice (child with two train calls)
    WARM = CHILD.replace("m.train(workers=w, **kw)", "m.train(workers=0, **kw); m2w = YOLO('C:/P18/assets/yolo26n.pt'); m2w.train(workers=0, **dict(kw, name='runs_f_warm2'))")
    r = subprocess.run([PY, "-c", WARM, "warm", "0"], cwd=r"C:\P18\combined", env=ENV, capture_output=True, text=True, timeout=1800)
    line = [l for l in r.stdout.splitlines() if l.startswith("F_JSON")]
    results.append({"stage": "warm(2 trains 1 proc)", "rc": r.returncode, "crash": not line, "detail": line[0][6:][:200] if line else (r.stdout + r.stderr)[-400:]})
    # workers 0/2/4
    for w in ("0", "2", "4"):
        results.append(run_child(f"workers{w}", w, timeout=1800))

    ok = all((not x.get("crash")) and x.get("rc") == 0 and x.get("amp_fwd_bwd", True) and x.get("ckpt_saved", True) for x in results)
    print(json.dumps({"results": results, "all_pass": ok}, indent=2))
    return 0 if ok else 10


if __name__ == "__main__":
    raise SystemExit(main())
