"""Phase-3 Gate 86: artifact manifest + SHA256SUMS for evidence/phase3.
Phase-1/2 manifests untouched. MANIFEST.json excludes its own hash."""
import hashlib
import json
import os
import subprocess

ROOT = r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA"
P3 = os.path.join(ROOT, "evidence", "phase3")

tracked = set(subprocess.run(["git", "ls-files", "--", "evidence/phase3"],
                             capture_output=True, text=True, cwd=ROOT).stdout.splitlines())

entries, sums = [], []
for dirpath, _dirs, files in os.walk(P3):
    for fn in sorted(files):
        if fn in ("SHA256SUMS.txt", "MANIFEST.json"):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
        if rel not in tracked:
            continue
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        sha = h.hexdigest()
        entries.append({"path": rel, "size_bytes": os.path.getsize(full), "sha256": sha})
        sums.append(f"{sha} *{rel}")

manifest = {"phase": 3, "files": entries,
            "note": "Phase-3 artifacts only; Phase-1/2 manifests untouched; "
                    "MANIFEST.json excludes its own hash (SHA256SUMS covers raw "
                    "evidence files only)."}
with open(os.path.join(P3, "MANIFEST.json"), "w", newline="\n") as f:
    json.dump(manifest, f, indent=1, sort_keys=True)
with open(os.path.join(P3, "SHA256SUMS.txt"), "w", newline="\n") as f:
    f.write("\n".join(sums) + "\n")
print(f"phase3 manifest: {len(entries)} files")
