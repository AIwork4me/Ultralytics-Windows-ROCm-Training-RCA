#!/usr/bin/env python3
"""B05: exact candidate reconstruction from frozen base + canonical patches.

Two INDEPENDENT methods, both mandatory to agree with the frozen Windows
head tree 605d0d214acdbc06086fdb27c61fec970c0f2798:

  METHOD A (git am):     worktree @ 7c586614 -> git am 0001 0002 0003
                         -> rev-parse HEAD^{tree}
  METHOD B (git apply):  worktree @ 7c586614 -> git apply --index <p1..p3>
                         -> git write-tree (index result)

Both run in DISPOSABLE worktrees; nothing here builds or runs the patched
library (mission boundary). Also verifies:
  - all changes confined to projects/miopen
  - git am yields exactly 3 commits with the manifest's ordered subjects
  - the 4 new copyright lines present; old placeholders absent
  - git diff --check clean (whitespace/conflict markers)
"""

import datetime
import json
import os
import shutil
import subprocess
import sys

WS = "/workspace/miopen-w7900-validation"
REPO = os.path.join(WS, "repos", "rocm-libraries")
PINNED = os.path.join(WS, "repos", "rca-evidence")
BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"
EXPECTED_TREE = "605d0d214acdbc06086fdb27c61fec970c0f2798"
PATCHES = [
    "patches/phase5_1/canonical/0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch",
    "patches/phase5_1/canonical/0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch",
    "patches/phase5_1/canonical/0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch",
]
EXPECTED_SUBJECTS = [
    "MIOpen: keep RTC type traits self-contained when no host STL is reachable",
    "MIOpen: make remaining RTC kernel std includes self-contained",
    "MIOpen: add HIPRTC no-host-STL regression test",
]
SCRATCH = os.path.join(WS, "build", "recon")
EVID = os.path.join(WS, "phase5_2", "evidence", "source_reconstruction.json")
LOGDIR = os.path.join(WS, "phase5_2", "logs")

env = dict(os.environ)
env["GIT_NO_LAZY_FETCH"] = "1"
env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Phase52Recon"
env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "recon@invalid"
env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "2026-10-08T00:00:00+00:00"


def git(args, cwd, check=True):
    r = subprocess.run(["git", "-C", cwd] + args, capture_output=True,
                       text=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {cwd} failed: "
                           f"{r.stderr.strip()}")
    return r


def log(name, text):
    with open(os.path.join(LOGDIR, name), "w") as f:
        f.write(text)


