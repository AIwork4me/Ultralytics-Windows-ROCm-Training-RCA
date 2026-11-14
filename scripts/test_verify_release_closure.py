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


def build_good_tree(root: Path) -> None:
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
    rc, res = run_verifier(good_tree)
    check("known-good synthetic tree ACCEPTED (exit 0)",
          rc == 0 and res["ok"] is True, json.dumps(res.get("violations", [])))

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
    shutil.rmtree(good_root, ignore_errors=True)

    print(f"SUMMARY {PASS}/{PASS + FAIL} checks PASS")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
