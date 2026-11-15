import json, time, datetime
import torch
from ultralytics import YOLO
from ultralytics.utils.checks import check_amp

t0 = time.perf_counter()
model = YOLO("yolo26n.yaml").model.to("cuda:0")
dev = next(model.parameters()).device
result = check_amp(model)
t1 = time.perf_counter()
print("\n=== A1 RESULT ===")
print(f"device = {dev}")
print(f"check_amp result = {result} (type {type(result).__name__})")
print(f"elapsed = {t1-t0:.2f}s")
print(f"hip runtime = torch.version.hip={torch.version.hip}, torch={torch.__version__}")
assert result is True, "check_amp must return True on healthy gfx1151"
json.dump({"result": result, "device": str(dev), "elapsed_s": t1-t0,
           "hip": torch.version.hip, "torch": torch.__version__,
           "timestamp": datetime.datetime.now().astimezone().isoformat()},
          open("a1_result.json","w"), indent=2)
print("A1 PASS")
