
from ultralytics import YOLO
import pathlib
last = pathlib.Path(r"C:\r22a5n\runs\g5_resume\runs\lifecycle\weights\last.pt")
assert last.is_file(), "last.pt missing: " + str(last)
m = YOLO(str(last))
r = m.train(resume=True)
print("RESUME_DONE")
