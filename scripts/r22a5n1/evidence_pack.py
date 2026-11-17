# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 evidence-pack manifest generator/verifier (mission PHASE 5 §8).

Exact-byte SHA256 manifest for a run pack, with the cryptographic closure
rules the mission mandates:

  gen     walk the pack, hash every file, emit SHA256MANIFEST.json with
          producer git SHA, script identity, lock SHA, run id
  verify  independent recomputation; REJECTS: missing files, wrong hashes,
          duplicate normalized paths, path traversal, case-insensitive
          Windows collisions, contradictory run ids, stale unmmanifested
          files, self-referential manifest entries. Raw and derived artifacts
          are distinguished via the manifest's kind map.

    python scripts/r22a5n1/evidence_pack.py gen --root PACK --run-id ID \
        [--lock lock.json] [--derived-glob ...] [--out SHA256MANIFEST.json]
    python scripts/r22a5n1/evidence_pack.py verify --root PACK --run-id ID
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "SHA256MANIFEST.json"
GLOB_CHARS = re.compile(r"[*?\[]")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git_head(repo: Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True,
                              timeout=15).stdout.strip() or None
    except Exception:
        return None


def norm(rel: str) -> str:
    return str(PurePosixPath(rel)).replace("\\", "/")


def classify(rel: str, derived_globs: list[str]) -> str:
    import fnmatch
    posix = norm(rel)
    for g in derived_globs:
        if GLOB_CHARS.search(g):
            if fnmatch.fnmatch(posix, g) or fnmatch.fnmatch(Path(rel).name, g):
                return "derived"
        elif norm(g) == posix:
            return "derived"
    return "raw"


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != MANIFEST_NAME:
            yield p


def gen(root: Path, run_id: str, lock: Path | None, derived_globs: list[str],
        out: Path) -> dict:
    repo = Path(__file__).resolve().parents[2]
    entries = []
    seen_norm: dict[str, str] = {}
    for p in iter_files(root):
        rel = norm(p.relative_to(root).as_posix())
        if rel != p.relative_to(root).as_posix() or ".." in PurePosixPath(rel).parts:
            raise SystemExit(f"path normalization problem: {p}")
        low = rel.lower()
        if low in seen_norm:
            raise SystemExit(f"case-insensitive collision: {rel} vs {seen_norm[low]}")
        seen_norm[low] = rel
        blob = p.read_bytes()
        entries.append({
            "path": rel, "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "kind": classify(rel, derived_globs),
        })
    manifest = {
        "run_id": run_id, "mission": "R22A.5N.1", "generated_utc": now_utc(),
        "producer_git_sha": git_head(repo),
        "producer_script": "scripts/r22a5n1/evidence_pack.py",
        "package_lock_sha256": (hashlib.sha256(lock.read_bytes()).hexdigest()
                                if lock and lock.is_file() else None),
        "algorithm": "sha256", "entries": entries,
        "note": "raw = captured-at-execution bytes; derived = recomputed "
                "reports/verdicts; the manifest never lists itself",
    }
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    return manifest


def verify(root: Path, run_id: str) -> dict:
    mpath = root / MANIFEST_NAME
    problems: list[str] = []
    if not mpath.is_file():
        return {"ok": False, "problems": [f"missing {MANIFEST_NAME}"]}
    m = json.loads(mpath.read_text(encoding="utf-8"))
    if m.get("run_id") != run_id:
        problems.append(f"manifest run_id {m.get('run_id')!r} != requested {run_id!r}")
    entries = m.get("entries") or []
    seen_norm: dict[str, str] = {}
    for e in entries:
        rel = e.get("path", "")
        if not rel or rel.startswith("/") or ".." in PurePosixPath(rel).parts:
            problems.append(f"path traversal/absolute: {rel!r}")
            continue
        if rel.lower() in seen_norm:
            problems.append(f"duplicate path (case-insensitive): {rel}")
        seen_norm[rel.lower()] = rel
        if norm(rel) != rel:
            problems.append(f"non-normalized path: {rel!r}")
        f = root / Path(*PurePosixPath(rel).parts)
        if not f.is_file():
            problems.append(f"missing file: {rel}")
            continue
        blob = f.read_bytes()
        h = hashlib.sha256(blob).hexdigest()
        if h != e.get("sha256"):
            problems.append(f"hash mismatch: {rel}")
        if len(blob) != e.get("bytes"):
            problems.append(f"size mismatch: {rel}")
    # stale files present in the tree but absent from the manifest
    listed = {e.get("path") for e in entries}
    for p in iter_files(root):
        rel = norm(p.relative_to(root).as_posix())
        if rel not in listed:
            problems.append(f"stale unmmanifested file: {rel}")
    if any(e.get("path") == MANIFEST_NAME for e in entries):
        problems.append("self-referential manifest entry")
    raw_n = sum(1 for e in entries if e.get("kind") == "raw")
    der_n = sum(1 for e in entries if e.get("kind") == "derived")
    return {"ok": not problems, "problems": problems,
            "entries": len(entries), "raw": raw_n, "derived": der_n,
            "producer_git_sha": m.get("producer_git_sha"),
            "package_lock_sha256": m.get("package_lock_sha256")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    g = sub.add_parser("gen")
    g.add_argument("--root", required=True)
    g.add_argument("--run-id", required=True)
    g.add_argument("--lock", default=None)
    g.add_argument("--derived-glob", action="append", default=[])
    g.add_argument("--out", default=None)
    v = sub.add_parser("verify")
    v.add_argument("--root", required=True)
    v.add_argument("--run-id", required=True)
    args = ap.parse_args()

    if args.mode == "gen":
        root = Path(args.root).resolve()
        out = Path(args.out).resolve() if args.out else root / MANIFEST_NAME
        m = gen(root, args.run_id, Path(args.lock) if args.lock else None,
                args.derived_glob, out)
        print(json.dumps({"manifest": str(out), "entries": len(m["entries"]),
                          "producer_git_sha": m["producer_git_sha"]}))
    else:
        r = verify(Path(args.root).resolve(), args.run_id)
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["ok"] else 5)


if __name__ == "__main__":
    main()
