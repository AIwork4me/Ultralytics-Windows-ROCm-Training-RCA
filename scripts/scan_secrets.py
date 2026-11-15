"""Scan repository working-tree text files for secret-like patterns.

Background: P9-era environment snapshots embedded live env vars (incl. ZHIPU_API_KEY)
into raw evidence JSONs that were pushed to the public RCA repo (found during P14.0,
redacted in the P14 secret-scan commit). This scanner is the regression guard so no
future evidence file ships a secret again.

Run:  python scripts/scan_secrets.py            # scan, exit 0 clean / 1 findings
      python scripts/scan_secrets.py --redact   # additionally redact findings in place

Pure stdlib; skips .git/__pycache__; only scans text extensions.
Secret-looking JWTs inside expired pre-signed artifact URLs are also flagged.
"""
import re
import sys
from pathlib import Path

# value patterns: (name, regex, replacement)
PATTERNS = [
    ("zhipu_api_key_value", re.compile(r"([\"']?ZHIPU_API_KEY[\"']?\s*[:=]\s*[\"']?)([A-Za-z0-9._\-]{16,})([\"']?)"), r"\g<1>[REDACTED]\g<3>"),
    ("generic_api_key_value", re.compile(r"([\"']?(?:OPENAI|ANTHROPIC|DEEPSEEK|ZHIPU|GLM|MOONSHOT|QWEN|DASHSCOPE)[_A-Z0-9]*API[_]?KEY[_A-Z0-9]*[\"']?\s*[:=]\s*[\"']?)([A-Za-z0-9._\-]{16,})([\"']?)", re.IGNORECASE), r"\g<1>[REDACTED]\g<3>"),
    ("openai_sk", re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED]"),
    ("github_pat", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED]"),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED]"),
    ("bearer_token", re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"), r"\g<1>[REDACTED]"),
    ("jwt_in_url", re.compile(r"(jwt=)eyJ[A-Za-z0-9._\-]{40,}"), r"\g<1>[REDACTED_EXPIRED_URL_TOKEN]"),
]

TEXT_EXTS = {".json", ".md", ".py", ".log", ".txt", ".yaml", ".yml", ".sh", ".cfg", ".toml"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}


def iter_text_files(root: Path):
    for dirpath, dirnames, filenames in os_walk(root):
        for fn in filenames:
            p = dirpath / fn
            if p.suffix.lower() in TEXT_EXTS:
                yield p


def os_walk(root: Path):
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        yield dp, dirnames, filenames


def main() -> int:
    redact = "--redact" in sys.argv
    root = Path(__file__).resolve().parent.parent
    findings = []
    for p in iter_text_files(root):
        try:
            s = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pat, repl in PATTERNS:
            matches = list(pat.finditer(s))
            if not matches:
                continue
            for m in matches:
                findings.append((name, str(p.relative_to(root)), m.group(0)[:40]))
            if redact:
                p.write_text(pat.sub(repl, s), encoding="utf-8", errors="replace", newline="")
    if findings:
        for name, rel, sample in findings:
            print(f"[FINDING] {name} {rel} :: {sample[:24]}…")
        print(f"TOTAL: {len(findings)} finding(s) in {len({f[1] for f in findings})} file(s)")
        return 1
    print("CLEAN: no secret-like patterns in tracked text files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
