
from ultralytics import YOLO
m = YOLO(r"C:\r22a5n\runs\g5_resume\runs\lifecycle\weights\best.pt")
r = m.predict(source=r"C:\r22a5n\runs\g5_resume\runs\lifecycle\val_batch0_labels.jpg", device=0, verbose=False)
n = len(r)
print("INFER_OK boxes_batches=" + str(n))
assert n >= 1
