"""Compare MIOpen kernel-cache DB blobs between two cache homes (A vs B).

Reads every kern_db sqlite under the given cache dir, extracts
(name, args, sha256(kernel_blob)) rows, and diffs the sets. Identical blob
hashes for the same kernel+args = byte-identical generated code objects.
"""
import hashlib
import os
import sqlite3
import sys

def load(cache_dir):
    rows = set()
    for root, _, files in os.walk(cache_dir):
        for f in files:
            if not f.endswith(".ukdb"):
                continue
            p = os.path.join(root, f)
            try:
                con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                for name, args, blob in con.execute(
                    "SELECT kernel_name, kernel_args, kernel_blob FROM kern_db"
                ):
                    rows.add((name, args, hashlib.sha256(blob).hexdigest()))
                con.close()
            except sqlite3.Error as e:
                print(f"skip {p}: {e}")
    return rows

a = load(sys.argv[1])
b = load(sys.argv[2])
print(f"A kernels: {len(a)}  B kernels: {len(b)}")
amap = {(n, ar): h for n, ar, h in a}
bmap = {(n, ar): h for n, ar, h in b}
common = set(amap) & set(bmap)
print(f"common (name,args): {len(common)}")
same = diff = 0
diffs = []
for k in sorted(common):
    if amap[k] == bmap[k]:
        same += 1
    else:
        diff += 1
        diffs.append(k)
onlya = set(amap) - set(bmap)
onlyb = set(bmap) - set(amap)
print(f"blob-identical: {same}  blob-different: {diff}  onlyA: {len(onlya)}  onlyB: {len(onlyb)}")
for k in diffs[:10]:
    print("DIFF", k)
for k in list(onlya)[:5]:
    print("ONLY-A", k)
for k in list(onlyb)[:5]:
    print("ONLY-B", k)
