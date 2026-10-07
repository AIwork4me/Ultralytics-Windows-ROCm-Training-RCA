"""Phase 18 supplement (from falsification review): which normalization ops
does the defect affect? Each case runs in an isolated subprocess.

Cases:
  bn1d_2d   BatchNorm1d with 2D input  (uses per-activation path)
  bn1d_3d   BatchNorm1d with 3D input  (maps to spatial BN kernel)
  bn2d      BatchNorm2d                (known failing)
  bn3d      BatchNorm3d                (maps to spatial BN kernel)
  groupnorm GroupNorm (no running stats, no MIOpen BN)
"""
import json
import subprocess
import sys

PY = sys.executable
SELF = __file__
CASES = ["bn1d_2d", "bn1d_3d", "bn2d", "bn3d", "groupnorm"]


def body(case: str) -> None:
    import torch
    import torch.nn as nn

    print(f"torch={torch.__version__} hip={torch.version.hip}")
    if case == "bn1d_2d":
        m, x = nn.BatchNorm1d(16).cuda().train(), torch.randn(8, 16, device="cuda")
    elif case == "bn1d_3d":
        m, x = nn.BatchNorm1d(16).cuda().train(), torch.randn(8, 16, 64, device="cuda")
    elif case == "bn2d":
        m, x = nn.BatchNorm2d(16).cuda().train(), torch.randn(8, 16, 64, 64, device="cuda")
    elif case == "bn3d":
        m, x = nn.BatchNorm3d(16).cuda().train(), torch.randn(2, 16, 8, 16, 16, device="cuda")
    elif case == "groupnorm":
        m, x = nn.GroupNorm(4, 16).cuda().train(), torch.randn(8, 16, 64, 64, device="cuda")
    else:
        raise SystemExit(f"unknown case {case}")
    print(f"module={type(m).__name__} input={tuple(x.shape)}")
    sys.stdout.flush()
    y = m(x)
    torch.cuda.synchronize()
    print(f"ok mean={y.mean().item():.6f}")
    print(f"CASE_{case}: PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        body(sys.argv[1])
        sys.exit(0)
    results = []
    for c in CASES:
        p = subprocess.run([PY, SELF, c], capture_output=True, text=True, timeout=600)
        out = (p.stdout or "") + (p.stderr or "")
        kernel = [ln for ln in out.splitlines() if "MIOpenBatchNormFwd" in ln]
        results.append({
            "case": c, "pass": p.returncode == 0, "exit_code": p.returncode,
            "miopen_kernel": kernel[0][:120] if kernel else None,
            "type_traits_err": "type_traits" in out,
        })
    print(json.dumps(results, indent=2))
    with open("evidence/raw/batchnorm/bn_variants_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    for r in results:
        print(f"{r['case']}: {'PASS' if r['pass'] else 'FAIL'} kernel={r['miopen_kernel']}")
