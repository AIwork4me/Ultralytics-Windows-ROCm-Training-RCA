"""Phase 4: pure PyTorch minimal BatchNorm reproduction (no Ultralytics).

If this fails with the same HIPRTC/type_traits/miopenStatusUnknownError
signature, Ultralytics is not required to reproduce the defect.

Sub-cases (select via argv[1], default "minimal"):
  minimal   BatchNorm2d(16), input (8,16,64,64)      - task-brief smallest case
  issue3956 BatchNorm2d(100), input (20,100,35,45)   - upstream MIOpen #3956 shape
  yololike  BatchNorm2d(16), input (16,16,320,320)   - YOLO first-stage-ish shape
"""
import sys

import torch
import torch.nn as nn

case = sys.argv[1] if len(sys.argv) > 1 else "minimal"

print(f"torch.__version__ = {torch.__version__}")
print(f"torch.version.hip = {torch.version.hip}")
print(f"device(0) = {torch.cuda.get_device_name(0)}")
print(f"case = {case}")

if case == "minimal":
    channels, shape = 16, (8, 16, 64, 64)
elif case == "issue3956":
    channels, shape = 100, (20, 100, 35, 45)
elif case == "yololike":
    channels, shape = 16, (16, 16, 320, 320)
else:
    raise SystemExit(f"unknown case {case}")

bn = nn.BatchNorm2d(channels).cuda().train()
x = torch.randn(*shape, device="cuda")
print(f"bn = BatchNorm2d({channels}).cuda().train()")
print(f"x shape = {tuple(x.shape)} device = {x.device}")
sys.stdout.flush()

y = bn(x)
torch.cuda.synchronize()
print(f"y shape = {tuple(y.shape)} mean = {y.mean().item():.6f} isfinite = {bool(torch.isfinite(y).all())}")
print(f"BATCHNORM_{case}: PASS")
