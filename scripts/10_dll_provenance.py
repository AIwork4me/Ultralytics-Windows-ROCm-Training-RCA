"""Phase 10: ROCm package / DLL provenance.

Locates the DLLs in the failing call path (MIOpen, hiprtc, amd_comgr, hip),
records size / Windows file version / SHA256, plus python package provenance
via importlib.metadata. READ-ONLY. Only metadata and hashes are emitted —
no DLL contents are copied.
"""
import ctypes
import hashlib
import importlib.metadata as md
import json
import os
import subprocess
import sys

SP = os.path.join(sys.prefix, "Lib", "site-packages")
SEARCH_ROOTS = [
    os.path.join(SP, "_rocm_sdk_libraries"),
    os.path.join(SP, "_rocm_sdk_core"),
    os.path.join(SP, "_rocm_sdk_devices"),
    os.path.join(SP, "torch", "lib"),
    os.path.join(sys.prefix, "Library", "bin"),
    os.path.join(SP, "rocm_sdk_libraries"),
    os.path.join(SP, "rocm_sdk_core"),
]
PATTERNS = ("miopen", "hiprtc", "amd_comgr", "amdhip", "hip64", "rocm")


def file_version(path):
    try:
        ps = (f"(Get-Item '{path}').VersionInfo | "
              f"Select-Object FileVersion, ProductVersion, CompanyName, FileDescription "
              f"| ConvertTo-Json -Compress")
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=60)
        return (out.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"<error {exc}>"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


records = []
seen = set()
for root in SEARCH_ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            low = fn.lower()
            if not low.endswith(".dll"):
                continue
            if not any(p in low for p in PATTERNS):
                continue
            full = os.path.join(dirpath, fn)
            if full in seen:
                continue
            seen.add(full)
            size = os.path.getsize(full)
            records.append({
                "path": full,
                "size_bytes": size,
                "sha256": sha256(full),
                "version_info": file_version(full),
            })

# Which ROCm DLLs are loaded in a live torch process? (provenance of the
# failing path, not just disk presence)
loaded = []
try:
    import torch  # noqa: F401  (forces HIP/ROCm runtime load)
    torch.zeros(8, device="cuda")
    import psutil
    proc = psutil.Process()
    loaded = sorted(
        m.path for m in proc.memory_maps()
        if any(p in m.path.lower() for p in PATTERNS)
        and m.path.lower().endswith(".dll")
    ) if hasattr(proc, "memory_maps") else []
except Exception as exc:  # noqa: BLE001
    loaded = [f"<enumeration unavailable: {exc}>"]

out = {
    "captured": subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Date -Format o"],
        capture_output=True, text=True).stdout.strip(),
    "python": sys.executable,
    "live_loaded_rocm_dlls": loaded,
    "dlls": records,
}
print(json.dumps(out, indent=2))
with open(os.path.join("evidence", "raw", "environment", "dll_provenance.json"),
          "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"\n{len(records)} DLL records written to evidence/raw/environment/dll_provenance.json")
