#!/usr/bin/env python3
"""Phase 5.1 R2 - FINAL_HANDOFF.json consistency verifier.

Validates the R2 manifest against the on-disk/on-git evidence:
identity self-consistency, honest status fields (linux PENDING, no
upstream actions, authorization false), all Windows validation evidence
present and PASS on the exact final HEAD, DCO/copyright truthfully
recorded. Exit 0 only if all checks pass.

Usage: python verify_final_handoff.py [RCA_REF]   (default: HEAD)
"""
import json
import subprocess
import sys
from pathlib import Path

RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")
WT = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5.1-r2-candidate")


def show(ref, path):
    return subprocess.run(["git", "-C", str(RCA), "show", f"{ref}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def git_wt(*a):
    return subprocess.run(["git", "-C", str(WT), *a], capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    m = json.loads(show(ref, "findings/phase5_1_r2/FINAL_HANDOFF.json"))
    checks, fails = [], 0

    def chk(name, ok, detail=""):
        nonlocal fails
        if not ok:
            fails += 1
        checks.append((name, ok, detail))

    head = m["ordered_commits"][-1]
    chk("candidate_id", m["candidate_id"] == "P5.1-CANDIDATE-R2")
    chk("base_frozen", m["base_sha"] == "7c5866144ac4b879be442563e2b49fa1c142ea36")
    chk("commits_match_worktree", git_wt("rev-parse", "HEAD") == head
        and git_wt("rev-parse", "HEAD~2", "HEAD~1", "HEAD").split() == m["ordered_commits"])
    chk("subjects_match_git", git_wt("log", "--reverse", "--format=%s",
        f"{m['base_sha']}..HEAD").splitlines() == m["ordered_commit_subjects"])
    chk("worktree_clean", git_wt("status", "--porcelain") == "")
    ev = m["windows_validation_status"]
    for k in ("cmake_configure", "target_build", "ctest_discovery", "ctest_execution",
              "ctest_clean_env_execution", "ci_ab_matrix", "exit_code_fixture",
              "restricted_list_parity", "miopen_dll_build", "dll_load_provenance",
              "hiprtc_dll_provenance", "nostl_runtime", "batchnorm_numerics",
              "yolo_train_amp_false", "yolo_train_amp_default", "wheel_dll_restored"):
        chk(f"win:{k}", str(ev.get(k, "")).startswith("PASS"), str(ev.get(k))[:60])
    # evidence files exist on this ref and carry the same head/sha
    for path, needle in (
        ("evidence/phase5_1_r2/ci/ci_integration.json", head),
        ("evidence/phase5_1_r2/ci/ci_matrix_phase5_1.json", head),
        ("evidence/phase5_1_r2/build/build_provenance.json", head),
        ("evidence/phase5_1_r2/runtime/runtime_validation.json", ev["miopen_dll_sha256"]),
        ("evidence/phase5_1_r2/yolo/yolo_train.json", ev["miopen_dll_sha256"]),
        ("evidence/phase5_1_r2/ci/fc24_fix_ctest_clean_env.json", head[:8]),
    ):
        try:
            txt = show(ref, path)
            chk(f"evidence:{Path(path).name}", needle in txt, path)
        except subprocess.CalledProcessError:
            chk(f"evidence:{Path(path).name}", False, "MISSING")
    yolo = json.loads(show(ref, "evidence/phase5_1_r2/yolo/yolo_train.json"))
    chk("yolo_overall", yolo["overall"] == "PASS")
    chk("yolo_wheel_restored", yolo["wheel_restored_ok"] is True)
    # honest statuses
    chk("linux_pending", m["linux_validation_status"] == "PENDING")
    chk("no_submit_authorization", m["authorization_to_submit_upstream"] is False)
    for k in ("upstream_pr_created", "upstream_issue_created",
              "upstream_comment_posted", "internal_pr_created"):
        chk(f"no_{k}", m[k] is False)
    chk("dco_truthful", "UNSIGNED" in m["dco_status"] and "Signed-off-by" not in
        git_wt("log", "--format=%B", "-3"))
    chk("copyright_4files", "4/4" in m["copyright_status"])
    # R1 supersede record exact
    chk("supersedes_r1", m["supersedes"]["candidate_id"] == "P5.1-CANDIDATE-R1"
        and m["supersedes"]["evidence_commit"] == "494907699f3b57095663f0a70b42278001a8efb7")
    # no R1 series hash leaking as R2 identity (allowed only inside supersedes)
    body = {k: v for k, v in m.items() if k != "supersedes"}
    chk("no_stale_r1_identity", "797a69b5" not in json.dumps(body))

    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    total = len(checks)
    print(f"{total - fails}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
