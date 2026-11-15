"""P18 Phase A: gfx1100 GPU basic correctness on the real RX 7900 XTX.

A1 device detection, A2 memory, A3 GPU math (fp32/fp16 matmul, conv2d, backward,
optimizer step), A4 runtime identity (loaded DLLs). Emits JSON to stdout.
Run with the shim env var set (MIOpen hipRTC fix for 7.14.1 wheels).
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time

RESULT: dict = {"phase": "A", "gpu_math": {}, "runtime_identity": {}}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    import torch

    # A1 device detection
    props = torch.cuda.get_device_properties(0) if torch.cuda.is_available() else None
    RESULT["a1_detection"] = {
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "cuda": torch.version.cuda,
        "available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "device_name": torch.cuda.get_device_name(0) if props else None,
        "gcn_arch_name": getattr(props, "gcnArchName", None) if props else None,
        "total_memory_gb": round(props.total_memory / 2**30, 2) if props else None,
        "multi_processor_count": getattr(props, "multi_processor_count", None) if props else None,
    }
    if not props:
        print(json.dumps(RESULT, indent=2))
        return 1

    # A2 memory
    free, total = torch.cuda.mem_get_info(0)
    RESULT["a2_memory"] = {
        "free_bytes": free,
        "total_bytes": total,
        "free_fraction": round(free / total, 4),
    }

    dev = torch.device("cuda:0")

    # A3 GPU math: fp32/fp16 matmul, conv2d both dtypes, backward, optimizer step
    torch.manual_seed(0)
    a32 = torch.randn(1024, 1024, device=dev)
    b32 = torch.randn(1024, 1024, device=dev)
    t0 = time.perf_counter()
    c32 = a32 @ b32
    torch.cuda.synchronize()
    RESULT["gpu_math"]["fp32_matmul"] = {
        "finite": bool(torch.isfinite(c32).all()),
        "checksum": float(c32.float().sum().item()),
        "ms": round((time.perf_counter() - t0) * 1000, 1),
    }

    a16 = a32.half()
    b16 = b32.half()
    c16 = a16 @ b16
    torch.cuda.synchronize()
    RESULT["gpu_math"]["fp16_matmul"] = {
        "finite": bool(torch.isfinite(c16).all()),
        "rel_err_vs_fp32": float(((c16.float() - c32).norm() / c32.norm()).item()),
    }

    conv = torch.nn.Conv2d(3, 16, 3, padding=1).to(dev)
    x32 = torch.randn(8, 3, 128, 128, device=dev, requires_grad=True)
    y32 = conv(x32)
    loss32 = y32.float().pow(2).mean()
    loss32.backward()
    torch.cuda.synchronize()
    RESULT["gpu_math"]["fp32_conv2d_backward"] = {
        "finite_out": bool(torch.isfinite(y32).all()),
        "finite_grad_x": bool(torch.isfinite(x32.grad).all()),
        "finite_grad_w": bool(torch.isfinite(conv.weight.grad).all()),
    }

    conv_h = torch.nn.Conv2d(3, 16, 3, padding=1).half().to(dev)
    x16 = torch.randn(8, 3, 128, 128, device=dev, dtype=torch.float16, requires_grad=True)
    y16 = conv_h(x16)
    loss16 = y16.float().pow(2).mean()
    loss16.backward()
    torch.cuda.synchronize()
    RESULT["gpu_math"]["fp16_conv2d_backward"] = {
        "finite_out": bool(torch.isfinite(y16).all()),
        "finite_grad_x": bool(torch.isfinite(x16.grad).all()),
        "finite_grad_w": bool(torch.isfinite(conv_h.weight.grad).all()),
    }

    # optimizer step: parameter must really change
    lin = torch.nn.Linear(64, 64).to(dev)
    opt = torch.optim.SGD(lin.parameters(), lr=0.1)
    w_before = lin.weight.detach().clone()
    inp = torch.randn(16, 64, device=dev)
    for _ in range(3):
        opt.zero_grad()
        out = lin(inp)
        out.pow(2).mean().backward()
        opt.step()
    torch.cuda.synchronize()
    delta = (lin.weight.detach() - w_before).abs().max().item()
    RESULT["gpu_math"]["optimizer_step"] = {
        "max_abs_weight_delta": delta,
        "params_changed": bool(delta > 0),
        "finite": bool(torch.isfinite(lin.weight).all()),
    }

    # A4 runtime identity: loaded modules of THIS process
    loaded = []
    kernel32 = ctypes.windll.kernel32
    hmods = (ctypes.c_void_p * 1024)()
    cb_needed = ctypes.c_ulong()
    psapi = ctypes.windll.psapi
    list_func = getattr(psapi, "EnumProcessModulesEx", psapi.EnumProcessModules)
    if hasattr(psapi, "EnumProcessModulesEx"):
        psapi.EnumProcessModulesEx(
            ctypes.windll.kernel32.GetCurrentProcess(),
            hmods,
            ctypes.sizeof(hmods),
            ctypes.byref(cb_needed),
            3,  # LIST_MODULES_ALL
        )
    else:
        psapi.EnumProcessModules(
            ctypes.windll.kernel32.GetCurrentProcess(), hmods, ctypes.sizeof(hmods), ctypes.byref(cb_needed)
        )
    name_buf = ctypes.create_unicode_buffer(512)
    n = min(cb_needed.value // ctypes.sizeof(ctypes.c_void_p), 1024)
    for i in range(n):
        if kernel32.GetModuleFileNameW(hmods[i], name_buf, 512):
            p = name_buf.value.lower()
            if any(k in p for k in ("migraph", "miopen", "amdhip", "hip64", "rocblas", "amd_", "torch")) and "site-packages" in p:
                loaded.append(p)
    RESULT["runtime_identity"]["loaded_rocm_torch_dlls"] = sorted(set(loaded))
    for cand in loaded:
        if "miopen" in cand:
            RESULT["runtime_identity"]["miopen_dll"] = cand
            RESULT["runtime_identity"]["miopen_sha256"] = sha256(cand)
            break

    # driver + windows info
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_VideoController | Where-Object Name -like '*Radeon*') | "
             "Select-Object -ExpandProperty DriverVersion"],
            capture_output=True, text=True, timeout=60,
        )
        RESULT["runtime_identity"]["driver_version"] = out.stdout.strip()
    except Exception as e:  # noqa: BLE001
        RESULT["runtime_identity"]["driver_version"] = f"QUERY_FAIL {e}"

    RESULT["env_hiprtc_append"] = os.environ.get("HIPRTC_COMPILE_OPTIONS_APPEND", "")
    RESULT["executable"] = sys.executable
    print(json.dumps(RESULT, indent=2))
    ok = (
        RESULT["a1_detection"]["available"]
        and RESULT["a2_memory"]["total_bytes"] > 20 * 2**30
        and RESULT["gpu_math"]["fp32_matmul"]["finite"]
        and RESULT["gpu_math"]["fp16_matmul"]["finite"]
        and RESULT["gpu_math"]["fp32_conv2d_backward"]["finite_grad_w"]
        and RESULT["gpu_math"]["optimizer_step"]["params_changed"]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
