#!/usr/bin/env python3
"""Phase 4 / Gate P41 - verify immutable patch identity of P3-FINAL-R3.

Reads the two Phase-3 patch files as exact Git blob bytes from origin/main
(via `git cat-file blob`, never working-tree files) and recomputes:
  - per-patch SHA256
  - ordered-series SHA256 (sha256_git_blob_concat_v1:
    SHA256(blob_bytes_0001 || blob_bytes_0002), no separator)

Compares against the authoritative identities published in the mission
brief and findings/phase3/PATCH_HANDOFF.json.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")

EXPECTED = {
    "source_sha": "b68f8944300f104875d953fc8e4510908c9aaf0b",
    "patch_0001_sha256": "f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20",
    "patch_0002_sha256": "77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532",
    "series_sha256": "b1150afcf2170a9d396f9a25669547c0ed4021c221f7feaa59e073d4b9706685",
}

PATCH_REFS = [
    ("patches/phase3/0001-miopen-hiprtc-selfcontained.patch", 1),
    ("patches/phase3/0002-miopen-hiprtc-selfcontained.patch", 2),
]


def git_cat_blob(ref: str, path: str) -> bytes:
    spec = f"{ref}:{path}"
    proc = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "blob", spec],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git cat-file failed for {spec}: {proc.stderr.decode(errors='replace')}")
    return proc.stdout


def git_rev_parse(ref: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", ref],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git rev-parse failed for {ref}")
    return proc.stdout.strip()


def main() -> int:
    origin_main = git_rev_parse("origin/main")

    # Cross-check SOURCE_SHA: the commit the patches were generated against.
    # The handoff records it; here we confirm the handoff blob agrees with
    # the mission constants and record where the baseline commit is present.
    handoff_bytes = git_cat_blob("origin/main", "findings/phase3/PATCH_HANDOFF.json")
    handoff = json.loads(handoff_bytes.decode("utf-8"))

    checks = {
        "origin_main": origin_main,
        "handoff_patch_id": handoff.get("patch_id"),
        "handoff_source_sha": handoff.get("source", {}).get("sha"),
        "source_sha_match": handoff.get("source", {}).get("sha") == EXPECTED["source_sha"],
    }

    blobs = {}
    per_patch = []
    for path, order in PATCH_REFS:
        blob = git_cat_blob("origin/main", path)
        blobs[order] = blob
        sha = hashlib.sha256(blob).hexdigest()
        exp = EXPECTED[f"patch_{order:04d}_sha256"]
        per_patch.append({
            "order": order,
            "path": path,
            "git_ref": f"origin/main:{path}",
            "size_bytes": len(blob),
            "sha256": sha,
            "expected_sha256": exp,
            "match": sha == exp,
            "handoff_sha256": handoff["patch_series"][order - 1]["sha256"],
            "handoff_match": sha == handoff["patch_series"][order - 1]["sha256"],
        })

    series = hashlib.sha256(blobs[1] + blobs[2]).hexdigest()
    series_check = {
        "algorithm": "sha256_git_blob_concat_v1",
        "sha256": series,
        "expected_sha256": EXPECTED["series_sha256"],
        "match": series == EXPECTED["series_sha256"],
        "handoff_sha256": handoff["series_hash"]["sha256"],
        "handoff_match": series == handoff["series_hash"]["sha256"],
    }

    all_ok = (
        checks["source_sha_match"]
        and all(p["match"] and p["handoff_match"] for p in per_patch)
        and series_check["match"]
        and series_check["handoff_match"]
    )

    out = {
        "schema": "phase4_identity_verification_v1",
        "gate": "P41",
        "date": "2026-10-08",
        "verified_ref": f"origin/main ({origin_main})",
        "source": checks,
        "patches": per_patch,
        "series": series_check,
        "overall": "MATCH" if all_ok else "MISMATCH",
    }
    dest = REPO / "evidence" / "phase4" / "identity" / "verification.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"origin/main            : {origin_main}")
    print(f"SOURCE_SHA             : {checks['handoff_source_sha']} -> {'MATCH' if checks['source_sha_match'] else 'MISMATCH'}")
    for p in per_patch:
        print(f"PATCH_{p['order']:04d}_SHA256        : {p['sha256']} -> {'MATCH' if p['match'] else 'MISMATCH'}")
    print(f"SERIES_SHA256          : {series} -> {'MATCH' if series_check['match'] else 'MISMATCH'}")
    print(f"OVERALL                : {out['overall']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
