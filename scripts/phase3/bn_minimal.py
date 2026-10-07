import torch
import torch.nn as nn

m = nn.BatchNorm2d(16).cuda().train()
x = torch.randn(8, 16, 64, 64, device="cuda")
y = m(x)
loss = y.mean()
loss.backward()
print("OUTPUT_MEAN", float(y.mean()))
print("BN_MINIMAL PASS (patched MIOpen, fresh caches)")
