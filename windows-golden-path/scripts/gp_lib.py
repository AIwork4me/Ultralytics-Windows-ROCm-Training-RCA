# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Shared library for the Windows Golden Path harness (R21+).

Every script in this harness imports gp_lib so that provenance, evidence
recording and runtime classification behave identically everywhere:

  - capture_environment(): machine + stack facts (GPU, driver, torch, wheels)
  - loaded_miopen_identity(): the ACTUALLY loaded MIOpen.dll path/SHA256/version
    (technique reused verbatim from golden-path/verify_environment.py, P14)
  - detect_workarounds(): HIPRTC/MIOPEN/DLL-redirect disclosures — an
    engineering shim is allowed but FORCES runtime_class ENGINEERING_REFERENCE
    and can never produce an OFFICIAL_* verdict
  - write_evidence(): strict-schema JSON records (bools are real bools, every
    required key present, timestamps UTC ISO-8601)

Nothing here may invent a PASS: records only describe what scripts measured.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- official AMD channels (mission §4; treat each separately) ---------------
OFFICIAL_CHANNELS = {
    "multi-arch": "https://repo.amd.com/rocm/whl-multi-arch/",
    "stable": "https://stable.repo.amd.com/rocm/whl-next/",
    "rc": "https://rc.repo.amd.com/rocm/whl-next/",
    "nightly": "https://nightly.repo.amd.com/rocm/whl-next/",
    "dev": "https://dev.repo.amd.com/rocm/whl-next/",
}

# package families whose index sub-pages are scanned per channel
DISCOVERY_PACKAGES = [
    "torch", "torchvision",
    "rocm-sdk-core", "rocm-sdk-libraries",
    "rocm-sdk-device-gfx1100", "rocm-sdk-device-gfx1151",
    "amd-torch-device-gfx1100", "amd-torch-device-gfx1151",
    "amd-torchvision-device-gfx1100", "amd-torchvision-device-gfx1151",
]

RUNTIME_CLASSES = [
    "OFFICIAL_STABLE", "OFFICIAL_CANDIDATE", "OFFICIAL_PRE_FIX",
    "ENGINEERING_REFERENCE", "BLOCKED_ENVIRONMENT", "INCONCLUSIVE",
]

FAILURE_CLASSES = [
    "SOURCE_REGRESSION", "MIOPEN_HIPRTC_COMPILATION", "MIOPEN_RUNTIME_KERNEL",
    "HIP_KERNEL_IMAGE_FAILURE", "TORCHVISION_DEVICE_WHEEL_MISSING",
    "DEPENDENCY_CONFLICT", "GPU_DEVICE_SELECTION", "CHECKPOINT_RESUME_FAILURE",
    "UNSUPPORTED_BACKEND", "ENVIRONMENT_BLOCKER", "INCONCLUSIVE",
]

# required keys on every evidence record (mission §11 common evidence schema)
EVIDENCE_REQUIRED_KEYS = [
    "run_id", "mission", "timestamp", "gpu_name", "gfx_target",
    "windows_build", "driver_version", "python", "torch", "torchvision",
    "hip", "runtime_class", "command", "exit_code", "duration_s",
    "pass_fail_skip", "failure_classification", "raw_log_path",
]

# PR #13437 fix marker inside MIOpen.dll embedded HIPRTC source
FIX_MARKER = b"miopen_initializer_list"


def now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# --- AMD ROCm local-version parsing (mission R21.1 TASK C) -------------------
# R22 dev-channel torch wheels use local versions like
#   2.15.0+gitf6cd88cb.devrocm10.3.0.dev0.ff5769655eeb1b91...   (observed)
# while stable/rc/multi-arch use
#   2.12.0+rocm7.14.1 / 2.14.0+rocm10.1.0 / 2.15.0+rocm10.2.0rc2
# A plain "+rocm" substring test rejects every dev wheel; these helpers parse
# the actual local segment instead, and vendor origin is additionally checked
# against the exact official channel URL (never a substring alone).
_ROCM_LOCAL_RE = re.compile(r"(?:^|[.\-_])[a-z0-9]*rocm(\d+(?:\.\d+){0,2})", re.IGNORECASE)


