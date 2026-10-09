#!/usr/bin/env python3
"""Phase 5.2.1 Gate 1 — clean-checkout reproducibility verification.

Run from the ROOT of a clean checkout of linux-w7900/phase5.2.1-ci-closure
(or with --repo pointing at one). Checks:

  C1  every wrapper listed in WRAPPERS_MANIFEST.json exists with the exact
      recorded sha256/size;
  C2  every `scripts/<name>` reference in the phase-5.2 and preflight docs
      resolves to at least one in-repo script location
      (preflight/scripts, phase5_2/scripts, phase5.2.1/wrappers);
  C3  the documented phase-5.2 consumer entry points exist in-repo;
  C4  Windows phase-5/5.1 artifact preservation: patches/, evidence/phase5,
      findings/phase5, docs/phase5 (plus the frozen phase5.1 evidence branch
      tip, when reachable) are byte-identical to origin/main / the freeze;
  C5  the integration branch contains the published phase-5.2 evidence
      commits 5883db9 and c4f9da2 (history included, not rewritten).

Exit 0 iff all checks pass; prints one line per check.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

PHASE52_COMMITS = {"5883db91254227c23b3af6088cfe5cffc05c4c03", "c4f9da2fc00af11989914aa4d4111e8ff6d58bae"}
FREEZE_TIP = "494907699f3b57095663f0a70b42278001a8efb7"
SCRIPT_SOURCES = [
    "linux-w7900/preflight/scripts",
    "linux-w7900/phase5_2/scripts",
    "linux-w7900/phase5.2.1/wrappers",
]
DOC_DIRS = ["linux-w7900/phase5_2/docs", "linux-w7900/preflight/docs"]
ENTRY_POINTS = [
    "linux-w7900/phase5_2/scripts/check_final_handoff.py",
    "linux-w7900/phase5_2/scripts/test_handoff_adversarial.py",
    "linux-w7900/phase5_2/scripts/verify_source_tree.py",
    "linux-w7900/phase5_2/docs/FINAL_AB_VALIDATION_RUNBOOK.md",
    "linux-w7900/phase5.2.1/wrappers/prepare_validation_legs.sh",
    "linux-w7900/phase5.2.1/wrappers/run_validation_leg.sh",
    "linux-w7900/phase5.2.1/wrappers/build_leg_miopen.sh",
    "linux-w7900/phase5.2.1/wrappers/env_rocm7141.sh",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, check=check)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    args = ap.parse_args()
    repo = args.repo
    failures = []

    # C1 wrapper manifest
    mpath = os.path.join(repo, "linux-w7900/phase5.2.1/wrappers/WRAPPERS_MANIFEST.json")
    try:
        manifest = json.load(open(mpath))
    except OSError as e:
        print(f"C1 FAIL: cannot read WRAPPERS_MANIFEST.json: {e}")
        return 1
    c1_bad = []
    for w in manifest["wrappers"]:
        full = os.path.join(repo, w["path"])
        if not os.path.isfile(full):
            c1_bad.append(f"{w['path']}: MISSING")
        elif sha256_file(full) != w["sha256"]:
            c1_bad.append(f"{w['path']}: SHA256 MISMATCH")
    if c1_bad:
        failures.append("C1")
        print(f"C1 FAIL: {len(c1_bad)} wrapper(s) missing/mismatched:")
        for b in c1_bad:
            print(f"      {b}")
    else:
        print(f"C1 PASS: {manifest['count']} wrappers byte-verified against manifest")

    # C2 documented script references resolve
    refs = set()
    for d in DOC_DIRS:
        droot = os.path.join(repo, d)
        if not os.path.isdir(droot):
            continue
        for name in sorted(os.listdir(droot)):
            if not name.endswith(".md"):
                continue
            text = open(os.path.join(droot, name)).read()
            for m in re.finditer(r"(?<![\w./-])scripts/([A-Za-z0-9_./-]+)", text):
                ref = m.group(1).strip("./-")
                if "<" in ref or ">" in ref or not ref:
                    continue  # documented placeholder (e.g. scripts/env_<stack>.sh)
                if m.end() < len(text) and text[m.end()] == "<":
                    continue  # placeholder opening right after the token (scripts/env_<stack>.sh)
                refs.add((os.path.join(d, name), ref))
    c2_bad = []
    for doc, name in sorted(refs):
        if not any(os.path.isfile(os.path.join(repo, s, name)) for s in SCRIPT_SOURCES):
            c2_bad.append(f"{doc}: scripts/{name}")
    if c2_bad:
        failures.append("C2")
        print(f"C2 FAIL: {len(c2_bad)} documented script reference(s) unresolvable:")
        for b in c2_bad:
            print(f"      {b}")
    else:
        print(f"C2 PASS: {len(refs)} documented scripts/<name> references all resolve in-repo")

    # C3 entry points
    c3_bad = [p for p in ENTRY_POINTS if not os.path.isfile(os.path.join(repo, p))]
    if c3_bad:
        failures.append("C3")
        print(f"C3 FAIL: missing entry points: {c3_bad}")
    else:
        print(f"C3 PASS: {len(ENTRY_POINTS)} consumer entry points present")

    # C4 Windows phase-5/5.1 artifact preservation vs origin/main
    c4_bad = []
    for path in ["patches", "evidence/phase5", "findings/phase5", "docs/phase5",
                 "evidence/manifest.json", "evidence/SHA256SUMS.txt"]:
        r = git(repo, "diff", "--quiet", "origin/main", "HEAD", "--", path, check=False)
        if r.returncode != 0:
            c4_bad.append(path)
    # and the freeze branch tip itself must still point at the frozen commit
    r = git(repo, "rev-parse", "--verify", "origin/phase5.1/windows-final-candidate-freeze^{commit}",
            check=False)
    if r.returncode == 0:
        if r.stdout.strip() != FREEZE_TIP:
            c4_bad.append(f"phase5.1 freeze tip moved: {r.stdout.strip()}")
    else:
        print("      note: phase5.1 freeze branch not fetched; tip check skipped")
    if c4_bad:
        failures.append("C4")
        print(f"C4 FAIL: Windows phase-5/5.1 artifacts changed: {c4_bad}")
    else:
        print("C4 PASS: patches/, evidence/phase5, findings/phase5, docs/phase5 identical to origin/main; freeze tip intact")

    # C5 published phase-5.2 history included
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    contained = []
    for c in PHASE52_COMMITS:
        r = git(repo, "merge-base", "--is-ancestor", c, "HEAD", check=False)
        contained.append(r.returncode == 0)
    if all(contained):
        print(f"C5 PASS: published phase-5.2 commits contained in HEAD {head}")
    else:
        failures.append("C5")
        print("C5 FAIL: published phase-5.2 evidence commits not fully contained")

    if failures:
        print(f"VERIFY RESULT: FAIL ({','.join(failures)})")
        return 1
    print("VERIFY RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
