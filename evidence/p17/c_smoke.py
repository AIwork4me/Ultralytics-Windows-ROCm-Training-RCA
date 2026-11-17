import json, datetime
import torch
from ultralytics.utils.checks import cuda_is_available, cuda_device_count
from ultralytics.utils.torch_utils import parse_device
from ultralytics import YOLO

out = {"timestamp": datetime.datetime.now().astimezone().isoformat(), "tree": "750b5061a0a7c397a15dd53641285b8b2dce1ded"}
out["S1_device_detection"] = {
    "cuda_is_available": cuda_is_available(), "cuda_device_count": cuda_device_count(),
    "torch_count": torch.cuda.device_count(),
}
out["S2_parse_device_-1"] = str(parse_device("-1"))

# S3 real check_amp
import logging
from ultralytics.utils import LOGGER
recs = []
class H(logging.Handler):
    def emit(self, r): recs.append(r.getMessage())
LOGGER.addHandler(H())
model = YOLO("yolo26n.yaml").model.to("cuda:0")
amp_result = None
try:
    amp_result = __import__("ultralytics.utils.checks", fromlist=["check_amp"]).check_amp(model)
except Exception as e:
    recs.append(f"ESCAPED: {type(e).__name__}: {e}")
LOGGER.removeHandler(next(h for h in LOGGER.handlers if isinstance(h, H)))
out["S3_check_amp"] = {"result": amp_result, "probe_log": [r for r in recs if "AMP" in r or "ESCAPED" in r][:3]}

# S4 minimal AMP training via official API
m = YOLO("C:/Users/rocm/Desktop/YOLO_AMD/yolo26n.pt")
import copy
before = [p.detach().cpu().clone() for p in m.model.parameters()]
try:
    m.train(data="coco8.yaml", epochs=1, imgsz=64, device=0, amp=True, workers=0,
            project="C:/Users/rocm/Desktop/YOLO_AMD/p17_scratch/runs", name="c_smoke", exist_ok=True)
    train_ok = True
except Exception as e:
    train_ok = False
    out["S4_train_error"] = f"{type(e).__name__}: {str(e)[:200]}"
out["S4_train_completed"] = train_ok

# S5 parameter updates
after = list(m.model.parameters())
changed = sum(1 for a, b in zip(before, after) if not torch.equal(a.cpu(), b.cpu()))
out["S5_params_changed"] = f"{changed}/{len(before)}"

# S6 checkpoint
import os
ck_path = "C:/Users/rocm/Desktop/YOLO_AMD/p17_scratch/runs/c_smoke/weights/last.pt"
out["S6_checkpoint_exists"] = os.path.isfile(ck_path)

# S7 real val + predict
try:
    vr = m.val(data="coco8.yaml", imgsz=64, device=0, project="C:/Users/rocm/Desktop/YOLO_AMD/p17_scratch/runs", name="c_smoke_val", exist_ok=True)
    out["S7_val"] = {"ok": True, "map50": float(vr.box.map50) if hasattr(vr, "box") else None}
    pr = m.predict("C:/Users/rocm/Desktop/YOLO_AMD/datasets/coco8/images/train/000000000009.jpg", imgsz=64, device=0, verbose=False)
    out["S7_predict"] = {"ok": True, "n_results": len(pr), "device": str(pr[0].device) if pr else None}
except Exception as e:
    out["S7_val_predict"] = f"{type(e).__name__}: {str(e)[:300]}"

json.dump(out, open("c_smoke_result.json", "w"), indent=2)
print(json.dumps(out, indent=2))
