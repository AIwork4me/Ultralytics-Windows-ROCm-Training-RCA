#!/usr/bin/env python3
"""Phase 4 / Gate P45 - eight-file semantic equivalence evidence matrix.

Reference  = baseline worktree at SOURCE_SHA with original Patch 0001+0002
             applied (staged, uncommitted).
Canonical  = canonical worktree commits (Commit 1 + Commit 2).

Emits SHA256 of exact Git blob bytes (via hash-object of cleaned/staged
content) for both sides, working-tree byte equality, and scope proof.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

FILES = [
    "projects/miopen/src/kernels/miopen_type_traits.hpp",
    "projects/miopen/src/kernels/miopen_utility.hpp",
    "projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp",
    "projects/miopen/src/kernels/miopen_freestanding_utility.hpp",
    "projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp",
    "projects/miopen/src/kernels/radix.hpp",
    "projects/miopen/src/kernels/tensor_view.hpp",
    "projects/miopen/src/CMakeLists.txt",
]

REF = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-baseline")
CAN = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical")
RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")


def run(args, cwd):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"{args} failed: {p.stderr.decode(errors='replace')}")
    return p.stdout


def blob_oid_staged(repo: Path, path: str) -> str:
    out = run(["git", "ls-files", "-s", "--", path], repo).decode().strip()
    return out.split()[1]


def blob_oid_head(repo: Path, path: str) -> str:
    out = run(["git", "ls-tree", "HEAD", "--", path], repo).decode().strip()
    return out.split()[2]


def blob_bytes(repo: Path, oid: str) -> bytes:
    return run(["git", "cat-file", "blob", oid], repo)


def main() -> int:
    rows = []
    all_match = True
    for f in FILES:
        ref_oid = blob_oid_staged(REF, f)
        can_oid = blob_oid_head(CAN, f)
        ref_sha = hashlib.sha256(blob_bytes(REF, ref_oid)).hexdigest()
        can_sha = hashlib.sha256(blob_bytes(CAN, can_oid)).hexdigest()
        # working-tree byte comparison
        wt_ref = (REF / f).read_bytes()
        wt_can = (CAN / f).read_bytes()
        wt_equal = wt_ref == wt_can
        match = (ref_oid == can_oid) and (ref_sha == can_sha) and wt_equal
        all_match &= match
        rows.append({
            "path": f,
            "size_bytes": len(wt_can),
            "reference_blob_oid": ref_oid,
            "canonical_blob_oid": can_oid,
            "reference_sha256": ref_sha,
            "canonical_sha256": can_sha,
            "working_tree_bytes_equal": wt_equal,
            "verdict": "MATCH" if match else "MISMATCH",
        })

    # scope proof: canonical HEAD vs baseline differs in exactly the 8 files
    scope = run(["git", "diff", "--name-status", "b68f8944300f104875d953fc8e4510908c9aaf0b", "HEAD"], CAN).decode().strip().splitlines()
    changed = sorted(l.split("\t", 1)[1] for l in scope)
    scope_ok = changed == sorted(FILES)

    out = {
        "schema": "phase4_semantic_equivalence_v1",
        "gate": "P45",
        "date": "2026-10-08",
        "reference_definition": "SOURCE_SHA b68f8944300f104875d953fc8e4510908c9aaf0b + original patches 0001+0002 applied (uncommitted, staged)",
        "canonical_definition": "SOURCE_SHA b68f8944300f104875d953fc8e4510908c9aaf0b + canonical commits c86d1b9(1) + 4084759(2)",
        "hash_domain": "exact git blob bytes (LF), independent of working-tree CRLF smudge",
        "files": rows,
        "match_count": sum(1 for r in rows if r["verdict"] == "MATCH"),
        "required": 8,
        "scope_changes": scope,
        "scope_exactly_eight_files": scope_ok,
        "overall": "PASS" if (all_match and scope_ok) else "FAIL",
    }
    dest = RCA / "evidence" / "phase4" / "equivalence" / "file_hash_matrix.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['verdict']:8s} {r['path']}  ({r['size_bytes']}B)")
    print(f"scope_exactly_eight_files: {scope_ok}")
    print(f"OVERALL: {out['overall']} ({out['match_count']}/8)")
    return 0 if out["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
