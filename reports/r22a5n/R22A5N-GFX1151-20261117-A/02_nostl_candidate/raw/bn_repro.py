
import json, sys
import torch
import torch.nn as nn

torch.manual_seed(0)
model = nn.BatchNorm2d(100).cuda()
x = torch.randn(20, 100, 35, 45, device="cuda")
y = model(x)
loss = (y * y).mean()
loss.backward()
torch.cuda.synchronize()
out_finite = bool(torch.isfinite(y).all().item())
grad_finite = bool(torch.isfinite(model.weight.grad).all().item()) and \
              bool(torch.isfinite(model.bias.grad).all().item())
print("BN_NOSTL_REPRO out_finite=%s grad_finite=%s loss=%.6f" %
      (out_finite, grad_finite, float(loss)))
sys.exit(0 if (out_finite and grad_finite) else 1)
