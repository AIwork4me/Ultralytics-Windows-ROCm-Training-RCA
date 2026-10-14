"""Validation D — BatchNorm forward/backward on patched MIOpen (mission spec).

nn.BatchNorm2d(100).cuda(), input (20,100,35,45); training-mode forward and
backward on GPU; finite outputs/grads; numerical agreement with CPU reference.
Prints the loaded MIOpen.dll module path from inside the process for
runtime-binary provenance, plus torch/HIP versions.
"""
import os
import sys
import datetime

print("D_RUN_STARTED_UTC", datetime.datetime.now(datetime.timezone.utc).isoformat())

import torch
import torch.nn as nn

print("torch", torch.__version__, "| hip", torch.version.hip)
print("device", torch.cuda.get_device_name(0))

# In-process proof of which MIOpen.dll this process loaded.
import ctypes
miopen = ctypes.CDLL("MIOpen.dll")
gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
path = ctypes.create_string_buffer(512)
gmfn(miopen._handle, path, 512)
print("MIOpen.dll loaded from:", path.value.decode(errors="replace"))

torch.manual_seed(0)
g = torch.Generator(device="cuda").manual_seed(1234)

def make(shape):
    return torch.randn(*shape, generator=g, device="cuda", dtype=torch.float32)

x_gpu = make((20, 100, 35, 45))
x_gpu.requires_grad_(True)
bn_gpu = nn.BatchNorm2d(100).cuda()
bn_gpu.train()

y_gpu = bn_gpu(x_gpu)
loss = y_gpu.square().mean()
loss.backward()

# CPU reference in train mode (same weights/statistics semantics).
bn_cpu = nn.BatchNorm2d(100, eps=bn_gpu.eps, momentum=bn_gpu.momentum)
bn_cpu.load_state_dict(bn_gpu.state_dict())
bn_cpu.train()
x_cpu = x_gpu.detach().cpu().requires_grad_(True)
y_cpu = bn_cpu(x_cpu)
y_cpu.square().mean().backward()

def report(name, t, ref):
    finite = bool(torch.isfinite(t).all())
    err = (t.detach().cpu() - ref).abs().max().item()
    print(f"{name}: finite={finite} max_abs_err={err:.3e}")
    return finite, err

checks = []
checks.append(report("output y", y_gpu, y_cpu.detach()))
checks.append(report("grad x", x_gpu.grad, x_cpu.grad))
for nm, p_gpu, p_cpu in [
    ("grad weight", bn_gpu.weight.grad, bn_cpu.weight.grad),
    ("grad bias", bn_gpu.bias.grad, bn_cpu.bias.grad),
]:
    checks.append(report(nm, p_gpu, p_cpu.detach()))

# Running stats: single train-mode forward from fresh init must equal
# momentum * batch_stat (PyTorch biased/unbiased conventions respected).
batch_mean = x_cpu.transpose(0, 1).contiguous().view(100, -1).mean(1)
rm_expected = bn_gpu.momentum * batch_mean
rv_expected = (1 - bn_gpu.momentum) * 1.0 + bn_gpu.momentum * x_cpu.transpose(0, 1).contiguous().view(100, -1).var(1, unbiased=False)
rm_err = (bn_gpu.running_mean.detach().cpu() - rm_expected).abs().max().item()
rv_err = (bn_gpu.running_var.detach().cpu() - rv_expected).abs().max().item()
rm_fin = bool(torch.isfinite(bn_gpu.running_mean.detach().cpu()).all())
rv_fin = bool(torch.isfinite(bn_gpu.running_var.detach().cpu()).all())
print(f"running_mean: finite={rm_fin} max_abs_err={rm_err:.3e}")
print(f"running_var:  finite={rv_fin} max_abs_err={rv_err:.3e}")
checks.append((rm_fin, rm_err))
checks.append((rv_fin, rv_err))

ok = all(f for f, _ in checks) and all(e < 1e-3 for _, e in checks)
print("BATCHNORM_VALIDATION:", "PASS" if ok else "FAIL")
print("D_RUN_ENDED_UTC", datetime.datetime.now(datetime.timezone.utc).isoformat())
sys.exit(0 if ok else 1)
