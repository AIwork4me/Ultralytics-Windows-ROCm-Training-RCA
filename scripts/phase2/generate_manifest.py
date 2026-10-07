"""Gate 43: Phase-2 artifact manifest + SHA256SUMS (Phase-1 hashes untouched)."""
import hashlib
import json
import os
import subprocess

ROOT = r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA"
P2ROOT = os.path.join(ROOT, "evidence", "phase2")
SEP = os.sep

now = (
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Date -Format o"],
        capture_output=True,
        text=True,
    ).stdout.strip()
)

tracked = set(
    subprocess.run(
        ["git", "ls-files", "--", "evidence/phase2"],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout.splitlines()
)
entries = []
for dirpath, dirnames, filenames in os.walk(P2ROOT):
    for fn in sorted(filenames):
        if fn == "SHA256SUMS.txt":
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
        if rel not in tracked:
            continue  # skip gitignored/untracked (e.g. *.bc)
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace(SEP, "/")
        data = open(full, "rb").read()
        entries.append(
            {
                "path": rel,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "capture_time": now,
            }
        )
entries.sort(key=lambda e: e["path"])
manifest = {
    "phase": 2,
    "generated": now,
    "note": "Phase-2 artifacts only; Phase-1 evidence/SHA256SUMS.txt untouched.",
    "files": entries,
}
with open(os.path.join(P2ROOT, "MANIFEST.json"), "w", newline="\n") as f:
    json.dump(manifest, f, indent=2)
with open(os.path.join(P2ROOT, "SHA256SUMS.txt"), "w", newline="\n") as f:
    for e in entries:
        f.write(f"{e['sha256']}  {e['path']}\n")
print("files:", len(entries))
print("total MB:", round(sum(e["size_bytes"] for e in entries) / 1e6, 1))