def parse_rocm_local_version(version: str) -> dict:
    """Parse an AMD ROCm local version segment (PEP 440 local part).

    Accepts URL-encoded input (%2B == '+'), as discovery files store versions
    exactly as they appear in index hrefs. Returns facts used by the vendor
    validation; is_amd_rocm_local is about the VERSION ONLY — callers must
    additionally verify the wheel's source URL against OFFICIAL_CHANNELS.
    """
    v = (version or "").replace("%2B", "+").replace("%2b", "+")
    local = v.split("+", 1)[1] if "+" in v else ""
    m = _ROCM_LOCAL_RE.search(local) if local else None
    return {
        "version": v,
        "local_segment": local or None,
        "rocm_version": m.group(1) if m else None,
        "rocm_family": (m.group(1).split(".")[0] if m else None),
        "is_amd_rocm_local": bool(m),
    }


def url_channel(url: str) -> str | None:
    """Which official AMD channel does a resolved URL belong to?

    Accepts both the channel root itself (…/rocm/whl-next/<pkg>/…) and the
    per-family sub-index layout the dev index actually serves
    (…/rocm/pytorch/whl-next/<pkg>/…) — both on the exact channel host
    (<channel>.repo.amd.com; multi-arch on repo.amd.com). Anything else
    (pypi.org, files.pythonhosted.org, a look-alike host) is NOT official."""
    if not url:
        return None
    for chan, root in OFFICIAL_CHANNELS.items():
        if url.startswith(root):
            rest = url[len(root):]
            if rest and "/" in rest:
                return chan
    m = re.match(r"https://([a-z0-9\-]+)\.repo\.amd\.com/rocm/", url)
    if m and m.group(1) in OFFICIAL_CHANNELS:
        return m.group(1)
    return None


def url_is_official_amd(url: str) -> bool:
    """True only when the URL belongs to an exact official AMD channel."""
    return url_channel(url) is not None


def torch_wheel_is_amd_hip(version: str, url: str | None) -> bool:
    """Vendor validation for a torch wheel: AMD ROCm local version AND origin
    from an exact official AMD channel. Neither signal alone is sufficient
    (a CPU wheel could be renamed with a rocm-looking local version; a genuine
    dev wheel does not carry the literal '+rocm' substring)."""
    parsed = parse_rocm_local_version(version)
    return parsed["is_amd_rocm_local"] and (url_is_official_amd(url) if url else False)


