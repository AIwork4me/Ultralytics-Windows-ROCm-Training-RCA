
import sys
from ultralytics import YOLO
m = YOLO("yolo26n.pt")
m.train(data="coco128.yaml", epochs=4, device=-1, project=r"C:\r22a5n1\g5_work\runs",
        name=r"lifecycle", exist_ok=True, seed=7, workers=0, batch=4, verbose=True)
