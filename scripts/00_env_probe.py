"""Phase 0 environment probe for Windows ROCm RCA.

Prints Python/PyTorch/ROCm stack facts and a sanitized whitelist of
GPU/toolchain-relevant environment variables. Exceptions are recorded,
never fatal. Run with the validated stack's python.exe.
"""
import importlib.metadata as md
import os
import platform
import sys

PASSED, FAILED = [], []


def section(name):
    print(f"\n===== {name} =====")


def safe(label, fn):
    try:
        value = fn()
        print(f"{label}: {value}")
        PASSED.append(label)
        return value
    except Exception as exc:  # noqa: BLE001 - probe must record, not abort
        print(f"{label}: <EXCEPTION> {type(exc).__name__}: {exc}")
        FAILED.append(label)
        return None


section("python")
print(f"executable: {sys.executable}")
print(f"version: {sys.version}")
print(f"platform: {platform.platform()}")
print(f"machine: {platform.machine()}")
safe("sys.prefix", lambda: sys.prefix)
safe("CONDA_PREFIX (env var)", lambda: os.environ.get("CONDA_PREFIX", "<unset>"))
safe("CONDA_DEFAULT_ENV (env var)", lambda: os.environ.get("CONDA_DEFAULT_ENV", "<unset>"))

section("torch")
safe("torch.__version__", lambda: __import__("torch").__version__)
safe("torch.version.hip", lambda: __import__("torch").version.hip)
safe("torch.version.cuda", lambda: __import__("torch").version.cuda)
import torch  # noqa: E402

safe("torch.cuda.is_available()", lambda: torch.cuda.is_available())
safe("torch.cuda.device_count()", lambda: torch.cuda.device_count())
safe("torch.cuda.get_device_name(0)", lambda: torch.cuda.get_device_name(0))


def device_props():
    p = torch.cuda.get_device_properties(0)
    return (
        f"name={p.name} total_memory={p.total_memory} "
        f"multi_processor_count={p.multi_processor_count} "
        f"major.minor={getattr(p, 'major', '?')}.{getattr(p, 'minor', '?')}"
    )


safe("torch.cuda.get_device_properties(0)", device_props)
safe("torch.backends.cudnn.enabled", lambda: torch.backends.cudnn.enabled)
safe("torch.backends.cudnn.is_available()", lambda: torch.backends.cudnn.is_available())
safe("torch.backends.cudnn.version()", lambda: torch.backends.cudnn.version())
safe("torch.backends.miopen.is_available()", lambda: torch.backends.mioopen.is_available()
     if hasattr(torch.backends, "miopen") else "<no torch.backends.miopen>")
safe("torch.version.git_version", lambda: getattr(torch.version, "git_version", "<absent>"))

section("torchvision / torchaudio / ultralytics")
safe("torchvision.__version__", lambda: __import__("torchvision").__version__)
safe("torchaudio.__version__", lambda: __import__("torchaudio").__version__)
safe("ultralytics.__version__", lambda: __import__("ultralytics").__version__)

section("package metadata (importlib.metadata)")
PACKAGES = [
    "torch", "torchvision", "torchaudio", "ultralytics", "ultralytics-thop",
    "rocm", "rocm-bootstrap", "rocm-sdk-core", "rocm-sdk-libraries",
    "rocm-sdk-device-gfx1151", "amd-torch-device-gfx1151",
    "amd-torch-device-gfx11", "amd-torchvision-device-gfx1151",
]
for name in PACKAGES:
    def get(n=name):
        d = md.distribution(n)
        return f"{d.version} (loc={d.locate_file('')})"
    safe(f"pkg:{name}", get)

section("environment variable whitelist (sanitized)")
# Never dump full environment. Only GPU/toolchain-relevant names.
WHITELIST = [
    "PATH", "INCLUDE", "LIB", "LIBPATH", "HIP_PATH", "ROCM_PATH",
    "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "GPU_DEVICE_ORDINAL",
    "CPATH", "CPLUS_INCLUDE_PATH", "TEMP", "TMP",
    "MIOPEN_ENABLE_LOGGING", "MIOPEN_FIND_MODE", "PYTORCH_ROCM_ARCH",
]
DENY_SUBSTRINGS = ("TOKEN", "KEY", "SECRET", "PASS", "AUTH", "COOKIE",
                   "CREDENTIAL")


def sanitize_path_value(value):
    parts = value.split(os.pathsep)
    return os.pathsep.join(p for p in parts if p.strip())


for name in WHITELIST:
    if any(d in name.upper() for d in DENY_SUBSTRINGS):
        print(f"{name}: <skipped by deny-rule>")
        continue
    value = os.environ.get(name, "<unset>")
    if name.upper() == "PATH":
        value = sanitize_path_value(value)
        # PATH can be long; print entry count and the entries (no secrets
        # expected in PATH, but keep it one-per-line for readability).
        print(f"PATH ({len(value.split(os.pathsep))} entries):")
        for entry in value.split(os.pathsep):
            print(f"  {entry}")
    else:
        print(f"{name}: {value}")

section("summary")
print(f"probes ok: {len(PASSED)}")
print(f"probes failed: {len(FAILED)} -> {FAILED}")
