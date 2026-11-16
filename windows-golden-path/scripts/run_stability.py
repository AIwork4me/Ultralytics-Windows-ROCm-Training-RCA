# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Reliability runner — UNIFIED implementation (missions §8 R21-F smoke /
§14 R22 ≥10 runs per arch / R22A.2 Part B / R22A.3 Part B / R22A.4 §7).

Runs N INDEPENDENT short training processes (exact standard command shape),
classifying each run and tallying anomaly families separately — an
unexplained kernel/runtime failure blocks stable Golden Path readiness and is
never assumed fixed by MIOpen #13437.

Cold vs warm cache are distinct evidence classes: a fresh Python process is
NOT a cold MIOpen cache. --cold runs redirect USERPROFILE to a per-run fresh
home; --warm-home redirects to a SHARED retained isolated home (warm runs
share one cache identity without touching the user's global cache). The first
use of a fresh shared home is a CACHE_PRIMING run, never a pre-warmed one
(R22A.2.1 P0-D / R22A.4 §5).

Unified workers contract (R22A.4):
  - --workers N (default 0 — historical G8 contract byte-compatible)
  - spawn-safe generated child (`__main__` guard + freeze_support) whose
    module-level statements cannot train; the runner REFUSES an unsafe child
  - the child records resolved `train_loader.num_workers` to a facts file;
    the parent additionally observes OS-level worker subprocess activity
    (psutil tree sampling with a CIM fallback) recording per-identity
    lifetimes keyed by (pid, create_time) — distinct identities are never
    over-interpreted as simultaneous workers (peak concurrency is measured
    separately) and the parent training process is never counted as a worker
  - the worker monitor has EXPLICIT failure semantics (R22A.4 §4):
      * psutil.NoSuchProcess between children()/ppid() is an expected
        Windows process-lifecycle race -> MONITOR_PROCESS_EXIT_RACE
        (recorded, sampler survives)
      * psutil.ZombieProcess / psutil.AccessDenied recorded distinctly
      * anything else -> MONITOR_INTERNAL_FAILURE (counted; acceptance
        fails closed unless independent lifecycle evidence substantiates
        the runs)
      * monitor health state is always recorded:
        monitoring_started / monitoring_completed / thread_alive_at_shutdown
        / unexpected_exception_count / observation_samples /
        first_observation / last_observation
      * bounded monitor shutdown; orphan detection is PID-reuse aware
  - per-run timeout bounded; a timeout fails even if later runs succeed

    python run_stability.py --out stability.json --run-id R22A4-B \
        --runs 5 --cold-runs 2 --workers 8 --data coco128.yaml --batch 16 \
        --imgsz 256 --warm-home <retained dir> --work-dir <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

# Spawn-safe generated child: every executable statement lives inside main();
# the __main__ guard (+ freeze_support) makes import-time side effects
# impossible, so DataLoader workers re-importing this module cannot recurse
# into training. Facts are written to a JSON file (authoritative per-run
# evidence: resolved workers, batches, checkpoint identity, timestamps).
CHILD = r'''
"""Generated child training script (spawn-safe; facts-file evidence)."""
import hashlib
import json
import multiprocessing
import os
import time

FACTS_PATH = r"{facts_path}"
RUN_ID = r"{run_id}"
T0 = time.time()


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
         train_args={{"data": "{data}", "epochs": 1, "workers": {workers},
                      "device": {device}, "batch": "{batch_arg}", "imgsz": "{imgsz_arg}"}})

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

    for cb, fn in (("on_train_start", on_start),
                   ("on_train_batch_end", on_batch_end),
                   ("on_fit_epoch_end", on_fit_epoch_end)):
        m.add_callback(cb, fn)

    r = m.train(data="{data}", epochs=1, device={device}, project=r"{project}",
                name=r"{name}", exist_ok=True, seed={seed}, workers={workers},
                verbose=True{extra})

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
    print(f"STABILITY_CHILD_DONE {{time.time() - T0:.1f}}s")


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
    # worker/process failure families (R22A.2 §8 / R22A.3 §7)
    "DataLoader worker (pid": "WORKER_CRASH",
    "exited unexpectedly": "WORKER_CRASH",
    "DataLoader worker exited": "WORKER_CRASH",
    "multiprocessing.spawn": "WORKER_SPAWN_FAILURE",
    "failed to start": "WORKER_SPAWN_FAILURE",
    "An attempt was made to access a socket in a way forbidden": "WORKER_INIT_FAILURE",
    "RuntimeError: DataLoader worker": "WORKER_INIT_FAILURE",
    "worker finished before startup complete": "WORKER_INIT_FAILURE",
    "deadlock detected": "DATALOADER_DEADLOCK",
    "worker loop": "DATALOADER_DEADLOCK",
    "DataLoader interpreter shutdown": "WORKER_SHUTDOWN_FAILURE",
    "CUDA out of memory": "GPU_OOM",
    "out of memory": "GPU_OOM",
}

WORKER_REQ = 8  # supplemental Part-B contract count

# Documented BENIGN diagnostics (R22A.2.1 P0-C): matched against the raw log
# on EVERY path — including exit_code == 0 — classified with rationale and
# preserved verbatim, never silently discarded and never fatal. Membership is
# evidence-grounded: each entry cites where it was observed completing cleanly.
BENIGN_DOCUMENTED = {
    "MIOpen: Error [EvaluateInvokers]": {
        "classification": "MIOPEN_FIND_TIMING_DIAGNOSTIC",
        "rationale": "MIOpen solver-find timing diagnostic emitted during "
                     "first-use kernel-finder evaluation; observed ONLY in "
                     "cache-priming runs (r22a2 cold_run01 / warm_run01), "
                     "both of which completed exit 0 with full training, "
                     "validation and checkpoints — the finder discards the "
                     "invalid elapsed-time entry and continues",
    },
}


def _raw_line(log_text: str, signature: str) -> str:
    for ln in log_text.splitlines():
        if signature in ln:
            return ln[:300]
    return signature


def scan_run_anomalies(log_text: str) -> dict:
    """Scan a raw run log for fatal signatures AND documented benign
    diagnostics. Fatal signatures fail the run regardless of exit code; benign
    ones are recorded with rationale and raw text."""
    fatal = [{"signature": sig, "classification": fc,
              "raw_line": _raw_line(log_text, sig)}
             for sig, fc in ANOMALY_SIGNATURES.items() if sig in log_text]
    benign = [{"signature": sig, "classification": meta["classification"],
               "rationale": meta["rationale"],
               "raw_line": _raw_line(log_text, sig)}
              for sig, meta in BENIGN_DOCUMENTED.items() if sig in log_text]
    return {"fatal": fatal, "benign": benign}


def classify_run(exit_code: int, output: str) -> dict:
    anomalies = sorted({fc for sig, fc in ANOMALY_SIGNATURES.items() if sig in output})
    if exit_code == 0 and not anomalies:
        return {"status": "PASS", "anomalies": []}
    if exit_code == 124:
        return {"status": "FAIL", "anomalies": anomalies or ["DATALOADER_TIMEOUT"],
                "failure_classification": anomalies[0] if anomalies
                else "DATALOADER_TIMEOUT"}
    return {"status": "FAIL", "anomalies": anomalies,
            "failure_classification": anomalies[0] if anomalies else "INCONCLUSIVE"}


# --- spawn safety (R22A.2 matrix gate + R22A.3 refuse-to-run check) ----------

def child_has_main_guard(child_src: str) -> bool:
    return ('if __name__ == "__main__":' in child_src
            and "freeze_support()" in child_src
            and "def main():" in child_src)


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
        module_level = not ln[: len(ln) - len(ln.lstrip())]
        if ".train(" in s and module_level:
            return False, f"module-level train() call: {s[:60]!r}"
        if s.startswith(("YOLO(", "m = YOLO")) and module_level:
            return False, f"module-level YOLO() call: {s[:60]!r}"
    return True, None


# --- OS-level worker observation (unified R22A.4 §4/§6) -----------------------

MONITOR_EXIT_RACE = "MONITOR_PROCESS_EXIT_RACE"
MONITOR_ZOMBIE = "MONITOR_ZOMBIE_PROCESS"
MONITOR_ACCESS_DENIED = "MONITOR_ACCESS_DENIED"
MONITOR_INTERNAL_FAILURE = "MONITOR_INTERNAL_FAILURE"


def _cim_python_procs() -> list[dict]:
    """Snapshot python.exe PID/PPID/creation-time via CIM (OS truth; fallback
    backend when psutil is unavailable)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -Query \"SELECT ProcessId,ParentProcessId,CreationDate "
             "FROM Win32_Process WHERE Name='python.exe'\" | ConvertTo-Json -Compress"],
            capture_output=True, timeout=20, encoding="utf-8", errors="replace")
        txt = (out.stdout or "").strip()
        if not txt:
            return []
        data = json.loads(txt)
        if isinstance(data, dict):
            data = [data]
        procs = []
        for d in data:
            try:
                ct = None
                raw_ct = d.get("CreationDate")
                if raw_ct:
                    from datetime import datetime, timezone
                    ct = datetime.fromisoformat(str(raw_ct)).timestamp()
            except Exception:
                ct = None
            procs.append({"pid": int(d["ProcessId"]),
                          "ppid": int(d["ParentProcessId"]), "create_time": ct})
        return procs
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
    """Unified OS process-tree sampler with EXPLICIT failure semantics.

    Expected disappearance races (a process exits between children() and
    ppid()/create_time()) are recorded as MONITOR_PROCESS_EXIT_RACE and never
    kill the sampler; the historical R22A.3 defect — a NoSuchProcess traceback
    silently ending the sampling thread while the receipt still certified
    full coverage — is structurally impossible here: the loop cannot die
    silently, health state is always recorded, and acceptance consumes it
    fail-closed. Identities are keyed by (pid, create_time) so PID reuse
    cannot forge or hide a worker. psutil is OPTIONAL (lazy import); the CIM
    backend keeps the harness dependency-free on CPU CI.
    """

    def __init__(self, root_pid: int, interval: float = 1.0):
        super().__init__(daemon=True, name=f"WorkerMonitor-{root_pid}")
        self.root_pid = root_pid
        self.interval = interval
        self.stop_event = threading.Event()
        self._psutil = None
        try:
            import psutil  # noqa: PLC0415 — optional dependency
            self._psutil = psutil
            self.backend = "psutil"
        except ImportError:
            self.backend = "cim"
        self.health = {
            "monitoring_started": False,
            "monitoring_completed": False,
            "thread_alive_at_shutdown": None,
            "unexpected_exception_count": 0,
            "observation_samples": 0,
            "first_observation": None,
            "last_observation": None,
        }
        self.events: list[dict] = []
        self.identities: dict[str, dict] = {}
        self.peak_concurrent = 0
        self.root_gone_seen = False

    # -- event bookkeeping ---------------------------------------------------
    def _note(self, kind: str, detail: str) -> None:
        self.events.append({"kind": kind, "detail": str(detail)[:200],
                            "at": gp_lib.now_utc()})
        if kind == MONITOR_INTERNAL_FAILURE:
            self.health["unexpected_exception_count"] += 1

    def _record_identity(self, pid: int, ppid, name, create_time, now: float) -> dict:
        key = f"{pid}@{create_time}" if create_time else f"{pid}@?"
        rec = self.identities.setdefault(key, {
            "identity": key, "pid": pid, "create_time": create_time,
            "ppid": None, "name": None, "first_seen": now,
            "last_seen": now, "sightings": 0})
        rec["sightings"] += 1
        rec["last_seen"] = now
        if ppid is not None:
            rec["ppid"] = ppid
        if name:
            rec["name"] = name
        return rec

    # -- backends --------------------------------------------------------------
    def _sample_psutil(self) -> None:
        psutil = self._psutil
        now = time.time()
        try:
            root = psutil.Process(self.root_pid)
            kids = root.children(recursive=True)
        except psutil.NoSuchProcess:
            self.root_gone_seen = True  # expected near shutdown
            self._note(MONITOR_EXIT_RACE, f"root pid {self.root_pid} gone")
            return
        except psutil.ZombieProcess:
            self._note(MONITOR_INTERNAL_FAILURE, f"root pid {self.root_pid} zombie")
            return
        except psutil.AccessDenied:
            self._note(MONITOR_INTERNAL_FAILURE, f"root pid {self.root_pid} access denied")
            return
        alive = 0
        for p in kids:
            pid = p.pid
            ppid = name = create_time = None
            try:
                ppid = p.ppid()
                name = p.name()
                create_time = p.create_time()
            except psutil.NoSuchProcess:
                # expected Windows process-lifecycle race: the worker exited
                # between children() and the attribute reads — record, survive
                self._note(MONITOR_EXIT_RACE, f"pid {pid} exited mid-enumeration")
            except psutil.ZombieProcess:
                self._note(MONITOR_ZOMBIE, f"pid {pid} zombie")
            except psutil.AccessDenied:
                self._note(MONITOR_ACCESS_DENIED, f"pid {pid} attribute access denied")
            except Exception as e:  # never let one bad process kill the sampler
                self._note(MONITOR_INTERNAL_FAILURE,
                           f"pid {pid} attributes: {type(e).__name__}")
            # the identity STILL counts (children() observed it this cycle)
            self._record_identity(pid, ppid, name, create_time, now)
            alive += 1
        self.peak_concurrent = max(self.peak_concurrent, alive)

    def _sample_cim(self) -> None:
        now = time.time()
        procs = _cim_python_procs()
        if not procs:
            return  # CIM unavailable this cycle (recorded via sample count)
        workers = descendants_of(procs, self.root_pid)
        by_pid = {p["pid"]: p for p in procs}
        alive = 0
        for pid in workers:
            info = by_pid.get(pid) or {}
            self._record_identity(pid, info.get("ppid"), "python.exe",
                                  info.get("create_time"), now)
            alive += 1
        self.peak_concurrent = max(self.peak_concurrent, alive)

    # -- thread lifecycle ------------------------------------------------------
    def run(self) -> None:
        self.health["monitoring_started"] = True
        try:
            while not self.stop_event.is_set():
                try:
                    if self.backend == "psutil":
                        self._sample_psutil()
                    else:
                        self._sample_cim()
                    self.health["observation_samples"] += 1
                    stamp = gp_lib.now_utc()
                    if not self.health["first_observation"]:
                        self.health["first_observation"] = stamp
                    self.health["last_observation"] = stamp
                except Exception as e:  # last-resort: loop NEVER dies silently
                    self._note(MONITOR_INTERNAL_FAILURE,
                               f"sampler cycle: {type(e).__name__}: {e}")
                self.stop_event.wait(self.interval)
        finally:
            self.health["monitoring_completed"] = True

    def stop(self, timeout: float = 10.0) -> bool:
        """Bounded shutdown; True iff the thread provably terminated."""
        self.stop_event.set()
        self.join(timeout)
        self.health["thread_alive_at_shutdown"] = self.is_alive()
        return not self.is_alive()

    # -- evidence --------------------------------------------------------------
    def _identity_alive(self, ident: dict) -> bool:
        """PID-reuse aware liveness: a recycled PID with a different
        create_time is a DIFFERENT process, not our orphan. Uncertainty
        reports alive (fail-closed direction for orphan detection)."""
        pid = ident["pid"]
        if self._psutil is not None:
            try:
                p = self._psutil.Process(pid)
                ct = p.create_time()
                if ident["create_time"] is not None \
                        and abs(ct - ident["create_time"]) > 1.0:
                    return False  # PID reused by another process
                return True
            except self._psutil.NoSuchProcess:
                return False
            except Exception:
                return True
        return pid in {q["pid"] for q in _cim_python_procs()}

    def lingering(self, wait_s: float = 20.0, interval: float = 1.0) -> list[str]:
        """Known worker identities still alive after the parent exited."""
        deadline = time.time() + wait_s
        while time.time() < deadline:
            alive = [i for i in self.identities.values() if self._identity_alive(i)]
            if not alive:
                return []
            time.sleep(interval)
        return sorted(i["identity"] for i in self.identities.values()
                      if self._identity_alive(i))

    def summary(self) -> dict:
        idents = sorted(self.identities.values(),
                        key=lambda r: (r["first_seen"], r["pid"]))
        kinds = sorted({e["kind"] for e in self.events})
        return {
            "backend": self.backend, "root_pid": self.root_pid,
            "health": dict(self.health),
            "monitor_events": self.events[-50:],
            "monitor_event_summary": {k: sum(1 for e in self.events
                                             if e["kind"] == k) for k in kinds},
            "distinct_worker_identities": len(self.identities),
            "worker_identities": idents,
            "peak_concurrent": self.peak_concurrent,
            "note": "identities keyed by (pid, create_time); distinct "
                    "identities are NOT simultaneous workers — peak_concurrent "
                    "measures concurrency; the parent is never counted",
        }


# --- pure CPU-testable worker contracts (mission §5/§9) ----------------------

def _norm_home(p) -> str:
    return str(p or "").replace("\\", "/").rstrip("/").lower()


def evaluate_single_run(run: dict) -> dict:
    """Acceptance contract for ONE workers run (observed facts only, R22A.4).

    Never consults a stored status/verdict — every check is recomputed from
    the run's recorded facts. The raw log is scanned for fatal signatures on
    EVERY path (exit 0 included). Monitor health is consumed fail-closed:
    an unhealthy or unrecorded monitor yields INCONCLUSIVE unless independent
    lifecycle corroboration is supplied.
    """
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
    exit_code = run.get("exit_code")
    log = str(run.get("log_text") or "")
    done_marker = "STABILITY_CHILD_DONE" in log
    identities = run.get("distinct_worker_identities")
    if identities is None:
        identities = len(run.get("worker_pids_observed") or [])
    peak = run.get("peak_concurrent_workers")
    peak_derived = run.get("concurrency_lower_bound_derived")
    monitor_health = run.get("monitor_health")
    corrob = run.get("independent_lifecycle_corroboration") or None

    if not check("workers_requested_8", req == WORKER_REQ,
                 f"requested_workers={req} (contract={WORKER_REQ})"):
        return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET", "checks": checks}

    if exit_code is None:
        return {"verdict": "FAIL", "classification": "MISSING_PROCESS_EXIT_CODE",
                "checks": checks + [{"check": "process_exit_code_recorded", "ok": False,
                                     "detail": "no native exit code recorded"}]}

    if res is None:
        return {"verdict": "FAIL", "classification": "MISSING_RESOLVED_WORKERS_EVIDENCE",
                "checks": checks + [{"check": "resolved_workers_evidence", "ok": False,
                                     "detail": "child did not report train_loader.num_workers"}]}
    if not check("workers_effective_8", res == WORKER_REQ,
                 f"resolved_num_workers={res} (requested {req})"):
        return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET", "checks": checks}

    if not check("worker_identity_evidence", int(identities or 0) >= WORKER_REQ,
                 f"{identities} distinct worker identities observed OS-level "
                 "(parent excluded by construction; identities ≠ simultaneity)"):
        if int(identities or 0) <= 0:
            return {"verdict": "INCONCLUSIVE", "classification": "NO_WORKER_PID_EVIDENCE",
                    "checks": checks}
        return {"verdict": "INCONCLUSIVE", "classification": "PARTIAL_WORKER_PID_EVIDENCE",
                "checks": checks}

    if peak is not None:
        if not check("worker_concurrency_evidence", int(peak) >= WORKER_REQ,
                     f"peak_concurrent_workers={peak} — all {WORKER_REQ} must "
                     "actually run simultaneously"):
            return {"verdict": "FAIL", "classification": "WORKER_COUNT_NOT_MET",
                    "checks": checks}
    elif peak_derived is not None:
        if not check("worker_concurrency_evidence", int(peak_derived) >= WORKER_REQ,
                     f"concurrency lower bound {peak_derived} derived from "
                     "per-identity first/last-seen interval overlap (derived, disclosed)"):
            return {"verdict": "INCONCLUSIVE",
                    "classification": "WORKER_CONCURRENCY_UNPROVEN", "checks": checks}
    else:
        return {"verdict": "INCONCLUSIVE", "classification": "WORKER_CONCURRENCY_UNPROVEN",
                "checks": checks + [{"check": "worker_concurrency_evidence", "ok": False,
                                     "detail": "no recorded or derivable concurrency evidence"}]}

    # --- anomaly scan applies on ALL exit paths, including exit 0 ------------
    scan = scan_run_anomalies(log)
    if scan["fatal"]:
        first = scan["fatal"][0]
        return {"verdict": "FAIL", "classification": first["classification"],
                "anomaly_evidence": scan,
                "checks": checks + [{"check": "no_fatal_anomaly_signatures", "ok": False,
                                     "detail": f"exit_code={exit_code} but raw log contains "
                                               f"{first['signature']!r} ({first['classification']})"}]}
    benign_note = (f"no fatal signatures; {len(scan['benign'])} benign documented "
                   "diagnostic(s) classified & preserved"
                   if scan["benign"] else "no fatal HIP/MIOpen/worker signatures in raw log")
    check("no_fatal_anomaly_signatures", True, benign_note)

    if exit_code == 124:
        return {"verdict": "FAIL", "classification": "DATALOADER_TIMEOUT",
                "anomaly_evidence": scan,
                "checks": checks + [{"check": "bounded_execution", "ok": False,
                                     "detail": "per-run timeout exceeded"}]}

    orphans = run.get("orphan_workers_alive")
    if orphans is None:
        orphans = len(run.get("lingering_after_parent_exit") or [])
    if orphans:
        return {"verdict": "FAIL", "classification": "WORKER_SHUTDOWN_FAILURE",
                "anomaly_evidence": scan,
                "checks": checks + [{"check": "no_orphan_workers", "ok": False,
                                     "detail": f"{orphans} worker processes survived parent exit"}]}
    check("no_orphan_workers", True, "no known worker identities alive after parent exit")

    # --- monitor lifecycle: fail-closed unless healthy or substantiated ------
    if monitor_health is None:
        if corrob and int(corrob.get("distinct_identities") or 0) >= WORKER_REQ:
            check("monitor_lifecycle_healthy", True,
                  "monitor health unrecorded (historical receipt) but independent "
                  f"lifecycle evidence substantiates: {corrob.get('source')} "
                  f"({corrob.get('distinct_identities')} identities, "
                  f"{corrob.get('total_sightings')} sightings)")
        else:
            return {"verdict": "INCONCLUSIVE",
                    "classification": "MONITOR_HEALTH_UNRECORDED",
                    "anomaly_evidence": scan,
                    "checks": checks + [{"check": "monitor_lifecycle_healthy", "ok": False,
                                         "detail": "worker monitor health not recorded and "
                                                   "no independent lifecycle evidence"}]}
    else:
        unhealthy = []
        if not monitor_health.get("monitoring_started"):
            unhealthy.append("monitoring never started")
        if not monitor_health.get("monitoring_completed"):
            unhealthy.append("monitoring loop did not complete")
        if monitor_health.get("thread_alive_at_shutdown"):
            unhealthy.append("monitor thread still alive after bounded shutdown")
        if int(monitor_health.get("observation_samples") or 0) <= 0:
            unhealthy.append("zero observation samples collected")
        if not monitor_health.get("last_observation"):
            unhealthy.append("last observation missing")
        unexpected = int(monitor_health.get("unexpected_exception_count") or 0)
        if unexpected > 0:
            unhealthy.append(f"{unexpected} unexpected monitor exception(s)")
        if unhealthy:
            if corrob and int(corrob.get("distinct_identities") or 0) >= WORKER_REQ:
                check("monitor_lifecycle_healthy", True,
                      "monitor UNHEALTHY (" + "; ".join(unhealthy) + ") but independent "
                      f"lifecycle evidence substantiates the runs: {corrob.get('source')}")
            else:
                return {"verdict": "INCONCLUSIVE",
                        "classification": "MONITOR_INTERNAL_FAILURE",
                        "anomaly_evidence": scan,
                        "checks": checks + [{"check": "monitor_lifecycle_healthy", "ok": False,
                                             "detail": "; ".join(unhealthy)}]}
        else:
            races = int((run.get("monitor_event_summary") or {}).get(MONITOR_EXIT_RACE) or 0)
            check("monitor_lifecycle_healthy", True,
                  f"monitor healthy ({monitor_health.get('observation_samples')} samples, "
                  f"first={str(monitor_health.get('first_observation'))[:19]} "
                  f"last={str(monitor_health.get('last_observation'))[:19]})"
                  + (f"; {races} expected exit-race(s) recorded as {MONITOR_EXIT_RACE}"
                     if races else ""))

    if exit_code != 0:
        cls = "WORKER_CRASH_AFTER_COMPLETE" if done_marker else "WORKER_CRASH"
        base = classify_run(int(exit_code), log)
        if base["status"] == "FAIL" and base.get("anomalies"):
            cls = base["failure_classification"]  # specific signature found
        return {"verdict": "FAIL", "classification": cls,
                "anomaly_evidence": scan,
                "checks": checks + [{"check": "process_exit_zero", "ok": False,
                                     "detail": f"exit_code={exit_code}"}]}

    if not check("training_completed",
                 done_marker or bool(run.get("training_completed")),
                 "STABILITY_CHILD_DONE marker / training_completed fact"):
        return {"verdict": "FAIL", "classification": "TRAINING_INCOMPLETE",
                "anomaly_evidence": scan, "checks": checks}

    if not check("checkpoint_present", bool(run.get("checkpoint_exists")),
                 str(run.get("checkpoint_path"))):
        return {"verdict": "FAIL", "classification": "CHECKPOINT_MISSING",
                "anomaly_evidence": scan, "checks": checks}

    return {"verdict": "PASS", "classification": None,
            "anomaly_evidence": scan, "checks": checks}


def assign_cache_roles(runs: list) -> list:
    """Derive each run's honest cache role from its own record (P0-D).

    cold expectation → 'cold'. Warm-family runs sharing one retained home:
    the FIRST use of a fresh home is 'cache_priming' (it populates the cache
    identity — it is NOT a pre-warmed run); subsequent runs on the same home
    are 'warm'. When the record carries an explicit home_pre_existed flag,
    that direct evidence wins; otherwise derivation is by first-seen order of
    the home, which matches the sequential execution.
    """
    seen_homes: dict = {}
    out = []
    for i, r in enumerate(runs):
        exp = r.get("cache_expectation")
        home = r.get("home_dir")
        if exp == "cold":
            role = "cold"
        elif "home_pre_existed" in r and r["home_pre_existed"] is not None:
            role = "warm" if r["home_pre_existed"] else "cache_priming"
        elif home not in seen_homes:
            seen_homes[home] = i
            role = "cache_priming"
        else:
            role = "warm"
        out.append({**r, "cache_role": role})
    return out


def evaluate_workers_matrix(matrix: dict) -> dict:
    return _evaluate_workers_matrix_impl(matrix)


def _evaluate_workers_matrix_impl(matrix: dict) -> dict:
    """Acceptance contract for the workers=8 short-reliability matrix (R22A.4).

    Requires the EXACT intended shape: `expected_cold` (default 2) cold runs
    with DISTINCT fresh cache homes, at most one cache_priming run per warm
    home, and exactly `expected_warm` (default 3) qualifying pre-warmed runs
    on ONE shared retained home. A single successful run can never satisfy
    the matrix; duplicate or missing records are NO-GO. Cache roles are
    RE-DERIVED from home identity — a record whose OWN direct evidence
    (home_pre_existed=true) contradicts a priming derivation is rejected;
    historical pre-classification claims are recorded as superseded, never
    silently trusted. Stored per-run statuses and serialized overall verdicts
    are never consulted; every per-run verdict is recomputed from facts. All
    runs must share one GPU identity and runtime.
    """
    runs = matrix.get("runs") or []
    expected_cold = int(matrix.get("expected_cold") or 2)
    expected_warm = int(matrix.get("expected_warm") or 3)
    synthetic = bool(matrix.get("harness_fixture")) or not matrix.get("gpu_name")
    child_guard_ok = bool(matrix.get("child_has_main_guard"))

    if synthetic:
        return {"verdict": "NO_GO", "reason": "synthetic evidence can never earn a physical PASS"}
    if not child_guard_ok:
        return {"verdict": "NO_GO",
                "reason": "child script lacks Windows spawn __main__ guard"}
    if not runs:
        return {"verdict": "NO_GO", "reason": "no runs recorded"}

    # unique run identities: no duplicate (matrix, run) keys, run_ids or logs
    ids = [(r.get("matrix"), r.get("run")) for r in runs]
    run_ids = [r.get("run_id") for r in runs]
    shas = [r.get("log_sha256") for r in runs]
    if len(set(map(str, ids))) != len(runs):
        return {"verdict": "NO_GO", "reason": "duplicate run identities in matrix"}
    if len(set(map(str, run_ids))) != len(runs):
        return {"verdict": "NO_GO", "reason": "duplicate run_ids in matrix"}
    if len(set(shas)) != len(runs):
        return {"verdict": "NO_GO", "reason": "duplicate raw logs (same sha256 twice)"}
    if any(not s for s in shas):
        return {"verdict": "NO_GO", "reason": "missing SHA256 raw-log evidence for a run"}
    stamps = [r.get("started_utc") or r.get("start_utc") for r in runs]
    if any(not t for t in stamps):
        return {"verdict": "NO_GO", "reason": "missing run timestamp (provenance)"}
    if len(set(map(str, stamps))) != len(runs):
        return {"verdict": "NO_GO", "reason": "duplicate run timestamps (provenance)"}

    # one GPU identity + one runtime for the whole matrix
    gpu_ids = {str(r.get("gpu_name") or r.get("device_name") or "") for r in runs}
    gpu_ids.discard("")
    if len(gpu_ids) > 1 or (gpu_ids and matrix.get("gpu_name")
                           and str(matrix["gpu_name"]) not in gpu_ids):
        return {"verdict": "NO_GO",
                "reason": f"mixed GPU identity across matrix runs: {sorted(gpu_ids)}"}
    torchs = {str(r.get("torch") or "") for r in runs}
    torchs.discard("")
    if len(torchs) > 1:
        return {"verdict": "NO_GO",
                "reason": f"mixed runtime evidence across matrix runs: {sorted(torchs)}"}

    roled = assign_cache_roles(runs)
    role_claim_discrepancies = []
    # warm-family home usage counts (a strayed warm run on a private home is a
    # composition problem, not a priming mislabel — composition catches it)
    warm_family_home_use: dict[str, int] = {}
    for r in roled:
        if r["cache_role"] != "cold":
            k = _norm_home(r.get("home_dir"))
            if k:
                warm_family_home_use[k] = warm_family_home_use.get(k, 0) + 1
    first_use_seen: set[str] = set()
    for r, with_role in zip(runs, roled):
        claimed = str(r.get("cache_class") or "")
        claims_warm = "warm" in claimed.lower() and "cold" not in claimed.lower()
        home_key = _norm_home(r.get("home_dir"))
        is_chronological_first_use = home_key not in first_use_seen \
            and with_role["cache_role"] in ("cache_priming", "warm")
        if home_key:
            first_use_seen.add(home_key)
        shared_family_home = warm_family_home_use.get(home_key, 0) > 1
        if is_chronological_first_use and shared_family_home \
                and with_role["cache_role"] != "cold":
            if r.get("home_pre_existed") is True:
                # direct evidence CONTRADICTS the record: this is the
                # demonstrably first use of the shared home, yet it asserts a
                # pre-warmed run (home existed before it)
                return {"verdict": "NO_GO",
                        "reason": f"run {r.get('run_id') or r.get('run')} mislabels a "
                                  "cache_priming first-use as pre-warmed with "
                                  "home_pre_existed=true (home "
                                  f"{r.get('home_dir')!r})"}
            if with_role["cache_role"] == "cache_priming" and claims_warm:
                # historical receipts pre-date the priming classification —
                # record the superseded claim honestly; composition decides
                role_claim_discrepancies.append(
                    f"run {r.get('run_id') or r.get('run')} claimed {claimed!r} but "
                    "derives cache_priming (first use of home "
                    f"{r.get('home_dir')!r}) — historical claim superseded by "
                    "R22A.4 derivation")

    colds = [r for r in roled if r["cache_role"] == "cold"]
    primes = [r for r in roled if r["cache_role"] == "cache_priming"]
    warms = [r for r in roled if r["cache_role"] == "warm"]
    additional = [r for r in roled if str(r.get("sample_class") or "").lower() == "additional"]
    for r in additional:
        if r["cache_role"] != "warm" or r.get("home_pre_existed") is not True:
            return {"verdict": "NO_GO",
                    "reason": "additional run must be a qualifying warm run with "
                              "home_pre_existed=true (own run id/log/timestamp)"}
        if not str(r.get("justification") or "").strip():
            return {"verdict": "NO_GO",
                    "reason": "additional run requires an explicit justification"}

    if len(colds) != expected_cold:
        return {"verdict": "NO_GO",
                "reason": f"matrix size: expected exactly {expected_cold} cold runs, "
                          f"found {len(colds)} — a partial matrix can never earn the verdict",
                "roles": [r["cache_role"] for r in roled]}
    if len(warms) != expected_warm:
        return {"verdict": "NO_GO",
                "reason": f"matrix size: expected exactly {expected_warm} qualifying "
                          f"pre-warmed runs, found {len(warms)} "
                          "(cache_priming runs do not qualify as pre-warmed)",
                "roles": [r["cache_role"] for r in roled]}
    if len(primes) > 1:
        return {"verdict": "NO_GO",
                "reason": f"{len(primes)} cache_priming runs — the shared warm home "
                          "must be primed exactly once",
                "roles": [r["cache_role"] for r in roled]}
    cold_homes = {_norm_home(r.get("home_dir")) for r in colds}
    if len(cold_homes) != len(colds) or "" in cold_homes:
        return {"verdict": "NO_GO",
                "reason": "cold runs must each use a DISTINCT fresh cache home",
                "roles": [r["cache_role"] for r in roled]}
    warm_family = primes + warms
    warm_homes = {_norm_home(r.get("home_dir")) for r in warm_family}
    if len(warm_homes) > 1 or (warm_homes and "" in warm_homes):
        return {"verdict": "NO_GO",
                "reason": "warm-family runs must SHARE one retained cache home",
                "roles": [r["cache_role"] for r in roled]}
    if cold_homes & warm_homes:
        return {"verdict": "NO_GO",
                "reason": "cold and warm cache identities must be disjoint "
                          "(wrong cache home identity)",
                "roles": [r["cache_role"] for r in roled]}

    verdicts = [evaluate_single_run(r) for r in runs]
    n_pass = sum(1 for v in verdicts if v["verdict"] == "PASS")
    timeouts = sum(1 for r in runs if int(r.get("exit_code") or 0) == 124)
    n_total = len(runs)

    if timeouts:
        return {"verdict": "NO_GO",
                "reason": f"{timeouts} run(s) timed out — a timeout fails even if "
                          "another run later succeeds",
                "run_verdicts": verdicts, "roles": [r["cache_role"] for r in roled]}
    n_fail = sum(1 for v in verdicts if v["verdict"] == "FAIL")
    if n_fail:
        return {"verdict": "NO_GO",
                "reason": f"{n_pass}/{n_total} runs PASS — one failure is overall NO-GO "
                          "(a diagnostic follow-up cannot erase it)",
                "run_verdicts": verdicts, "roles": [r["cache_role"] for r in roled]}
    if any(v["verdict"] == "INCONCLUSIVE" for v in verdicts):
        return {"verdict": "INCONCLUSIVE",
                "reason": "worker evidence inconclusive in at least one run "
                          "(no run FAILED — evidence, not training, is the gap)",
                "run_verdicts": verdicts, "roles": [r["cache_role"] for r in roled]}
    add_note = (f" + {len(additional)} ADDITIONAL justified warm sample(s)"
                if additional else "")
    return {"verdict": "WORKERS8_SHORT_RELIABILITY_PASS",
            "reason": f"exact matrix satisfied: {len(colds)} COLD (distinct homes) + "
                      f"{len(primes)} CACHE_PRIMING + {len(warms)} WARM (shared home"
                      f"{add_note}), all {n_total} PASS with workers={WORKER_REQ} "
                      "verified OS-level and clean shutdown",
            "run_verdicts": verdicts, "roles": [r["cache_role"] for r in roled],
            "role_claim_discrepancies": role_claim_discrepancies}


def finalize_worker_run(base: dict) -> tuple[str, str | None]:
    """DEPRECATED compat shim (R22A.3 name) — now a thin wrapper over the
    unified per-run contract. Stored 'status' is NOT trusted; facts are
    recomputed. Returns (verdict, classification)."""
    v = evaluate_single_run(base)
    return v["verdict"], v.get("classification")


def overall_workers8_verdict(runs: list, cold_expected: int, warm_expected: int) -> dict:
    """DEPRECATED compat shim (R22A.3 name) — recomputes the matrix from run
    FACTS via the unified strict contract. Never consults stored statuses or
    serialized overall verdicts (R22A.4 §5 fail-open fix)."""
    m = evaluate_workers_matrix({
        "runs": runs,
        "child_has_main_guard": all(r.get("child_has_main_guard", True) for r in runs)
        if runs else False,
        "gpu_name": (runs[0].get("gpu_name") or runs[0].get("device_name")) if runs else None,
        "expected_cold": cold_expected,
        "expected_warm": warm_expected,
    })
    out = {"verdict": m["verdict"], "problems": [m["reason"]] if m.get("reason") else [],
           "n_planned": cold_expected + warm_expected}
    return out


def bounded_terminate(proc: subprocess.Popen, grace_s: float = 10.0) -> None:
    """Bounded, auditable shutdown of OUR OWN child process (never a foreign
    process)."""
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


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--runs", type=int, default=3,
                    help="independent processes (R22: 10; supplemental Part B: 5)")
    ap.add_argument("--cold", action="store_true",
                    help="fresh MIOpen cache identity per run (isolated USERPROFILE)")
    ap.add_argument("--cold-runs", type=int, default=None,
                    help="first N runs cold, remaining runs warm (shared --warm-home)")
    ap.add_argument("--warm-home", default=None,
                    help="retained isolated USERPROFILE shared by warm runs "
                         "(never the user's global cache)")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--device", default="-1")
    ap.add_argument("--workers", type=int, default=0,
                    help="DataLoader workers requested in the child train() call "
                         "(default 0 = historical G8 contract)")
    ap.add_argument("--data", default="coco8.yaml")
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--per-run-timeout", type=int, default=900)
    ap.add_argument("--overall-budget", type=int, default=5400)
    ap.add_argument("--weights", default=None,
                    help="local yolo26n.pt copied into each run dir (removes "
                         "network dependence; default None = child resolves as before)")
    ap.add_argument("--expected-cold", type=int, default=2)
    ap.add_argument("--expected-warm", type=int, default=3,
                    help="exact QUALIFYING pre-warmed count (cache_priming excluded)")
    ap.add_argument("--strict-matrix", action="store_true",
                    help="enforce the FULL matrix contract within THIS invocation")
    ap.add_argument("--sample-class", default="original", choices=["original", "additional"],
                    help="classification of the runs in this invocation "
                         "(additional requires --justification)")
    ap.add_argument("--justification", default=None,
                    help="explicit justification recorded with additional samples")
    args = ap.parse_args()
    if args.sample_class == "additional" and not (args.justification or "").strip():
        ap.error("--sample-class additional requires --justification")

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
    lock_path = Path(__file__).resolve().parents[2] / \
        "evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json"
    lock_sha = gp_lib.sha256_file(lock_path) if lock_path.exists() else None
    _miopen_rec = gp_lib.loaded_miopen_identity()
    shim_removed = os.environ.pop("HIPRTC_COMPILE_OPTIONS_APPEND", None)
    gpu_name0 = torch.cuda.get_device_name(0) if torch.cuda.device_count() else None

    t0 = time.time()
    runs = []
    for i in range(1, args.runs + 1):
        if time.time() - t0 > args.overall_budget:
            runs.append({"run": i, "run_id": f"{args.run_id}-R{i}", "status": "SKIP",
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
            batch_arg=str(args.batch), imgsz=str(args.imgsz)), encoding="utf-8")
        child_src = child.read_text(encoding="utf-8")
        safe, why = child_spawn_safe(child_src)
        guard_ok = child_has_main_guard(child_src)
        if not safe or not guard_ok:
            runs.append({"run": i, "run_id": run_id, "status": "FAIL",
                         "failure_classification": f"CHILD_SCRIPT_UNSAFE: {why}",
                         "child_has_main_guard": guard_ok, "log": str(run_dir / "child.log")})
            (run_dir / "run_record.json").write_text(
                json.dumps(runs[-1], indent=2), encoding="utf-8")
            print(f"[run {i}/{args.runs}] REJECTED child script: {why}")
            continue
        env = dict(os.environ)
        home_dir = None
        home_pre_existed = None
        if is_cold:
            fresh_home = run_dir / "home"
            fresh_home.mkdir(exist_ok=True)
            env["USERPROFILE"] = str(fresh_home)
            cache_note = "cold(fresh-USERPROFILE, run-isolated)"
            home_dir = str(fresh_home)
        elif warm_home is not None:
            env["USERPROFILE"] = str(warm_home)
            cache_note = f"warm(retained isolated home shared by warm runs: {warm_home})"
            home_dir = str(warm_home)
            home_pre_existed = any(warm_home.iterdir())  # direct evidence wins
        else:
            cache_note = "warm(process-level)"
        log = run_dir / "child.log"
        t1 = time.time()
        started_utc = gp_lib.now_utc()
        monitor = None
        spawned = False
        child_pid = None
        timed_out = False
        out = ""
        try:
            proc = subprocess.Popen([sys.executable, "-I", str(child)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace",
                                    cwd=str(run_dir), env=env)
            spawned, child_pid = True, proc.pid
            if args.workers > 0:
                monitor = WorkerMonitor(proc.pid)
                monitor.start()
            try:
                out, _ = proc.communicate(timeout=args.per_run_timeout)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                bounded_terminate(proc)
                out, _ = proc.communicate()
                rc = 124
        except Exception as e:  # spawn-level failure of the parent process itself
            rc, out = 1, f"PARENT_SPAWN_ERROR {type(e).__name__}: {e}"
        dur = round(time.time() - t1, 1)
        finished_utc = gp_lib.now_utc()
        # newline="\n" keeps the committed log bytes hash-identical to the
        # recorded raw_log_sha256 (no CRLF translation on Windows)
        log.write_text(out, encoding="utf-8", errors="replace", newline="\n")

        monitor_summary = None
        lingering = None
        if monitor is not None:
            monitor.stop()
            monitor_summary = monitor.summary()
            lingering = monitor.lingering()

        facts: dict = {}
        fp = run_dir / "child_facts.json"
        if fp.exists():
            try:
                facts = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                facts = {"error": "unreadable facts file"}

        ckpt = run_dir / "train" / "weights" / "last.pt"
        rec = {
            "run": i, "run_id": run_id, "exit_code": rc, "duration_s": dur,
            "cache_class": cache_note, "log": str(log),
            "started_utc": started_utc, "finished_utc": finished_utc,
            "parent_pid": child_pid, "child_pid": facts.get("child_pid"),
            "source_sha": head, "wheel_lock_sha256": lock_sha,
            "home_dir": home_dir, "home_pre_existed": home_pre_existed,
            "cache_expectation": "cold" if is_cold else "warm",
            "sample_class": args.sample_class,
            "justification": args.justification,
            "requested_workers": args.workers,
            "resolved_num_workers": facts.get("resolved_num_workers_train"),
            "val_num_workers": facts.get("val_num_workers"),
            "distinct_worker_identities":
                (monitor_summary or {}).get("distinct_worker_identities"),
            "worker_identities": (monitor_summary or {}).get("worker_identities"),
            "peak_concurrent_workers": (monitor_summary or {}).get("peak_concurrent"),
            "monitor_health": (monitor_summary or {}).get("health"),
            "monitor_event_summary": (monitor_summary or {}).get("monitor_event_summary"),
            "monitor_events": (monitor_summary or {}).get("monitor_events"),
            "lingering_after_parent_exit": lingering,
            "orphan_workers_alive": (len(lingering) if lingering is not None else None),
            "batches_completed": facts.get("batches_completed", 0),
            "training_completed": facts.get("training_completed", False),
            "val_completed": facts.get("val_completed", False),
            "checkpoint_path": str(facts.get("checkpoint_path") or ckpt),
            "checkpoint_exists": bool(facts.get("checkpoint_exists") or ckpt.exists()),
            "checkpoint_sha256": facts.get("checkpoint_sha256"),
            "amp_resolved": facts.get("amp_resolved"),
            "optimizer": facts.get("optimizer"),
            "gpu_name": facts.get("device_name") or gpu_name0,
            "torch": facts.get("torch") or torch.__version__,
            "hip": facts.get("hip"),
            "raw_log_sha256": sha256_text(out),
            "log_sha256": sha256_text(out),
            "spawned_by_parent": spawned,
            "child_has_main_guard": guard_ok,
            "userprofile_env": facts.get("userprofile_env"),
            "cold_identity_verified": (not is_cold) or (
                bool(facts.get("userprofile_env"))
                and str(facts.get("userprofile_env")).lower().startswith(
                    str(run_dir).lower())),
            "log_text": out[-20000:],
        }
        if args.workers > 0:
            verdict = evaluate_single_run(rec)
            rec["status"] = verdict["verdict"]
            rec["failure_classification"] = verdict.get("classification")
            rec["worker_contract_checks"] = verdict["checks"]
            rec["anomaly_evidence"] = verdict.get("anomaly_evidence")
        else:
            rec.update(classify_run(rc, out))
        slim = {k: v for k, v in rec.items() if k != "log_text"}
        runs.append(slim)
        (run_dir / "run_record.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")
        print(f"[run {i}/{args.runs}] exit={rc} {slim['status']} "
              f"nw={slim.get('resolved_num_workers')} "
              f"idents={slim.get('distinct_worker_identities')} "
              f"peak={slim.get('peak_concurrent_workers')} ({dur}s)")

    n_pass = sum(1 for r in runs if r.get("status") == "PASS")
    tally: dict[str, int] = {}
    for r in runs:
        for a in r.get("anomalies", []):
            tally[a] = tally.get(a, 0) + 1
    verdict = "PASS" if n_pass == len(runs) and runs else "FAIL"
    matrix_evaluation = None
    workers8_overall = None
    if args.workers > 0 and args.strict_matrix:
        # The FULL matrix-size contract is enforced only under --strict-matrix
        # (a single invocation covering the whole planned composition).
        # Partial invocations — e.g. ONE additional justified warm sample —
        # carry per-run verdicts; the acceptance-level matrix is derived
        # across invocations by supplemental_acceptance (CPU-testable).
        matrix_evaluation = evaluate_workers_matrix({
            "runs": runs,
            "child_has_main_guard": all(r.get("child_has_main_guard") for r in runs
                                        if r.get("run")),
            "gpu_name": gpu_name0,
            "expected_cold": args.expected_cold,
            "expected_warm": args.expected_warm,
        })
        workers8_overall = {"verdict": matrix_evaluation["verdict"],
                            "problems": [matrix_evaluation["reason"]]
                            if matrix_evaluation.get("reason") else []}
        verdict = "PASS" \
            if matrix_evaluation["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS" \
            else "FAIL"

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "source_sha": head,
        "gpu_name": gpu_name0,
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
                   + (f" --warm-home {warm_home}" if warm_home else "")
                   + (f" --sample-class {args.sample_class}" if args.sample_class != "original" else ""),
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": (tally and next(iter(tally))) or None if verdict == "FAIL" else None,
        "raw_log_path": str(work / "stability_runs.json"),
        "runs": runs, "n_pass": n_pass, "n_total": len(runs),
        "anomaly_tally": tally,
        "requested_workers": args.workers,
        "workers8_overall": workers8_overall,
        "matrix_evaluation": matrix_evaluation,
        "cold_runs": cold_runs,
        "warm_runs": len(runs) - cold_runs,
        "sample_class": args.sample_class,
        "cache_class": (f"cold {cold_runs} (fresh-USERPROFILE per run) / "
                        f"warm {len(runs) - cold_runs} "
                        + (f"(retained shared home {warm_home})" if warm_home else "(process-level)")),
        "child_spawn_safety": {
            "main_guard_present": all(r.get("child_has_main_guard") for r in runs if r.get("run")),
            "freeze_support": "freeze_support()" in CHILD,
            "note": "Windows spawn re-imports child.py in every worker; the guard "
                    "prevents recursive training processes; unsafe children are "
                    "refused before execution",
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
