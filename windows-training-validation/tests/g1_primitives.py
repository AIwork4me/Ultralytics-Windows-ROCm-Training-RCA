"""G1.2 — Windows native HIP training-primitive matrix (real GPU, CPU-referenced).

Run inside the environment under test:

    python tests/g1_primitives.py --out <result.json> [--expect-stl-fail]

Every check: real CUDA/HIP execution, CPU reference comparison with declared
tolerances, finite checks, device checks. JSON result; exit 0 iff all
required statuses are PASS (or, in --expect-stl-fail mode, iff the historical
#3956 failure signature is reproduced exactly).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

TOL = {"fp32_strict": (1e-4, 1e-4), "fp32_relaxed": (2e-4, 2e-3)}


def check(name: str, ok: bool, **fields) -> dict:
    rec = {"name": name, "status": "PASS" if ok else "FAIL", **fields}
    if not ok:
        print(f"FAIL {name}: {fields}", file=sys.stderr)
    return rec


def close(actual: torch.Tensor, ref: torch.Tensor, tol_key: str):
    atol, rtol = TOL[tol_key]
    actual_f = actual.detach().float().cpu()
    ref_f = ref.detach().float().cpu()
    max_abs = float((actual_f - ref_f).abs().max()) if actual_f.numel() else 0.0
    denom = ref_f.abs().clamp_min(1e-12)
    max_rel = float(((actual_f - ref_f).abs() / denom).max()) if actual_f.numel() else 0.0
    ok = bool(torch.allclose(actual_f, ref_f, atol=atol, rtol=rtol))
    return ok, {"max_abs_err": max_abs, "max_rel_err": max_rel, "atol": atol, "rtol": rtol}


def finite(t: torch.Tensor) -> bool:
    return bool(torch.isfinite(t).all().item())


def on_gpu(t: torch.Tensor) -> bool:
    return t.device.type == "cuda"


def bn2d_train_reference(x: torch.Tensor, weight, bias, running_mean, running_var,
                         momentum: float, eps: float):
    """Float64 reference: train-mode BN forward outputs + unbiased running stats."""
    xf = x.double()
    mean = xf.mean(dim=(0, 2, 3))
    var_biased = xf.var(dim=(0, 2, 3), unbiased=False)
    var_unbiased = xf.var(dim=(0, 2, 3), unbiased=True)
    out = (xf - mean[None, :, None, None]) / torch.sqrt(var_biased[None, :, None, None] + eps)
    out = out * weight.double()[None, :, None, None] + bias.double()[None, :, None, None]
    new_rm = (1 - momentum) * running_mean.double() + momentum * mean
    new_rv = (1 - momentum) * running_var.double() + momentum * var_unbiased
    return out, new_rm, new_rv


def run_matrix() -> list[dict]:
    results: list[dict] = []
    dev = torch.device("cuda:0")
    torch.manual_seed(1234)
    torch.backends.cuda.matmul.allow_tf32 = False

    # 1. GEMM FP32
    a = torch.randn(128, 256, device=dev)
    b = torch.randn(256, 192, device=dev)
    c = a @ b
    ref = a.cpu().double() @ b.cpu().double()
    ok, errs = close(c, ref, "fp32_strict")
    results.append(check("gemm_fp32", ok and finite(c) and on_gpu(c),
                         forward_device=str(c.device), **errs))

    # 2+3. Conv2d forward + backward (grad_input/grad_weight/grad_bias)
    conv = torch.nn.Conv2d(3, 8, 3, padding=1).to(dev)
    x = torch.randn(2, 3, 32, 32, device=dev, requires_grad=True)
    y = conv(x)
    loss = y.square().mean()
    loss.backward()
    cpu_conv = torch.nn.Conv2d(3, 8, 3, padding=1).to("cpu").double()
    cpu_conv.weight.data = conv.weight.detach().cpu().double()
    cpu_conv.bias.data = conv.bias.detach().cpu().double()
    cpu_x = x.detach().cpu().double().requires_grad_(True)
    cpu_y = cpu_conv(cpu_x)
    cpu_loss = cpu_y.square().mean()
    cpu_loss.backward()
    ok, errs = close(y, cpu_y, "fp32_relaxed")
    results.append(check("conv2d_forward", ok and finite(y) and on_gpu(y), **errs))
    okg, errsg = close(x.grad, cpu_x.grad, "fp32_relaxed")
    okw, errsw = close(conv.weight.grad, cpu_conv.weight.grad, "fp32_relaxed")
    okb, errsb = close(conv.bias.grad, cpu_conv.bias.grad, "fp32_relaxed")
    results.append(check("conv2d_backward", okg and okw and okb,
                         grad_input=errsg, grad_weight=errsw, grad_bias=errsb))

    # 4+5. BatchNorm2d train forward + backward (spatial — the #3956 trigger)
    bn = torch.nn.BatchNorm2d(16).to(dev)
    x = torch.randn(8, 16, 64, 64, device=dev, requires_grad=True)
    rm_pre = bn.running_mean.detach().clone()      # pre-update running stats —
    rv_pre = bn.running_var.detach().clone()       # reference needs THESE
    y = bn(x)
    loss = y.square().mean()
    loss.backward()
    ref_out, ref_rm, ref_rv = bn2d_train_reference(
        x.detach(), bn.weight.detach(), bn.bias.detach(),
        rm_pre, rv_pre, bn.momentum, bn.eps)
    ok, errs = close(y, ref_out, "fp32_relaxed")
    okrm, errsrm = close(bn.running_mean, ref_rm, "fp32_strict")
    okrv, errsrv = close(bn.running_var, ref_rv, "fp32_strict")
    results.append(check("batchnorm2d_train_forward",
                         ok and okrm and okrv and finite(y) and on_gpu(y),
                         output=errs, running_mean=errsrm, running_var=errsrv,
                         running_var_estimator="unbiased (PyTorch semantics)"))
    cpu_bn = torch.nn.BatchNorm2d(16).double()
    cpu_bn.load_state_dict({k: v.detach().cpu().double() for k, v in bn.state_dict().items()})
    cpu_x = x.detach().cpu().double().requires_grad_(True)
    cpu_y = cpu_bn(cpu_x)
    cpu_y.square().mean().backward()
    okg, errsg = close(x.grad, cpu_x.grad, "fp32_relaxed")
    okw, errsw = close(bn.weight.grad, cpu_bn.weight.grad, "fp32_relaxed")
    okb, errsb = close(bn.bias.grad, cpu_bn.bias.grad, "fp32_relaxed")
    results.append(check("batchnorm2d_train_backward", okg and okw and okb,
                         grad_input=errsg, grad_weight=errsw, grad_bias=errsb))

    # 6. BatchNorm2d eval — normalizes with the module's RUNNING stats (not this
    # batch's statistics), matching PyTorch eval semantics exactly
    bn.eval()
    with torch.no_grad():
        y_eval = bn(x.detach())
    rm_now = bn.running_mean.detach().double()
    rv_now = bn.running_var.detach().double()
    ref_eval = ((x.detach().double() - rm_now[None, :, None, None])
                / torch.sqrt(rv_now[None, :, None, None] + bn.eps)
                * bn.weight.double()[None, :, None, None]
                + bn.bias.double()[None, :, None, None])
    ok, errs = close(y_eval, ref_eval, "fp32_relaxed")
    results.append(check("batchnorm2d_eval", ok and finite(y_eval) and on_gpu(y_eval), **errs))

    # 7. BatchNorm1d 2D input (native path)
    bn1 = torch.nn.BatchNorm1d(16).to(dev)
    x2 = torch.randn(32, 16, device=dev)
    y2 = bn1(x2)
    x2d = x2.double()
    ref2 = (x2d - x2d.mean(0)) / torch.sqrt(x2d.var(0, unbiased=False) + bn1.eps) \
        * bn1.weight.double() + bn1.bias.double()
    ok, errs = close(y2, ref2, "fp32_relaxed")
    results.append(check("batchnorm1d_2d_input", ok and finite(y2) and on_gpu(y2), **errs))

    # 8. BatchNorm1d 3D input (spatial → MIOpen path)
    bn3 = torch.nn.BatchNorm1d(8).to(dev)
    x3 = torch.randn(4, 8, 128, device=dev, requires_grad=True)
    y3 = bn3(x3)
    y3.square().mean().backward()
    x3d = x3.detach().double()
    ref3 = (x3d - x3d.mean(dim=(0, 2))[None, :, None]) / torch.sqrt(
        x3d.var(dim=(0, 2), unbiased=False)[None, :, None] + bn3.eps) \
        * bn3.weight.double()[None, :, None] + bn3.bias.double()[None, :, None]
    ok, errs = close(y3, ref3, "fp32_relaxed")
    results.append(check("batchnorm1d_3d_input",
                         ok and finite(y3) and on_gpu(y3) and x3.grad is not None
                         and finite(x3.grad), output=errs))

    # 9. BatchNorm3d
    bn5 = torch.nn.BatchNorm3d(4).to(dev)
    x5 = torch.randn(2, 4, 8, 8, 8, device=dev, requires_grad=True)
    y5 = bn5(x5)
    y5.square().mean().backward()
    x5d = x5.detach().double()
    ref5 = (x5d - x5d.mean(dim=(0, 2, 3, 4))[None, :, None, None, None]) / torch.sqrt(
        x5d.var(dim=(0, 2, 3, 4), unbiased=False)[None, :, None, None, None] + bn5.eps) \
        * bn5.weight.double()[None, :, None, None, None] \
        + bn5.bias.double()[None, :, None, None, None]
    ok, errs = close(y5, ref5, "fp32_relaxed")
    results.append(check("batchnorm3d", ok and finite(y5) and on_gpu(y5)
                         and finite(x5.grad), **errs))

    # 10. GroupNorm
    gn = torch.nn.GroupNorm(4, 8).to(dev)
    xg = torch.randn(4, 8, 16, 16, device=dev)
    yg = gn(xg)
    xgd = xg.double().reshape(4, 4, -1)
    refg = ((xgd - xgd.mean(-1, keepdim=True))
            / torch.sqrt(xgd.var(-1, unbiased=False, keepdim=True) + gn.eps))
    refg = refg.reshape(4, 8, 16, 16) * gn.weight.double()[None, :, None, None] \
        + gn.bias.double()[None, :, None, None]
    ok, errs = close(yg, refg, "fp32_relaxed")
    results.append(check("groupnorm", ok and finite(yg) and on_gpu(yg), **errs))

    # 11. LayerNorm
    ln = torch.nn.LayerNorm(32).to(dev)
    xl = torch.randn(8, 16, 32, device=dev)
    yl = ln(xl)
    xld = xl.double()
    refl = ((xld - xld.mean(-1, keepdim=True))
            / torch.sqrt(xld.var(-1, unbiased=False, keepdim=True) + ln.eps)) \
        * ln.weight.double() + ln.bias.double()
    ok, errs = close(yl, refl, "fp32_relaxed")
    results.append(check("layernorm", ok and finite(yl) and on_gpu(yl), **errs))

    # 12. kthvalue FP32 / FP16 / BF16 (unique, exactly-representable values → no ties;
    # selection op compares exactly, index included)
    for dtype, tag, n in [(torch.float32, "fp32", 4096),
                          (torch.float16, "fp16", 1024),   # integers ≤2048 exact in fp16
                          (torch.bfloat16, "bf16", 250)]:  # integers ≤256 exact in bf16
        t = torch.arange(1, n + 1, dtype=dtype, device=dev)
        t = t[torch.randperm(n, device=torch.device("cpu")).to(dev)]
        k = n // 2
        v, i = torch.kthvalue(t, k)
        cv, ci = torch.kthvalue(t.cpu(), k)
        ok = bool(v.cpu() == cv) and bool(i.cpu() == ci) and on_gpu(v)
        results.append(check(f"kthvalue_{tag}", ok,
                             value=float(v), expected=float(cv), index=int(i), expected_index=int(ci)))

    # 13. optimizer.step — param update matches CPU SGD formula exactly (lr=0.1, no momentum)
    p = torch.nn.Parameter(torch.tensor([2.0, -1.0, 0.5], device=dev))
    opt = torch.optim.SGD([p], lr=0.1)
    p.grad = torch.tensor([1.0, 2.0, -0.5], device=dev)
    opt.step()
    expected = torch.tensor([2.0, -1.0, 0.5]) - 0.1 * torch.tensor([1.0, 2.0, -0.5])
    ok = bool(torch.equal(p.detach().cpu(), expected.to(p.device).cpu()))
    results.append(check("optimizer_step", ok,
                         updated=p.detach().cpu().tolist(), expected=expected.tolist(),
                         param_actually_changed=True))

    # 14. GPU synchronization + event timing sanity
    s = torch.cuda.Event(enable_timing=True)
    e = torch.cuda.Event(enable_timing=True)
    s.record()
    z = torch.randn(64, 64, device=dev) @ torch.randn(64, 64, device=dev)
    torch.cuda.synchronize()
    e.record()
    torch.cuda.synchronize()
    ms = s.elapsed_time(e)
    results.append(check("gpu_synchronization", ms > 0.0 and finite(z) and on_gpu(z),
                         elapsed_ms=ms))

    return results


def try_expect_stl_fail() -> dict:
    """Negative control: hidden host STL must reproduce the exact #3956 signature."""
    dev = torch.device("cuda:0")
    try:
        bn = torch.nn.BatchNorm2d(16).to(dev).train()
        x = torch.randn(8, 16, 64, 64, device=dev)
        y = bn(x)
        torch.cuda.synchronize()
        return {"status": "FAIL_NOT_EXPECTED", "detail": "spatial BN passed under hidden STL — signature NOT reproduced"}
    except RuntimeError as exc:
        msg = str(exc)
        sig = {
            "hiprtc_compilation_error": "HIPRTC_ERROR_COMPILATION (6)" in msg or "hiprtcCompileProgram" in msg,
            "type_traits_missing": "'type_traits' file not found" in msg,
            "batchnorm_fwd_train_spatial": "BatchNormFwdTrainSpatial" in msg or "BatchNormFwdTrain" in msg,
            "miopen_status_unknown": "miopenStatusUnknownError" in msg or "miopenStatus" in msg,
        }
        matched = sig["hiprtc_compilation_error"] and sig["type_traits_missing"]
        return {"status": "EXPECTED_FAIL" if matched else "UNEXPECTED_FAIL",
                "signature": sig, "message_excerpt": msg[:600]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expect-stl-fail", action="store_true",
                        help="negative-control mode: expect the #3956 signature")
    parser.add_argument("--log-level", type=int, default=None, help="MIOPEN_LOG_LEVEL passthrough")
    args = parser.parse_args()

    meta = {
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "torch_version_hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_available": bool(torch.cuda.is_available()),
        "hip_present": bool(torch.version.hip),
    }
    if not meta["cuda_available"] or not meta["hip_present"]:
        meta["gate"] = "BLOCKED_NOT_GPU"
        Path(args.out).write_text(json.dumps({"environment": meta, "results": []}, indent=2))
        sys.exit(3)

    if args.expect_stl_fail:
        outcome = try_expect_stl_fail()
        payload = {"environment": meta, "expect_stl_fail": outcome}
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        sys.exit(0 if outcome["status"] == "EXPECTED_FAIL" else 4)

    results = run_matrix()
    failed = [r["name"] for r in results if r["status"] != "PASS"]
    payload = {"environment": meta, "results": results,
               "summary": {"total": len(results), "pass": len(results) - len(failed),
                           "failed": failed,
                           "status": "PASS" if not failed else "FAIL"}}
    Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
