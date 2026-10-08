"""Phase 4 / Gate P57 - evidence manifest + security scan for the RCA repo.

Manifest: SHA256 + size + provenance for every file under docs/phase4,
evidence/phase4, findings/phase4, patches/phase4, scripts/phase4.
Security scan: pattern sweep for secrets/tokens/credentials/absolute
home paths in the phase-4 text artifacts (informational; no secrets
expected in evidence paths, which are intentionally absolute).
"""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")
ROOTS = [RCA / "docs" / "phase4", RCA / "evidence" / "phase4",
         RCA / "findings" / "phase4", RCA / "patches" / "phase4",
         RCA / "scripts" / "phase4"]

SECRET_PATTERNS = [
    (r"github_pat_[A-Za-z0-9_]{20,}", "github PAT"),
    (r"ghp_[A-Za-z0-9]{30,}", "github token"),
    (r"gho_[A-Za-z0-9]{30,}", "github oauth"),
    (r"AKIA[0-9A-Z]{16}", "AWS key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "slack token"),
    (r"eyJhbGciOi[A-Za-z0-9._-]{30,}", "JWT"),
    (r"(?i)password\s*[:=]\s*\S{6,}", "password literal"),
    (r"(?i)api[_-]?key\s*[:=]\s*\S{12,}", "api key literal"),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    entries = []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and ".git" not in p.parts:
                entries.append({
                    "path": p.relative_to(RCA).as_posix(),
                    "size_bytes": p.stat().st_size,
                    "sha256": sha256(p),
                })

    findings = []
    for e in entries:
        p = RCA / e["path"]
        if p.suffix.lower() in {".json", ".md", ".txt", ".py", ".cpp", ".cmake",
                                ".patch", ".log"}:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat, label in SECRET_PATTERNS:
                for m in re.finditer(pat, text):
                    findings.append({"path": e["path"], "type": label,
                                     "match": m.group(0)[:12] + "..."})

    manifest = {
        "schema": "phase4_evidence_manifest_v1",
        "gate": "P57",
        "timestamp": datetime.now().isoformat(),
        "generator": "scripts/phase4/generate_manifest.py",
        "file_count": len(entries),
        "files": entries,
        "security_scan": {
            "patterns": [label for _, label in SECRET_PATTERNS],
            "findings": findings,
            "verdict": "CLEAN" if not findings else "REVIEW REQUIRED",
        },
        "provenance": {
            "producer": "Phase-4 Windows upstream submission preparation",
            "patch_id": "P3-FINAL-R3 (canonical reconstruction)",
            "canonical_commits": ["c86d1b95aacc35eed6b25e69ba659e1f6a133197",
                                   "4084759f3804748b7935d882db2d0445a3e0c380"],
            "base_source_sha": "b68f8944300f104875d953fc8e4510908c9aaf0b",
        },
    }
    out = RCA / "findings" / "phase4" / "evidence_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {len(entries)} files -> {out}")
    print(f"security scan: {manifest['security_scan']['verdict']}")
    for f in findings[:10]:
        print("  FINDING:", f)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
