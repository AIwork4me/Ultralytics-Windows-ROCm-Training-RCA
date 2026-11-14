import json
import sys

import torch

dev = torch.device("cuda:0")
torch.manual_seed(1234)
torch.backends.cuda.matmul.allow_tf32 = False

print("[probe] importing done, building BN", flush=True)
bn = torch.nn.BatchNorm2d(16).to(dev)
x = torch.randn(8, 16, 64, 64, device=dev)
print("[probe] calling bn(x) train — MIOpen spatial BN", flush=True)
y = bn(x)
torch.cuda.synchronize()
print("[probe] train forward done", flush=True)
xd = x.double()
mean = xd.mean(dim=(0, 2, 3))
var_b = xd.var(dim=(0, 2, 3), unbiased=False)
var_u = xd.var(dim=(0, 2, 3), unbiased=True)
rm = bn.running_mean.detach().double()          # stays on cuda, matches xd
rv = bn.running_var.detach().double()
m = bn.momentum
ref_rm_u = m * mean
ref_rv_u = (1 - m) * 1 + m * var_u
ref_rv_b = (1 - m) * 1 + m * var_b
out = {
    "rm_vs_unbiased_max_abs": float((rm - ref_rm_u).abs().max()),
    "rm_vs_unbiased_max_rel": float(((rm - ref_rm_u).abs() / ref_rm_u.abs().clamp_min(1e-12)).max()),
    "rv_vs_unbiased_max_abs": float((rv - ref_rv_u).abs().max()),
    "rv_vs_biased_max_abs": float((rv - ref_rv_b).abs().max()),
    "rv_gpu_first4": [round(v, 7) for v in rv[:4].cpu().tolist()],
    "rv_unb_first4": [round(v, 7) for v in ref_rv_u[:4].cpu().tolist()],
    "rv_bias_first4": [round(v, 7) for v in ref_rv_b[:4].cpu().tolist()],
}
print("[probe] eval forward", flush=True)
bn.eval()
with torch.no_grad():
    ye = bn(x)
re = ((xd - rm[None, :, None, None]) / torch.sqrt(rv[None, :, None, None] + bn.eps)
      * bn.weight.double()[None, :, None, None] + bn.bias.double()[None, :, None, None])
out["eval_manualref_max_abs"] = float((ye.double() - re).abs().max())
print("[probe] CPU BN cross-check", flush=True)
cpu_bn = torch.nn.BatchNorm2d(16)
cpu_bn.load_state_dict({k: v.cpu().clone() for k, v in bn.state_dict().items()})
cpu_bn.train()
xc = x.detach().cpu()
cpu_bn(xc)
out["cpu_bn_rv_vs_unbiased"] = float((cpu_bn.running_var.double() - ref_rv_u.cpu()).abs().max())
out["cpu_bn_rv_vs_biased"] = float((cpu_bn.running_var.double() - ref_rv_b.cpu()).abs().max())
print(json.dumps(out, indent=1), flush=True)
