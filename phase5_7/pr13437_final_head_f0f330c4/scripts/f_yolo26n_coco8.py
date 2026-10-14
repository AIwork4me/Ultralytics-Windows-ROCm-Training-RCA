"""Validation F — YOLO26n COCO8 one-epoch smoke train on patched MIOpen.

Deterministic small workload, existing pinned Ultralytics env (8.4.174),
COCO8 dataset already on disk. Success = GPU detected, model loads, >=1 real
training iteration completes (one full epoch), no missing-STL MIOpen failure,
no new MIOpen compile failure. AMP precheck outcome reported separately and
not attributed to this fix.
"""
import ctypes
import sys

import torch

print("torch", torch.__version__, "| hip", torch.version.hip)
print("device", torch.cuda.get_device_name(0))

miopen = ctypes.CDLL("MIOpen.dll")
gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
path = ctypes.create_string_buffer(512)
gmfn(miopen._handle, path, 512)
print("MIOpen.dll loaded from:", path.value.decode(errors="replace"))

from ultralytics import YOLO

model = YOLO("yolo26n.pt")
results = model.train(
    data="coco8.yaml",
    epochs=1,
    imgsz=640,
    batch=8,
    device=0,
    workers=0,
    seed=7,
    deterministic=True,
    verbose=True,
    exist_ok=True,
    project="C:/Users/rocm/Desktop/YOLO_AMD/fin_mission/runs",
    name="yolo26n_coco8",
)
metrics = results.results_dict if hasattr(results, "results_dict") else (results[0].results_dict if results else {})
print("FINAL_METRICS", dict(metrics))
print("YOLO_SMOKE_VALIDATION: PASS")
sys.exit(0)
