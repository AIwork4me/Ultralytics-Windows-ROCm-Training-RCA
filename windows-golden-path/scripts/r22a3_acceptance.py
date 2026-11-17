# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.3 combined acceptance CLI — COMPATIBILITY WRAPPER (R22A.4 §7).

The implementation now lives in supplemental_acceptance.py (ONE shared
verdict engine for gfx1100 and gfx1151). The R22A.3 fail-open defect —
`part_b.get("workers8_overall") or overall_workers8_verdict(...)` trusting a
stored serialized verdict — is gone: the wrapper ALWAYS recomputes Part B
from the frozen runs[] facts through the unified strict matrix contract.

Behaviour note: under the unified contract the ORIGINAL five-run gfx1151
matrix derives as 2 COLD + 1 CACHE_PRIMING + 2 WARM (the frozen receipts did
not distinguish the priming first-use of the shared warm home), so this
wrapper reports NO-GO for the original receipt alone. The qualifying
2 COLD + 3 WARM composition is established by the R22A.4 reconciliation with
the additional justified warm sample — see
supplemental_acceptance.py --arch gfx1151 --additional-runs ... and
docs/release-closure/R22A4_DUAL_ARCH_SUPPLEMENTAL_RECONCILIATION.md.

    python r22a3_acceptance.py --part-a R22A3_ADAMW_AMP.json \
        --part-b R22A3_WORKERS8_RUNS.json --out R22A3_ACCEPTANCE_REPORT.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402
import supplemental_acceptance as sa  # noqa: E402


def combined_verdict(part_a: dict, part_b: dict | list, repo_root: Path) -> dict:
    """Recompute from embedded facts of BOTH records; claimed verdicts are
    inputs only, never authority (R22A.4 §5 fix of the stored-PASS bypass).
    part_b accepts either the full receipt dict (R22A3_WORKERS8.json) or the
    bare runs[] list (R22A3_WORKERS8_RUNS.json — the documented CLI example;
    gpu_name then falls back to the Part A record)."""
    runs = sa.runs_from_r22a3_receipt(
        part_b, repo_root,
        lifecycle_path=repo_root / "evidence/raw/r22a3-gfx1151/R22A3_PROCESS_LIFECYCLE.json")
    gpu_b = part_b.get("gpu_name") if isinstance(part_b, dict) else None
    return sa.combined_verdict(part_a, runs, "gfx1151", gpu_b)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part-a", required=True)
    ap.add_argument("--part-b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="R22A3-ACCEPT")
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    part_a = json.loads(Path(args.part_a).read_text(encoding="utf-8"))
    part_b = json.loads(Path(args.part_b).read_text(encoding="utf-8"))
    c = combined_verdict(part_a, part_b, repo_root)
    report = {
        "run_id": args.run_id, "mission": "R22A.3", "timestamp": gp_lib.now_utc(),
        "part_a_record": str(args.part_a), "part_b_record": str(args.part_b),
        "combined": c,
        "pass_fail_skip": c["verdict"],
        "failure_classification": (c["reasons"][0] if c["reasons"] else None),
        "note": "combined verdict recomputed from embedded facts of both evidence "
                "records via the R22A.4 unified engine; claimed verdicts are "
                "inputs only, never authority; the serialized workers8_overall "
                "field is deliberately not consulted",
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                         default=repr), encoding="utf-8")
    print(json.dumps(c, indent=2, default=repr))
    sys.exit(0 if c["verdict"] == "R22A3_GFX1151_SUPPLEMENTAL_PASS" else 1)


if __name__ == "__main__":
    main()