def rocm_family_of(package: str, version: str) -> str | None:
    """ROCm family of a package version: the rocm local segment when present
    (torch/torchvision), else the public version for rocm-sdk*/rocm packages
    (their public version IS the ROCm version, e.g. 10.3.0.dev0+ff576965).
    rocm-bootstrap and friends are excluded (their 0.x version is not a ROCm
    family)."""
    parsed = parse_rocm_local_version(version)
    if parsed["rocm_family"]:
        return parsed["rocm_family"]
    name = (package or "").lower()
    if name == "rocm" or name.startswith("rocm-sdk"):
        pub = (version or "").split("+")[0]
        m = re.match(r"(\d+)\.", pub)
        if m:
            return m.group(1)
    return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_json_types(obj) -> None:
    """Recursively assert no stringified booleans / ints sneak into records."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("exit_code",) and isinstance(v, bool):
                raise ValueError(f"exit_code must be int, got bool at {k}")
            strict_json_types(v)
    elif isinstance(obj, list):
        for v in obj:
            strict_json_types(v)
    elif isinstance(obj, str):
        if obj in ("True", "False"):
            raise ValueError(f"stringified boolean {obj!r} in evidence record")


def write_evidence(record: dict, out_path: Path) -> Path:
    """Validate the common evidence schema and write strict JSON."""
    missing = [k for k in EVIDENCE_REQUIRED_KEYS if k not in record]
    if missing:
        raise ValueError(f"evidence record missing required keys: {missing}")
    strict_json_types(record)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def loaded_miopen_identity() -> dict:
    """Load MIOpen.dll in-process; return path, SHA256, versions, fix marker.

    Reused from golden-path/verify_environment.py (P14 provenance contract).
    """
    try:
        miopen = ctypes.CDLL("MIOpen.dll")
    except OSError as e:
        return {"loaded": False, "error": str(e)}
    gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
    gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    buf = ctypes.create_string_buffer(1024)
    gmfn(miopen._handle, buf, 1024)
    path = buf.value.decode(errors="replace")
    h = hashlib.sha256()
    blob = b""
    try:
        blob = Path(path).read_bytes()
        h = hashlib.sha256(blob)
    except OSError:
        pass
    versions = sorted(set(re.findall(rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", blob)))
    return {
        "loaded": True,
        "path": path,
        "sha256": h.hexdigest(),
        "bytes": len(blob),
        "embedded_version_strings": [v.decode() for v in versions],
        "pr13437_marker_miopen_initializer_list": blob.count(FIX_MARKER),
    }


def detect_workarounds(env: dict | None = None) -> dict:
    """Detect engineering workarounds that void OFFICIAL_* classification."""
    env = env if env is not None else dict(os.environ)
    hiprtc = env.get("HIPRTC_COMPILE_OPTIONS_APPEND", "")
    miopen_overrides = {k: v for k, v in env.items()
                        if k.startswith("MIOPEN_") and k != "MIOPEN_LOG_LEVEL"}
    # DLL search-path redirection: MIOPEN dlls found outside the venv/site-packages
    suspicious_path_hits = []
    for var in ("PATH",):
        for entry in env.get(var, "").split(os.pathsep):
            if entry and "miopen" in entry.lower():
                suspicious_path_hits.append({"var": var, "entry": entry})
    return {
        "hiprtc_compile_options_append": hiprtc or None,
        "hiprtc_include_injection": ("-I" in hiprtc) if hiprtc else False,
        "miopen_env_overrides": miopen_overrides,
        "miopen_path_redirection": suspicious_path_hits,
        "any_workaround_present": bool(hiprtc or miopen_overrides or suspicious_path_hits),
    }


def classify_runtime(workarounds: dict, channel: str | None,
                     miopen: dict | None) -> str:
    """Runtime classification (mission §3/§5).

    Any detected workaround → ENGINEERING_REFERENCE (fail-closed: an official
    verdict is never issued on a shimmed process, even if tests pass).
    """
    if workarounds.get("any_workaround_present"):
        return "ENGINEERING_REFERENCE"
    if miopen is not None and miopen.get("loaded"):
        if miopen.get("pr13437_marker_miopen_initializer_list", 0) > 0:
            # fail-closed: OFFICIAL_STABLE requires the EXPLICIT stable channel;
            # an unlabelled post-fix stack can never claim stable
            if channel == "stable":
                return "OFFICIAL_STABLE"
            if channel in ("dev", "nightly", "rc"):
                return "OFFICIAL_CANDIDATE"
            return "INCONCLUSIVE"
        return "OFFICIAL_PRE_FIX"
    return "INCONCLUSIVE"


def windows_build() -> str:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[System.Environment]::OSVersion.Version.ToString()"],
            capture_output=True, timeout=30,
            encoding="utf-8", errors="replace").stdout.strip()
        return out or platform.version()
    except Exception:
        return platform.version()


def gpu_driver_facts() -> dict:
    """GPU name + driver via CIM (no GPU init; safe in any process)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | Where-Object {$_.Name -match 'AMD|Radeon'}"
             " | Select-Object -First 1 Name,DriverVersion | ConvertTo-Json -Compress"],
            capture_output=True, timeout=60,
            encoding="utf-8", errors="replace")
        return json.loads(out.stdout) if out.stdout.strip() else {}
    except Exception:
        return {}


def gfx_from_device_name(name: str) -> str:
    n = name.lower()
    if "7900 xtx" in n or "7900xtx" in n.replace(" ", ""):
        return "gfx1100"
    if "8060s" in n.replace(" ", ""):
        return "gfx1151"
    return "unknown"


