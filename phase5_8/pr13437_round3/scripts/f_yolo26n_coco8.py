"""Round-3 Validation F — YOLO26n COCO8 one-epoch smoke train on Round-3 MIOpen.

Same deterministic workload as Phase 5.7 (epochs=1, imgsz=640, batch=8, seed=7,
workers=0, deterministic=True). Reports the loaded MIOpen.dll module path from
inside the process for runtime-binary provenance.
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
    project="C:/Users/rocm/Desktop/YOLO_AMD/r3_mission/runs",
    name="yolo26n_coco8",
)
metrics = results.results_dict if hasattr(results, "results_dict") else (results[0].results_dict if results else {})
print("FINAL_METRICS", dict(metrics))
print("YOLO_SMOKE_VALIDATION: PASS")
sys.exit(0)
