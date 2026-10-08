#!/usr/bin/env python3
"""Phase 4 / Gate P44 - extract validated commit messages from the two
Phase-3 patch blobs and emit provisional commit-message files.

Rules:
- Subject and body text are taken verbatim from the validated patch
  envelopes (these texts were reviewed in Phase 3 PR drafts).
- The placeholder trailer
    'Signed-off-by: <AUTHOR NAME> <author@example.com>  # DCO: fill in before submission'
  is replaced by an explicit DCO-pending marker. No Signed-off-by is
  fabricated.
- Envelope noise (From/Date/Subject header lines, '---', diffstat, diff,
  trailing '--\n2.x.y') is dropped.
"""

import re
import subprocess
import sys
from pathlib import Path

RCA = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA")
OUT_DIR = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\phase4_work\commit_messages")

PLACEHOLDER_SOB = re.compile(
    r"^Signed-off-by: <AUTHOR NAME> <author@example\.com>.*$",
    re.MULTILINE,
)
DCO_MARKER = (
    "DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for "
    "upstream submission; replace this line with a real Signed-off-by per "
    "DCO before submitting."
)


def blob(path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(RCA), "cat-file", "blob", f"origin/main:{path}"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace"))
    return proc.stdout


def extract_message(patch_text: str) -> str:
    # Drop mail header block: everything up to and including the Subject line.
    m = re.search(r"^Subject: \[PATCH \d+/\d+\] (.*)$", patch_text, re.MULTILINE)
    if not m:
        raise RuntimeError("Subject line not found")
    subject = m.group(1).strip()

    rest = patch_text[m.end():]
    # Body runs until the '---' diff separator at line start.
    sep = rest.find("\n---\n")
    if sep == -1:
        # fallback: until first 'diff --git'
        sep = rest.find("\ndiff --git ")
    body = rest[:sep].strip("\n")

    msg = subject + "\n\n" + body + "\n"
    msg, n = PLACEHOLDER_SOB.subn(DCO_MARKER, msg)
    if n != 1:
        raise RuntimeError(f"expected exactly one placeholder Signed-off-by, found {n}")
    return msg


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, name in [
        ("patches/phase3/0001-miopen-hiprtc-selfcontained.patch", "commit1.msg"),
        ("patches/phase3/0002-miopen-hiprtc-selfcontained.patch", "commit2.msg"),
    ]:
        text = blob(path).decode("utf-8")
        msg = extract_message(text)
        out = OUT_DIR / name
        out.write_bytes(msg.encode("utf-8"))
        print(f"wrote {out} ({len(msg)} bytes)")
        print("  subject:", msg.splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
