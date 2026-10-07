#!/usr/bin/env python3
"""Phase-3 Gate 52 helper v2: materialize worktree files using curl
--parallel (connection reuse) against raw.githubusercontent.com, with
SHA1 verification against the git index. Robust to per-file failures.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

REPO = os.path.abspath(sys.argv[1])
PREFIXES = sys.argv[2:]
COMMIT = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                        capture_output=True, text=True).stdout.strip()
BASE = f"https://raw.githubusercontent.com/ROCm/rocm-libraries/{COMMIT}/"
CHUNK = 60


def git_out(args: list[str]) -> str:
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout


def list_paths(prefixes: list[str]) -> list[str]:
    out = git_out(["git", "ls-tree", "-r", "--name-only", "HEAD", "--", *prefixes])
    return [l for l in out.splitlines() if l.strip()]


def blob_shas(paths: list[str]) -> dict[str, str]:
    shas = {}
    # ls-tree -r with object ids, one line: <mode> <type> <sha>\t<path>
    out = git_out(["git", "ls-tree", "-r", "HEAD", "--", *PREFIXES])
    for line in out.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 2 and parts[1] == "blob":
            shas[path] = parts[2]
    return shas


def sha1_of(path: str) -> str:
    h = hashlib.sha1()
    size = os.path.getsize(path)
    h.update(f"blob {size}\0".encode())
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def curl_chunk(items: list[tuple[str, str]]) -> None:
    # curl config file avoids Windows command-line length limits
    cfg = os.path.join(REPO, ".git", "curl_chunk.cfg")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("parallel\nparallel-max = 6\nmax-time = 180\n"
                "retry = 6\nretry-delay = 4\nretry-all-errors\nsilent\nlocation\n")
        for url, dest in items:
            f.write(f'url = "{url}"\noutput = "{dest}"\n')
    subprocess.run(["curl", "-q", "-K", cfg], capture_output=True)


def main() -> int:
    shas = blob_shas(PREFIXES)
    paths = list_paths(PREFIXES)
    todo = []
    for p in paths:
        dest = os.path.join(REPO, p.replace("/", os.sep))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        todo.append(p)
    print(f"{len(paths)} tracked, {len(todo)} to fetch", flush=True)

    for round_no in range(12):
        if not todo:
            break
        batch = todo[:]
        for i in range(0, len(batch), CHUNK):
            items = [(BASE + p, os.path.join(REPO, p.replace("/", os.sep)))
                     for p in batch[i:i + CHUNK]]
            curl_chunk(items)
            time.sleep(2)
        remaining = []
        for p in batch:
            dest = os.path.join(REPO, p.replace("/", os.sep))
            if not (os.path.exists(dest) and os.path.getsize(dest) > 0
                    and sha1_of(dest) == shas.get(p)):
                remaining.append(p)
        todo = remaining
        print(f"round {round_no}: fetched {len(batch) - len(todo)}, "
              f"remaining {len(todo)}", flush=True)
        if todo:
            time.sleep(3)
    if todo:
        print(f"FAILED after retries: {len(todo)}")
        for p in todo[:15]:
            print("  ", p)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
