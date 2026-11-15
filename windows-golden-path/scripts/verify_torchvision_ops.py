# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""PyTorch + torchvision GPU gates (mission §7) — runs INSIDE the target venv.

Real gfx execution only; NO CPU fallback anywhere:
  torch.cuda.is_available / device_count / device name+gfx identity /
  FP32 GEMM / FP16 GEMM / autograd / Conv2d fwd+bwd / BatchNorm fwd+bwd /
  torchvision.ops.nms ON GPU / minimal tensor lifetime / clean process exit.

The torchvision nms gate exists so the P18/P19 split-wheel failure
(hipErrorInvalidDeviceFunction when amd-torchvision-device-gfx* is missing) is
classified as AMD_PACKAGE_DEPENDENCY_MISSING, never as a MIOpen source
regression. Exit 0 only when every gate passes on the GPU.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

GATES: list[dict] = []


def gate(name):
    def deco(fn):
        GATES.append({"name": name, "fn": fn})
        return fn
    return deco


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    args = ap.parse_args()
    t0 = time.time()

    results: dict[str, dict] = {}

    @gate("cuda_available")
    def g1():
        assert torch.cuda.is_available(), "torch.cuda.is_available() is False"
        return {"device_count": int(torch.cuda.device_count())}

    @gate("device_identity")
    def g2():
        name = torch.cuda.get_device_name(0)
        return {"name": name, "capability": list(torch.cuda.get_device_capability(0)),
                "gfx_target": gp_lib.gfx_from_device_name(name)}

    @gate("fp32_gemm")
    def g3():
        a = torch.randn(512, 512, device="cuda")
        b = torch.randn(512, 512, device="cuda")
        c = a @ b
        s = float(c.sum().item())
        assert math.isfinite(s), f"FP32 GEMM non-finite: {s}"
        return {"sum": s}

    @gate("fp16_gemm")
    def g4():
        a = torch.randn(512, 512, device="cuda", dtype=torch.float16)
        b = torch.randn(512, 512, device="cuda", dtype=torch.float16)
        c = a @ b
        s = float(c.float().sum().item())
        assert math.isfinite(s), f"FP16 GEMM non-finite: {s}"
        return {"sum": s}

    @gate("autograd")
    def g5():
        x = torch.randn(64, 64, device="cuda", requires_grad=True)
        y = (x * x).sum()
        y.backward()
        assert torch.isfinite(x.grad).all().item(), "autograd produced non-finite grads"
        return {"loss": float(y.item())}

    @gate("conv2d_fwd_bwd")
    def g6():
        conv = torch.nn.Conv2d(8, 16, 3, padding=1).cuda()
        x = torch.randn(4, 8, 64, 64, device="cuda", requires_grad=True)
        out = conv(x)
        out.sum().backward()
        assert torch.isfinite(conv.weight.grad).all().item(), "conv grads non-finite"
        return {"out_shape": list(out.shape)}

    @gate("batchnorm_fwd_bwd")
    def g7():
        bn = torch.nn.BatchNorm2d(16).cuda()
        x = torch.randn(8, 16, 32, 32, device="cuda", requires_grad=True)
        out = bn(x)
        out.sum().backward()
        assert torch.isfinite(x.grad).all().item(), "BN grads non-finite"
        return {"out_shape": list(out.shape)}

    @gate("torchvision_nms_gpu")
    def g8():
        import torchvision
        from torchvision.ops import nms
        boxes = torch.tensor([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]],
                             dtype=torch.float32, device="cuda")
        scores = torch.tensor([0.9, 0.8, 0.7], device="cuda")
        keep = nms(boxes, scores, 0.5)
        torch.cuda.synchronize()
        return {"keep": keep.cpu().tolist(), "torchvision": torchvision.__version__}

    @gate("tensor_lifetime")
    def g9():
        for _ in range(50):
            t = torch.randn(256, 256, device="cuda")
            del t
        torch.cuda.synchronize()
        return {"cycles": 50}

    exit_code = 0
    for g in GATES:
        try:
            detail = g["fn"]()
            results[g["name"]] = {"status": "PASS", "detail": detail}
            print(f"[PASS] {g['name']}")
        except Exception as e:  # noqa: BLE001 — classify, never crash the report
            msg = str(e)
            if "hipErrorInvalidDeviceFunction" in msg:
                fc = "TORCHVISION_DEVICE_WHEEL_MISSING"
            elif "hipErrorInvalidKernelFile" in msg:
                fc = "HIP_KERNEL_IMAGE_FAILURE"
            elif "HIPRTC" in msg or "type_traits" in msg:
                fc = "MIOPEN_HIPRTC_COMPILATION"
            elif not torch.cuda.is_available():
                fc = "ENVIRONMENT_BLOCKER"
            else:
                fc = "INCONCLUSIVE"
            results[g["name"]] = {"status": "FAIL", "error": msg[:1500],
                                  "failure_classification": fc}
            exit_code = 1
            print(f"[FAIL] {g['name']}: {msg[:300]}")

    gpu_name = results.get("device_identity", {}).get("detail", {}).get("name")
    import json
    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": gpu_name, "gfx_target": gp_lib.gfx_from_device_name(gpu_name or ""),
        "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
        gp_lib.detect_workarounds(), args.channel,
        (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None),
        "command": f"python {Path(__file__).name}",
        "exit_code": exit_code, "duration_s": round(time.time() - t0, 2),
        "pass_fail_skip": "PASS" if exit_code == 0 else "FAIL",
        "failure_classification": (next((r["failure_classification"] for r in results.values()
                                         if r["status"] == "FAIL"), None)),
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "gates": results,
        "cpu_fallback_used": False,
        "miopen_identity": gp_lib.loaded_miopen_identity(),
    }
    gp_lib.write_evidence(record, Path(args.out))
    print(f"TORCHVISION_OPS: {'PASS' if exit_code == 0 else 'FAIL'} (exit {exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
