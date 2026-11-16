# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Reliability runner (missions §8 R21-F smoke / §14 R22 ≥10 runs per arch / R22A.2 Part B).

Runs N INDEPENDENT short training processes (exact standard command shape),
classifying each run and tallying anomaly families separately — an
unexplained kernel/runtime failure blocks stable Golden Path readiness and is
never assumed fixed by MIOpen #13437.

Cold vs warm cache are distinct evidence classes: a fresh Python process is
NOT a cold MIOpen cache. --cold runs redirect USERPROFILE to a per-run fresh
home; --warm-home redirects to a SHARED retained isolated home (R22A.2 warm
runs must share one cache identity without touching the user's global cache).
The user's global caches are never touched or deleted.

R22A.2 Part B (--workers, mission §6/§7):
  - --workers N (default 0 — historical G8 contract byte-compatible)
  - the generated child script has a proper Windows spawn entry guard
    (`if __name__ == "__main__":` + freeze_support) — with workers>0, spawn
    re-imports the child module in every worker and module-level training
    statements would recursively start training processes
  - the runner VERIFIES the effective DataLoader worker count (child records
    trainer.train_loader.num_workers) AND observes actual worker subprocess
    activity OS-level (CIM process-tree snapshots; never a private PyTorch
    implementation detail as sole proof), then re-scans for orphaned workers
    after the child exits
  - per-run timeout bounded; a timeout fails even if later runs succeed

    python run_stability.py --out stability.json --run-id R22A2-B1 \
        --runs 2 --cold --workers 8 --data <coco128.yaml> --work-dir <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

# Windows-spawn-safe child: executable statements live inside main(); the
# __main__ guard (+ freeze_support) makes import-time side effects impossible,
# so DataLoader workers re-importing this module cannot recurse into training.
CHILD = r'''
import multiprocessing
import os
import sys
import time


def main():
    t0 = time.time()
    import torch
    from ultralytics import YOLO

    resolved = {{}}

    def on_train_start(trainer):
        resolved["num_workers"] = int(getattr(trainer.train_loader, "num_workers", -1))
        resolved["n_batches"] = int(len(trainer.train_loader))
        resolved["amp"] = bool(trainer.amp)
        resolved["optimizer"] = type(trainer.optimizer).__name__
        resolved["torch"] = torch.__version__

    m = YOLO("yolo26n.pt")
    m.add_callback("on_train_start", on_train_start)
    kwargs = dict(data=r"{data}", epochs=1, device={device}, project=r"{project}",
                  name=r"{name}", exist_ok=True, seed={seed}, workers={workers},
                  verbose=True)
    if {batch}:
        kwargs["batch"] = {batch}
    if {imgsz}:
        kwargs["imgsz"] = {imgsz}
    m.train(**kwargs)
    print(f"R22A2_WORKERS resolved={{resolved.get('num_workers')}} "
          f"n_batches={{resolved.get('n_batches')}} amp={{resolved.get('amp')}} "
          f"optimizer={{resolved.get('optimizer')}} requested={workers}")
    print(f"R22A2_PID {{os.getpid()}}")
    print(f"STABILITY_CHILD_DONE {{time.time() - t0:.1f}}s")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
'''

ANOMALY_SIGNATURES = {
    "hipErrorInvalidKernelFile": "HIP_KERNEL_IMAGE_FAILURE",
    "hipErrorInvalidDeviceFunction": "TORCHVISION_DEVICE_WHEEL_MISSING",
    "HIPRTC_ERROR_COMPILATION": "MIOPEN_HIPRTC_COMPILATION",
    "type_traits": "MIOPEN_HIPRTC_COMPILATION",
    "miopenStatusUnknownError": "MIOPEN_RUNTIME_KERNEL",
    "MIOpen(HIP): [FindSolution]": "MIOPEN_SOLVER_ANOMALY",
    "missing CK kernel": "MIOPEN_MISSING_CK_SYMBOL",
    # R22A.2 Part B worker/process failure families (mission §8)
    "DataLoader worker (pid": "WORKER_CRASH",
    "exited unexpectedly": "WORKER_CRASH",
    "DataLoader worker exited": "WORKER_CRASH",
    "multiprocessing.spawn": "WORKER_SPAWN_FAILURE",
    "An attempt was made to access a socket in a way forbidden": "WORKER_INIT_FAILURE",
    "RuntimeError: DataLoader worker": "WORKER_INIT_FAILURE",
    "worker finished before startup complete": "WORKER_INIT_FAILURE",
    "deadlock detected": "DATALOADER_DEADLOCK",
    "worker loop": "DATALOADER_DEADLOCK",
    "CUDA out of memory": "GPU_OOM",
}

WORKER_REQ = 8  # R22A.2 Part B contract count


def classify_run(exit_code: int, output: str) -> dict:
    anomalies = sorted({fc for sig, fc in ANOMALY_SIGNATURES.items() if sig in output})
    if exit_code == 0 and not anomalies:
        return {"status": "PASS", "anomalies": []}
    return {"status": "FAIL", "anomalies": anomalies,
            "failure_classification": anomalies[0] if anomalies else "INCONCLUSIVE"}


# --- R22A.2 Part B: pure CPU-testable worker contract (mission §9) -----------

def evaluate_single_run(run: dict) -> dict:
    """Acceptance contract for ONE workers run (observed facts only)."""
    checks: list[dict] = []

    def check(name, ok, why):
        checks.append({"check": name, "ok": bool(ok), "detail": why})
        return bool(ok)

    synthetic = bool(run.get("harness_fixture")) or not run.get("gpu_name")
    if not check("physical_gpu_identity", not synthetic,
                 "synthetic/fixture evidence can never earn a physical PASS" if synthetic
                 else str(run.get("gpu_name"))):
        return {"verdict": "FAIL", "classification": "SYNTHETIC_EVIDENCE_REJECTED",
                "checks": checks}

    req = int(run.get("requested_workers") or 0)
    res = run.get("resolved_num_workers")
    res = int(res) if res is not None else None
    activity = bool(run.get("worker_activity_observed"))
    peak = int(run.get("peak_concurrent_workers") or 0)
    exit_code = run.get("exit_code")
    log = str(run.get("log_text") or "")
    done_marker = "STABILITY_CHILD_DONE" in log

    if not check("workers_requested_8", req == WORKER_REQ,
                 f"requested_workers={req} (contract={WORKER_REQ})"):
        return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET", "checks": checks}

    if res is None:
        return {"verdict": "FAIL", "classification": "MISSING_RESOLVED_WORKERS_EVIDENCE",
                "checks": checks + [{"check": "resolved_workers_evidence", "ok": False,
                                     "detail": "child did not report train_loader.num_workers"}]}
    if not check("workers_effective_8", res == WORKER_REQ,
                 f"resolved_num_workers={res} (requested {req})"):
        return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET", "checks": checks}

    if not check("worker_activity_observed", activity,
                 f"peak_concurrent_workers={peak} via OS process-tree snapshots"):
        return {"verdict": "INCONCLUSIVE",
                "classification": "WORKER_ACTIVITY_UNPROVEN", "checks": checks}

    if not check("peak_workers_reached_8", peak >= WORKER_REQ,
                 f"peak_concurrent_workers={peak} — all {WORKER_REQ} must actually run"):
        return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET", "checks": checks}

    if exit_code == 124:
        return {"verdict": "FAIL", "classification": "DATALOADER_TIMEOUT",
                "checks": checks + [{"check": "bounded_execution", "ok": False,
                                     "detail": "per-run timeout exceeded"}]}

    orphans = int(run.get("orphan_workers_alive") or 0)
    if orphans:
        return {"verdict": "FAIL", "classification": "WORKER_SHUTDOWN_FAILURE",
                "checks": checks + [{"check": "no_orphan_workers", "ok": False,
                                     "detail": f"{orphans} worker processes survived parent exit"}]}

    if exit_code != 0:
        cls = "WORKER_CRASH_AFTER_COMPLETE" if done_marker else "WORKER_CRASH"
        base = classify_run(int(exit_code), log)
        if base["status"] == "FAIL" and base.get("anomalies"):
            cls = base["failure_classification"]  # specific signature found
        return {"verdict": "FAIL", "classification": cls,
                "checks": checks + [{"check": "process_exit_zero", "ok": False,
                                     "detail": f"exit_code={exit_code}"}]}

    if not check("training_completed", done_marker, "STABILITY_CHILD_DONE marker present"):
        return {"verdict": "FAIL", "classification": "TRAINING_INCOMPLETE",
                "checks": checks}

    if not check("checkpoint_present", bool(run.get("checkpoint_exists")),
                 str(run.get("checkpoint_path"))):
        return {"verdict": "FAIL", "classification": "CHECKPOINT_MISSING", "checks": checks}

    return {"verdict": "PASS", "classification": None, "checks": checks}


def evaluate_workers_matrix(matrix: dict) -> dict:
    """Acceptance contract for the five-run workers=8 matrix (mission §8/§9)."""
    runs = matrix.get("runs") or []
    synthetic = bool(matrix.get("harness_fixture")) or not matrix.get("gpu_name")
    child_guard_ok = bool(matrix.get("child_has_main_guard"))

    if synthetic:
        return {"verdict": "NO_GO", "reason": "synthetic evidence can never earn a physical PASS"}
    if not child_guard_ok:
        return {"verdict": "NO_GO",
                "reason": "child script lacks Windows spawn __main__ guard"}

    if not runs:
        return {"verdict": "NO_GO", "reason": "no runs recorded"}

    verdicts = [evaluate_single_run(r) for r in runs]
    n_pass = sum(1 for v in verdicts if v["verdict"] == "PASS")
    timeouts = sum(1 for r in runs if int(r.get("exit_code") or 0) == 124)
    n_total = len(runs)

    cold_labels = [r.get("cache_class") for r in runs if r.get("cache_expectation") == "cold"]
    cold_homes = {r.get("home_dir") for r in runs if r.get("cache_expectation") == "cold"}
    warm_homes = {r.get("home_dir") for r in runs if r.get("cache_expectation") == "warm"}
    if len(cold_labels) > 1 and len(cold_homes) != len({r.get("run") for r in runs
                                                        if r.get("cache_expectation") == "cold"}):
        return {"verdict": "NO_GO",
                "reason": "cold runs must each use a FRESH isolated cache identity"}
    if len(warm_homes) > 1:
        return {"verdict": "NO_GO",
                "reason": "warm runs must SHARE one retained isolated cache identity"}

    if timeouts:
        return {"verdict": "NO_GO",
                "reason": f"{timeouts} run(s) timed out — a timeout fails even if "
                          "another run later succeeds",
                "run_verdicts": verdicts}
    if n_pass != n_total:
        return {"verdict": "NO_GO",
                "reason": f"{n_pass}/{n_total} runs PASS — one failure is overall NO-GO "
                          "(a diagnostic follow-up cannot erase it)",
                "run_verdicts": verdicts}
    if any(v["verdict"] == "INCONCLUSIVE" for v in verdicts):
        return {"verdict": "INCONCLUSIVE",
                "reason": "worker activity evidence inconclusive in at least one run",
                "run_verdicts": verdicts}
    return {"verdict": "WORKERS8_SHORT_RELIABILITY_PASS",
            "reason": f"all {n_total} runs PASS with workers={WORKER_REQ} verified "
                      "OS-level and clean shutdown",
            "run_verdicts": verdicts}


def child_has_main_guard(child_src: str) -> bool:
    return ('if __name__ == "__main__":' in child_src
            and "freeze_support()" in child_src
            and "def main():" in child_src)


# --- OS-level worker observation (mission §6) ---------------------------------

def _cim_python_procs() -> list[dict]:
    """Snapshot all python.exe PIDs/PPIDs via CIM (OS truth, no torch internals)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -Query \"SELECT ProcessId,ParentProcessId FROM "
             "Win32_Process WHERE Name='python.exe'\" | ConvertTo-Json -Compress"],
            capture_output=True, timeout=20, encoding="utf-8", errors="replace")
        txt = (out.stdout or "").strip()
        if not txt:
            return []
        data = json.loads(txt)
        if isinstance(data, dict):
            data = [data]
        return [{"pid": int(d["ProcessId"]), "ppid": int(d["ParentProcessId"])}
                for d in data]
    except Exception:
        return []


def descendants_of(pids: list[dict], root: int) -> set[int]:
    children: dict[int, set[int]] = {}
    for p in pids:
        children.setdefault(p["ppid"], set()).add(p["pid"])
    seen: set[int] = set()
    frontier = {root}
    while frontier:
        nxt = set()
        for pp in frontier:
            for c in children.get(pp, ()):  # direct children
                if c not in seen:
                    seen.add(c)
                    nxt.add(c)
        frontier = nxt
    return seen


class WorkerMonitor(threading.Thread):
    """Samples the OS process tree under the training child for its lifetime."""

    def __init__(self, root_pid: int, interval: float = 0.8):
        super().__init__(daemon=True)
        self.root_pid = root_pid
        self.interval = interval
        self.stop_event = threading.Event()
        self.samples = 0
        self.worker_pids_seen: set[int] = set()
        self.peak_concurrent = 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            procs = _cim_python_procs()
            self.samples += 1
            if procs:
                workers = descendants_of(procs, self.root_pid)
                self.worker_pids_seen |= workers
                self.peak_concurrent = max(self.peak_concurrent, len(workers))
            self.stop_event.wait(self.interval)


def orphan_scan(child_pid: int, worker_pids: set[int]) -> dict:
    """Detect surviving worker processes after the parent child exited."""
    time.sleep(2.0)  # bounded settle window
    procs = _cim_python_procs()
    parents = {child_pid} | set(worker_pids)
    alive = sorted(p["pid"] for p in procs if p["ppid"] in parents)
    return {"scanned_at": gp_lib.now_utc(), "orphan_pids": alive,
            "orphan_count": len(alive)}


def bounded_terminate(proc: subprocess.Popen, grace_s: float = 10.0) -> None:
    """Bounded, auditable shutdown of OUR OWN child process."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=grace_s)
            except subprocess.TimeoutExpired:
                pass


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--runs", type=int, default=3, help="independent processes (R22: 10; R22A.2 Part B: cold 2 / warm 3)")
    ap.add_argument("--cold", action="store_true",
                    help="fresh MIOpen cache identity per run (isolated USERPROFILE)")
    ap.add_argument("--warm-home", default=None,
                    help="warm runs share THIS retained isolated USERPROFILE "
                         "(never the user's global cache)")
    ap.add_argument("--workers", type=int, default=0,
                    help="DataLoader workers requested in the child (R22A.2 Part B: 8)")
    ap.add_argument("--data", default="coco8.yaml",
                    help="dataset (R22A.2 Part B: coco128 — 8 batches at batch=16 "
                         "so the framework actually creates 8 workers)")
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--per-run-timeout", type=int, default=900)
    args = ap.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    runs = []
    shim_removed = os.environ.pop("HIPRTC_COMPILE_OPTIONS_APPEND", None)
    warm_home = Path(args.warm_home).resolve() if args.warm_home else None
    if warm_home:
        warm_home.mkdir(parents=True, exist_ok=True)

    for i in range(1, args.runs + 1):
        run_dir = work / f"run{i:02d}"
        run_dir.mkdir(exist_ok=True)
        child = run_dir / "child.py"
        child_src = CHILD.format(device=args.device, project=run_dir,
                                 name="train", seed=100 + i, workers=args.workers,
                                 data=args.data, batch=args.batch, imgsz=args.imgsz)
        child.write_text(child_src, encoding="utf-8")
        env = dict(os.environ)
        cache_note = "warm(process-level)"
        home_dir = None
        if args.cold:
            fresh_home = run_dir / "home"
            fresh_home.mkdir(exist_ok=True)
            env["USERPROFILE"] = str(fresh_home)
            cache_note = "cold(fresh-USERPROFILE)"
            home_dir = str(fresh_home)
        elif warm_home:
            env["USERPROFILE"] = str(warm_home)
            cache_note = "warm(shared-isolated-USERPROFILE)"
            home_dir = str(warm_home)
        log = run_dir / "child.log"
        t1 = time.time()
        cmd = [sys.executable, "-I", str(child)]
        with open(log, "w", encoding="utf-8", errors="replace") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                    cwd=str(run_dir), env=env,
                                    text=True, encoding="utf-8", errors="replace")
            pid = proc.pid
            mon = WorkerMonitor(pid) if args.workers > 0 else None
            if mon:
                mon.start()
            deadline = time.monotonic() + args.per_run_timeout
            timed_out = False
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    timed_out = True
                    bounded_terminate(proc)
                    break
                time.sleep(0.5)
            if mon:
                mon.stop_event.set()
                mon.join(timeout=10)
        rc = 124 if timed_out else (proc.returncode if proc.returncode is not None else -1)
        dur = round(time.time() - t1, 1)
        out = log.read_text(encoding="utf-8", errors="replace")
        orphans = orphan_scan(pid, mon.worker_pids_seen) if mon else None

        m = re.search(r"R22A2_WORKERS resolved=(-?\d+) n_batches=(\d+) amp=(\w+) "
                      r"optimizer=(\S+) requested=(\d+)", out)
        resolved_nw = int(m.group(1)) if m else None
        n_batches = int(m.group(2)) if m else None
        amp_seen = (m.group(3) == "True") if m else None
        opt_seen = m.group(4) if m else None
        ckpt = run_dir / "train" / "weights" / "last.pt"

        run_rec = {
            "run": i, "command": f"{sys.executable} -I child.py (workers={args.workers})",
            "pid": pid, "started_utc": gp_lib.now_utc(),
            "exit_code": rc, "duration_s": dur,
            "cache_class": cache_note, "home_dir": home_dir,
            "cache_expectation": "cold" if args.cold else "warm",
            "requested_workers": args.workers,
            "resolved_num_workers": resolved_nw,
            "resolved_n_batches": n_batches,
            "amp_enabled_child": amp_seen,
            "optimizer_class_child": opt_seen,
            "worker_activity_observed": bool(mon.worker_pids_seen) if mon else None,
            "worker_pids_observed": sorted(mon.worker_pids_seen) if mon else [],
            "peak_concurrent_workers": mon.peak_concurrent if mon else None,
            "monitor_samples": mon.samples if mon else None,
            "orphan_workers_alive": (orphans or {}).get("orphan_count"),
            "orphan_scan": orphans,
            "checkpoint_path": str(ckpt),
            "checkpoint_exists": ckpt.exists(),
            "log": str(log),
            "log_sha256": hashlib.sha256(out.encode("utf-8", "replace")).hexdigest(),
            "log_text": out[-20000:],
            "child_has_main_guard": child_has_main_guard(child_src),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
            "torch": torch.__version__,
        }
        verdict = classify_run(rc, out) if args.workers <= 0 else evaluate_single_run(run_rec)
        if args.workers <= 0:
            run_rec.update(verdict)
        else:
            run_rec["status"] = verdict["verdict"]
            run_rec["failure_classification"] = verdict.get("classification")
            run_rec["worker_contract_checks"] = verdict["checks"]
        runs.append(run_rec)
        peak = (mon.peak_concurrent if mon else None)
        print(f"[run {i}/{args.runs}] exit={rc} {run_rec['status']} "
              f"resolved_workers={resolved_nw} peak={peak} "
              f"{run_rec.get('anomalies') or ''} ({dur}s)")

    n_pass = sum(1 for r in runs if r["status"] == "PASS")
    tally: dict[str, int] = {}
    for r in runs:
        for a in r.get("anomalies", []):
            tally[a] = tally.get(a, 0) + 1

    if args.workers <= 0:
        verdict = "PASS" if n_pass == len(runs) and runs else "FAIL"
        failure_classification = (tally and next(iter(tally))) or None
    else:
        matrix = evaluate_workers_matrix({
            "runs": runs,
            "child_has_main_guard": all(r["child_has_main_guard"] for r in runs),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        })
        verdict = "PASS" if matrix["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS" else "FAIL"
        failure_classification = matrix.get("reason")

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), args.channel,
            (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None)),
        "command": f"python run_stability.py --runs {args.runs} "
                   f"{'--cold' if args.cold else ('--warm-home ' + str(warm_home) if warm_home else '--warm')} "
                   f"--device {args.device} --workers {args.workers} --data {args.data}",
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": failure_classification if verdict == "FAIL" else None,
        "raw_log_path": str(work / "stability_runs.json"),
        "runs": runs, "n_pass": n_pass, "n_total": len(runs),
        "anomaly_tally": tally,
        "workers_requested": args.workers,
        "cache_class": ("cold(fresh-USERPROFILE per run)" if args.cold
                        else ("warm(shared-isolated-USERPROFILE)" if warm_home else "warm")),
        "child_spawn_safety": {
            "main_guard_present": all(r["child_has_main_guard"] for r in runs),
            "freeze_support": "freeze_support()" in CHILD,
            "note": "Windows spawn re-imports child.py in every worker; the guard "
                    "prevents recursive training processes",
        },
        "environment_disclosure": {
            "hiprtc_compile_options_append_removed_from_child_env": shim_removed,
            "note": "host-level shim var (if present) is stripped from child env so "
                    "runs execute on the official stack unmodified; global env untouched",
        },
        "note": "independent training PROCESSES; cache classes tracked separately; "
                "unexplained kernel/runtime failures block stable readiness",
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    slim = [{k: v for k, v in r.items() if k != "log_text"} for r in runs]
    (work / "stability_runs.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")
    gp_lib.write_evidence(record, Path(args.out))
    print(f"STABILITY: {verdict} ({n_pass}/{len(runs)})")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
