# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Verify a Windows Radeon training environment before any training run (Golden Path step 3).

Checks, in order: real AMD GPU visible (rejects CPU-only installs), HIP-enabled torch,
official package versions, wheel/driver compatibility notes. Writes a runtime-identity
JSON for the acceptance manifest. Exits 0 on PASS, 2 on any failure with actionable output.

Usage:
    python verify_environment.py [--out ENV_JSON_PATH]
"""

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def fail(msg: str, hint: str = ""):
    """Print a FAIL line with a recovery hint and exit with code 2 (never silently continue)."""
    print(f"[FAIL] {msg}")
    if hint:
        print(f"       fix: {hint}")
    sys.exit(2)


def loaded_miopen_identity() -> dict:
    """Load MIOpen.dll, return its full path, SHA256 and embedded version string (if any)."""
    import ctypes
    import re

    try:
        miopen = ctypes.CDLL("MIOpen.dll")
    except OSError as e:
        return {"loaded": False, "error": str(e)}
    gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
    gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    buf = ctypes.create_string_buffer(1024)
    gmfn(miopen._handle, buf, 1024)
    path = buf.value.decode(errors="replace")
    h = hashlib.sha256()
    blob = b""
    try:
        blob = Path(path).read_bytes()
        h = hashlib.sha256(blob)
    except OSError:
        pass
    versions = sorted(set(re.findall(rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", blob)))
    return {
        "loaded": True,
        "path": path,
        "sha256": h.hexdigest(),
        "bytes": len(blob),
        "embedded_version_strings": [v.decode() for v in versions],
        "pr13437_marker_miopen_initializer_list": blob.count(b"miopen_initializer_list"),
    }


def main():
    """Run all environment checks and write the runtime identity JSON."""
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment_identity.json", help="output JSON path")
    args = ap.parse_args()

    ident = {"captured_utc": datetime.now(tz=timezone.utc).isoformat(), "checks": {}}

    # 1) Python / OS identity
    ident["python"] = sys.version.split()[0]
    ident["os"] = platform.platform()
    print(f"[OK] python {ident['python']} on {ident['os']}")

    # 2) torch provenance
    ident["torch"] = torch.__version__
    if "+rocm" not in torch.__version__ and "rocm" not in torch.__version__.lower():
        fail(
            f"torch {torch.__version__} is not a ROCm build",
            "pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/",
        )
    print(f"[OK] torch {ident['torch']} (ROCm build)")

    # 3) HIP runtime
    hip = getattr(torch.version, "hip", None)
    ident["hip"] = hip
    if not hip:
        fail("torch.version.hip is None — this torch cannot use AMD GPUs", "reinstall the official ROCm wheel (see WINDOWS_SETUP.md §2)")
    print(f"[OK] HIP runtime {hip}")

    # 4) real GPU visible — this is the CPU-only rejection gate
    if not torch.cuda.is_available():
        fail(
            "torch.cuda.is_available() is False — no usable GPU (CPU-only install or driver too old)",
            "reinstall the official ROCm wheel (see WINDOWS_SETUP.md §2) and update the AMD driver",
        )
    name = torch.cuda.get_device_name(0)
    ident["device_name"] = name
    ident["device_capability"] = list(torch.cuda.get_device_capability(0))
    ident["device_count"] = torch.cuda.device_count()
    ident["total_mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
    print(f"[OK] GPU 0: {name} (count={ident['device_count']}, {ident['total_mem_gb']} GB)")

    # 5) real GPU compute (not just enumeration)
    x = torch.rand(256, 256, device="cuda:0")
    s = float((x @ x).sum())
    if s != s or abs(s) == float("inf"):  # NaN/inf guard
        fail("GPU matrix product returned non-finite values — GPU compute is unhealthy", "update the AMD driver; check GPU stability")
    print(f"[OK] real GPU compute: matmul sum finite ({s:.1f})")

    # 6) package identity (informational — recorded for the manifest)
    import importlib.metadata as im

    for pkg in ("ultralytics", "torchvision"):
        try:
            ident[pkg] = im.version(pkg)
            print(f"[OK] {pkg} {ident[pkg]}")
        except im.PackageNotFoundError:
            fail(f"{pkg} is not installed in this environment", f"pip install {pkg}")

    # 7) loaded MIOpen identity (records what is ACTUALLY loaded in a process like this one)
    ident["miopen"] = loaded_miopen_identity()
    if ident["miopen"].get("loaded"):
        m = ident["miopen"]
        print(f"[OK] MIOpen.dll {m['embedded_version_strings'] or '?'} sha256={m['sha256'][:16]}…")
        if m.get("pr13437_marker_miopen_initializer_list") == 0:
            print(
                "[WARN] loaded MIOpen.dll does NOT contain the #13437 no-STL fix — training works only "
                "on machines with MSVC Build Tools (known BLOCKED_RELEASE, rocm-libraries#15862)"
            )

    Path(args.out).write_text(json.dumps(ident, indent=2), encoding="utf-8")
    print(f"[OK] runtime identity written to {args.out}")
    print("VERIFY_ENVIRONMENT: PASS")


if __name__ == "__main__":
    main()
