"""Adversarial self-test for verify_release_closure.py (mission §3.4).

    python scripts/test_verify_release_closure.py

Builds a minimal KNOWN-GOOD synthetic evidence tree, then one mutated copy
per violation class (bad status vocabulary, SKIP-as-PASS, a PASS claim that
contradicts its own embedded evidence, run-id mismatch, missing raw logs,
missing DLL provenance, cross-environment DLL contamination, conflicting
hardware claims, unreconciled epoch accounting, missing CSV preservation,
uncited ledger claims) and asserts the verifier REJECTS every one with the
specific violation — and accepts the good tree.

All trees live in a temp directory; nothing in the repo is modified.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "verify_release_closure.py"
RID = "20260101T000000Z"
DLL_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
DLL_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
DEV = "AMD Radeon(TM) Test GPU"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        p.write_text(obj, encoding="utf-8")
    else:
        p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def lifecycle_record(rid: str = RID, **over) -> dict:
    rec = {
        "run_id": rid, "environment_id": "ENV_T", "run_tag": "detect_ENV_T",
        "environment": {"torch": "9.9.9+rocm0.0.0", "hip": "0.0", "device": DEV,
                        "gpu_authentic": True, "python_executable": "X"},
        "args": {"task": "detect", "stage": "resume", "amp": "False"},
        "tests": {
            "t01_gpu_pretrained_inference": {"status": "PASS", "n_results": 4},
            "t03_gpu_training_init": {"status": "PASS"},
            "t04_one_epoch_smoke": {"status": "PASS"},
            "t05_multi_epoch_interrupted": {"status": "PASS"},
            "t06_loss_finite_throughout": {"status": "PASS"},
            "t07_backward_gradient_finite": {"status": "PASS", "n_steps": 2,
                                             "failed_step_indices": []},
            "t08_optimizer_step": {"status": "PASS"},
            "t09_save_last_pt": {"status": "PASS"},
            "t10_save_best_pt": {"status": "PASS"},
            "t11_reload_checkpoint": {"status": "PASS"},
            "t12_resume_interrupted": {"status": "PASS"},
            "t13_gpu_val_saved_model": {"status": "PASS"},
            "t14_gpu_predict_saved_model": {"status": "PASS"},
            "t15_metrics_before_after_reload": {"status": "PASS"},
        },
        "step_audit_detail": {"main": {"counts": {"UPDATED": 2}},
                              "resume": {"counts": {"UPDATED": 1}}},
        "loaded_dll": {"sha256": DLL_A, "path": "M.dll"},
    }
    rec.update(over)
    return rec


def build_good_tree(root: Path, trap_uncommitted: bool = False) -> None:
    req = {
        "release-provenance": ["G0_VERDICT.md", "RELEASE_LINEAGE.md", "RELEASE_MATRIX.csv",
                               "WHEEL_MANIFEST.json", "BINARY_PROVENANCE.json", "LOADED_DLL_REPORT.json"],
        "windows-training-validation": ["G1_VERDICT.md", "G2_VERDICT.md"],
        "amp-rca": ["ROOT_CAUSE.md", "MINIMAL_REPRO.py", "PRECISION_COMPARISON.csv", "G3_VERDICT.md"],
        "upstream-readiness": ["AMP_FIX_PR_DRAFT.md", "TEST_PR_DRAFT.md", "DOCS_PR_DRAFT.md",
                               "MAINTAINER_CHECKLIST.md"],
        "platform-matrix": ["GPU_SUPPORT_MATRIX.md", "WINDOWS_GFX1151.md"],
    }
    for dr, files in req.items():
        for f in files:
            write(root / dr / f, "stub\n")
    write(root / "docs" / "release-closure" / "BASELINE_STATE.json",
          {"repo_head_at_audit": "f9f745e0"})
    stem = f"g2_detect_fp32_{RID}"
    rec = lifecycle_record()
    raw = root / "windows-training-validation" / "raw"
    write(raw / f"{stem}.json", rec)
    header = f"# run_id={RID} task=detect tag=fp32 environment_id=ENV_T\n"
    for stage in ("main", "resume"):
        write(raw / f"{stem}_{stage}.log", header + "output\n")
    write(raw / f"{stem}_probe.log", header + "probe\n")
    write(raw / f"{stem}_loaddll.json", {"miopen_loaded": {"sha256": DLL_A, "path": "M.dll"}})
    write(root / "docs" / "release-closure" / "CLAIMS_AND_EVIDENCE.md",
          "| # | Claim | Status | Class | Evidence |\n|---|---|---|---|---|\n"
          f"| C1 | synthetic lifecycle works | PASS | PROVEN | `windows-training-validation/raw/{stem}.json` |\n")

    # --- R22A.2.1 P0-B fixture: git-backed evidence pack --------------------
    # a runs/ directory exercises the .gitignore trap class that dropped the
    # 8 r22a2 raw files: without `git add -f`, sums entries resolve to nothing.
    import hashlib as _hl
    pack = root / "evidence" / "raw" / "r22a2-gfx1100-test"
    pack_files = {
        "R22A2_TEST.json": b'{"ok": true}\n',
        "runs/cold_run01_child.log": b"child output\nSTABILITY_CHILD_DONE 1.0s\n",
        "runs/child_sample_cold_run01.py": b"def main():\n    pass\n",
    }
    for rel, content in pack_files.items():
        (pack / rel).parent.mkdir(parents=True, exist_ok=True)
        (pack / rel).write_bytes(content)  # exact bytes — hashes must match them
    sums_lines = [f"{_hl.sha256(v).hexdigest()}  {(pack / rel).relative_to(root).as_posix()}"
                  for rel, v in pack_files.items()]
    sums_bytes = ("\n".join(sums_lines) + "\n").encode("utf-8")
    sums_path = pack / "SHA256SUMS.txt"
    sums_path.write_bytes(sums_bytes)
    manifest = [{"path": (pack / rel).relative_to(root).as_posix(),
                 "timestamp": "2026-11-16T00:00:00Z", "command": "fixture",
                 "sha256": _hl.sha256(v).hexdigest(),
                 "size_bytes": len(v)}
                for rel, v in pack_files.items()]
    manifest.append({"path": sums_path.relative_to(root).as_posix(),
                     "timestamp": "2026-11-16T00:00:00Z", "command": "fixture",
                     "sha256": _hl.sha256(sums_bytes).hexdigest(),
                     "size_bytes": len(sums_bytes)})
    write(root / "evidence" / "manifest.json", manifest)
    # commit the tree (the evidence pack integrity is verified against HEAD).
    # The fixture repo mirrors the REAL defect conditions: a repo-wide
    # `runs/` gitignore rule, and no CRLF translation so tree bytes == the
    # bytes the checksums were computed from.
    write(root / ".gitignore", "runs/\n")
    for args in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
                 ["git", "config", "user.name", "t"],
                 ["git", "config", "core.autocrlf", "false"], ["git", "add", "-A"]):
        subprocess.run([*args], cwd=root, check=True, capture_output=True)
    if not trap_uncommitted:
        # without -f the gitignore rule silently drops runs/ — the exact
        # R22A.2 evidence-loss mechanism; the good tree commits it explicitly
        subprocess.run(["git", "add", "-f", str(pack / "runs")], cwd=root,
                       check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root,
                   check=True, capture_output=True)


def run_verifier(root: Path) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, "-I", str(VERIFIER), "--root", str(root)],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    out = proc.stdout
    try:
        return proc.returncode, json.loads(out[out.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return proc.returncode, {"ok": None, "violations": [f"unparseable output: {out[:200]}"]}


def mutate_case(name: str, mutator) -> tuple[str, Path]:
    root = Path(tempfile.mkdtemp(prefix=f"vfix_{name}_"))
    build_good_tree(root)
    mutator(root)
    return name, root


def has_violation(res: dict, needle: str) -> bool:
    return any(needle in v for v in res.get("violations", []))


def main() -> None:
    good_root = Path(tempfile.mkdtemp(prefix="vfix_good_"))
    build_good_tree(good_tree := good_root)
    rc, res = run_verifier(good_root)
    check("known-good synthetic tree ACCEPTED (exit 0)",
          rc == 0 and res["ok"] is True, json.dumps(res.get("violations", [])))
    check("valid complete evidence pack ACCEPTED (zero git-tree violations)",
          res["ok"] is True and not any("git-tree" in v for v in res.get("violations", [])),
          json.dumps([v for v in res.get("violations", []) if "git-tree" in v]))

    cases = []

    def m_status_vocab(root: Path):
        raw = next(root.rglob(f"g2_detect_fp32_{RID}.json"))
        d = json.loads(raw.read_text(encoding="utf-8"))
        d["tests"]["t01_gpu_pretrained_inference"]["status"] = "GREAT"
        write(raw, d)
    cases.append(("status-vocabulary", m_status_vocab, "status-vocab:"))

    def m_skip_as_pass(root: Path):
        raw = next(root.rglob(f"g2_detect_fp32_{RID}.json"))
        d = json.loads(raw.read_text(encoding="utf-8"))
        for t in d["tests"].values():
            t["status"] = "SKIP"
        write(raw, d)
    cases.append(("all-SKIP record presented as success", m_skip_as_pass, "skip-not-pass"))

    def m_pass_contradicts(root: Path):
        raw = next(root.rglob(f"g2_detect_fp32_{RID}.json"))
        d = json.loads(raw.read_text(encoding="utf-8"))
        d["tests"]["t08_optimizer_step"]["status"] = "PASS"
        d["step_audit_detail"]["main"]["counts"] = {"UPDATED": 0, "STUCK_FAILURE": 1}
        write(raw, d)
    cases.append(("claimed PASS contradicting embedded evidence", m_pass_contradicts,
                  "assertion:g2_detect_fp32"))

    def m_run_id(root: Path):
        raw = next(root.rglob(f"g2_detect_fp32_{RID}_main.log"))
        raw.write_text("# run_id=OTHER-RUN\noutput\n", encoding="utf-8")
    cases.append(("run_id absent from stage log", m_run_id, "run-id-consistency"))

    def m_missing_log(root: Path):
        next(root.rglob(f"g2_detect_fp32_{RID}_resume.log")).unlink()
    cases.append(("missing raw stage log", m_missing_log, "raw-log"))

    def m_no_dll(root: Path):
        raw = next(root.rglob(f"g2_detect_fp32_{RID}.json"))
        d = json.loads(raw.read_text(encoding="utf-8"))
        d.pop("loaded_dll")
        write(raw, d)
        next(root.rglob(f"g2_detect_fp32_{RID}_loaddll.json")).unlink()
    cases.append(("PASS record without DLL provenance", m_no_dll, "dll-provenance"))

    def m_env_contamination(root: Path):
        stem = f"g2_pose_fp32_{RID}"
        write(root / "windows-training-validation" / "raw" / f"{stem}.json",
              lifecycle_record(device=DEV, loaded_dll={"sha256": DLL_B, "path": "M.dll"}))
        header = f"# run_id={RID} task=pose tag=fp32 environment_id=ENV_T\n"
        for stage in ("main", "resume"):
            write(root / "windows-training-validation" / "raw" / f"{stem}_{stage}.log",
                  header + "output\n")
        write(root / "windows-training-validation" / "raw" / f"{stem}_probe.log", header + "probe\n")
        write(root / "windows-training-validation" / "raw" / f"{stem}_loaddll.json",
              {"miopen_loaded": {"sha256": DLL_B}})
        # add t07/t08 legacy-safe copy to satisfy expected-tests for resume stage
        raw = root / "windows-training-validation" / "raw" / f"{stem}.json"
        d = json.loads(raw.read_text(encoding="utf-8"))
        d["args"] = {"task": "pose", "stage": "resume", "amp": "False"}
        write(raw, d)
    cases.append(("same environment_id, DIFFERENT loaded MIOpen SHA (contamination)",
                  m_env_contamination, "dll-env-consistency"))

    def m_hardware(root: Path):
        stem = f"g2_pose_fp32_{RID}"
        rec = lifecycle_record()
        rec["environment"]["device"] = "NVIDIA Fake GPU"
        rec["args"] = {"task": "pose", "stage": "resume", "amp": "False"}
        write(root / "windows-training-validation" / "raw" / f"{stem}.json", rec)
        header = f"# run_id={RID} task=pose tag=fp32 environment_id=ENV_T\n"
        for stage in ("main", "resume"):
            write(root / "windows-training-validation" / "raw" / f"{stem}_{stage}.log",
                  header + "output\n")
        write(root / "windows-training-validation" / "raw" / f"{stem}_probe.log", header + "probe\n")
        write(root / "windows-training-validation" / "raw" / f"{stem}_loaddll.json",
              {"miopen_loaded": {"sha256": DLL_A}})
    cases.append(("conflicting hardware claims across records", m_hardware, "hardware-consistency"))

    def m_unreconciled(root: Path):
        g4 = root / "windows-training-validation" / "raw" / "g4_long_run_x.json"
        write(g4, {"run_id": "g4long_x", "environment": {"torch": "9.9.9", "hip": "0.0", "device": DEV},
                   "epoch_reconciliation": {"reconciled": False, "epochs_configured": 30,
                                            "results_csv_rows": 31},
                   "results_csv_text": "a,b\n1,2\n", "wall_samples": [{"epoch": 0}],
                   "dll_provenance": {"miopen_loaded": {"sha256": DLL_A}}})
    cases.append(("G4 epoch accounting NOT reconciled", m_unreconciled, "epoch-reconciled"))

    def m_no_csv(root: Path):
        g4 = root / "windows-training-validation" / "raw" / "g4_long_run_y.json"
        write(g4, {"run_id": "g4long_y", "environment": {"torch": "9.9.9", "hip": "0.0", "device": DEV},
                   "epoch_reconciliation": {"reconciled": True},
                   "results_csv_text": None, "wall_samples": [],
                   "dll_provenance": {"miopen_loaded": {"sha256": DLL_A}}})
    cases.append(("G4 without preserved results.csv", m_no_csv, "csv-preserved"))

    def m_claim_no_evidence(root: Path):
        write(root / "docs" / "release-closure" / "CLAIMS_AND_EVIDENCE.md",
              "| # | Claim | Status | Class | Evidence |\n|---|---|---|---|---|\n"
              "| C9 | totally unverified claim | PASS | PROVEN | `raw/does_not_exist.json` |\n")
    cases.append(("ledger PASS claim citing a nonexistent file", m_claim_no_evidence,
                  "claim-evidence:C9"))

    for name, mutator, needle in cases:
        case_name, root = mutate_case(name, mutator)
        rc, res = run_verifier(root)
        rejected = rc != 0 and res.get("ok") is False
        check(f"REJECTS: {case_name}", rejected and has_violation(res, needle),
              f"rc={rc} violations={res.get('violations')}" if not rejected or not has_violation(res, needle) else "")
        shutil.rmtree(root, ignore_errors=True)

    # --- R22A.2.1 P0-B: evidence integrity against the exact Git tree -------
    PACK = "evidence/raw/r22a2-gfx1100-test"

    def commit_tree(root: Path, msg: str) -> None:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=root,
                       check=True, capture_output=True)

    def mk_p0b_root(mutator=None) -> Path:
        root = Path(tempfile.mkdtemp(prefix="vfix_p0b_"))
        build_good_tree(root)
        if mutator:
            mutator(root)
        return root

    p0b: list[tuple[str, Path, str]] = []

    def m_sums_missing_log(root: Path):
        (root / PACK / "runs" / "cold_run01_child.log").unlink()
        commit_tree(root, "drop raw log")
    p0b.append(("missing raw log in Git tree", mk_p0b_root(m_sums_missing_log),
                f"git-tree:sums:{PACK}/runs/cold_run01_child.log"))

    def m_sums_missing_source(root: Path):
        (root / PACK / "runs" / "child_sample_cold_run01.py").unlink()
        commit_tree(root, "drop source sample")
    p0b.append(("missing generated-source sample in Git tree",
                mk_p0b_root(m_sums_missing_source),
                f"git-tree:sums:{PACK}/runs/child_sample_cold_run01.py"))

    def m_manifest_entry_missing(root: Path):
        mp = root / "evidence" / "manifest.json"
        entries = json.loads(mp.read_text(encoding="utf-8"))
        mp.write_text(json.dumps(
            [e for e in entries if not e["path"].endswith("cold_run01_child.log")],
            indent=2), encoding="utf-8")
        commit_tree(root, "drop manifest entry")
    p0b.append(("committed evidence file without manifest entry",
                mk_p0b_root(m_manifest_entry_missing),
                f"git-tree:pack-complete:{PACK}/runs/cold_run01_child.log"))

    def m_hash_mismatch(root: Path):
        write(root / PACK / "R22A2_TEST.json", '{"ok": false, "tampered": true}\n')
        commit_tree(root, "tamper content")
    p0b.append(("committed file hash mismatch vs declared checksum",
                mk_p0b_root(m_hash_mismatch),
                f"git-tree:manifest:{PACK}/R22A2_TEST.json"))

    root_uncommitted = Path(tempfile.mkdtemp(prefix="vfix_uncommitted_"))
    build_good_tree(root_uncommitted, trap_uncommitted=True)
    p0b.append(("checksum matches only a local UNCOMMITTED file",
                root_uncommitted,
                f"git-tree:sums:{PACK}/runs/cold_run01_child.log"))

    # --- R22A.4 §8: manifest hygiene + r22a3*/r22a4* pack completeness -------
    def m_r22a3_unlisted(root: Path):
        pack3 = root / "evidence" / "raw" / "r22a3-gfx1151-test"
        (pack3 / "runs").mkdir(parents=True, exist_ok=True)
        (pack3 / "runs" / "child.log").write_bytes(b"raw child log\n")
        subprocess.run(["git", "add", "-f", str(pack3 / "runs" / "child.log")],
                       cwd=root, check=True, capture_output=True)
        commit_tree(root, "add r22a3 pack file without manifest entry")
    p0b.append(("committed r22a3* evidence file with no manifest entry",
                mk_p0b_root(m_r22a3_unlisted),
                "git-tree:pack-complete:evidence/raw/r22a3-gfx1151-test/runs/child.log"))

    def m_traversal(root: Path):
        mp = root / "evidence" / "manifest.json"
        entries = json.loads(mp.read_text(encoding="utf-8"))
        entries.append({"path": "../outside-repo.json", "timestamp": "t",
                        "command": "fixture", "sha256": "0" * 64, "size_bytes": 1})
        mp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        commit_tree(root, "manifest path traversal")
    p0b.append(("manifest path traversal outside the repository",
                mk_p0b_root(m_traversal), "git-tree:manifest-hygiene:../outside-repo.json"))

    def m_dup_conflict(root: Path):
        mp = root / "evidence" / "manifest.json"
        entries = json.loads(mp.read_text(encoding="utf-8"))
        dup = dict(next(e for e in entries if e["path"].endswith("R22A2_TEST.json")))
        dup["sha256"] = "f" * 64
        entries.append(dup)
        mp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        commit_tree(root, "duplicate conflicting manifest entry")
    p0b.append(("duplicate manifest entry with conflicting hash",
                mk_p0b_root(m_dup_conflict), "git-tree:manifest-dup:"))

    def m_self_referential(root: Path):
        import hashlib as _hl2
        mp = root / "evidence" / "manifest.json"
        entries = json.loads(mp.read_text(encoding="utf-8"))
        entries.append({"path": "evidence/manifest.json", "timestamp": "t",
                        "command": "fixture",
                        "sha256": _hl2.sha256(mp.read_bytes()).hexdigest(),
                        "size_bytes": len(mp.read_bytes())})
        mp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        commit_tree(root, "self-referential manifest entry")
    p0b.append(("manifest lists ITSELF (self-referential hash requirement)",
                mk_p0b_root(m_self_referential),
                "git-tree:manifest-hygiene:evidence/manifest.json"))

    for name, root, needle in p0b:
        rc, res = run_verifier(root)
        rejected = rc != 0 and res.get("ok") is False
        check(f"REJECTS: {name}", rejected and has_violation(res, needle),
              f"rc={rc} violations={[v for v in res.get('violations', []) if 'git-tree' in v]}")
        shutil.rmtree(root, ignore_errors=True)

    shutil.rmtree(good_root, ignore_errors=True)

    print(f"SUMMARY {PASS}/{PASS + FAIL} checks PASS")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
