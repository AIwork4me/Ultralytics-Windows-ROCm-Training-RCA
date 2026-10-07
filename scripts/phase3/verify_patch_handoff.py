"""Deterministic verifier for findings/phase3/PATCH_HANDOFF.json.

Recomputes the canonical identities from Git blob bytes and compares them
to the handoff metadata. Ref argument defaults to HEAD; pass a branch or
commit (e.g. origin/main) to verify a published state.

Algorithm (sha256_git_blob_concat_v1):
  - individual hash: SHA256(exact `git cat-file blob <ref>:<path>` bytes)
  - series hash:     SHA256(blob bytes of patch order 1 || blob bytes of
                     patch order 2)  — no separator, no transformation

Exit 0 = HANDOFF VALID; nonzero on any mismatch.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys

EXPECTED_SOURCE_SHA = "b68f8944300f104875d953fc8e4510908c9aaf0b"
HANDOFF_PATH = "findings/phase3/PATCH_HANDOFF.json"


def blob(ref: str, path: str) -> bytes:
    return subprocess.check_output(["git", "cat-file", "blob", f"{ref}:{path}"])


def load_handoff(ref: str) -> tuple[dict, str]:
    """Read handoff JSON from Git blobs; before the first commit of the
    handoff itself, fall back to the working-tree copy (patch hashes stay
    blob-authoritative either way)."""
    try:
        return json.loads(blob(ref, HANDOFF_PATH).decode("utf-8")), f"git-blob:{ref}"
    except subprocess.CalledProcessError:
        if ref == "HEAD":
            with open(HANDOFF_PATH, "rb") as f:
                return json.loads(f.read().decode("utf-8")), "working-tree"
        raise


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    handoff, handoff_src = load_handoff(ref)
    print(f"HANDOFF SOURCE: {handoff_src}")

    entries = sorted(handoff["patch_series"], key=lambda e: e["order"])
    series = b""
    ok = True
    for i, entry in enumerate(entries, start=1):
        data = blob(ref, entry["path"])
        sha = hashlib.sha256(data).hexdigest()
        match = sha == entry["sha256"]
        ok &= match
        print(f"PATCH {i} SHA256 {'MATCH' if match else 'MISMATCH: ' + sha}")
        series += data

    series_sha = hashlib.sha256(series).hexdigest()
    series_match = series_sha == handoff["series_hash"]["sha256"]
    ok &= series_match
    print(f"SERIES SHA256 {'MATCH' if series_match else 'MISMATCH: ' + series_sha}")

    algo_ok = handoff["series_hash"]["algorithm"] == "sha256_git_blob_concat_v1"
    ok &= algo_ok
    print(f"SERIES ALGORITHM {'OK' if algo_ok else 'UNEXPECTED'}")

    src = handoff["source"]["sha"]
    src_ok = src == EXPECTED_SOURCE_SHA and bool(re.fullmatch(r"[0-9a-f]{40}", src))
    ok &= src_ok
    print(f"SOURCE SHA FORMAT {'OK' if src_ok else 'BAD'}")

    cc = handoff["consumer_contract"]
    cc_ok = (cc["patch_mutation_allowed"] is False
             and cc["source_sha_must_match"] is True
             and cc["individual_patch_sha256_must_match"] is True
             and cc["series_sha256_must_match"] is True)
    ok &= cc_ok
    print(f"CONSUMER CONTRACT {'OK' if cc_ok else 'VIOLATION'}")

    us = handoff["upstream_state"]
    us_ok = all(us[k] is False for k in ("pr_created", "issue_created", "comment_posted"))
    ok &= us_ok
    print(f"UPSTREAM STATE {'OK' if us_ok else 'VIOLATION'}")

    print("HANDOFF VALID" if ok else "HANDOFF INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
