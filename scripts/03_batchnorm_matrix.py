"""Phase 5: BatchNorm A/B matrix. Each case runs in an isolated subprocess so
one crash cannot abort the matrix.

Usage: python 03_batchnorm_matrix.py            # runs all cases as subprocesses
       python 03_batchnorm_matrix.py <case>     # internal: run one case
Cases:
  A  GPU GEMM control
  B  BatchNorm2d CPU, training=True
  C  BatchNorm2d GPU, eval()
  D  BatchNorm2d GPU, training=True   (known failing path)
  E  BatchNorm2d GPU, training=True, torch.backends.cudnn.enabled=False (DIAGNOSTIC ONLY)
  F  Conv2d only, GPU, training mode
  G  Conv2d + BatchNorm2d, GPU, training mode
  H  Linear + loss + backward on GPU (autograd control, no BatchNorm)
"""
import json
import subprocess
import sys
import time

PY = sys.executable
SELF = __file__


def run_case(case: str) -> dict:
    env_note = ""
    cmd = [PY, SELF, case]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    dt = time.time() - t0
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    sig_lines = [
        ln for ln in out.splitlines()
        if any(k in ln for k in (
            "HIPRTC_ERROR_COMPILATION", "type_traits", "miopenStatusUnknownError",
            "Code object build failed", "MIOpenBatchNormFwd", "Error"))
    ]
    result = {
        "case": case,
        "cmd": " ".join(cmd),
        "env": env_note,
        "pass": ok,
        "exit_code": proc.returncode,
        "seconds": round(dt, 2),
        "signature": sig_lines[:8],
        "last_output_lines": [ln for ln in out.splitlines() if ln.strip()][-4:],
    }
    return result


def body(case: str) -> None:
    import torch
    import torch.nn as nn

    print(f"torch={torch.__version__} hip={torch.version.hip} "
          f"dev={torch.cuda.get_device_name(0)}")

    if case == "A":  # GPU GEMM control
        x = torch.randn(4096, 4096, device="cuda")
        y = x @ x
        torch.cuda.synchronize()
        print(f"gemm ok mean={y.mean().item():.6f}")

    elif case == "B":  # BatchNorm CPU training
        bn = nn.BatchNorm2d(16).train()
        x = torch.randn(8, 16, 64, 64)
        y = bn(x)
        assert torch.isfinite(y).all()
        print(f"cpu bn ok mean={y.mean().item():.6f}")

    elif case == "C":  # BatchNorm GPU eval
        bn = nn.BatchNorm2d(16).cuda().eval()
        x = torch.randn(8, 16, 64, 64, device="cuda")
        with torch.no_grad():
            y = bn(x)
        torch.cuda.synchronize()
        print(f"gpu bn eval ok mean={y.mean().item():.6f}")

    elif case == "D":  # BatchNorm GPU training (failing path)
        bn = nn.BatchNorm2d(16).cuda().train()
        x = torch.randn(8, 16, 64, 64, device="cuda")
        y = bn(x)
        torch.cuda.synchronize()
        print(f"gpu bn train ok mean={y.mean().item():.6f}")

    elif case == "E":  # DIAGNOSTIC ONLY — not a fix
        torch.backends.cudnn.enabled = False
        bn = nn.BatchNorm2d(16).cuda().train()
        x = torch.randn(8, 16, 64, 64, device="cuda")
        y = bn(x)
        torch.cuda.synchronize()
        print(f"gpu bn train cudnn.disabled ok mean={y.mean().item():.6f}")

    elif case == "F":  # Conv2d only, training mode
        conv = nn.Conv2d(16, 32, 3, padding=1).cuda().train()
        x = torch.randn(8, 16, 64, 64, device="cuda")
        y = conv(x)
        torch.cuda.synchronize()
        print(f"gpu conv ok mean={y.mean().item():.6f}")

    elif case == "G":  # Conv + BN, training mode
        conv = nn.Conv2d(16, 32, 3, padding=1).cuda().train()
        bn = nn.BatchNorm2d(32).cuda().train()
        x = torch.randn(8, 16, 64, 64, device="cuda")
        y = bn(conv(x))
        torch.cuda.synchronize()
        print(f"gpu conv+bn ok mean={y.mean().item():.6f}")

    elif case == "H":  # autograd control without BatchNorm
        lin = nn.Linear(1024, 1024).cuda().train()
        x = torch.randn(64, 1024, device="cuda", requires_grad=True)
        y = lin(x).sum()
        y.backward()
        torch.cuda.synchronize()
        print(f"gpu linear+backward ok grad_norm={lin.weight.grad.norm().item():.6f}")

    else:
        raise SystemExit(f"unknown case {case}")
    print(f"CASE_{case}: PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("--all",):
        body(sys.argv[1])
        sys.exit(0)
    cases = list("ABCDEFGH")
    results = [run_case(c) for c in cases]
    print("\n===== MATRIX RESULTS =====")
    print(json.dumps(results, indent=2))
    with open("evidence/raw/batchnorm/matrix_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n===== SUMMARY =====")
    for r in results:
        print(f"CASE {r['case']}: {'PASS' if r['pass'] else 'FAIL'} "
              f"(exit {r['exit_code']}, {r['seconds']}s)")
