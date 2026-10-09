#!/usr/bin/env python3
"""Phase 5.1 R2 - verify canonical patch identity from raw bytes.

Recomputes every identity the manifest carries (patch SHA256s, ordered
series sha256_file_concat_v1, head tree, changed-file blob/sha256 map)
from git blob bytes and compares against the committed artifacts.
Exit 0 only if all checks pass.

Usage: python verify_patch_identity.py [RCA_REF]   (default: HEAD)
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")
WT = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5.1-r2-candidate")
BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"


def blob(ref, repo=RCA):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "blob", ref],
                          capture_output=True, check=True).stdout


def git_wt(*a):
    return subprocess.run(["git", "-C", str(WT), *a], capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    checks, fails = [], 0

    def chk(name, ok, detail=""):
        nonlocal fails
        if not ok:
            fails += 1
        checks.append((name, ok, detail))

    manifest = json.loads(blob(f"{ref}:findings/phase5_1_r2/FINAL_HANDOFF.json"))
    names = sorted(p["path"].split("/")[-1] for p in manifest["ordered_patches"])
    concat = b""
    for i, n in enumerate(names, 1):
        b = blob(f"{ref}:patches/phase5_1_r2/canonical/{n}")
        concat += b
        recorded = next(p for p in manifest["ordered_patches"]
                        if p["path"].endswith(n))
        chk(f"patch{i}_sha256", hashlib.sha256(b).hexdigest() == recorded["sha256"], n)
        chk(f"patch{i}_bytes", len(b) == recorded["bytes"], n)
    series = hashlib.sha256(concat).hexdigest()
    chk("series_concat_v1", series == manifest["series_hash"]["sha256"], series)

    head = manifest["ordered_commits"][-1]
    tree = git_wt("rev-parse", f"{head}^{{tree}}")
    chk("head_tree", tree == manifest["source_tree_identity"]["head_tree_sha1"], tree)
    chk("parent_chain", git_wt("rev-parse", f"{head}~3") == BASE, "base ok")
    for f, rec in manifest["source_tree_identity"]["changed_files_vs_base"].items():
        b = subprocess.run(["git", "-C", str(WT), "cat-file", "blob", f"{head}:{f}"],
                           capture_output=True, check=True).stdout
        chk(f"blob:{f}", hashlib.sha256(b).hexdigest() == rec["sha256"] and len(b) == rec["bytes"])
    # R1 immutability
    r1 = subprocess.run(["git", "-C", str(RCA), "rev-parse",
                         "phase5.1/windows-final-candidate-freeze"],
                        capture_output=True, text=True, check=True).stdout.strip()
    chk("r1_branch_unchanged", r1 == "494907699f3b57095663f0a70b42278001a8efb7", r1)
    r1c = blob("494907699f3b57095663f0a70b42278001a8efb7:"
               "patches/phase5_1/canonical/0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch")
    chk("r1_0003_immutable", hashlib.sha256(r1c).hexdigest() ==
        "3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4")
    # no DCO markers / no stale R1 identity in R2 docs
    for n in names:
        txt = blob(f"{ref}:patches/phase5_1_r2/canonical/{n}").decode("utf-8", "replace")
        chk(f"nodco:{n}", "PENDING HUMAN CONFIRMATION" not in txt and "Signed-off-by" not in txt)
    handoff_txt = blob(f"{ref}:findings/phase5_1_r2/FINAL_HANDOFF.json").decode()
    chk("manifest_no_r1_series", "797a69b5" not in json.dumps(
        {k: v for k, v in manifest.items() if k != "supersedes"}))

    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    total = len(checks)
    print(f"{total - fails}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
