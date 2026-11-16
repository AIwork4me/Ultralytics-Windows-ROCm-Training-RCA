
"""Generated child training script (R22A.3: spawn-safe — Windows DataLoader
workers re-import this module; without the __main__ guard each worker would
recursively launch training)."""
import json
import multiprocessing
import os
import sys
import time

FACTS_PATH = r"C:\RadeonYOLO\R22A3\scratch\workers8\run01\child_facts.json"
RUN_ID = r"R22A3-B-R1"
t0 = time.time()


def main():
    facts = {"run_id": RUN_ID, "child_pid": os.getpid(), "parent_pid": os.getppid(),
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "userprofile_env": os.environ.get("USERPROFILE")}
    batches = {"n": 0}
    from ultralytics import YOLO
    import torch
    import ultralytics
    m = YOLO("yolo26n.pt")

    def _put(**kw):
        facts.update(kw)
        with open(FACTS_PATH, "w", encoding="utf-8") as f:
            json.dump(facts, f)

    _put(torch=torch.__version__, hip=torch.version.hip,
         ultralytics=ultralytics.__version__,
         device_name=(torch.cuda.get_device_name(0) if torch.cuda.device_count() else None),
         train_args={"data": "coco128.yaml", "epochs": 1, "workers": 8, "device": -1,
                      "batch": "16", "imgsz": "256"})

    def on_start(trainer):
        try:
            nw_train = getattr(trainer.train_loader, "num_workers", None)
        except Exception:
            nw_train = None
        _put(resolved_num_workers_train=nw_train,
             requested_workers=trainer.args.workers,
             amp_resolved=bool(trainer.amp),
             optimizer=trainer.args.optimizer,
             effective_batch=trainer.batch_size)

    def on_batch_end(trainer):
        batches["n"] += 1
        if batches["n"] % 4 == 0:
            _put(batches_completed=batches["n"])

    def on_fit_epoch_end(trainer):
        _put(fit_epochs=(facts.get("fit_epochs") or 0) + 1,
             metrics_present=bool(trainer.metrics),
             val_num_workers=(getattr(trainer.test_loader, "num_workers", None)
                              if getattr(trainer, "test_loader", None) else None))

    for cb, fn in (("on_train_start", on_start), ("on_train_batch_end", on_batch_end),
                   ("on_fit_epoch_end", on_fit_epoch_end)):
        m.add_callback(cb, fn)

    r = m.train(data="coco128.yaml", epochs=1, device=-1, project=r"C:\RadeonYOLO\R22A3\scratch\workers8\run01",
                name=r"train", exist_ok=True, seed=101, workers=8,
                verbose=True, batch=16, imgsz=256)
    import hashlib

    def _sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    ckpt = m.trainer.save_dir / "weights" / "last.pt"
    _put(batches_completed=batches["n"], training_completed=True,
         results_keys=sorted(r.results_dict.keys()) if hasattr(r, "results_dict") else None,
         val_completed=bool(facts.get("metrics_present")),
         checkpoint_path=str(ckpt), checkpoint_exists=bool(ckpt.exists()),
         checkpoint_sha256=(_sha(ckpt) if ckpt.exists() else None),
         finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print(f"STABILITY_CHILD_DONE {time.time()-t0:.1f}s")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
