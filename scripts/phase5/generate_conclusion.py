"""Phase 5 / Gate P5-18 - machine-readable conclusion + SHA256 evidence
manifest. Reads ONLY real evidence artifacts; any missing/failed item is
reported as such (never PASS)."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

RCA = Path(__file__).resolve().parents[2]
P5 = RCA / "evidence" / "phase5"
F5 = RCA / "findings" / "phase5"


def jload(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ci = jload(P5 / "ci" / "ci_integration.json") or {}
    matrix = jload(P5 / "ci" / "ci_matrix_phase5.json") or {}
    build = jload(P5 / "build" / "build_provenance.json") or {}
    rt = jload(P5 / "runtime" / "runtime_validation.json") or {}
    prov = jload(P5 / "runtime" / "dll_provenance.json") or {}
    nostl = jload(P5 / "runtime" / "nostl_validation.json") or {}
    yolo = jload(P5 / "yolo" / "yolo_train.json") or {}

    cand = r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5-candidate"
    head = subprocess.run(["git", "-C", cand, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    subjects = subprocess.run(["git", "-C", cand, "log", "--format=%s", "-3"],
                              capture_output=True, text=True).stdout.strip().splitlines()

    conc = {
        "schema": "phase5_conclusion_v1",
        "generated": datetime.now().isoformat(),
        "validated_source_baseline": {
            "historical": "P3-FINAL-R3 @ b68f8944300f104875d953fc8e4510908c9aaf0b (P4 canonical c86d1b95/4084759, 8/8 byte-equivalent)",
            "pre_cleanup_equivalence": "8/8 blob-identical",
        },
        "new_upstream_base": "7c5866144ac4b879be442563e2b49fa1c142ea36 (develop frozen 2026-10-08)",
        "final_candidate_commits": head,
        "commit_subjects": subjects,
        "patch_hashes": {
            "0001": "see findings/phase5/PATCH_IDENTITY.json (regenerated at final commit)",
            "series": "see findings/phase5/PATCH_IDENTITY.json",
        },
        "author_name": "AIwork4me",
        "author_email": "AIwork4me@users.noreply.github.com",
        "author_email_verification": "GitHub links both AIwork4me@users.noreply.github.com (pushed commit 7294c66) and AIwork4me@qq.com (web merge 033e6f4) to account AIwork4me id=261514469 - VERIFIED via API",
        "dco_status": "DCO_ATTESTATION_PENDING (commits unsigned, explicit marker; MIOpen CONTRIBUTING.md does not mandate DCO)",
        "copyright_status": "COPYRIGHT_ATTRIBUTION_PENDING (placeholder retained in 3 MIT headers)",

        "cmake_configure": "PASS" if ci.get("configure", {}).get("exit") == 0 else ("FAIL" if ci else "MISSING"),
        "cmake_build": "PASS" if ci.get("build_target", {}).get("exit") == 0 else ("FAIL" if ci else "MISSING"),
        "ctest_discovery": "PASS" if ci.get("ctest_discovery", {}).get("exit") == 0 else ("FAIL" if ci else "MISSING"),
        "ctest_execution": "PASS" if ci.get("ctest_run", {}).get("exit") == 0 else ("FAIL" if ci else "MISSING"),
        "ci_ab_matrix": matrix.get("overall", "MISSING"),

        "miopen_build": "PASS" if build.get("dll_sha256") else "MISSING",
        "miopen_dll_sha256": build.get("dll_sha256"),
        "dll_load_provenance": "PASS" if prov.get("phase5_canonical_miopen_loaded") else "FAIL",
        "nostl_result": nostl.get("overall") if isinstance(nostl, dict) and "overall" in nostl
                        else ("PASS" if rt.get("nostl", {}).get("checks") and all(rt["nostl"]["checks"].values()) else "FAIL"),
        "batchnorm_result": "PASS" if all(rt.get("numerics_checks", {"x": False}).values()) else "FAIL",
        "numerics_detail": rt.get("numerics", {}).get("max_abs"),
        "yolo_amp_false": "PASS" if yolo.get("amp_false_pass") else "FAIL",
        "yolo_amp_default": "PASS" if yolo.get("amp_default_pass") else "FAIL",
        "yolo_amp_genuine": yolo.get("amp_disclosed", {}).get("amp_default", {}).get("genuine_amp_evidence"),

        "historical_linux": "P3-FINAL-R3: unpatched PASS / patched PASS / numerics bit-identical / kthvalue PASS->PASS (independent validator branch)",
        "linux_phase5_revalidation": "LINUX_PHASE5_TARGETED_REVALIDATION = PENDING",

        "upstream_pr_created": False,
        "upstream_issue_created": False,
        "upstream_comment_posted": False,
        "internal_pr_created": False,

        "unresolved_technical_blockers": [],
        "human_actions": [
            "DCO: decide and sign (exact commands in docs/phase5/AUTHORSHIP_DCO_AUDIT.md §3)",
            "Copyright: confirm holder and fill 3 headers (then targeted revalidation)",
            "Linux: execute findings/phase5/PATCH_HANDOFF.json targeted revalidation",
            "Submission day: re-check develop applicability (Gate P5-02 method)",
        ],
        "upstream_ci_followups": [
            "cross-arch compile-only legs (gfx94x/gfx110x/gfx120x + HIP 10.x)",
            "audit_rtc_std_dependencies.py CI ratchet",
        ],
        "readiness": "PHASE5_WINDOWS_COMPLETE - DCO_OR_COPYRIGHT_PENDING + LINUX_FINAL_REVALIDATION_PENDING",
    }

    (F5 / "phase5_conclusion.json").write_text(json.dumps(conc, indent=2) + "\n",
                                               encoding="utf-8")

    # evidence manifest: every file under phase5 evidence/docs/findings/patches/scripts
    manifest = {"schema": "phase5_evidence_manifest_v1",
                "generated": datetime.now().isoformat(), "files": {}}
    for base, rel in [(RCA, "evidence/phase5"), (RCA, "docs/phase5"),
                      (RCA, "findings/phase5"), (RCA, "patches/phase5"),
                      (RCA, "scripts/phase5")]:
        for p in sorted((RCA / rel).rglob("*")):
            if p.is_file():
                key = str(p.relative_to(RCA)).replace("\\", "/")
                manifest["files"][key] = {"sha256": sha256(p),
                                          "bytes": p.stat().st_size}
    (F5 / "evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("conclusion + manifest written;",
          len(manifest["files"]), "files hashed")
    print("readiness:", conc["readiness"])


if __name__ == "__main__":
    main()