def method_a():
    wt = os.path.join(SCRATCH, "method-a-git-am")
    shutil.rmtree(wt, ignore_errors=True)
    git(["worktree", "prune"], REPO, check=False)
    git(["worktree", "add", "--detach", "--no-checkout", wt, BASE], REPO)
    # Sparse materialization: only dirs the patches touch (this filesystem
    # is very slow on full 54k-file checkouts; git am needs working files
    # only for the patched paths; the INDEX still carries the full tree).
    git(["sparse-checkout", "init", "--cone"], wt)
    git(["sparse-checkout", "set", "projects/miopen/src",
         "projects/miopen/test"], wt)
    git(["reset", "--hard", "HEAD"], wt)
    amlog = []
    for p in PATCHES:
        r = git(["am", os.path.join(PINNED, p)], wt, check=False)
        amlog.append({"patch": p, "exit": r.returncode,
                      "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]})
        if r.returncode != 0:
            return {"ok": False, "stage": f"git am {os.path.basename(p)}",
                    "log": amlog, "worktree": wt}
    tree = git(["rev-parse", "HEAD^{tree}"], wt).stdout.strip()
    commits = git(["log", "--format=%H %s", f"{BASE}..HEAD"], wt).stdout
    subjects = [l.split(" ", 1)[1]
                for l in reversed(commits.strip().splitlines())]  # oldest first
    shas = [l.split(" ", 1)[0]
            for l in reversed(commits.strip().splitlines())]
    diffcheck = git(["diff", "--check", f"{BASE}..HEAD"], wt, check=False)
    stat = git(["diff", "--stat", f"{BASE}..HEAD"], wt).stdout
    changed = git(["diff", "--name-only", f"{BASE}..HEAD"], wt).stdout.split()
    ok = (tree == EXPECTED_TREE and len(subjects) == 3 and
          subjects == EXPECTED_SUBJECTS and diffcheck.returncode == 0 and
          all(c.startswith("projects/miopen/") for c in changed))
    return {"ok": ok, "method": "A: git am (3 commits)",
            "tree": tree, "expected_tree": EXPECTED_TREE,
            "tree_match": tree == EXPECTED_TREE,
            "commit_shas": shas, "subjects": subjects,
            "subjects_match": subjects == EXPECTED_SUBJECTS,
            "diff_check_clean": diffcheck.returncode == 0,
            "all_changes_under_projects_miopen":
                all(c.startswith("projects/miopen/") for c in changed),
            "changed_files": changed, "stat": stat, "am_log": amlog,
            "worktree": wt}


def method_b():
    """Index-only reconstruction: git apply --cached (zero file I/O; base
    contents come from the object store through the index — the isolated
    index variant of the mission's 'git apply --index' method B)."""
    wt = os.path.join(SCRATCH, "method-b-apply-index")
    shutil.rmtree(wt, ignore_errors=True)
    git(["worktree", "prune"], REPO, check=False)
    git(["worktree", "add", "--detach", "--no-checkout", wt, BASE], REPO)
    git(["read-tree", "HEAD"], wt)
    applog = []
    for p in PATCHES:
        r = git(["apply", "--cached", os.path.join(PINNED, p)], wt,
                check=False)
        applog.append({"patch": p, "exit": r.returncode,
                       "stderr": r.stderr[-2000:]})
        if r.returncode != 0:
            return {"ok": False, "stage": f"git apply --cached {os.path.basename(p)}",
                    "log": applog, "worktree": wt}
    tree = git(["write-tree"], wt).stdout.strip()
    staged = git(["diff", "--cached", "--name-only", "HEAD"], wt).stdout
    changed = staged.split()
    ok = tree == EXPECTED_TREE and all(
        c.startswith("projects/miopen/") for c in changed)
    return {"ok": ok, "method": "B: isolated index; git apply --cached + write-tree",
            "tree": tree, "expected_tree": EXPECTED_TREE,
            "tree_match": tree == EXPECTED_TREE,
            "all_changes_under_projects_miopen":
                all(c.startswith("projects/miopen/") for c in changed),
            "changed_files": sorted(changed), "apply_log": applog,
            "worktree": wt}


def content_checks():
    """Copyright notices present, placeholders absent (from method A tree)."""
    wt = os.path.join(SCRATCH, "method-a-git-am")
    new_files = [
        "projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp",
        "projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp",
        "projects/miopen/src/kernels/miopen_freestanding_utility.hpp",
        "projects/miopen/test/hiprtc_selfcontained.cpp",
    ]
    res = {"files": {}, "all_copyright_ok": True, "no_placeholders": True}
    for f in new_files:
        txt = open(os.path.join(wt, f), encoding="utf-8", errors="replace").read()
        cp_ok = "Copyright (c) 2026 AIwork4me" in txt
        ph = ("Copyright (c) [YEAR] AIwork4me" in txt or
              "Copyright (c) YYYY" in txt or
              "[YOUR NAME]" in txt or "YOUR COPYRIGHT" in txt)
        res["files"][f] = {"copyright_2026_aiwork4me": cp_ok,
                           "placeholder_present": ph}
        res["all_copyright_ok"] &= cp_ok
        res["no_placeholders"] &= not ph
    return res


def main():
    os.makedirs(LOGDIR, exist_ok=True)
    a = method_a()
    b = method_b() if a.get("tree_match") else {"ok": False, "skipped":
                                                "method A failed; STOP per mission"}
    c = content_checks() if a.get("tree_match") else {}
    both = a.get("tree_match") and b.get("tree_match")
    report = {
        "gate": "B05",
        "mission": "W7900-PHASE52-BRIDGE-R1",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "frozen_base": BASE,
        "expected_head_tree": EXPECTED_TREE,
        "method_a": a,
        "method_b": b,
        "content_checks": c,
        "both_methods_exact_tree_match": bool(both),
        "workloads_executed": False,
        "operational_leg_b_touched": False,
        "disposable_worktrees_to_be_cleaned": [a.get("worktree"), b.get("worktree")],
        "verdict": "PASS" if (both and c.get("all_copyright_ok") and
                              c.get("no_placeholders") and a["ok"] and b["ok"])
                   else "FAIL",
    }
    os.makedirs(os.path.dirname(EVID), exist_ok=True)
    with open(EVID, "w") as f:
        json.dump(report, f, indent=2)
    log("B05_method_a_git_am.log", json.dumps(a, indent=2))
    log("B05_method_b_apply_index.log", json.dumps(b, indent=2))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("method_a", "method_b")}, indent=2))
    print("METHOD_A:", {k: a.get(k) for k in ("ok", "tree", "tree_match",
                                              "subjects_match")})
    print("METHOD_B:", {k: b.get(k) for k in ("ok", "tree", "tree_match")})
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
