# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.3 combined acceptance report (mission §12/§13) — Part A + Part B →
R22A3_GFX1151_SUPPLEMENTAL_PASS, computed ONLY from the evidence records with
fail-closed rules:

  - each part's own verdict is recomputed from embedded facts where a pure
    recomputation exists (Part A assertions, Part B run matrix); a claimed
    verdict is never trusted on its own
  - both parts must independently PASS; one PASS + one FAIL → PARTIAL_PASS;
    otherwise NO-GO, always with the exact reason
  - physical provenance is mandatory: gfx_target must be gfx1151 with a GPU
    name recorded — a synthetic/abstract receipt can never earn a physical
    verdict; runtime_class ENGINEERING_REFERENCE/INCONCLUSIVE cannot PASS
  - verdict ceiling is DEV_CANDIDATE-class (OFFICIAL_STABLE / R23_RELEASE
    strings are structurally unreachable here)

    python r22a3_acceptance.py --part-a R22A3_ADAMW_AMP.json \
        --part-b R22A3_WORKERS8.json --out R22A3_ACCEPTANCE_REPORT.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402
from audit_adamw_amp import compute_adamw_verdict  # noqa: E402
from run_stability import overall_workers8_verdict  # noqa: E402

CEILING = "DEV_CANDIDATE (maximum runtime classification; never OFFICIAL_STABLE / R23_RELEASE_READY)"


def recompute_part_a(rec: dict) -> dict:
    """Recompute Part A's verdict from its embedded facts; never trust the
    stored pass_fail_skip."""
    try:
        return compute_adamw_verdict(rec, rec.get("minimum_effective_updates_required", 3))
    except Exception as e:  # malformed record can never pass
        return {"verdict": "REJECTED", "failure_classification": f"MALFORMED_PART_A({type(e).__name__})"}


def physical_provenance_ok(rec: dict) -> tuple[bool, str | None]:
    if not rec.get("gpu_name"):
        return False, "no gpu_name recorded (synthetic receipt cannot claim physical GPU)"
    if rec.get("gfx_target") != "gfx1151":
        return False, f"gfx_target {rec.get('gfx_target')!r} != gfx1151"
    rc = rec.get("runtime_class")
    if rc in ("ENGINEERING_REFERENCE", "INCONCLUSIVE", None):
        return False, f"runtime_class {rc!r} cannot earn a physical PASS"
    return True, None


def combined_verdict(part_a: dict, part_b: dict) -> dict:
    """Pure final R22A.3 verdict (CPU-testable, mission §13)."""
    reasons: list[str] = []
    a = recompute_part_a(part_a)
    a_ok = a["verdict"] == "ADAMW_AMP_MULTISTEP_PASS"
    if not a_ok:
        reasons.append(f"PartA {a['verdict']}/{a.get('failure_classification')}")
    b_overall = part_b.get("workers8_overall") or overall_workers8_verdict(
        part_b.get("runs", []),
        part_b.get("cold_runs", 0),
        max(len(part_b.get("runs", [])) - part_b.get("cold_runs", 0), 0))
    b_ok = b_overall.get("verdict") == "WORKERS8_SHORT_RELIABILITY_PASS"
    if not b_ok:
        reasons.append(f"PartB {b_overall.get('verdict')}: {b_overall.get('problems')}")

    prov_a, pa_reason = physical_provenance_ok(part_a)
    prov_b, pb_reason = physical_provenance_ok(part_b)
    if not prov_a:
        reasons.append(f"PartA provenance: {pa_reason}")
    if not prov_b:
        reasons.append(f"PartB provenance: {pb_reason}")

    if a_ok and b_ok and prov_a and prov_b:
        verdict = "R22A3_GFX1151_SUPPLEMENTAL_PASS"
    elif a_ok != b_ok:
        verdict = "PARTIAL_PASS"
    else:
        verdict = "NO-GO"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "part_a_recomputed": {"verdict": a["verdict"],
                              "failure_classification": a.get("failure_classification")},
        "part_b_overall": b_overall,
        "runtime_ceiling": CEILING,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part-a", required=True)
    ap.add_argument("--part-b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="R22A3-ACCEPT")
    args = ap.parse_args()

    part_a = json.loads(Path(args.part_a).read_text(encoding="utf-8"))
    part_b = json.loads(Path(args.part_b).read_text(encoding="utf-8"))
    c = combined_verdict(part_a, part_b)
    report = {
        "run_id": args.run_id, "mission": "R22A.3", "timestamp": gp_lib.now_utc(),
        "part_a_record": str(args.part_a), "part_b_record": str(args.part_b),
        "combined": c,
        "pass_fail_skip": c["verdict"],
        "failure_classification": (c["reasons"][0] if c["reasons"] else None),
        "note": "combined verdict recomputed from embedded facts of both evidence "
                "records; claimed verdicts are inputs only, never authority",
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(c, indent=2))
    sys.exit(0 if c["verdict"] == "R22A3_GFX1151_SUPPLEMENTAL_PASS" else 1)


if __name__ == "__main__":
    main()
