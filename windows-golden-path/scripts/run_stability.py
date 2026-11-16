# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Reliability runner (missions §8 R21-F smoke / §14 R22 ≥10 runs per arch).

Runs N INDEPENDENT short training processes (exact standard command shape),
classifying each run and tallying anomaly families separately — an
unexplained kernel/runtime failure blocks stable Golden Path readiness and is
never assumed fixed by MIOpen #13437.

Cold vs warm cache are distinct evidence classes: a fresh Python process is
NOT a cold MIOpen cache. --cold runs redirect USERPROFILE to a per-run fresh
home (the user's global cache is never touched or deleted).

R22A.3 Part B extension (minimal, default-preserving): optional --workers
(default 0 — the historical test is unchanged), optional --data/--batch/--imgsz
(defaults keep the historical coco8 command), and a spawn-safe generated child
( __main__ guard + freeze_support; no import-time training). When workers>0
the parent monitors the child's process tree (psutil, bounded polling) to
capture real Windows worker-process PIDs/lifetimes, verify clean worker
shutdown after parent exit (no orphans), and classify worker-family failures.
--warm-home redirects warm runs to one RETAINED isolated cache identity shared
by every warm run (still never touching the user's global cache).

Bounded execution: per-run timeout + overall wall budget; no retry loops.

    python run_stability.py --out stability.json --run-id R22-G8 --runs 10 [--cold]
    python run_stability.py --out workers8.json --run-id R22A3-B --runs 5 \
        --cold-runs 2 --workers 8 --data coco128.yaml --batch 16 --imgsz 256 \
        --warm-home <retained dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

CHILD = r'''
"""Generated child training script (R22A.3: spawn-safe — Windows DataLoader
workers re-import this module; without the __main__ guard each worker would
recursively launch training)."""
import json
import multiprocessing
import os
import sys
import time

FACTS_PATH = r"{facts_path}"
RUN_ID = r"{run_id}"
t0 = time.time()


def main():
    facts = {{"run_id": RUN_ID, "child_pid": os.getpid(), "parent_pid": os.getppid(),
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "userprofile_env": os.environ.get("USERPROFILE")}}
    batches = {{"n": 0}}
    from ultralytics import YOLO
    import torch
    import ultralytics
    m = YOLO("yolo26n.pt")

    def _put(**kw):
        facts.update(kw)
        with open(FACTS_PATH, "w", encoding="utf-8") as f:
            json.dump(facts, f)

    _put(torch=torch.__version__, hip=torch.version.hip,
         ultralytics=ultralytics.__version__,
         device_name=(torch.cuda.get_device_name(0) if torch.cuda.device_count() else None),
         train_args={{"data": "{data}", "epochs": 1, "workers": {workers}, "device": {device},
                      "batch": "{batch_arg}", "imgsz": "{imgsz_arg}"}})

    def on_start(trainer):
        try:
            nw_train = getattr(trainer.train_loader, "num_workers", None)
        except Exception:
            nw_train = None
        _put(resolved_num_workers_train=nw_train,
             requested_workers=trainer.args.workers,
             amp_resolved=bool(trainer.amp),
             optimizer=trainer.args.optimizer,
             effective_batch=trainer.batch_size)

    def on_batch_end(trainer):
        batches["n"] += 1
        if batches["n"] % 4 == 0:
            _put(batches_completed=batches["n"])

    def on_fit_epoch_end(trainer):
        _put(fit_epochs=(facts.get("fit_epochs") or 0) + 1,
             metrics_present=bool(trainer.metrics),
             val_num_workers=(getattr(trainer.test_loader, "num_workers", None)
                              if getattr(trainer, "test_loader", None) else None))

    for cb, fn in (("on_train_start", on_start), ("on_train_batch_end", on_batch_end),
                   ("on_fit_epoch_end", on_fit_epoch_end)):
        m.add_callback(cb, fn)

    r = m.train(data="{data}", epochs=1, device={device}, project=r"{project}",
                name=r"{name}", exist_ok=True, seed={seed}, workers={workers},
                verbose=True{extra})
    import hashlib

    def _sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    ckpt = m.trainer.save_dir / "weights" / "last.pt"
    _put(batches_completed=batches["n"], training_completed=True,
         results_keys=sorted(r.results_dict.keys()) if hasattr(r, "results_dict") else None,
         val_completed=bool(facts.get("metrics_present")),
         checkpoint_path=str(ckpt), checkpoint_exists=bool(ckpt.exists()),
         checkpoint_sha256=(_sha(ckpt) if ckpt.exists() else None),
         finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print(f"STABILITY_CHILD_DONE {{time.time()-t0:.1f}}s")


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
    # worker-family signatures (R22A.3 Part B)
    "DataLoader worker (pid": "WORKER_CRASH",
    "exited unexpectedly": "WORKER_CRASH",
    "failed to start": "WORKER_SPAWN_FAILURE",
    "DataLoader worker exited with": "WORKER_CRASH",
    "out of memory": "GPU_OOM",
    "DataLoader interpreter shutdown": "WORKER_SHUTDOWN_FAILURE",
}


def child_spawn_safe(source: str) -> tuple[bool, str | None]:
    """Structural spawn-safety check for the generated child (mission §8).

    Windows DataLoader workers re-import the child module: without the
    __main__ guard, each worker would recursively launch training. Reject
    (do not run) any generated child that trains at import time.
    """
    if 'if __name__ == "__main__":' not in source \
            and "if __name__ == '__main__':" not in source:
        return False, "missing __main__ guard"
    if "freeze_support()" not in source:
        return False, "missing multiprocessing.freeze_support()"
    for ln in source.splitlines():
        s = ln.strip()
        if ".train(" in s and not ln[: len(ln) - len(ln.lstrip())]:
            return False, f"module-level train() call: {s[:60]!r}"
        if s.startswith(("YOLO(", "m = YOLO")) and not ln[: len(ln) - len(ln.lstrip())]:
            return False, f"module-level YOLO() call: {s[:60]!r}"
    return True, None


def classify_run(exit_code: int, output: str) -> dict:
    anomalies = sorted({fc for sig, fc in ANOMALY_SIGNATURES.items() if sig in output})
    if exit_code == 0 and not anomalies:
        return {"status": "PASS", "anomalies": []}
    if exit_code == 124:
        return {"status": "FAIL", "anomalies": anomalies or ["DATALOADER_TIMEOUT"],
                "failure_classification": anomalies[0] if anomalies else "DATALOADER_TIMEOUT"}
    return {"status": "FAIL", "anomalies": anomalies,
            "failure_classification": anomalies[0] if anomalies else "INCONCLUSIVE"}


class TreeMonitor:
    """Bounded psutil process-tree sampler (parent-side, read-only)."""

    def __init__(self, root_pid: int, interval: float = 1.2):
        import psutil  # noqa: PLC0415
        self._psutil = psutil
        self.root_pid = root_pid
        self.interval = interval
        self._stop = threading.Event()
        self.samples: dict[int, dict] = {}
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _snapshot_once(self) -> list[int]:
        alive: list[int] = []
        try:
            kids = self._psutil.Process(self.root_pid).children(recursive=True)
        except Exception:
            return alive
        now = time.time()
        for p in kids:
            alive.append(p.pid)
            rec = self.samples.setdefault(p.pid, {
                "pid": p.pid, "ppid": None,
                "name": None, "first_seen": now, "last_seen": now, "sightings": 0})
            rec["sightings"] += 1
            rec["last_seen"] = now
            try:  # workers legitimately exit mid-run — never let the sampler die
                rec["ppid"] = p.ppid()
                rec["name"] = p.name()
                rec["create_time"] = p.create_time()
            except Exception:
                pass
        return alive

    def _run(self):
        while not self._stop.is_set():
            self._snapshot_once()
            self._stop.wait(self.interval)

    def start(self):
        self._thread.start()

    def stop(self, timeout: float = 5.0):
        self._stop.set()
        self._thread.join(timeout)

    def descendants_summary(self) -> dict:
        return {"distinct_descendant_pids": len(self.samples),
                "descendants": sorted(self.samples.values(), key=lambda r: r["first_seen"])}

    def lingering(self, wait_s: float = 30.0, interval: float = 1.5) -> list[int]:
        """Known descendant PIDs still alive after the parent exited.

        The root pid is gone at this point, so tree descent from it is useless
        here — the KNOWN descendant pids are checked directly instead.
        """
        deadline = time.time() + wait_s
        while time.time() < deadline:
            alive = [pid for pid in self.samples if self._psutil.pid_exists(pid)]
            if not alive:
                return []
            time.sleep(interval)
        return sorted(pid for pid in self.samples if self._psutil.pid_exists(pid))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def finalize_worker_run(base: dict) -> tuple[str, str | None]:
    """Pure workers>0 run-verdict amendment (CPU-testable; mission §7/§9/§10).

    The underlying process classification (classify_run) stands; a clean
    process exit is only the START of acceptance: the resolved loader worker
    count must equal the request, real worker-process PID evidence must exist,
    workers must shut down with the parent (no orphans), the native exit code
    must be recorded, and a cold-labeled run must carry isolated-cache
    identity evidence.
    """
    if base.get("status") != "PASS":
        return base.get("status", "INCONCLUSIVE"), base.get("failure_classification")
    if base.get("exit_code") is None:
        return "FAIL", "MISSING_PROCESS_EXIT_CODE"
    if base.get("resolved_num_workers") != base.get("requested_workers"):
        return "FAIL", "WORKER_COUNT_NOT_MET"
    if not base.get("distinct_worker_pids"):
        return "INCONCLUSIVE", "NO_WORKER_PID_EVIDENCE"
    if (base.get("distinct_worker_pids") or 0) < (base.get("resolved_num_workers") or 0):
        return "INCONCLUSIVE", "PARTIAL_WORKER_PID_EVIDENCE"
    if base.get("worker_shutdown") != "CLEAN":
        return "FAIL", "WORKER_SHUTDOWN_FAILURE"
    if "cold(" in (base.get("cache_class") or "") and not base.get("cold_identity_verified"):
        return "FAIL", "COLD_LABEL_WITHOUT_CACHE_IDENTITY_EVIDENCE"
    return "PASS", None


def overall_workers8_verdict(runs: list, cold_expected: int, warm_expected: int) -> dict:
    """Pure Part-B overall verdict: five planned runs, cold 2/2 AND warm 3/3,
    every run individually PASS, no substitutions (mission §9/§13)."""
    planned = cold_expected + warm_expected
    problems = []
    if len(runs) != planned:
        problems.append(f"run count {len(runs)} != planned {planned}")
    if len({r.get("run_id") for r in runs}) != len(runs):
        problems.append("duplicate run_ids")
    cold = [r for r in runs if "cold(" in (r.get("cache_class") or "")]
    warm = [r for r in runs if "warm" in (r.get("cache_class") or "")]
    cold_pass = sum(1 for r in cold if r.get("status") == "PASS")
    warm_pass = sum(1 for r in warm if r.get("status") == "PASS")
    if len(cold) != cold_expected:
        problems.append(f"cold runs {len(cold)} != {cold_expected}")
    if len(warm) != warm_expected:
        problems.append(f"warm runs {len(warm)} != {warm_expected}")
    if cold_pass != cold_expected:
        problems.append(f"cold {cold_pass}/{len(cold)} (need {cold_expected}/{cold_expected})")
    if warm_pass != warm_expected:
        problems.append(f"warm {warm_pass}/{len(warm)} (need {warm_expected}/{warm_expected})")
    verdict = "WORKERS8_SHORT_RELIABILITY_PASS" if not problems else "NO-GO"
    return {"verdict": verdict, "problems": problems,
            "cold_pass": f"{cold_pass}/{len(cold)}",
            "warm_pass": f"{warm_pass}/{len(warm)}",
            "n_planned": planned}


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--runs", type=int, default=3, help="independent processes (R22: 10; R22A.3 Part B: 5)")
    ap.add_argument("--cold", action="store_true",
                    help="fresh MIOpen cache identity per run (isolated USERPROFILE)")
    ap.add_argument("--cold-runs", type=int, default=None,
                    help="R22A.3: first N runs cold, remaining runs warm (shared --warm-home)")
    ap.add_argument("--warm-home", default=None,
                    help="retained isolated USERPROFILE shared by warm runs (never the user's global cache)")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--workers", type=int, default=0,
                    help="DataLoader workers requested in the child train() call (default 0 = historical)")
    ap.add_argument("--data", default="coco8.yaml")
    ap.add_argument("--batch", type=int, default=None, help="default: framework default (historical)")
    ap.add_argument("--imgsz", type=int, default=None, help="default: framework default (historical)")
    ap.add_argument("--per-run-timeout", type=int, default=900)
    ap.add_argument("--overall-budget", type=int, default=5400)
    ap.add_argument("--weights", default=None,
                    help="local yolo26n.pt to copy into each run dir (removes network "
                         "dependence; default None = child resolves as before)")
    args = ap.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    warm_home = Path(args.warm_home).resolve() if args.warm_home else None
    if warm_home:
        warm_home.mkdir(parents=True, exist_ok=True)
    cold_runs = args.cold_runs if args.cold_runs is not None else (args.runs if args.cold else 0)

    def source_head() -> str | None:
        try:
            return subprocess.run(["git", "rev-parse", "HEAD"],
                                  cwd=str(Path(__file__).resolve().parents[2]),
                                  capture_output=True, text=True, timeout=15).stdout.strip() or None
        except Exception:
            return None

    head = source_head()
    lock_path = Path(__file__).resolve().parents[2] / "evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json"
    lock_sha = gp_lib.sha256_file(lock_path) if lock_path.exists() else None
    _miopen_rec = gp_lib.loaded_miopen_identity()

    t0 = time.time()
    runs = []
    for i in range(1, args.runs + 1):
        if time.time() - t0 > args.overall_budget:
            runs.append({"run": i, "status": "SKIP",
                         "failure_classification": "DATALOADER_TIMEOUT",
                         "note": "overall wall budget exhausted before this run started"})
            continue
        run_dir = work / f"run{i:02d}"
        run_dir.mkdir(exist_ok=True)
        run_id = f"{args.run_id}-R{i}"
        is_cold = i <= cold_runs
        extra = ""
        if args.batch is not None:
            extra += f", batch={args.batch}"
        if args.imgsz is not None:
            extra += f", imgsz={args.imgsz}"
        child = run_dir / "child.py"
        if args.weights and not (run_dir / "yolo26n.pt").exists():
            shutil.copy(args.weights, run_dir / "yolo26n.pt")
        child.write_text(CHILD.format(
            device=args.device, project=run_dir, name="train", seed=100 + i,
            workers=args.workers, data=args.data, extra=extra,
            facts_path=run_dir / "child_facts.json", run_id=run_id,
            batch_arg=str(args.batch), imgsz_arg=str(args.imgsz)), encoding="utf-8")
        safe, why = child_spawn_safe(child.read_text(encoding="utf-8"))
        if not safe:
            runs.append({"run": i, "run_id": f"{args.run_id}-R{i}", "status": "FAIL",
                         "failure_classification": f"CHILD_SCRIPT_UNSAFE: {why}",
                         "cache_class": cache_note, "log": str(log)})
            (run_dir / "run_record.json").write_text(
                json.dumps(runs[-1], indent=2), encoding="utf-8")
            print(f"[run {i}/{args.runs}] REJECTED child script: {why}")
            continue
        env = dict(os.environ)
        if is_cold:
            fresh_home = run_dir / "home"
            fresh_home.mkdir(exist_ok=True)
            env["USERPROFILE"] = str(fresh_home)
            cache_note = "cold(fresh-USERPROFILE, run-isolated)"
        elif warm_home is not None:
            env["USERPROFILE"] = str(warm_home)
            cache_note = f"warm(retained isolated home shared by warm runs: {warm_home})"
        else:
            cache_note = "warm(process-level)"
        log = run_dir / "child.log"
        t1 = time.time()
        monitor = None
        spawned = False
        child_pid = None
        try:
            proc = subprocess.Popen([sys.executable, "-I", str(child)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace",
                                    cwd=str(run_dir), env=env)
            spawned, child_pid = True, proc.pid
            if args.workers > 0:
                monitor = TreeMonitor(proc.pid)
                monitor.start()
            try:
                out, _ = proc.communicate(timeout=args.per_run_timeout)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
                rc = 124
        except Exception as e:  # spawn-level failure of the parent process itself
            rc, out = 1, f"PARENT_SPAWN_ERROR {type(e).__name__}: {e}"
        dur = round(time.time() - t1, 1)
        log.write_text(out, encoding="utf-8", errors="replace")
        verdict = classify_run(rc, out)

        # worker lifecycle evidence (parent-side, bounded)
        lifecycle = {"monitored": False}
        worker_shutdown = "NOT_APPLICABLE(workers=0)" if args.workers == 0 else None
        if monitor is not None:
            monitor.stop()
            lingering = monitor.lingering()
            lifecycle = {"monitored": True, **monitor.descendants_summary()}
            lifecycle["lingering_after_parent_exit"] = lingering
            worker_shutdown = "CLEAN" if not lingering else \
                f"ORPHANS({len(lingering)}): {lingering}"

        facts = {}
        fp = run_dir / "child_facts.json"
        if fp.exists():
            try:
                facts = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                facts = {"error": "unreadable facts file"}

        rec = {
            "run": i, "run_id": run_id, "exit_code": rc, "duration_s": dur,
            "cache_class": cache_note, "log": str(log),
            "start_utc": datetime.fromtimestamp(t1, tz=timezone.utc).isoformat(),
            "end_utc": datetime.now(tz=timezone.utc).isoformat(),
            "parent_pid": child_pid, "child_pid": facts.get("child_pid"),
            "source_sha": head, "wheel_lock_sha256": lock_sha,
            "requested_workers": args.workers,
            "resolved_num_workers": facts.get("resolved_num_workers_train"),
            "val_num_workers": facts.get("val_num_workers"),
            "worker_pids": ([d["pid"] for d in lifecycle.get("descendants", [])]
                            if lifecycle.get("monitored") else []),
            "distinct_worker_pids": lifecycle.get("distinct_descendant_pids"),
            "worker_shutdown": worker_shutdown,
            "batches_completed": facts.get("batches_completed", 0),
            "training_completed": facts.get("training_completed", False),
            "val_completed": facts.get("val_completed", False),
            "checkpoint_exists": facts.get("checkpoint_exists", False),
            "checkpoint_sha256": facts.get("checkpoint_sha256"),
            "amp_resolved": facts.get("amp_resolved"),
            "optimizer": facts.get("optimizer"),
            "device_name": facts.get("device_name"),
            "torch": facts.get("torch"), "hip": facts.get("hip"),
            "raw_log_sha256": sha256_text(out),
            "spawned_by_parent": spawned,
            "process_lifecycle": lifecycle,
            "userprofile_env": facts.get("userprofile_env"),
            "cold_identity_verified": (not is_cold) or (
                bool(facts.get("userprofile_env"))
                and str(facts.get("userprofile_env")).lower().startswith(
                    str(run_dir).lower())),
            **verdict,
        }
        if args.workers > 0:  # workers>0 acceptance amendments (pure function)
            rec["status"], rec["failure_classification"] = finalize_worker_run(rec)
        runs.append(rec)
        (run_dir / "run_record.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
        print(f"[run {i}/{args.runs}] exit={rc} {rec['status']} "
              f"{rec.get('anomalies') or ''} nw={rec['resolved_num_workers']} "
              f"wpids={rec['distinct_worker_pids']} ({dur}s)")

    n_pass = sum(1 for r in runs if r["status"] == "PASS")
    tally: dict[str, int] = {}
    for r in runs:
        for a in r.get("anomalies", []):
            tally[a] = tally.get(a, 0) + 1
    verdict = "PASS" if n_pass == len(runs) and runs else "FAIL"
    workers8_overall = None
    if args.workers > 0:
        warm_expected = max(len(runs) - cold_runs, 0)
        workers8_overall = overall_workers8_verdict(runs, cold_runs, warm_expected)
        verdict = "PASS" if workers8_overall["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS" \
            else "FAIL"

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "source_sha": head,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "ultralytics": im.version("ultralytics"),
        "wheel_lock_sha256": lock_sha,
        "loaded_miopen_dll_sha256": (_m2.get("sha256") if (_m2 := _miopen_rec).get("loaded") else None),
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), args.channel,
            (_m if (_m := _miopen_rec).get("loaded") else None)),
        "command": f"python run_stability.py --runs {args.runs} "
                   f"--cold-runs {cold_runs} --workers {args.workers} "
                   f"--data {args.data} --device {args.device}"
                   + (f" --warm-home {warm_home}" if warm_home else ""),
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": (tally and next(iter(tally))) or None if verdict == "FAIL" else None,
        "raw_log_path": str(work / "stability_runs.json"),
        "runs": runs, "n_pass": n_pass, "n_total": len(runs),
        "anomaly_tally": tally,
        "requested_workers": args.workers,
        "workers8_overall": workers8_overall,
        "cold_runs": cold_runs,
        "warm_runs": len(runs) - cold_runs,
        "cache_class": (f"cold {cold_runs} (fresh-USERPROFILE per run) / "
                        f"warm {len(runs) - cold_runs} "
                        + (f"(retained shared home {warm_home})" if warm_home else "(process-level)")),
        "note": "independent training PROCESSES; cache classes tracked separately; "
                "unexplained kernel/runtime failures block stable readiness",
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    (work / "stability_runs.json").write_text(
        json.dumps(runs, indent=2, default=repr), encoding="utf-8")
    try:
        gp_lib.write_evidence(record, Path(args.out))
    except Exception as e:  # a receipt MUST exist even if the strict writer objects
        Path(args.out).write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=repr), encoding="utf-8")
        print(f"WRITE_EVIDENCE_STRICT_FAILED ({type(e).__name__}: {e}) — "
              "fallback receipt written", file=sys.stderr)
    print(f"STABILITY: {verdict} ({n_pass}/{len(runs)})")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