def capture_environment(label: str) -> dict:
    """Full environment snapshot. torch import is OPTIONAL (preflight runs
    before any venv exists); GPU facts come from CIM when torch is absent."""
    env: dict = {"label": label, "captured_utc": now_utc(),
                 "python": sys.version.split()[0],
                 "python_executable": sys.executable,
                 "os": platform.platform(),
                 "windows_build": windows_build()}
    facts = gpu_driver_facts()
    env["gpu_name_cim"] = facts.get("Name")
    env["driver_version"] = facts.get("DriverVersion")
    env["gfx_target"] = gfx_from_device_name(facts.get("Name", ""))
    env["workarounds"] = detect_workarounds()
    env["env"] = {var: os.environ.get(var) for var in
                  ("PATH", "INCLUDE", "LIB", "VCToolsInstallDir", "HIP_PATH",
                   "ROCM_PATH", "PYTHONPATH")}
    env["env"]["HIPRTC_COMPILE_OPTIONS_APPEND"] = os.environ.get("HIPRTC_COMPILE_OPTIONS_APPEND")
    try:
        import torch  # noqa: PLC0415
        env["torch"] = torch.__version__
        env["hip"] = torch.version.hip
        env["torch_cuda_available"] = bool(torch.cuda.is_available())
        env["device_count"] = int(torch.cuda.device_count())
        if env["device_count"]:
            env["gpu_name_torch"] = torch.cuda.get_device_name(0)
        env["miopen"] = loaded_miopen_identity()
        import importlib.metadata as im
        env["packages"] = {}
        for pkg in ("torch", "torchvision", "ultralytics", "rocm-sdk-libraries",
                    "rocm-sdk-core", "amd-torch-device-gfx1100",
                    "amd-torch-device-gfx1151", "amd-torchvision-device-gfx1100",
                    "amd-torchvision-device-gfx1151"):
            try:
                env["packages"][pkg] = im.version(pkg)
            except im.PackageNotFoundError:
                env["packages"][pkg] = None
    except ImportError:
        env["torch"] = None
        env["note"] = "torch not importable in this process (preflight context)"
    return env


# --- known-good official stacks (from frozen P14/P16 audits) -----------------
# Used by compatibility checks; updated by discovery when new wheels appear.
KNOWN_STACKS = {
    "engref-7.14.1": {
        "channel": "multi-arch",
        "torch": "2.12.0+rocm7.14.1",
        "torchvision": "0.27.0+rocm7.14.1",
        "rocm_sdk": "7.14.1",
        "device_wheels_required": ["amd-torch-device-gfx1100",
                                   "amd-torch-device-gfx110x",
                                   "amd-torchvision-device-gfx1100"],
        "python_tags": ["cp312", "cp313"],
        "miopen_fix_present": False,  # official 7.14.1 wheel = pre-fix
    },
    "whlnext-10.1.0": {
        "channel": "stable",
        "torch": "2.14.0+rocm10.1.0",
        "torchvision": None,  # layout differs; discovered at scan time
        "rocm_sdk": "10.1.0",
        "device_wheels_required": ["rocm-sdk-device-gfx1100",
                                   "rocm-sdk-device-gfx1151"],
        "python_tags": ["cp310", "cp311", "cp312", "cp313", "cp314"],
        "miopen_fix_present": False,  # P16 re-audit: byte-identical pre-fix DLL
    },
}


def parse_wheel_filename(fn: str) -> dict:
    """Parse name-version-tag-arch from a wheel filename (PEP 427).

    Handles local version segments like 2.12.0+rocm7.14.1 and AMD's
    amd_torch_device naming. Returns {} when the filename is not a wheel.
    """
    if not fn.endswith(".whl"):
        return {}
    stem = fn[:-4]
    parts = stem.split("-")
    if len(parts) < 3:
        return {}
    name, version = parts[0], parts[1]
    rest = parts[2:]
    # rest = [python_tag...] abi... platform... (AMD wheels sometimes carry
    # extra build segments; last 3 chunks are the PEP 427 tags)
    tags = rest[-3:] if len(rest) >= 3 else rest
    return {"package": name.replace("_", "-").lower(), "version": version,
            "python_tag": tags[0], "abi_tag": tags[1] if len(tags) > 1 else "",
            "platform_tag": tags[2] if len(tags) > 2 else "",
            "win_amd64": "win_amd64" in tags[-1] if tags else False}


def classify_nostl_failure(stderr: str) -> str:
    """Map a no-STL leg failure to the mission failure vocabulary."""
    s = stderr or ""
    if "HIPRTC_ERROR_COMPILATION" in s or "'type_traits' file not found" in s \
            or "type_traits" in s and "fatal error" in s:
        return "MIOPEN_HIPRTC_COMPILATION"
    if "hipErrorInvalidKernelFile" in s:
        return "HIP_KERNEL_IMAGE_FAILURE"
    if "miopenStatusUnknownError" in s:
        return "MIOPEN_RUNTIME_KERNEL"
    if "hipErrorInvalidDeviceFunction" in s:
        return "TORCHVISION_DEVICE_WHEEL_MISSING"
    return "INCONCLUSIVE"
