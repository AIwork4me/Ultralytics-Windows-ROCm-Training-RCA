"""Phase-3 Gate 68: non-BN MIOpen RTC workload matrix with the patched
build. Maps each op to the upstream kernel sources it exercises
(per Gate 54 audit): pooling -> MIOpenPooling* (miopen_type_traits via
vector_types), prelu -> MIOpenPReLU.cpp (tensor_view+initializer_list),
conv variants -> Conv* family + MIOpenConv* (type_traits), kthvalue-style
paths documented separately (torch routes kthvalue via its own kernels;
MIOpenKthvalue is driver-only).
"""
import json
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

results = []


def run_case(name, fn):
    try:
        info = fn()
        results.append({"case": name, "status": "PASS", **info})
        print(f"[PASS] {name}: {info.get('detail','')}")
    except Exception as e:  # noqa: BLE001
        results.append({"case": name, "status": "FAIL", "error": repr(e)[:400]})
        print(f"[FAIL] {name}: {repr(e)[:250]}")


def fwdbwd(mod_factory, x):
    torch.manual_seed(3)
    m = mod_factory().cuda()
    xt = x.clone().requires_grad_(True)
    y = m(xt.cuda() if not xt.is_cuda else xt)
    (y * y).mean().backward()
    finite = bool(torch.isfinite(y).all()) and bool(torch.isfinite(xt.grad).all())
    return {"ok": finite, "detail": f"finite={finite}", "shape": tuple(y.shape)}


run_case("maxpool2d_bwd", lambda: fwdbwd(
    lambda: nn.MaxPool2d(3, stride=2), torch.randn(2, 8, 32, 32)))
run_case("avgpool2d_bwd", lambda: fwdbwd(
    lambda: nn.AvgPool2d(3, stride=2), torch.randn(2, 8, 32, 32)))
run_case("adaptive_avgpool2d", lambda: fwdbwd(
    lambda: nn.AdaptiveAvgPool2d((7, 7)), torch.randn(2, 8, 32, 32)))
run_case("prelu_fwd_bwd", lambda: fwdbwd(
    lambda: nn.PReLU(num_parameters=4), torch.randn(2, 4, 16, 16)))
run_case("conv_depthwise", lambda: fwdbwd(
    lambda: nn.Conv2d(8, 8, 3, padding=1, groups=8), torch.randn(2, 8, 16, 16)))
run_case("conv_grouped", lambda: fwdbwd(
    lambda: nn.Conv2d(8, 16, 3, padding=1, groups=2), torch.randn(2, 8, 16, 16)))
run_case("conv_dilated", lambda: fwdbwd(
    lambda: nn.Conv2d(4, 8, 3, padding=2, dilation=2), torch.randn(2, 4, 16, 16)))
run_case("conv_transpose", lambda: fwdbwd(
    lambda: nn.ConvTranspose2d(8, 8, 3, padding=1), torch.randn(2, 8, 16, 16)))
run_case("conv_1x1_gemm_path", lambda: fwdbwd(
    lambda: nn.Conv2d(16, 32, 1), torch.randn(2, 16, 20, 20)))
run_case("softmax_attn_like", lambda: fwdbwd(
    lambda: nn.Softmax(dim=-1), torch.randn(2, 8, 64, 64)))
run_case("dropout2d_train", lambda: fwdbwd(
    lambda: nn.Dropout2d(p=0.5), torch.randn(2, 16, 8, 8)))

n_fail = sum(1 for r in results if r["status"] == "FAIL")
print(f"\nG68 MATRIX: {len(results) - n_fail} PASS / {n_fail} FAIL")
json.dump(results, open(sys.argv[1], "w"), indent=1)
sys.exit(1 if n_fail else 0)
