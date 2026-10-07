"""Phase-3 Gate 67: YOLO26n end-to-end training closure with the REAL
patched MIOpen build. amp mode via argv[1] in {off, default}.
"""
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "off"

from ultralytics import YOLO  # noqa: E402

model = YOLO(r"C:\Users\rocm\Desktop\YOLO_AMD\yolo26n.pt")
kwargs = dict(data="coco8.yaml", epochs=1, imgsz=640, device=0, workers=0,
              project=r"C:\Users\rocm\Desktop\YOLO_AMD\runs\phase3",
              name=f"g67_{mode}", exist_ok=True, verbose=True)
if mode == "off":
    kwargs["amp"] = False
results = model.train(**kwargs)
print("TRAIN_DONE metrics:", results.results_dict if hasattr(results, "results_dict") else results)
print(f"YOLO_CLOSURE_{mode.upper()} PASS")
