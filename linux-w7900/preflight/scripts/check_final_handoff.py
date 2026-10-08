#!/usr/bin/env python3
"""Strict consumer for the future findings/phase5_1/FINAL_HANDOFF.json.

Modes:
  --check-only <manifest>   validate manifest + recompute every hash from
                            RAW BYTES. No source modification, no writes
                            outside a --json-out report.
  --apply <manifest> <dir>  reconstruct the patched tree in <dir> from a
                            clean git worktree + ordered patch application.
                            REFUSES unless ENABLE_APPLY=1 (the Phase-5.1
                            candidate is not frozen yet).

Hardened after the G08 adversarial audit:
  * ONE path-resolution routine for check-only AND apply (no root divergence)
  * path containment: relative paths only, no '..' escape, no absolute
    paths, no symlinks, regular files only
  * unlisted files in a patch directory are rejected (unexpected = reject)
  * hash_chain implemented exactly as documented in
    docs/FINAL_HANDOFF_CONSUMER.md
  * apply re-verifies each patch sha256 immediately before `git apply`

Hash discipline: every hash is computed with hashlib over raw bytes.
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

WS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.join(WS, "repos", "rocm-libraries")

STALE_REJECTED_COMMIT_PREFIXES = [
    "b68f8944300f104875d953fc8e4510908c9aaf0b",  # Phase-3 Linux source base
    "07959f8",                                     # Phase-3 run-1 blocked marker
    "013f6f005f97aca5ef46d841ca754f2283dc62f0",   # RCA main head at prep time
]

SUPPORTED_SERIES_MODES = ("concat_bytes", "hash_chain")
HASH_CHAIN_SEED = b"MIOpen-P5.1-series-v1\0"

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_patch_path(manifest_dir, rca_root, rel):
    """Single resolution routine used by check-only AND apply."""
    if os.path.isabs(rel) or rel.startswith("~"):
        fail(f"patch path must be relative: {rel!r}")
        return None
    root = rca_root if rca_root else manifest_dir
    p = os.path.normpath(os.path.join(root, rel))
    root_abs = os.path.abspath(root)
    if os.path.commonpath([p, root_abs]) != root_abs:
        fail(f"patch path escapes the repo root: {rel!r}")
        return None
    if os.path.islink(p):
        fail(f"patch path is a symlink (rejected): {rel!r}")
        return None
    return p


def resolve(manifest_path, cli_root=None):
    """Returns (manifest_dict, [(entry, abs_path)]) or None on fatal errors."""
    raw_manifest = open(manifest_path, "rb").read()
    notes.append(f"manifest_sha256={hashlib.sha256(raw_manifest).hexdigest()}")
    try:
        m = json.loads(raw_manifest.decode("utf-8"))
    except Exception as e:
        fail(f"manifest is not valid UTF-8 JSON: {e}")
        return None
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    rca_root = cli_root or m.get("rca_repo_root")
    if rca_root is None:
        fail("patch-path root is ambiguous: pass --rca-root <dir> or set "
             "manifest key rca_repo_root (paths are NEVER resolved against "
             "the manifest directory silently)")
        return None
    rca_root = os.path.abspath(rca_root)
    if not os.path.isdir(rca_root):
        fail(f"rca root is not a directory: {rca_root}")
        return None
    resolved = []
    for idx, entry in enumerate(m.get("patch_series", []) or []):
        if not isinstance(entry, dict) or "path" not in entry:
            fail(f"patch_series[{idx}] must be an object with path+sha256")
            continue
        p = resolve_patch_path(manifest_dir, rca_root, entry["path"])
        resolved.append((entry, p))
    return m, resolved


def git(args, cwd=REPO, check=True):
    return subprocess.run(["git", "-C", cwd] + args, capture_output=True,
                          text=True, check=check)


def commit_exists(sha):
    if not os.path.isdir(os.path.join(REPO, ".git")):
        notes.append(f"git repo unavailable; cannot verify {sha} locally")
        return None
    r = git(["cat-file", "-e", f"{sha}^{{commit}}"], check=False)
    return r.returncode == 0


def hash_chain_of(blobs):
    """Documented definition (docs/FINAL_HANDOFF_CONSUMER.md):
    h0 = sha256(seed); h_i = sha256(h_{i-1} || sha256(blob_i).digest());
    result = h_n.hex()
    """
    h = hashlib.sha256(HASH_CHAIN_SEED).digest()
    for b in blobs:
        h = hashlib.sha256(h + hashlib.sha256(b).digest()).digest()
    return h.hex()


def series_hash(mode, blobs):
    if mode == "concat_bytes":
        return hashlib.sha256(b"".join(blobs)).hexdigest()
    return hash_chain_of(blobs)


def check_unlisted_files(manifest, resolved):
    """Reject unexpected files sitting next to declared patches.
    Per-directory declared sets (G10 Reviewer C m-1: a rogue file in dir A
    whose basename matches a declared file in dir B must still be caught)."""
    by_dir = {}
    for entry, p in resolved:
        if p:
            by_dir.setdefault(os.path.dirname(p), set()).add(os.path.basename(p))
    for d, declared in sorted(by_dir.items()):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            full = os.path.join(d, name)
            if not os.path.isfile(full) or os.path.islink(full):
                fail(f"non-regular file in patch dir: {full}")
                continue
            if name not in declared:
                fail(f"unexpected unlisted file in patch dir {d}: {name}")


def verify_manifest(manifest_path, cli_root=None):
    """Full verification; returns (manifest, resolved) on success, else None."""
    del failures[:]
    del notes[:]
    if not os.path.isfile(manifest_path):
        fail(f"manifest not found: {manifest_path}")
        return None
    out = resolve(manifest_path, cli_root)
    if out is None:
        return None
    m, resolved = out

    for key in ("upstream_base_sha", "patch_series", "series_sha256",
                "series_sha256_mode", "rca_evidence_commit"):
        if key not in m:
            fail(f"manifest missing required key: {key}")

    base = m.get("upstream_base_sha", "")
    if not (isinstance(base, str) and len(base) == 40 and
            all(c in "0123456789abcdef" for c in base)):
        fail(f"upstream_base_sha is not a full 40-hex lowercase sha: {base!r}")

    for stale in STALE_REJECTED_COMMIT_PREFIXES:
        if base.startswith(stale):
            fail(f"upstream_base_sha {base} is a known-stale historical anchor "
                 f"({stale}) — the final candidate must use the fresh frozen SHA")

    mode = m.get("series_sha256_mode")
    if mode not in SUPPORTED_SERIES_MODES:
        fail(f"series_sha256_mode must be one of {SUPPORTED_SERIES_MODES}, got {mode!r}")

    series = m.get("patch_series")
    if not isinstance(series, list) or not series:
        fail("patch_series must be a non-empty ordered list")
        return None

    seen = set()
    blobs = []
    for idx, (entry, p) in enumerate(resolved):
        rel = entry.get("path", "?")
        expect = str(entry.get("sha256", "")).lower()
        if len(expect) != 64 or any(c not in "0123456789abcdef" for c in expect):
            fail(f"patch_series[{idx}].sha256 is not 64-hex lowercase: {expect!r}")
            continue
        if rel in seen:
            fail(f"duplicate patch path in series: {rel}")
        seen.add(rel)
        if p is None or not os.path.isfile(p):
            fail(f"patch file missing: {p or rel}")
            continue
        got = sha256_file(p)
        if got != expect:
            fail(f"patch {rel}: sha256 mismatch manifest={expect} actual={got}")
        else:
            notes.append(f"patch[{idx}] {rel} sha256 OK ({expect[:12]}…)")
        with open(p, "rb") as f:
            blobs.append(f.read())

    check_unlisted_files(m, resolved)

    if mode in SUPPORTED_SERIES_MODES:
        actual = series_hash(mode, blobs)
        if m.get("series_sha256", "").lower() != actual:
            fail(f"series_sha256 mismatch manifest={m.get('series_sha256')} "
                 f"actual={actual} (mode={mode})")
        else:
            notes.append(f"series_sha256 OK ({actual[:12]}…, mode={mode})")

    if not failures:
        ok = commit_exists(base)
        if ok is False:
            fail(f"upstream_base_sha {base} not present in local git repo "
                 f"(fetch the exact commit first)")
        elif ok is None:
            notes.append("base-commit presence NOT verified (no repo yet)")

    ev = m.get("rca_evidence_commit", "")
    for stale in STALE_REJECTED_COMMIT_PREFIXES:
        if ev.startswith(stale):
            fail(f"rca_evidence_commit {ev} is a known-stale reference ({stale})")

    return (m, resolved) if not failures else None


def render_report(mode, extra=None):
    verdict = "PASS" if not failures else "FAIL"
    report = {
        "gate": "G08",
        "mode": mode,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verdict": verdict,
        "failures": list(failures),
        "notes": list(notes),
    }
    if extra:
        report.update(extra)
    return json.dumps(report, indent=2)


def check_only(manifest_path, json_out=None, cli_root=None):
    verify_manifest(manifest_path, cli_root)
    rendered = render_report("check-only")
    if json_out:
        with open(json_out, "w") as f:
            f.write(rendered + "\n")
    print(rendered)
    return 0 if not failures else 1


def apply_manifest(manifest_path, target_dir, cli_root=None):
    if os.environ.get("ENABLE_APPLY") != "1":
        print("FATAL: --apply is disabled until the Phase-5.1 candidate is "
              "frozen. Re-run with ENABLE_APPLY=1 after the final handoff is "
              "published.", file=sys.stderr)
        return 2
    out = verify_manifest(manifest_path, cli_root)
    print(render_report("apply-precheck"))
    if out is None:
        print("FATAL: manifest failed verification; refusing to apply",
              file=sys.stderr)
        return 1
    m, resolved = out
    base = m["upstream_base_sha"]
    if os.path.exists(target_dir):
        print(f"FATAL: target {target_dir} already exists; the final run must "
              f"reconstruct into a clean dir", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(target_dir) or ".", exist_ok=True)
    r = git(["worktree", "add", "--detach", target_dir, base])
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        return r.returncode
    st = git(["status", "--porcelain"], cwd=target_dir)
    if st.stdout.strip():
        print("FATAL: worktree not clean before patch application",
              file=sys.stderr)
        return 2
    for entry, p in resolved:
        # re-verify immediately before apply (TOCTOU hardening)
        if sha256_file(p) != str(entry["sha256"]).lower():
            print(f"FATAL: patch {entry['path']} changed since verification",
                  file=sys.stderr)
            return 2
        chk = git(["apply", "--check", p], cwd=target_dir, check=False)
        if chk.returncode != 0:
            print(f"FATAL: git apply --check failed for {entry['path']}",
                  file=sys.stderr)
            return 2
        git(["apply", p], cwd=target_dir)
        print(f"applied {entry['path']}")
    st = git(["status", "--porcelain"], cwd=target_dir)
    print("post-apply changed paths:")
    print(st.stdout)
    ident = {"base_sha": base,
             "patched_files": st.stdout.splitlines(),
             "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with open(os.path.join(WS, "evidence", "G08_reconstructed_identity.json"), "w") as f:
        json.dump(ident, f, indent=2)
    print("RECONSTRUCTION_OK")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", metavar="MANIFEST")
    ap.add_argument("--rca-root", metavar="DIR", help="RCA repo root for patch paths (required unless manifest sets rca_repo_root)")
    ap.add_argument("--json-out", metavar="PATH")
    ap.add_argument("--apply", nargs=2, metavar=("MANIFEST", "TARGET_DIR"))
    a = ap.parse_args()
    if a.apply:
        sys.exit(apply_manifest(a.apply[0], a.apply[1], a.rca_root))
    if a.check_only:
        sys.exit(check_only(a.check_only, a.json_out, a.rca_root))
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
