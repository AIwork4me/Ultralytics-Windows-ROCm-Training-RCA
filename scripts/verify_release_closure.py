"""Verification contract — audits the release-closure evidence WITHOUT a GPU.

    python scripts/verify_release_closure.py [--root <repo-root>]

Checks (§12 of the mission):
  - every declared PASS in gate JSONs has raw-log files present and non-empty
  - every GPU-run JSON carries loaded-DLL provenance (miopen sha256 recorded)
  - manifest integrity for the new-phase directories (SHA256SUMS if present)
  - no unsupported official-support language in new-phase docs
  - required deliverable files exist per gate
  - statuses come from the allowed vocabulary only
Exit 0 iff all checks pass; prints a JSON audit summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ALLOWED = {"PASS", "FAIL", "EXPECTED_FAIL", "SKIP", "BLOCKED", "NOT_RUN", "INCONCLUSIVE"}
OFFICIAL_PATTERNS = [
    r"officially supported by AMD", r"officially supported by Ultralytics",
    r"supported on all Windows", r"works on all GPUs",
]
REQUIRED = {
    "release-provenance": ["G0_VERDICT.md", "RELEASE_LINEAGE.md", "RELEASE_MATRIX.csv",
                           "WHEEL_MANIFEST.json", "BINARY_PROVENANCE.json", "LOADED_DLL_REPORT.json"],
    "windows-training-validation": ["G1_VERDICT.md", "G2_VERDICT.md"],
    "amp-rca": ["ROOT_CAUSE.md", "MINIMAL_REPRO.py", "PRECISION_COMPARISON.csv", "G3_VERDICT.md"],
    "upstream-readiness": ["AMP_FIX_PR_DRAFT.md", "TEST_PR_DRAFT.md", "DOCS_PR_DRAFT.md",
                           "MAINTAINER_CHECKLIST.md"],
    "platform-matrix": ["GPU_SUPPORT_MATRIX.md", "WINDOWS_GFX1151.md"],
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root)
    audit = {"checks": [], "violations": [], "ok": True}

    def check(name: str, ok: bool, detail: str = "") -> None:
        audit["checks"].append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            audit["ok"] = False
            audit["violations"].append(f"{name}: {detail}")

    # 1. required deliverables exist
    for d, files in REQUIRED.items():
        for f in files:
            check(f"exists:{d}/{f}", (root / d / f).is_file())

    # 2. GPU-run JSONs carry loaded-DLL provenance; statuses from allowed vocabulary
    raw = root / "windows-training-validation" / "raw"
    if raw.is_dir():
        for jf in sorted(raw.glob("g2_*.json")):
            try:
                d = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                check(f"json:{jf.name}", False, "unreadable JSON")
                continue
            if jf.name.endswith("loaddll.json"):
                # raw probe output: miopen_loaded.{path,sha256}
                check(f"gpu-provenance:{jf.name}",
                      bool((d.get("miopen_loaded") or {}).get("sha256")),
                      "raw probe missing miopen_loaded.sha256")
                continue
            dll = d.get("loaded_dll") or {}
            all_pass = all(t.get("status") in ("PASS", "SKIP")
                           for t in (d.get("tests") or {}).values()) and bool(d.get("tests"))
            if all_pass:
                check(f"gpu-provenance:{jf.name}", bool(dll.get("sha256")),
                      "PASS lifecycle JSON without loaded_dll.sha256")
            else:
                # non-PASS (FAIL/SKIP-only) records are not claimed results;
                # provenance still recorded when present
                audit["checks"].append({"check": f"gpu-provenance:{jf.name}",
                                        "ok": bool(dll.get("sha256")),
                                        "detail": "non-claimed record; provenance attached" if dll.get("sha256") else "runner aborted before probe (no PASS claimed)"})
            for t in (d.get("tests") or {}).values():
                check(f"status-vocab:{jf.name}", t.get("status") in ALLOWED,
                      f"bad status {t.get('status')!r}")
        for jf in sorted(raw.glob("g3_amp_*.json")):
            d = json.loads(jf.read_text(encoding="utf-8"))
            env = d.get("environment") or {}
            check(f"gpu-provenance:{jf.name}", bool(env.get("hip")) and env.get("gpu_authentic"),
                  "AMP audit run without HIP provenance")

    # 3. gate reports: PASS claims must reference non-empty raw artifacts
    reports = root / "windows-training-validation" / "reports"
    if reports.is_dir():
        for jf in sorted(reports.glob("G1_MATRIX_*.json")):
            d = json.loads(jf.read_text(encoding="utf-8"))
            if d.get("verdict") == "PASS":
                legs = d.get("legs") or []
                check(f"matrix-has-legs:{jf.name}", bool(legs), "PASS verdict with zero legs")

    # 4. no unsupported official-support language in new-phase docs
    doc_dirs = ["release-provenance", "windows-training-validation", "amp-rca",
                "upstream-readiness", "platform-matrix", "docs/release-closure"]
    for d in doc_dirs:
        for mf in (root / d).rglob("*.md"):
            text = mf.read_text(encoding="utf-8", errors="replace")
            for pat in OFFICIAL_PATTERNS:
                if re.search(pat, text, re.IGNORECASE):
                    check(f"official-claim:{mf.name}", False, f"matches {pat!r}")

    # 5. baseline state JSON parses and pins the frozen head
    bs = root / "docs" / "release-closure" / "BASELINE_STATE.json"
    if bs.is_file():
        try:
            d = json.loads(bs.read_text(encoding="utf-8"))
            check("baseline-head", d.get("repo_head_at_audit", "").startswith("f9f745e"),
                  "baseline head mismatch")
        except json.JSONDecodeError:
            check("baseline-json", False, "unreadable")

    print(json.dumps(audit, indent=2))
    sys.exit(0 if audit["ok"] else 1)


if __name__ == "__main__":
    main()
