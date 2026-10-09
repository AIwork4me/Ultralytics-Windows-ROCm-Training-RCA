#!/usr/bin/env python3
"""Phase 5.3 - Linux runner for the published Phase 5.1 R2 verifiers.

The published Windows verifiers hardcode:
  RCA = C:\\Users\\rocm\\...\\Ultralytics-Windows-ROCm-Training-RCA
  WT  = C:\\Users\\rocm\\...\\rocm-libraries-phase5.1-r2-candidate

Declared deltas vs the published verifiers (complete list):
 1. RCA/WT point at Linux paths (mechanical).
 2. commits_match_worktree substitution (see below) - flagged SUBSTITUTED in output.
 3. head_tree / parent_chain / blob:* anchoring: the published forms address the
    manifest's head commit SHA (f18c4de9...) which does not exist on Linux
    (objects unpublished; verified 404/422 on GitHub). This runner anchors the
    same checks on the reconstructed WT HEAD and additionally pins the two
    intermediate trees by incrementally applying the sha256-pinned patches to
    the frozen base (checks: intermediate_tree_1/2), so the WT history is
    verified by content, not just its final tree.

Substitution rationale: verify_final_handoff's `commits_match_worktree`
compares git commit SHAs, which embed the Windows committer timestamp.
The exact R2 commit objects are unpublished (no AIwork4me fork of
rocm-libraries exists on GitHub; RCA repo lacks the objects), so byte-exact
SHA equality is impossible on Linux. Per the Phase-5.2 precedent recorded in
linux-w7900/phase5_2/docs/SOURCE_RECONSTRUCTION.md (merged to RCA main),
the Git TREE is the content identity. The substitution:
  original:  rev-parse HEAD == manifest.ordered_commits[-1]
  substituted: HEAD^{tree} == manifest.source_tree_identity.head_tree_sha1
             AND HEAD~3 == base_sha
             AND HEAD~2/HEAD~1 trees == incremental patch application trees
             AND subjects == manifest.ordered_commit_subjects
The substitution is reported as `SUBSTITUTED` in the output, never as a
plain PASS. All other checks are unchanged from the published verifiers.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RCA = Path("/workspace/miopen-w7900-validation/repos/rca-evidence")
WT = Path("/workspace/miopen-w7900-validation/source/final-patched")
BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"
REF = sys.argv[1] if len(sys.argv) > 1 else "HEAD"


def blob(ref, repo=RCA):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "blob", ref],
                          capture_output=True, check=True).stdout


def git_wt(*a):
    return subprocess.run(["git", "-C", str(WT), *a], capture_output=True,
                          text=True, check=True).stdout.strip()


results = []


def chk(name, ok, detail="", substituted=False):
    results.append({"check": name, "ok": bool(ok), "detail": detail,
                    "substituted": substituted})


# ---------------- verify_patch_identity (logic unchanged; paths only) --------
manifest = json.loads(blob(f"{REF}:findings/phase5_1_r2/FINAL_HANDOFF.json"))
names = sorted(p["path"].split("/")[-1] for p in manifest["ordered_patches"])
concat = b""
for i, n in enumerate(names, 1):
    b = blob(f"{REF}:patches/phase5_1_r2/canonical/{n}")
    concat += b
    recorded = next(p for p in manifest["ordered_patches"] if p["path"].endswith(n))
    chk(f"patch{i}_sha256", hashlib.sha256(b).hexdigest() == recorded["sha256"], n)
    chk(f"patch{i}_bytes", len(b) == recorded["bytes"], n)
series = hashlib.sha256(concat).hexdigest()
chk("series_concat_v1", series == manifest["series_hash"]["sha256"], series)

head = manifest["ordered_commits"][-1]
tree = git_wt("rev-parse", "HEAD^{tree}")
chk("head_tree", tree == manifest["source_tree_identity"]["head_tree_sha1"], tree)
chk("parent_chain", git_wt("rev-parse", "HEAD~3") == BASE, "base ok")
for f, rec in manifest["source_tree_identity"]["changed_files_vs_base"].items():
    b = subprocess.run(["git", "-C", str(WT), "cat-file", "blob", f"HEAD:{f}"],
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
for n in names:
    txt = blob(f"{REF}:patches/phase5_1_r2/canonical/{n}").decode("utf-8", "replace")
    chk(f"nodco:{n}", "PENDING HUMAN CONFIRMATION" not in txt and "Signed-off-by" not in txt)
chk("manifest_no_r1_series", "797a69b5" not in json.dumps(
    {k: v for k, v in manifest.items() if k != "supersedes"}))

# ---------------- verify_final_handoff (one substituted check) ---------------
m = manifest
head = m["ordered_commits"][-1]
chk("candidate_id", m["candidate_id"] == "P5.1-CANDIDATE-R2")
chk("base_frozen", m["base_sha"] == "7c5866144ac4b879be442563e2b49fa1c142ea36")
wt_head = git_wt("rev-parse", "HEAD")
raw_sha_match = wt_head == head
tree_eq = git_wt("rev-parse", "HEAD^{tree}") == m["source_tree_identity"]["head_tree_sha1"]
chain_ok = git_wt("rev-parse", "HEAD~2", "HEAD~1", "HEAD").split() and \
    git_wt("rev-parse", "HEAD~3") == m["base_sha"]
subj_ok = git_wt("log", "--reverse", "--format=%s",
                 f"{m['base_sha']}..HEAD").splitlines() == m["ordered_commit_subjects"]
chk("commits_match_worktree",
    raw_sha_match or (tree_eq and chain_ok and subj_ok),
    f"raw_commit_sha_match={raw_sha_match}; substituted tree-identity equivalence "
    f"(tree={tree_eq}, parent_chain={chain_ok}, subjects={subj_ok})",
    substituted=not raw_sha_match)
# Intermediate-commit content pinning: incrementally apply the sha256-pinned
# patches to the frozen base in a scratch index and require the WT's
# HEAD~2/HEAD~1 trees to match those trees (delta 3 in module docstring).
import tempfile
_trees = []
for i in (1, 2, 3):
    idx = tempfile.NamedTemporaryFile(prefix=f"p53idx{i}", delete=False)
    idx.close()
    env = dict(os.environ, GIT_INDEX_FILE=idx.name)
    subprocess.run(["git", "-C", str(WT), "read-tree", BASE],
                   env=env, check=True, capture_output=True)
    for n in names[:i]:
        subprocess.run(["git", "-C", str(WT), "apply", "--cached",
                        str(RCA / "patches" / "phase5_1_r2" / "canonical" / n)],
                       env=env, check=True, capture_output=True)
    r = subprocess.run(["git", "-C", str(WT), "write-tree"],
                       env=env, check=True, capture_output=True, text=True)
    _trees.append(r.stdout.strip())
    os.unlink(idx.name)
inter_ok = (git_wt("rev-parse", "HEAD~2^{tree}") == _trees[0]
            and git_wt("rev-parse", "HEAD~1^{tree}") == _trees[1]
            and git_wt("rev-parse", "HEAD^{tree}") == _trees[2])
chk("intermediate_tree_1", git_wt("rev-parse", "HEAD~2^{tree}") == _trees[0], _trees[0])
chk("intermediate_tree_2", git_wt("rev-parse", "HEAD~1^{tree}") == _trees[1], _trees[1])
chk("subjects_match_git", subj_ok)
chk("worktree_clean", git_wt("status", "--porcelain") == "")
ev = m["windows_validation_status"]
for k in ("cmake_configure", "target_build", "ctest_discovery", "ctest_execution",
          "ctest_clean_env_execution", "ci_ab_matrix", "exit_code_fixture",
          "restricted_list_parity", "miopen_dll_build", "dll_load_provenance",
          "hiprtc_dll_provenance", "nostl_runtime", "batchnorm_numerics",
          "yolo_train_amp_false", "yolo_train_amp_default", "wheel_dll_restored"):
    chk(f"win:{k}", str(ev.get(k, "")).startswith("PASS"), str(ev.get(k))[:60])


def show(ref, path):
    return subprocess.run(["git", "-C", str(RCA), "show", f"{ref}:{path}"],
                          capture_output=True, text=True, check=True).stdout


for path, needle in (
    ("evidence/phase5_1_r2/ci/ci_integration.json", head),
    ("evidence/phase5_1_r2/ci/ci_matrix_phase5_1.json", head),
    ("evidence/phase5_1_r2/build/build_provenance.json", head),
    ("evidence/phase5_1_r2/runtime/runtime_validation.json", ev["miopen_dll_sha256"]),
    ("evidence/phase5_1_r2/yolo/yolo_train.json", ev["miopen_dll_sha256"]),
    ("evidence/phase5_1_r2/ci/fc24_fix_ctest_clean_env.json", head[:8]),
):
    try:
        txt = show(REF, path)
        chk(f"evidence:{Path(path).name}", needle in txt, path)
    except subprocess.CalledProcessError:
        chk(f"evidence:{Path(path).name}", False, "MISSING")
yolo = json.loads(show(REF, "evidence/phase5_1_r2/yolo/yolo_train.json"))
chk("yolo_overall", yolo["overall"] == "PASS")
chk("yolo_wheel_restored", yolo["wheel_restored_ok"] is True)
chk("linux_pending", m["linux_validation_status"] == "PENDING")
chk("no_submit_authorization", m["authorization_to_submit_upstream"] is False)
for k in ("upstream_pr_created", "upstream_issue_created",
          "upstream_comment_posted", "internal_pr_created"):
    chk(f"no_{k}", m[k] is False)
chk("dco_truthful", "UNSIGNED" in m["dco_status"] and "Signed-off-by" not in
    git_wt("log", "--format=%B", "-3"))
chk("copyright_4files", "4/4" in m["copyright_status"])
chk("supersedes_r1", m["supersedes"]["candidate_id"] == "P5.1-CANDIDATE-R1"
    and m["supersedes"]["evidence_commit"] == "494907699f3b57095663f0a70b42278001a8efb7")
body = {k: v for k, v in m.items() if k != "supersedes"}
chk("no_stale_r1_identity", "797a69b5" not in json.dumps(body))

# ---------------- report ------------------------------------------------------
fails = [r for r in results if not r["ok"]]
subs = [r for r in results if r["substituted"]]
for r in results:
    tag = "FAIL " if not r["ok"] else ("SUBST" if r["substituted"] else "PASS ")
    print(tag + r["check"] + (f"  [{r['detail']}]" if r["detail"] else ""))
print(f"{len(results) - len(fails)}/{len(results)} checks passed "
      f"({len(subs)} substituted, {len(fails)} failed)")
json.dump({"runner": "run_r2_verifiers_linux.py", "rca_ref": REF,
           "rca_head": subprocess.run(["git", "-C", str(RCA), "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip(),
           "wt_head": wt_head, "results": results,
           "total": len(results), "passed": len(results) - len(fails),
           "failed": len(fails), "substituted": len(subs)},
          open("/workspace/miopen-w7900-validation/phase5_3/evidence/L01_verifier_run.json", "w"),
          indent=2)
sys.exit(1 if fails else 0)
