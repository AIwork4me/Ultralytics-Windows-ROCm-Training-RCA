"""Gate L48: Linux evidence manifest generator.

Builds evidence/phase3/linux_MANIFEST.json + linux_SHA256SUMS.txt for every
file under docs/phase3/linux, evidence/phase3/raw/linux, findings/phase3/linux,
scripts/phase3/linux. The manifest never contains its own hash (self-exclusion).
Files must not be modified after manifest generation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROOTS = [
    "docs/phase3/linux",
    "evidence/phase3/raw/linux",
    "findings/phase3/linux",
    "scripts/phase3/linux",
]
MANIFEST_REL = "evidence/phase3/linux_MANIFEST.json"
SUMS_REL = "evidence/phase3/linux_SHA256SUMS.txt"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    entries = []
    for root in ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and not p.is_symlink():
                st = p.stat()
                entries.append(
                    {
                        "path": str(p.relative_to(REPO)),
                        "sha256": sha256(p),
                        "size": st.st_size,
                        "mtime_utc": datetime.fromtimestamp(
                            st.st_mtime, tz=timezone.utc
                        ).isoformat(timespec="seconds"),
                    }
                )
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": "linux",
        "gpu": "gfx1151 (Radeon 8060S)",
        "rocm": "7.14.0 (wheel stack)",
        "pytorch": "2.12.0+rocm7.14.0",
        "ultralytics": "8.4.174",
        "source_sha": None,  # no patch handoff yet
        "patch_id": None,
        "patch_sha256": None,
        "file_count": len(entries),
        "files": entries,
    }
    mpath = REPO / MANIFEST_REL
    mpath.parent.mkdir(parents=True, exist_ok=True)
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    with open(REPO / SUMS_REL, "w") as f:
        for e in entries:
            f.write(f"{e['sha256']}  {e['path']}\n")
    print(f"manifest: {len(entries)} files -> {MANIFEST_REL}, {SUMS_REL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
