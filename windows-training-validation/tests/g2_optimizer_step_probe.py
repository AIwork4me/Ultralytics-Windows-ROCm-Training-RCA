import torch
from ultralytics import YOLO

model = YOLO("yolo26n.pt")
state = {"n": 0}


def probe(trainer):
    print(f"[cb] accumulate={trainer.accumulate} nb={len(trainer.train_loader)} "
          f"epochs={trainer.epochs} amp={trainer.amp} scaler={type(trainer.scaler).__name__} "
          f"enabled={getattr(trainer.scaler, '_enabled', None)} optimizer={type(trainer.optimizer).__name__}",
          flush=True)
    orig = trainer.optimizer_step

    def wrapped():
        gn = torch.nn.utils.clip_grad_norm_(trainer.model.parameters(), 1e9)
        lr = [g["lr"] for g in trainer.optimizer.param_groups]
        s0 = sum(float(p.detach().double().abs().sum()) for p in trainer.model.parameters())
        orig()
        s1 = sum(float(p.detach().double().abs().sum()) for p in trainer.model.parameters())
        state["n"] += 1
        print(f"[step {state['n']}] grad_norm={float(gn):.6f} lr={lr} "
              f"delta={s1 - s0:.10f}", flush=True)
    trainer.optimizer_step = wrapped


model.add_callback("on_train_start", probe)
r = model.train(data="coco8.yaml", epochs=2, device=0, workers=0, amp=False,
                name="probe_step", exist_ok=True, plots=False, seed=42)
print("done", flush=True)
