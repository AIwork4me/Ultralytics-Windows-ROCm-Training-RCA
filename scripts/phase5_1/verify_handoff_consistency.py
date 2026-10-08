#!/usr/bin/env python3
"""Phase-5.1 Gate-02 handoff consistency validator.

Verifies that the Phase-5 record (PATCH_HANDOFF.json, PATCH_IDENTITY.json,
phase5_conclusion.json, docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md, the
canonical Git commits in the candidate worktree, and the canonical patch
files) is internally consistent, using byte-exact hashing only.

Checks (acceptance = 10/10):
  1  same upstream base everywhere
  2  same ordered candidate commits everywhere
  3  same commit subjects (actual Git objects vs JSON arrays)
  4  same patch paths everywhere
  5  same individual patch SHA256 (recomputed from file bytes)
  6  same ordered series SHA256 (sha256_file_concat_v1)
  7  same source-fix content (patch post-image blob SHAs == commit trees)
  8  no stale commit IDs in current instruction documents
  9  correct Linux validation status (PENDING, not claimed as executed)
 10  correct outstanding human-action status (DCO/copyright truthfully recorded)

All hashing uses raw file bytes / git stdout bytes (no PowerShell text
conversion). Binary-authoritative on Windows.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"
EXPECTED_COMMITS = [
    "135f775e855bc40185d0a39e13d0a1a97105c1b9",
    "66f66944f171628076785e5b89b4a1334d5a987d",
    "29846fc4fb736800ff0ad91af95c7cc32f1373ad",
]
EXPECTED_SUBJECTS = [
    "MIOpen: keep RTC type traits self-contained when no host STL is reachable",
    "MIOpen: make remaining RTC kernel std includes self-contained",
    "MIOpen: add HIPRTC no-host-STL regression test",
]
EXPECTED_PATCH_NAMES = [
    "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch",
    "0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch",
    "0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch",
]
EXPECTED_PATCH_SHA256 = [
    "76fd6623958fb58fc71a9fabbf662bc28a22cfd19aeacba76ca9eee841abc586",
    "d37376c9318c79f750b456ff6491ed1e6978d0eafa45a49a34fc66cf85f7a9ea",
    "593061053e113c5005040d6d9b1dee39c4d0d7cb2d0c27626749815ed6877821",
]
EXPECTED_SERIES_SHA256 = "5ad951c716fbf986e627a94f65db679f4f49519d672912cb2e407bf3b714391d"

# Commit IDs that may legitimately appear in current instruction documents:
# the frozen base, the three canonical P5 commits, the P3 source SHA, the P4
# canonical commits, and RCA-repo evidence commits.
ALLOWED_COMMIT_PREFIXES = [
    EXPECTED_BASE,
    *EXPECTED_COMMITS,
    "b68f8944300f104875d953fc8e4510908c9aaf0b",  # P3-FINAL-R3 source
    "c86d1b95aacc35eed6b25e69ba659e1f6a133197",  # P4 canonical 1
    "4084759f3804748b7935d882db2d0445a3e0c380",  # P4 canonical 2
]
# Known obsolete intermediate Phase-5 commit IDs that must NOT appear.
KNOWN_STALE_IDS = ["b1adc77a", "39319c4d"]

PENDING_TOKENS = ("PENDING",)


def git_bytes(worktree: Path, *args: str) -> bytes:
    r = subprocess.run(["git", "-C", str(worktree), *args],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="RCA repository root")
    ap.add_argument("--worktree", required=True, help="canonical source worktree")
    ap.add_argument("--out", required=True, help="output findings JSON path")
    ap.add_argument("--label", default="run", help="label recorded in the output")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    worktree = Path(args.worktree).resolve()

    handoff = json.loads((repo / "findings/phase5/PATCH_HANDOFF.json").read_text(encoding="utf-8"))
    identity = json.loads((repo / "findings/phase5/PATCH_IDENTITY.json").read_text(encoding="utf-8"))
    conclusion = json.loads((repo / "findings/phase5/phase5_conclusion.json").read_text(encoding="utf-8"))
    md_text = (repo / "docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md").read_text(encoding="utf-8")

    checks = []

    def record(num, name, ok, detail):
        checks.append({"check": num, "name": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    # ---- actual Git objects -------------------------------------------------
    git_head = git_bytes(worktree, "rev-parse", "HEAD").decode().strip()
    git_commits = git_bytes(worktree, "rev-parse", "HEAD~2", "HEAD~1", "HEAD").decode().split()
    git_base = git_bytes(worktree, "rev-parse", "HEAD~3").decode().strip()
    git_subjects = [s for s in git_bytes(worktree, "log", "--reverse", "--format=%s",
                                         f"{EXPECTED_BASE}..HEAD").decode().split("\n") if s]
    git_author = git_bytes(worktree, "log", "-3", "--format=%an <%ae>").decode().split("\n")[0].strip()

    # ---- 1. same upstream base ----------------------------------------------
    bases = {
        "git_HEAD~3": git_base,
        "PATCH_HANDOFF.upstream_base.sha": handoff["upstream_base"]["sha"],
        "PATCH_IDENTITY.new_upstream_base_sha": identity["new_upstream_base_sha"],
        "phase5_conclusion.new_upstream_base": conclusion["new_upstream_base"].split(" ")[0],
        "md_frozen_base": (re.search(r"frozen upstream base SHA:\s+([0-9a-f]{40})", md_text) or [None, None])[1],
    }
    ok1 = all(v == EXPECTED_BASE for v in bases.values())
    record(1, "same upstream base", ok1, {k: v for k, v in bases.items()})

    # ---- 2. same ordered commits --------------------------------------------
    h_commits = handoff["phase5_candidate_commits"]
    i_commits = identity["new_commit_shas"]
    c_commits = conclusion["final_candidate_commits"]
    # handoff md: SHA on the label line + following standalone-SHA lines
    md_commits = []
    m = re.search(r"phase5 candidate commits:\s*([0-9a-f]{40})", md_text)
    if m:
        md_commits.append(m.group(1))
        tail = md_text[m.end():m.end() + 400]
        md_commits += re.findall(r"^\s+([0-9a-f]{40})\s*$", tail, re.M)
    ordered = [git_commits, h_commits, i_commits, c_commits, md_commits]
    ok2 = all(c == EXPECTED_COMMITS for c in ordered)
    record(2, "same ordered candidate commits", ok2, {
        "git": git_commits, "PATCH_HANDOFF": h_commits, "PATCH_IDENTITY": i_commits,
        "conclusion": c_commits, "handoff_md": md_commits,
        "head": git_head,
    })

    # ---- 3. same commit subjects --------------------------------------------
    c_subjects = conclusion["commit_subjects"]
    ok3 = git_subjects == EXPECTED_SUBJECTS and git_subjects == c_subjects
    record(3, "same commit subjects", ok3, {"git": git_subjects, "conclusion": c_subjects})

    # ---- 4. same patch paths -------------------------------------------------
    h_paths = [p["path"].split("/")[-1] for p in sorted(handoff["patch_series"], key=lambda x: x["order"])]
    disk = sorted((repo / "patches/phase5/canonical").glob("*.patch"))
    disk_names = [p.name for p in disk if p.name != "README.md"]
    ok4 = (h_paths == EXPECTED_PATCH_NAMES and disk_names == EXPECTED_PATCH_NAMES)
    record(4, "same patch paths", ok4, {"PATCH_HANDOFF": h_paths, "disk": disk_names})

    # ---- 5. individual patch SHA256 ------------------------------------------
    details5 = {}
    ok5 = True
    for name, exp in zip(EXPECTED_PATCH_NAMES, EXPECTED_PATCH_SHA256):
        p = repo / "patches/phase5/canonical" / name
        actual = sha256_file(p) if p.exists() else "MISSING"
        details5[name] = {"recomputed": actual, "expected": exp}
        if actual != exp:
            ok5 = False
    # PATCH_HANDOFF / PATCH_IDENTITY recorded hashes must match too
    for src, arr in (("PATCH_HANDOFF", [p["sha256"] for p in sorted(handoff["patch_series"], key=lambda x: x["order"])]),
                     ("PATCH_IDENTITY", identity["new_patch_sha256"])):
        for name, rec, exp in zip(EXPECTED_PATCH_NAMES, arr, EXPECTED_PATCH_SHA256):
            details5[f"{src}:{name}"] = {"recorded": rec, "expected": exp}
            if rec != exp:
                ok5 = False
    # handoff md individual hashes (block of 3 after 'individual SHA256:')
    md_ind = re.findall(r"([0-9a-f]{64})", md_text)
    details5["handoff_md_hashes"] = md_ind
    record(5, "same individual patch SHA256", ok5, details5)

    # ---- 6. ordered series SHA256 --------------------------------------------
    concat = b"".join((repo / "patches/phase5/canonical" / n).read_bytes() for n in EXPECTED_PATCH_NAMES)
    series = hashlib.sha256(concat).hexdigest()
    ok6 = (series == EXPECTED_SERIES_SHA256
           and handoff["series_hash"]["sha256"] == EXPECTED_SERIES_SHA256
           and identity["new_series_sha256"]["sha256"] == EXPECTED_SERIES_SHA256
           and conclusion["patch_hashes"]["series"] == EXPECTED_SERIES_SHA256
           and series in md_ind)
    record(6, "same ordered series SHA256", ok6, {
        "recomputed": series, "expected": EXPECTED_SERIES_SHA256,
        "PATCH_HANDOFF": handoff["series_hash"]["sha256"],
        "PATCH_IDENTITY": identity["new_series_sha256"]["sha256"],
        "conclusion": conclusion["patch_hashes"]["series"],
        "in_handoff_md": series in md_ind,
    })

    # ---- 7. same source-fix content -------------------------------------------
    # (a) union of files touched by patches == git diff name-only base..HEAD
    git_files = sorted(git_bytes(worktree, "diff", "--name-only",
                                 f"{EXPECTED_BASE}..HEAD").decode().split())
    patch_files = set()
    blob_ok = True
    blob_detail = {}
    for name, commit in zip(EXPECTED_PATCH_NAMES, EXPECTED_COMMITS):
        text = (repo / "patches/phase5/canonical" / name).read_text(encoding="utf-8")
        for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.M):
            path = m.group(2)
            patch_files.add(path)
            # post-image blob abbreviation from the index line right after
            idx = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", text[m.end():m.end() + 200], re.M)
            if idx:
                abbrev = idx.group(2)
                full = git_bytes(worktree, "rev-parse", f"{commit}:{path}").decode().strip()
                good = full.startswith(abbrev)
                blob_ok = blob_ok and good
                blob_detail[f"{name}:{path}"] = {"patch_post_blob": abbrev, "commit_blob": full, "match": good}
    ok7 = sorted(patch_files) == git_files and blob_ok
    record(7, "same source-fix content", ok7, {
        "git_files": git_files, "patch_files": sorted(patch_files),
        "post_image_blob_matches": blob_detail,
    })

    # ---- 8. no stale commit IDs in current instructions -----------------------
    stale = []
    # mask 64-hex sha256 values so their prefixes are not read as commit IDs
    masked = re.sub(r"[0-9a-f]{64}", "<sha256>", md_text)
    for tok in re.findall(r"\b[0-9a-f]{7,40}\b", masked):
        if any(p.startswith(tok) or tok.startswith(p) for p in ALLOWED_COMMIT_PREFIXES):
            continue
        stale.append(tok)
    ok8 = not stale and not any(s in md_text for s in KNOWN_STALE_IDS)
    record(8, "no stale commit IDs in current instructions", ok8,
           {"stale_tokens": sorted(set(stale)), "known_stale_present": [s for s in KNOWN_STALE_IDS if s in md_text]})

    # ---- 9. correct Linux validation status ------------------------------------
    linux_vals = {
        "PATCH_HANDOFF.linux_validation_status": handoff["linux_validation_status"],
        "conclusion.linux_phase5_revalidation": conclusion["linux_phase5_revalidation"],
        "md_status_line": (re.search(r"\*\*Status:\s*`([^`]+)`\*\*", md_text) or [None, None])[1],
    }
    ok9 = all(any(t in str(v) for t in PENDING_TOKENS) for v in linux_vals.values())
    record(9, "correct Linux validation status (PENDING)", ok9, linux_vals)

    # ---- 10. correct outstanding human-action status ----------------------------
    dco = {"PATCH_HANDOFF.pending": handoff["source_delta_classification"]["pending"],
           "PATCH_IDENTITY.dco_status": identity["dco_status"],
           "conclusion.dco_status": conclusion["dco_status"]}
    cpy = {"PATCH_IDENTITY.copyright_status": identity["copyright_status"],
           "conclusion.copyright_status": conclusion["copyright_status"]}
    dco_pending = any("DCO" in str(v) and "PENDING" in str(v) for v in dco.values())
    cpy_recorded = any("COPYRIGHT" in str(v) or "copyright" in str(v) for v in cpy.values())
    hu = conclusion.get("human_actions", [])
    ok10 = dco_pending and cpy_recorded and any("DCO" in h for h in hu)
    record(10, "correct outstanding human-action status", ok10, {"dco": dco, "copyright": cpy,
                                                                 "human_actions": hu})

    passed = sum(1 for c in checks if c["result"] == "PASS")
    out = {
        "label": args.label,
        "schema_version": 1,
        "repo": str(repo),
        "worktree": str(worktree),
        "git_author": git_author,
        "checks": checks,
        "summary": {"passed": passed, "total": len(checks),
                    "verdict": "CONSISTENT" if passed == len(checks) else "INCONSISTENT"},
    }
    Path(args.out).resolve().parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).resolve().write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"[{args.label}] {passed}/{len(checks)} checks PASS -> {out['summary']['verdict']}")
    for c in checks:
        print(f"  {c['result']:4s} check {c['check']:2d}: {c['name']}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
