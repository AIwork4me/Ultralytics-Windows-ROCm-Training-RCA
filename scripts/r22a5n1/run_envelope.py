# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 execution envelope (mission PHASE 2 §5) — capture-at-execution
logging for every new physical GPU run.

Root cause being fixed: the R22A.5N training scripts pointed `raw_log_path` at
caller-side stdout redirects that were never committed, so five mandatory raw
logs are unrecoverable. This envelope makes that impossible to repeat: the
driver itself owns the raw stdout/stderr bytes, process identity and timestamps
from BEFORE process start to AFTER exit, so every attempt (including failures
and retries) leaves a durable, unique-named artifact directory.

Captured per attempt (nothing synthesized after the fact):
  stdout.log / stderr.log  — original child bytes, separate streams
  envelope.json            — cmd array, cwd, python exe, PIDs (child, envelope,
                             envelope parent), start/finish UTC, duration,
                             exit code, sanitized effective env subset, exact
                             git source identity, optional package-lock SHA,
                             CIM GPU identity, post-exit artifact hashes

    python scripts/r22a5n1/run_envelope.py --name stage_c --run-root DIR \
        [--lock lock.json] [--cwd DIR] [--hash GLOB ...] [--timeout S] -- <cmd>
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "windows-golden-path" / "scripts"))
import gp_lib  # noqa: E402

# environment variables recorded verbatim (security/provenance relevant, bounded)
ENV_KEYS = (
    "VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH", "PYTHONHOME",
    "HIPRTC_COMPILE_OPTIONS_APPEND", "MIOPEN_LOG_LEVEL", "MIOPEN_USER_DB_PATH",
    "MIOPEN_CUSTOM_CACHE_DIR", "ROCM_PATH", "HIP_PATH", "CUDA_VISIBLE_DEVICES",
    "TORCH_HOME", "HF_HOME", "ULTRALYTICS_CONFIG_DIR",
)
ENV_PREFIXES = ("MIOPEN_", "HIP_", "ROCM_", "AMD_", "PYTORCH_")


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git_identity() -> dict:
    def git(*a: str) -> str:
        try:
            return subprocess.run(["git", *a], cwd=str(REPO_ROOT), capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    return {
        "head": git("rev-parse", "HEAD") or None,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD") or None,
        "dirty_files": git("status", "--porcelain") or None,
    }


def sanitized_env() -> dict:
    out: dict[str, object] = {}
    for k in ENV_KEYS:
        if k in os.environ:
            out[k] = os.environ[k]
    for k in sorted(os.environ):
        if k.startswith(ENV_PREFIXES) and k not in out:
            v = os.environ[k]
            out[k] = v if len(v) <= 400 else f"<{len(v)} chars>"
    out["_PATH_ENTRIES"] = [e for e in os.environ.get("PATH", "").split(os.pathsep) if e]
    out["_ALL_VAR_NAMES"] = sorted(os.environ.keys())
    return out


def hash_glob(pattern: str, cwd: Path) -> list[dict]:
    hits = sorted(p for p in cwd.glob(pattern) if p.is_file())
    return [{"path": str(p), "bytes": p.stat().st_size,
             "sha256": gp_lib.sha256_file(p)} for p in hits]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True, help="stage name (dir prefix)")
    ap.add_argument("--run-root", required=True, help="parent dir for attempt dirs")
    ap.add_argument("--lock", default=None, help="experiment wheel lock (SHA recorded)")
    ap.add_argument("--cwd", default=None, help="child working dir (default: current)")
    ap.add_argument("--hash", action="append", default=[],
                    help="glob (against child cwd) hashed AFTER child exit; repeatable")
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="child command after '--'")
    args = ap.parse_args()
    if args.cmd and args.cmd[0] == "--":
        args.cmd = args.cmd[1:]
    if not args.cmd:
        ap.error("no child command given (put it after '--')")

    root = Path(args.run_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    attempt = root / f"{args.name}_{stamp}_{os.getpid()}"
    n = 1
    while attempt.exists():  # unique name per attempt — never overwrite
        n += 1
        attempt = root / f"{args.name}_{stamp}_{os.getpid()}_{n}"
    attempt.mkdir(parents=True)

    child_cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    lock_sha = gp_lib.sha256_file(Path(args.lock)) if args.lock else None
    meta: dict = {
        "envelope_version": "r22a5n1-envelope-v1",
        "name": args.name, "attempt_dir": str(attempt),
        "command": args.cmd, "cwd": str(child_cwd),
        "python_executable": sys.executable,
        "envelope_pid": os.getpid(), "envelope_parent_pid": os.getppid(),
        "lock_path": str(args.lock) if args.lock else None,
        "lock_sha256": lock_sha,
        "git": git_identity(),
        "gpu_cim": gp_lib.gpu_driver_facts(),
        "env": sanitized_env(),
        "started_utc": utcnow(),
    }
    (attempt / "envelope.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    out_f = open(attempt / "stdout.log", "wb")
    err_f = open(attempt / "stderr.log", "wb")
    t0 = time.time()
    exit_code: int | None = None
    timed_out = False
    try:
        proc = subprocess.Popen(args.cmd, cwd=str(child_cwd),
                                stdout=out_f, stderr=err_f)
        meta["child_pid"] = proc.pid
        meta["child_started_utc"] = utcnow()
        # rewrite metadata with child pid as soon as it exists
        (attempt / "envelope.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            exit_code = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            exit_code = proc.wait(timeout=60)
            timed_out = True
    finally:
        out_f.close()
        err_f.close()
    meta.update({
        "finished_utc": utcnow(),
        "duration_s": round(time.time() - t0, 1),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_bytes": (attempt / "stdout.log").stat().st_size,
        "stderr_bytes": (attempt / "stderr.log").stat().st_size,
        "artifact_hashes": [h for g in args.hash for h in hash_glob(g, child_cwd)],
    })
    (attempt / "envelope.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"attempt_dir": str(attempt), "exit_code": exit_code,
                      "timed_out": timed_out,
                      "stdout_bytes": meta["stdout_bytes"],
                      "stderr_bytes": meta["stderr_bytes"]}))
    sys.exit(0 if (exit_code == 0 and not timed_out) else 1)


if __name__ == "__main__":
    main()
