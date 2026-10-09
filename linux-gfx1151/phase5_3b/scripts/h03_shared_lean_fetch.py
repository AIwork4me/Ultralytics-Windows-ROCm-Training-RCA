#!/usr/bin/env python3
"""Lean shared/ blob fetch: no per-blob pre-check (list is already the
missing set), 24 workers, SHA-1 verified via hash-object -w."""
import concurrent.futures as cf
import subprocess, sys, time, os, tempfile

REPO = "/home/amd/Desktop/YOLO_AMD/phase5_3b/src/upstream.git"
SHA = "7c5866144ac4b879be442563e2b49fa1c142ea36"
BASE = f"https://raw.githubusercontent.com/ROCm/rocm-libraries/{SHA}/"

pairs = []
for line in open("/tmp/shared_blobs.txt"):
    if "\t" not in line: continue
    s, p = line.rstrip("\n").split("\t", 1)
    pairs.append((s, p))
print(f"{len(pairs)} shared blobs queued", flush=True)

done = [0]; fails = []
def fetch(item):
    sha, path = item
    for attempt in range(5):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            r = subprocess.run(["curl", "-sfL", "--max-time", "45", BASE + path, "-o", tmp.name], capture_output=True)
            if r.returncode == 0:
                got = subprocess.run(["git", "-c", "gc.auto=0", "hash-object", "-w", tmp.name], cwd=REPO, capture_output=True, text=True).stdout.strip()
                if got == sha:
                    done[0] += 1
                    if done[0] % 200 == 0: print(f"progress {done[0]}/{len(pairs)}", flush=True)
                    return None
        finally:
            os.unlink(tmp.name)
        time.sleep(1 + attempt)
    return (sha, path)

with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for res in ex.map(fetch, pairs):
        if res: fails.append(res)
print(f"done: {len(pairs)-len(fails)} fetched, {len(fails)} FAILED", flush=True)
for s, p in fails[:10]: print("  FAILED", p, s, flush=True)
sys.exit(1 if fails else 0)
