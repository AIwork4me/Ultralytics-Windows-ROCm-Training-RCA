#!/usr/bin/env python3
"""Fetch missing blobs via raw.githubusercontent.com with SHA-1 verification.

Same discipline as Phase-3 raw_backfill (every blob verified against the
tree's expected SHA-1 before entering the object store), driven in parallel
with bounded retries. Idempotent: reads /tmp/missing_shas.txt (sha\tpath),
skips anything already present.
"""
import concurrent.futures as cf
import subprocess, sys, time, os, tempfile

REPO = "/home/amd/Desktop/YOLO_AMD/phase5_3b/src/upstream.git"
SHA = "7c5866144ac4b879be442563e2b49fa1c142ea36"
BASE = f"https://raw.githubusercontent.com/ROCm/rocm-libraries/{SHA}/"

pairs = []
for line in open("/tmp/missing_shas.txt"):
    line = line.rstrip("\n")
    if "\t" not in line:
        continue
    s, p = line.split("\t", 1)
    pairs.append((s, p))

def have(sha):
    r = subprocess.run(["git", "-c", "gc.auto=0", "cat-file", "-e", sha],
                       cwd=REPO, capture_output=True)
    return r.returncode == 0

todo = [(s, p) for s, p in pairs if not have(s)]
print(f"{len(pairs)} listed, {len(todo)} to fetch", flush=True)

def fetch(item):
    sha, path = item
    for attempt in range(6):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            r = subprocess.run(["curl", "-sfL", "--max-time", "60",
                                BASE + path, "-o", tmp.name],
                               capture_output=True)
            if r.returncode == 0:
                got = subprocess.run(["git", "-c", "gc.auto=0", "hash-object",
                                      "-w", tmp.name], cwd=REPO,
                                     capture_output=True, text=True).stdout.strip()
                if got == sha:
                    return None
                print(f"SHA-MISMATCH {path} expected {sha} got {got}", flush=True)
        finally:
            os.unlink(tmp.name)
        time.sleep(2 + attempt * 2)
    return (sha, path)

fails = []
with cf.ThreadPoolExecutor(max_workers=16) as ex:
    for i, res in enumerate(ex.map(fetch, todo)):
        if res:
            fails.append(res)
        if (i + 1) % 500 == 0:
            print(f"progress {i+1}/{len(todo)} fails={len(fails)}", flush=True)

print(f"done: {len(todo)-len(fails)} fetched, {len(fails)} FAILED")
for s, p in fails[:20]:
    print("  FAILED", p, s)
sys.exit(1 if fails else 0)
