#!/usr/bin/env python3
"""Generate WRAPPERS_MANIFEST.json for phase 5.2.1 wrappers (reproducibility).

Records, for every runtime/build wrapper published under
linux-w7900/phase5.2.1/wrappers/, its sha256, size, mode, and provenance
against previously published copies:
  - origin/main            -> linux-w7900/preflight/scripts/<relpath>
  - phase 5.2 branch merge -> linux-w7900/phase5_2/scripts/<basename>

An IDENTICAL match against any published copy wins the classification;
otherwise the newest published copy is recorded as superseded.

Output: linux-w7900/phase5.2.1/wrappers/WRAPPERS_MANIFEST.json
Exit 0 on success; nonzero if a wrapper file is missing or unreadable.
"""
import hashlib
import json
import os
import subprocess
import sys

REPO = os.environ.get(
    "RCA_REPO_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
WRAP_DIR = os.path.join(REPO, "linux-w7900", "phase5.2.1", "wrappers")
PHASE52_REF = "origin/linux-w7900/phase5.2-handoff-bridge"

# relpath inside wrappers/ -> candidate published locations (label, ref, path)
def candidates(rel):
    base = os.path.basename(rel)
    out = [("preflight_scripts", "origin/main", f"linux-w7900/preflight/scripts/{rel}")]
    out.append(("phase5_2_scripts", PHASE52_REF, f"linux-w7900/phase5_2/scripts/{base}"))
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def published_blob(ref, path):
    try:
        blob = subprocess.run(
            ["git", "-C", REPO, "show", f"{ref}:{path}"],
            capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None
    return {"sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob)}


def main():
    entries = []
    for root, dirs, files in os.walk(WRAP_DIR):
        dirs.sort()
        for name in sorted(files):
            if name == "WRAPPERS_MANIFEST.json":
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, WRAP_DIR)
            cur_sha = sha256_file(full)
            cur_size = os.path.getsize(full)
            identical = None
            superseded = None
            for label, ref, pubpath in candidates(rel):
                pub = published_blob(ref, pubpath)
                if pub is None:
                    continue
                if pub["sha256"] == cur_sha:
                    identical = {"status": "IDENTICAL_TO_PUBLISHED",
                                 "matches": label, "published_path": pubpath}
                    break
                if superseded is None:
                    superseded = {"status": "SUPERSEDES_PUBLISHED",
                                  "published_copy": label,
                                  "published_path": pubpath,
                                  "published_sha256": pub["sha256"],
                                  "note": ("local version is the exact operative version; "
                                           "drift documented in phase 5.2 reviews/resolutions")}
            prov = identical or superseded or {
                "status": "UNPUBLISHED_PREVIOUSLY",
                "note": ("convenience wrapper local to the validation machine workspace root; "
                         "published here verbatim for reproducibility")
                if rel.startswith("workspace-root") else
                "first publication in this manifest"}
            entries.append({
                "path": f"linux-w7900/phase5.2.1/wrappers/{rel}",
                "sha256": cur_sha,
                "size": cur_size,
                "executable": bool(os.stat(full).st_mode & 0o111),
                "provenance": prov,
            })
    manifest = {
        "schema": "wrappers-manifest/1.0",
        "purpose": ("exact operative versions of all locally modified runtime/build "
                    "wrappers at phase 5.2.1 closure"),
        "count": len(entries),
        "wrappers": entries,
    }
    out = os.path.join(WRAP_DIR, "WRAPPERS_MANIFEST.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"wrote {out} ({len(entries)} wrappers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
