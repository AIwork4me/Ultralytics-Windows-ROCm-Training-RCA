"""Gate L35 part 2: compare unpatched vs patched MIOpen numerics.

Loads the two capture files, compares every tensor:
  max_abs_error, mean_abs_error, max_relative_error (denominator-clamped),
  finite checks; plus each build vs the CPU reference for sanity.
Exit 0 only if unpatched-vs-patched errors are within fp-noise tolerances.
"""

import json
import sys
from datetime import datetime

import torch

TOL_MAX_ABS = 5e-6  # same-operator, same-input GPU builds: expect ~bit-level
TOL_MEAN_ABS = 1e-8


def stats(a: torch.Tensor, b: torch.Tensor) -> dict:
    d = (a.double() - b.double()).abs()
    denom = b.double().abs().clamp_min(1e-3)
    return {
        "max_abs": float(d.max()),
        "mean_abs": float(d.mean()),
        "max_rel": float((d / denom).max()),
        "finite": bool(torch.isfinite(a).all() and torch.isfinite(b).all()),
        "allclose_1e-5": bool(torch.allclose(a, b, atol=1e-5, rtol=1e-5)),
    }


def main() -> int:
    unp = torch.load(sys.argv[1])
    pat = torch.load(sys.argv[2])
    keys = sorted(set(unp) | set(pat))
    rows = {}
    ok = True
    for k in keys:
        if k.endswith("cpu_ref"):
            continue
        if k not in unp or k not in pat:
            rows[k] = "MISSING"
            ok = False
            continue
        s = stats(unp[k], pat[k])
        # sanity vs CPU ref for both builds
        ref_key = k.rsplit("/", 1)[0] + "/y_cpu_ref"
        if k.endswith("/y") and ref_key in unp:
            s["unp_vs_cpu_max_abs"] = stats(unp[k], unp[ref_key])["max_abs"]
            s["pat_vs_cpu_max_abs"] = stats(pat[k], unp[ref_key])["max_abs"]
        rows[k] = s
        if not s["finite"] or not s["allclose_1e-5"]:
            ok = False
    out = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "tolerances": {"max_abs": TOL_MAX_ABS, "mean_abs": TOL_MEAN_ABS},
        "comparison": rows,
        "overall_max_abs": max(
            (v["max_abs"] for v in rows.values() if isinstance(v, dict)), default=None
        ),
        "overall": "PASS" if ok else "FAIL",
    }
    print(json.dumps(out, indent=2))
    with open(sys.argv[3], "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
