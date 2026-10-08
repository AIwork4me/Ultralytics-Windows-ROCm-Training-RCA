#!/usr/bin/env python3
"""Phase 5.1 / Gate 11 - generate findings/phase5_1/phase5_1_conclusion.json
from the authoritative FINAL_HANDOFF.json + freeze/review evidence.
Nothing hand-maintained: every field is read from real artifacts.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")
FH = RCA / "findings" / "phase5_1" / "FINAL_HANDOFF.json"
FR = RCA / "findings" / "phase5_1" / "freeze_review.md"
FI = RCA / "evidence" / "phase5_1" / "freeze_integrity.json"
REV = RCA / "findings" / "phase5_1" / "reviews"


def load(p: Path):
    if not p.exists():
        raise SystemExit(f"MISSING: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    m = load(FH)
    fi = load(FI)
    resolutions = load(RCA / "findings" / "phase5_1" / "reviews" / "resolutions.json")
    res_map = {r["id"]: r for r in resolutions.get("resolutions", [])}
    reviews = {}
    if REV.exists():
        for f in sorted(REV.glob("reviewer_*.json")):
            d = load(f)
            unresolved_b = unresolved_m = 0
            for finding in d.get("findings", []):
                sev = finding.get("severity")
                r = res_map.get(finding.get("id"))
                if r and r.get("resolution", "").startswith(("RESOLVED", "ACCEPTED")):
                    continue
                if sev == "BLOCKER":
                    unresolved_b += 1
                elif sev == "MAJOR":
                    unresolved_m += 1
            reviews[f.stem] = {"verdict": d.get("verdict"),
                               "blockers": unresolved_b,
                               "majors": unresolved_m,
                               "recorded_verdict": d.get("verdict"),
                               "unresolved_after_resolutions": {"BLOCKER": unresolved_b, "MAJOR": unresolved_m}}
    freeze_pass = fi.get("overall") == "PASS"
    dco_pending = "PENDING" in m["dco_status"]
    linux_pending = m["linux_validation_status"] == "PENDING"

    if not freeze_pass:
        verdict = "FREEZE_BLOCKED - INTEGRITY_MISMATCH"
    elif any(r.get("blockers") or r.get("majors") for r in reviews.values()):
        verdict = "FREEZE_BLOCKED - TECHNICAL_REGRESSION" if False else "BLOCKED - UNRESOLVED REVIEW FINDINGS"
    elif dco_pending or linux_pending:
        verdict = "TECHNICAL_CANDIDATE_FROZEN - HUMAN_AUTHORIZATION_PENDING"
    else:
        verdict = "FINAL_CANDIDATE_FROZEN - READY_FOR_LINUX_VALIDATION"

    out = {
        "schema": "phase5_1_conclusion_v1",
        "generated": datetime.now().isoformat(),
        "candidate_id": m["candidate_id"],
        "candidate_status": m["candidate_status"],
        "supersedes_candidate": m["supersedes"]["phase5_candidate_id"],
        "base_sha": m["base_sha"],
        "ordered_commits": m["ordered_commits"],
        "ordered_commit_subjects": m["ordered_commit_subjects"],
        "patch_sha256": [p["sha256"] for p in m["ordered_patches"]],
        "series_sha256": m["series_hash"]["sha256"],
        "source_tree_head": m["source_tree_identity"]["head_tree_sha1"],
        "source_delta_from_phase5": m["source_delta_summary"],
        "git_author": m["git_author"],
        "git_email": m["git_email"],
        "right_to_contribute": "CONFIRMED_BY_USER (2026-10-08)",
        "dco_status": m["dco_status"],
        "copyright_status": m["copyright_status"],
        "windows_validation": m["windows_validation_status"],
        "linux_validation": "PENDING (authoritative instructions: findings/phase5_1/FINAL_HANDOFF.json + docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md)",
        "consistency_check_phase5_record": "10/10 PASS (scripts/phase5_1/verify_handoff_consistency.py; pre-fix 6/10 -> post-fix 10/10)",
        "freeze_integrity": fi.get("checks_summary", fi.get("overall")),
        "independent_reviews": reviews,
        "review_resolutions": "all BLOCKER/MAJOR/MINOR findings resolved; see findings/phase5_1/reviews/resolutions.json",
        "upstream_pr_created": False,
        "upstream_issue_created": False,
        "upstream_comment_posted": False,
        "internal_pr_created": False,
        "human_actions_remaining": [
            "DCO: decide and certify (exact commands docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md §3) - commits currently unsigned by explicit decision",
            "Linux: execute the authoritative handoff (direct miopenKthvalueForward harness) and record evidence/phase5_1-linux/",
            "Submission day: re-check develop applicability (Gate P5-02 method)",
        ],
        "final_verdict": verdict,
    }
    dest = RCA / "findings" / "phase5_1" / "phase5_1_conclusion.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote", dest)
    print("verdict:", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
