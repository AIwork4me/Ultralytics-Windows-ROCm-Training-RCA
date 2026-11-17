
import multiprocessing
import os
import sys
import time


def main():
    t0 = time.time()
    import torch
    from ultralytics import YOLO

    resolved = {}

    def on_train_start(trainer):
        resolved["num_workers"] = int(getattr(trainer.train_loader, "num_workers", -1))
        resolved["n_batches"] = int(len(trainer.train_loader))
        resolved["amp"] = bool(trainer.amp)
        resolved["optimizer"] = type(trainer.optimizer).__name__
        resolved["torch"] = torch.__version__

    m = YOLO("yolo26n.pt")
    m.add_callback("on_train_start", on_train_start)
    kwargs = dict(data=r"C:/RadeonYOLO/R22A2/cache/datasets/coco128-r22a2.yaml", epochs=1, device=-1, project=r"C:\RadeonYOLO\R22A2\scratch\workers8\cold\run01",
                  name=r"train", exist_ok=True, seed=101, workers=8,
                  verbose=True)
    if 16:
        kwargs["batch"] = 16
    if 256:
        kwargs["imgsz"] = 256
    m.train(**kwargs)
    print(f"R22A2_WORKERS resolved={resolved.get('num_workers')} "
          f"n_batches={resolved.get('n_batches')} amp={resolved.get('amp')} "
          f"optimizer={resolved.get('optimizer')} requested=8")
    print(f"R22A2_PID {os.getpid()}")
    print(f"STABILITY_CHILD_DONE {time.time() - t0:.1f}s")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
