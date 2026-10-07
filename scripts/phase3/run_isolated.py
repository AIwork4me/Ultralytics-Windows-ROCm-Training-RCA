"""Phase-3 Gates 62-66 runner core: run a Python snippet under a FRESH
isolation environment (HOME/USERPROFILE/LOCALAPPDATA redirected to a new
GUID dir => fresh MIOpen user kernel DB + fresh comgr cache), with
loaded-DLL provenance for MIOpen.dll/hiprtc.dll, and captured exit code.

Usage (module): python run_isolated.py <tag> <outdir> <script.py> [args...]
Writes <outdir>/<tag>.json with env, provenance, stdout/stderr, exit code.
"""
from __future__ import annotations

import ctypes
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid


def module_path(name: str) -> str | None:
    k = ctypes.windll.kernel32
    h = k.GetModuleHandleW(name)
    if not h:
        return None
    buf = ctypes.create_unicode_buffer(2048)
    if not k.GetModuleFileNameW(h, buf, 2048):
        return None
    return buf.value


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    tag, outdir, script = sys.argv[1], sys.argv[2], sys.argv[3]
    script_args = sys.argv[4:]
    yolo_mode = os.environ.get("PHASE3_ISOLATION") == "yolo"
    os.makedirs(outdir, exist_ok=True)
    iso = os.path.join(tempfile.gettempdir(), f"phase3_iso_{tag}_{uuid.uuid4().hex[:8]}")
    os.makedirs(iso)

    env = os.environ.copy()
    # scrub ambient injection channels (Phase-3 handoff confounder list)
    for var in ("ROCM_PATH", "INCLUDE", "LIB", "MIOPEN_FIND_MODE",
                "MIOPEN_USER_CACHE_PATH", "MIOPEN_USER_DB_PATH",
                "AMD_COMGR_CACHE", "HIP_VISIBLE_DEVICES"):
        env.pop(var, None)
    if not yolo_mode:
        env["HOME"] = iso
        env["USERPROFILE"] = iso
    env["LOCALAPPDATA"] = os.path.join(iso, "AppData", "Local")
    env["TEMP"] = os.path.join(iso, "tmp")
    env["TMP"] = env["TEMP"]
    # explicit fresh MIOpen user caches regardless of profile layout
    env["MIOPEN_USER_CACHE_PATH"] = os.path.join(iso, "miopen_cache")
    env["MIOPEN_USER_DB_PATH"] = os.path.join(iso, "miopen_db")
    os.makedirs(env["LOCALAPPDATA"], exist_ok=True)
    os.makedirs(env["TEMP"], exist_ok=True)
    os.makedirs(env["MIOPEN_USER_CACHE_PATH"], exist_ok=True)
    os.makedirs(env["MIOPEN_USER_DB_PATH"], exist_ok=True)
    env["PYTHONUNBUFFERED"] = "1"

    probe = r"""
import ctypes, json, atexit
from ctypes import wintypes
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.GetModuleHandleW.restype = ctypes.c_void_p
k.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
k.GetModuleFileNameW.restype = wintypes.DWORD
k.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
def mp(n):
    h = k.GetModuleHandleW(n)
    if not h: return None
    b = ctypes.create_unicode_buffer(2048)
    return b.value if k.GetModuleFileNameW(h, b, 2048) else None
def _dump():
    print("MODULE_PROVENANCE " + json.dumps({n: mp(n) for n in
          ["MIOpen.dll", "hiprtc0714.dll", "amd_comgr.dll", "amdhip64_7.dll"]}))
atexit.register(_dump)
"""

    started = datetime.datetime.now().isoformat()
    r = subprocess.run([sys.executable, "-c", probe + "\n" + open(script).read(), *script_args],
                       capture_output=True, text=True, env=env, timeout=1800)
    record = {
        "tag": tag,
        "started": started,
        "finished": datetime.datetime.now().isoformat(),
        "isolation_dir": iso,
        "env_HOME": env["HOME"],
        "argv": [script, *script_args],
        "returncode": r.returncode,
        "stdout_tail": r.stdout[-8000:],
        "stderr_tail": r.stderr[-8000:],
    }
    # module provenance of the CHILD (parsed from its stdout)
    for line in r.stdout.splitlines():
        if line.startswith("MODULE_PROVENANCE "):
            record["module_provenance"] = json.loads(line[len("MODULE_PROVENANCE "):])
    for name, p in (record.get("module_provenance") or {}).items():
        record[f"sha256_{name}"] = sha256_file(p) if p else None
    out = os.path.join(outdir, f"{tag}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(json.dumps({k: record[k] for k in
                      ("tag", "returncode", "module_provenance", "sha256_MIOpen.dll")}, indent=2))
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
