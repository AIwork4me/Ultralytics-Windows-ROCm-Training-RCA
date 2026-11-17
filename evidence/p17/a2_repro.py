import torch
from ultralytics import YOLO
from ultralytics.utils.torch_utils import autocast

model = YOLO("C:/Users/rocm/Desktop/YOLO_AMD/yolo26n.pt").model.to("cuda:0")
model.train()
dev = next(model.parameters()).device
batch = {
    "img": torch.randn(16, 3, 64, 64, device=dev),  # same shape trainer uses (batch=16, imgsz=64)
    "batch_idx": torch.zeros(16),
    "cls": torch.zeros(8, 1),
    "bboxes": torch.rand(8, 4) * 0.5,
}
opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
scaler = torch.amp.GradScaler("cuda")
try:
    for i in range(3):
        opt.zero_grad()
        with autocast(enabled=True, device=dev.type):
            loss, items = model(batch)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        torch.cuda.synchronize()
        print(f"batch {i}: loss={loss.item():.4f} finite={bool(torch.isfinite(loss))}")
    print("ULTRALYTICS_FORWARD_LOSS_OK")
except Exception as e:
    print(f"ULTRALYTICS_FORWARD_LOSS_FAILED: {type(e).__name__}: {str(e)[:300]}")
