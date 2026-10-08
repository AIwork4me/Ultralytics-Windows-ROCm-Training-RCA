"""Gate L12: record provenance (path/size/sha256/SONAME/ldd) for key wheel libraries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SP = Path(sys.prefix) / "lib" / "python3.13" / "site-packages"

SEARCH_DIRS = [
    SP / "_rocm_sdk_core" / "lib",
    SP / "_rocm_sdk_libraries" / "lib",
    SP / "_rocm_sdk_devel" / "lib",
]

PATTERNS = [
    "libMIOpen.so*",
    "libhiprtc.so*",
    "libamdhip64.so*",
    "libamd_comgr.so*",
    "librocblas.so*",
    "libhiprtc-builtins.so*",
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def soname(p: Path) -> str | None:
    try:
        out = subprocess.run(
            ["readelf", "-d", str(p)], capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines():
            if "SONAME" in line:
                return line.split("[")[-1].rstrip("]").strip()
    except Exception as e:  # noqa: BLE001
        return f"readelf-failed: {e}"
    return None


def ldd(p: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["ldd", str(p)], capture_output=True, text=True, check=True
        ).stdout
        return [l.strip() for l in out.splitlines() if "=>" in l or "ld-linux" in l]
    except Exception as e:  # noqa: BLE001
        return [f"ldd-failed: {e}"]


def main() -> int:
    result = {"generated": datetime.now().isoformat(timespec="seconds"), "libraries": {}}
    for pat in PATTERNS:
        for d in SEARCH_DIRS:
            for p in sorted(d.glob(pat)):
                if p.is_symlink():
                    real = p.resolve()
                    entry = {
                        "path": str(p),
                        "symlink_to": str(real),
                        "size": real.stat().st_size,
                        "sha256": sha256(real),
                        "soname": soname(real),
                        "ldd": ldd(real),
                    }
                else:
                    entry = {
                        "path": str(p),
                        "size": p.stat().st_size,
                        "sha256": sha256(p),
                        "soname": soname(p),
                        "ldd": ldd(p),
                    }
                result["libraries"].setdefault(pat, []).append(entry)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
