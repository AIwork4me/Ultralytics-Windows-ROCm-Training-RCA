import ctypes
import hashlib
import json
import os

# ---- in-process MIOpen provenance (before any torch import side effects) ----
class Dl_info(ctypes.Structure):
    _fields_ = [("dli_fname", ctypes.c_char_p), ("dli_fbase", ctypes.c_void_p),
                ("dli_sname", ctypes.c_char_p), ("dli_saddr", ctypes.c_void_p)]

libc = ctypes.CDLL(None)
libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(Dl_info)]
libc.dladdr.restype = ctypes.c_int

lib = ctypes.CDLL("libMIOpen.so.1")  # returns the ALREADY-LOADED (LD_PRELOADed) object
info = Dl_info()
addr = ctypes.cast(lib.miopenKthvalueForward, ctypes.c_void_p)
rc = libc.dladdr(addr, ctypes.byref(info))
path = info.dli_fname.decode() if rc and info.dli_fname else "<unknown>"
sha = ""
if path and os.path.exists(path):
    real = os.path.realpath(path)
    h = hashlib.sha256()
    with open(real, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    sha = h.hexdigest()
print(f"YOLO_MIOPEN_PROVENANCE path={path} sha256={sha}", flush=True)
assert "phase5_3b/installs/legB" in path, f"not bound to legB R2 build: {path}"
assert sha == "b14e907a8f259b27e9fc2ebc5fa58120ae90ff179f63a84676ab1a60619e90eb", sha

import torch
print(f"torch={torch.__version__} hip={torch.version.hip} "
      f"cuda_available={torch.cuda.is_available()} "
      f"device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}", flush=True)

from ultralytics import YOLO

model = YOLO("/home/amd/Desktop/YOLO_AMD/yolo26n.pt")
results = model.train(
    data="/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/coco8_local.yaml",
    epochs=1, imgsz=640, device=0, amp=False,
    project="/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/yolo_runs",
    name="p53b_smoke", exist_ok=True, verbose=True, plots=False)
print("TRAIN_COMPLETE", flush=True)

# validation pass with the trained weights
val = YOLO("/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/yolo_runs/p53b_smoke/weights/last.pt")
vm = val.val(data="/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/coco8_local.yaml", imgsz=640, device=0,
             project="/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/yolo_runs",
             name="p53b_smoke_val", exist_ok=True, verbose=True, plots=False)
print("VAL_COMPLETE", flush=True)

w = "/home/amd/Desktop/YOLO_AMD/phase5_3b/tmp/yolo_runs/p53b_smoke/weights/last.pt"
print(f"WEIGHTS_EXIST={os.path.exists(w)}", flush=True)
if os.path.exists(w):
    h = hashlib.sha256()
    with open(w, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(f"LAST_PT_SHA256={h.hexdigest()}", flush=True)
metrics = results.results_dict if hasattr(results, "results_dict") else {}
print(f"METRICS={json.dumps({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})}", flush=True)
