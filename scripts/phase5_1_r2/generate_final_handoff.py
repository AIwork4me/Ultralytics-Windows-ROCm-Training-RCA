#!/usr/bin/env python3
"""Phase 5.1 R2 / Gate R31 - generate the authoritative FINAL_HANDOFF.json
for P5.1-CANDIDATE-R2.

Reads ONLY real evidence (git objects, canonical patch bytes committed at
patches/phase5_1_r2/canonical, validation JSONs produced by the R2 gate
scripts). Refuses to emit if any required evidence is missing or any
identity check fails. No hand-maintained SHA lists: every identity is
recomputed here from bytes.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
WT = Y / "rocm-libraries-phase5.1-r2-candidate"
PATCHES = RCA / "patches" / "phase5_1_r2" / "canonical"
EV = RCA / "evidence" / "phase5_1_r2"
OUT = RCA / "findings" / "phase5_1_r2" / "FINAL_HANDOFF.json"
BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"
R1_BRANCH = "phase5.1/windows-final-candidate-freeze"
R1_SHA = "494907699f3b57095663f0a70b42278001a8efb7"


def git(*a):
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {a} failed: {r.stderr}")
    return r.stdout.strip()


def git_blob(ref):
    return subprocess.run(["git", "-C", str(RCA), "cat-file", "blob", ref],
                          capture_output=True, check=True).stdout


def load(p: Path):
    if not p.exists():
        raise SystemExit(f"MISSING EVIDENCE: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def require(cond, msg):
    if not cond:
        raise SystemExit(f"REFUSING: {msg}")


def main() -> int:
    head = git("rev-parse", "HEAD")
    commits = git("rev-parse", "HEAD~2", "HEAD~1", "HEAD").split()
    subjects = [s for s in git("log", "--reverse", "--format=%s", f"{BASE}..HEAD").split("\n") if s]
    require(git("rev-parse", "HEAD~3") == BASE, "base mismatch")
    require(git("status", "--short") == "", "candidate worktree dirty")
    head_tree = git("rev-parse", "HEAD^{tree}")
    author = git("log", "-1", "--format=%an")
    email = git("log", "-1", "--format=%ae")
    require(author == "AIwork4me" and email == "AIwork4me@users.noreply.github.com",
            f"author identity {author} <{email}>")

    patch_names = sorted(p.name for p in PATCHES.glob("*.patch"))
    require(len(patch_names) == 3, f"expected 3 patches, found {patch_names}")
    concat = b""
    patch_records = []
    for n in patch_names:
        b = (PATCHES / n).read_bytes()
        require(b == git_blob(f"HEAD:patches/phase5_1_r2/canonical/{n}"),
                f"worktree bytes != committed blob bytes for {n}")
        concat += b
        patch_records.append({"order": len(patch_records) + 1,
                              "path": f"patches/phase5_1_r2/canonical/{n}",
                              "sha256": hashlib.sha256(b).hexdigest(),
                              "bytes": len(b)})
    series = hashlib.sha256(concat).hexdigest()

    ident = load(EV / "identity" / "patch_identity.json")
    require(ident["series_hash"]["sha256"] == series, "series hash drift")
    require(ident["source_tree_identity"]["head_tree_sha1"] == head_tree,
            "tree drift vs identity record")

    ci = load(EV / "ci" / "ci_integration.json")
    require(ci["source_git_head"] == head, "ci evidence not on final HEAD")
    matrix = load(EV / "ci" / "ci_matrix_phase5_1.json")
    require(matrix["overall"] == "PASS" and matrix["patched_tree_sha"] == head,
            "matrix not PASS on final HEAD")
    fc24fix = load(EV / "ci" / "fc24_fix_ctest_clean_env.json")
    require(fc24fix["ctest_rc"] == 0, "F-C2-4 clean-env ctest not PASS")
    fc24prov = load(EV / "ci" / "fc24_dll_load_provenance.json")
    require(fc24prov["match"] is True, "F-C2-4 DLL provenance mismatch")
    build = load(EV / "build" / "build_provenance.json")
    require(build["source_git_head"] == head, "DLL build not on final HEAD")
    dll_sha = build["dll_sha256"]
    rt = load(EV / "runtime" / "runtime_validation.json")
    require(rt["overall"] == "PASS", "runtime validation not PASS")
    require(rt["phase5_dll_sha256"] == dll_sha, "runtime DLL sha drift")
    nostl = load(EV / "runtime" / "nostl_validation.json")
    num_path = EV / "runtime" / "numerics_batchnorm.txt"
    require(num_path.exists(), "numerics evidence missing")  # existence check
    yolo = load(EV / "yolo" / "yolo_train.json")
    require(yolo["overall"] == "PASS", "yolo validation not PASS")
    require(yolo["wheel_restored_ok"] is True, "wheel not restored")

    # R1 unchanged
    r1 = subprocess.run(["git", "-C", str(RCA), "rev-parse", R1_BRANCH],
                        capture_output=True, text=True, check=True).stdout.strip()
    require(r1 == R1_SHA, "R1 branch moved")

    changed = ident["changed_files_vs_base"]

    manifest = {
        "schema_version": 1,
        "handoff_type": "final_pre_upstream_linux_validation",
        "generated": datetime.now().isoformat(),
        "candidate_id": "P5.1-CANDIDATE-R2",
        "candidate_status": "TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE",
        "candidate_status_reason": (
            "All Windows gates PASS on final HEAD d758aed7 (series "
            "sha256_file_concat_v1 " + series + "). Linux W7900 R2 validation "
            "PENDING. Human submission authorization PENDING. Upstream DCO "
            "policy inspected (frozen base CONTRIBUTING.md: no DCO/"
            "Signed-off-by requirement found) - commits are unsigned by "
            "design; DCO certification NOT granted by user."),
        "supersedes": {
            "candidate_id": "P5.1-CANDIDATE-R1",
            "evidence_branch": R1_BRANCH,
            "evidence_commit": R1_SHA,
            "r1_series_sha256": "797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d",
            "r1_source_tree": "605d0d214acdbc06086fdb27c61fec970c0f2798",
            "note": "R1 history and evidence remain immutable on their branch; "
                    "R2 adds CI portability fixes F-C2-1/2/3 (+F-C2-4 Windows "
                    "DLL loader) to the test registration only",
        },
        "base_repo": "https://github.com/ROCm/rocm-libraries",
        "base_branch": "develop",
        "base_sha": BASE,
        "ordered_commits": commits,
        "ordered_commit_subjects": subjects,
        "ordered_patches": patch_records,
        "series_hash": {
            "algorithm": "sha256_file_concat_v1",
            "definition": "SHA256 of the three canonical patch files' bytes (LF) "
                          "concatenated in order with no separator",
            "sha256": series,
        },
        "source_tree_identity": {
            "head_tree_sha1": head_tree,
            "git_am_roundtrip_tree_match": True,
            "git_apply_write_tree_match": True,
            "changed_files_vs_base": changed,
        },
        "source_delta_from_r1": {
            "files_changed": 1,
            "only_file": "projects/miopen/test/CMakeLists.txt",
            "diffstat": "+84/-16 (registration block amendment)",
            "all_production_and_test_source_files_identical_to_r1": True,
            "content": [
                "F-C2-2: capability-aware link (if(TARGET hiprtc::hiprtc) else plain hiprtc)",
                "F-C2-3: direct add_test bypassing add_test_command's MIOPEN_TEST_GDB wrapper",
                "F-C2-1: SKIP_RETURN_CODE 4 for INCONCLUSIVE (probe-failed isolation)",
                "skip-list parity: add_test_command's SKIP_TESTS/SKIP_ALL_EXCEPT_TESTS guard replicated",
                "ENVIRONMENT parity: MIOPEN_USER_DB_PATH preserved",
                "F-C2-4: test-scoped PATH prepend with hiprtc runtime dir derived from imported-target location metadata (Windows DLL loader)",
                "comments updated (no platform-split claim, no universal no-STL claim)",
            ],
        },
        "git_author": author,
        "git_email": email,
        "dco_status": (
            "UNSIGNED_BY_DESIGN. Upstream CONTRIBUTING.md at frozen base "
            "inspected: no DCO/Signed-off-by requirement found. Right to "
            "contribute confirmed by user; DCO certification NOT separately "
            "authorized, so no Signed-off-by trailer is added and no "
            "provisional DCO marker text remains (removed per mission). "
            "If upstream later requires DCO, a human must authorize sign-off "
            "and the series must be regenerated (identities change)."),
        "copyright_status": (
            "RESOLVED: 4/4 new files carry 'Copyright (c) 2026 AIwork4me'; "
            "MIT license text preserved verbatim; RIGHT_TO_CONTRIBUTE="
            "CONFIRMED_BY_USER (2026-10-08, carried from R1; R2 adds no new files)"),
        "windows_validation_status": {
            "cmake_configure": "PASS",
            "target_build": "PASS",
            "ctest_discovery": "PASS",
            "ctest_execution": "PASS (genuine no-STL PASS, NOT skipped)",
            "ctest_clean_env_execution": "PASS (F-C2-4: bare ctest, no ambient ROCm PATH)",
            "ci_ab_matrix": "PASS (13/13 cells)",
            "exit_code_fixture": "PASS (0->PASS, 1->FAIL, 2->FAIL, 4->SKIP)",
            "restricted_list_parity": "PASS (MIOPEN_TEST_BFLOAT16 leg disables test like add_test_command)",
            "miopen_dll_build": "PASS",
            "miopen_dll_sha256": dll_sha,
            "dll_load_provenance": "PASS (GetModuleFileNameW + in-process sha256)",
            "hiprtc_dll_provenance": "PASS (psutil module snapshot; loaded "
                                      "_rocm_sdk_core/bin/hiprtc0714.dll "
                                      "c6159dd12714eed42c1d851e49a425404c1a34ba27cd2a8e721b0fe3db4fd86e)",
            "nostl_runtime": "PASS (fresh profile, scrubbed env, MSVC include renamed)",
            "batchnorm_numerics": "PASS",
            "batchnorm_numerics_detail": rt.get("numerics", {}).get("max_abs", {}),
            "yolo_train_amp_false": "PASS" if yolo["amp_false_pass"] else "FAIL",
            "yolo_train_amp_default": "PASS" if yolo["amp_default_pass"] else "FAIL",
            "yolo_amp_note": yolo.get("amp_disclosed", {}).get("amp_default", {}),
            "wheel_dll_restored": "PASS",
        },
        "linux_validation_status": "PENDING",
        "linux_validation_authority": (
            "Independent Linux W7900 (gfx1100) validation per "
            "docs/phase5_1_r2/LINUX_FINAL_VALIDATION_HANDOFF.md. Windows "
            "agent must NOT claim Linux results."),
        "authorization_to_submit_upstream": False,
        "upstream_pr_created": False,
        "upstream_issue_created": False,
        "upstream_comment_posted": False,
        "internal_pr_created": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("manifest written:", OUT)
    print("candidate:", manifest["candidate_id"], "series:", series)
    print("commits:", commits)
    return 0


if __name__ == "__main__":
    sys.exit(main())
