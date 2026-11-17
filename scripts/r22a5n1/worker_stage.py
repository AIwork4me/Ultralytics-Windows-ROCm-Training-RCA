# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 workers=8 bounded exercise orchestrator (mission PHASE 4 §7.5).

Runs ONE bounded workers=8 training under full process observation:

  baseline    python PIDs BEFORE the run (preexisting zombies disclosed)
  training    audit_adamw_amp.py child with stdout/stderr captured to durable
              logs (execution-time capture — the R22A.5N loss was a caller-side
              redirect nobody committed)
  mid census  live Win32_Process snapshot WHILE training: children with
              ppid == trainer pid (spawn-method DataLoader workers), command
              lines verified, checker pid recorded
  orphan      post-exit python PID scan; leftover = all − baseline − checker
              (RECOMPUTED here and again by the acceptance engine — a stored
              CLEAN string is never authority)

    python scripts/r22a5n1/worker_stage.py --python VENV_PYTHON --run-root DIR \
        --lock lock.json --repo-root REPO --receipt out.json --epochs 3
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def cim_python_processes() -> list[dict]:
    """Win32_Process snapshot of python processes (pid, ppid, cmdline)."""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, timeout=120, encoding="utf-8", errors="replace")
    txt = (out.stdout or "").strip()
    if not txt:
        return []
    data = json.loads(txt)
    if isinstance(data, dict):
        data = [data]
    return [{"pid": int(p["ProcessId"]), "ppid": int(p["ParentProcessId"]),
             "cmdline": (p.get("CommandLine") or "")[:400]} for p in data]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python", required=True, help="venv python executable")
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--lock", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--census-out", required=True)
    ap.add_argument("--orphan-out", required=True)
    ap.add_argument("--run-id", default="R22A5N1-G7-W8")
    ap.add_argument("--trainer-mission", default="R22A.5N.1",
                    help="mission string recorded in the trainer receipt "
                         "(stacked/derived missions label their own runs)")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=5400)
    args = ap.parse_args()

    run_root = Path(args.run_root).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    work = run_root / "train"
    logs = run_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    repo = Path(args.repo_root).resolve()
    lock = Path(args.lock).resolve()

    # baseline BEFORE any mission process exists
    baseline = cim_python_processes()
    baseline_pids = sorted(p["pid"] for p in baseline)
    print(f"[baseline] {len(baseline_pids)} preexisting python pids: {baseline_pids}")

    stdout_l = logs / "workers8_stdout.log"
    stderr_l = logs / "workers8_stderr.log"
    cmd = [args.python, "-X", "utf8",
           str(repo / "windows-golden-path" / "scripts" / "audit_adamw_amp.py"),
           "--out", str(Path(args.receipt).resolve()),
           "--run-id", args.run_id, "--mission", args.trainer_mission,
           "--channel", "nightly", "--wheel-lock", str(lock),
           "--data", "coco128.yaml", "--epochs", str(args.epochs),
           "--imgsz", "256", "--batch", "8", "--device", "-1",
           "--workers", "8",
           "--run-dir", str(work)]
    meta = {"stage": "workers=8 bounded exercise (R22A.5N.1)",
            "command": cmd, "checker_pid": None, "baseline_python_pids": baseline_pids,
            "started_utc": utcnow(), "cwd": str(run_root)}
    t0 = time.time()
    fo = open(stdout_l, "wb")
    fe = open(stderr_l, "wb")
    proc = subprocess.Popen(cmd, cwd=str(run_root), stdout=fo, stderr=fe,
                            env={**__import__("os").environ})
    meta["trainer_pid"] = proc.pid
    meta["checker_pid"] = None  # filled below from snapshot
    print(f"[train] trainer pid={proc.pid}")

    # mid-run census: wait for epoch 1 row, then take a BOUNDED series of live
    # FULL-TREE snapshots (workers recycle between epochs on Windows; the
    # trainer is identified as the deepest process whose cmdline carries the
    # audit script — orchestrator layers above it are not the trainer)
    results_csv = work / "results.csv"
    census: dict = {"stage": "mid-run census", "captured_utc": None,
                    "trainer_pid": proc.pid, "spawn_children_of_trainer": [],
                    "checker_pid": None}
    deadline = time.time() + args.timeout
    me = __import__("os").getpid()
    snapshots: list[dict] = []
    census_started = False
    census_deadline = 0.0

    def find_trainer(tree: list[dict]) -> dict | None:
        audits = [p for p in tree if "audit_adamw_amp" in p["cmdline"]]
        if not audits:
            return None
        # deepest = one that is not the parent of another audit-carrying process
        deepest = [p for p in audits
                   if not any(q["ppid"] == p["pid"] for q in audits)]
        return deepest[0] if deepest else audits[0]

    while time.time() < deadline and proc.poll() is None:
        if not census_started and results_csv.is_file():
            rows = max(0, len(results_csv.read_text(encoding="utf-8",
                     errors="replace").strip().splitlines()) - 1)
            if rows >= 1:
                census_started = True
                census_deadline = time.time() + 150  # bounded observation window
        if census_started and time.time() < census_deadline:
            tree = cim_python_processes()
            trainer = find_trainer(tree) or {"pid": proc.pid, "cmdline": "?"}
            kids = sorted(p["pid"] for p in tree if p["ppid"] == trainer["pid"])
            spawn_main = [p["pid"] for p in tree
                          if p["ppid"] == trainer["pid"]
                          and "spawn_main" in p["cmdline"]]
            snapshots.append({
                "captured_utc": utcnow(),
                # 400 chars (full CIM capture): on redirector-venv topologies the
                # deepest trainer's script name lives past 160 chars, and the
                # acceptance engine's raw-snapshot recompute must still see it
                "python_tree": [{"pid": p["pid"], "ppid": p["ppid"],
                                 "cmdline": p["cmdline"][:400]} for p in tree],
                "trainer_pid": trainer["pid"],
                "children": kids, "spawn_main": spawn_main})
            best = max(snapshots, key=lambda s: len(s["children"]))
            census.update({
                "captured_utc": best["captured_utc"],
                "rows_at_census": 1,
                "trainer_pid": best["trainer_pid"],
                "orchestrator_pid": proc.pid,
                "spawn_children_of_trainer": best["children"],
                "spawn_children_count": len(best["children"]),
                "spawn_main_children_count": len(best["spawn_main"]),
                "checker_pid": me,
                "snapshot_count": len(snapshots),
                "snapshots": snapshots,
                "capture_method": "series of full Win32_Process CIM tree "
                                  "snapshots executed live while training; "
                                  "trainer identified as the deepest "
                                  "audit_adamw_amp process; every snapshot "
                                  "retained; peak snapshot cited",
                "preexisting_zombies_disclosed": baseline_pids,
            })
            print(f"[census] snap {len(snapshots)}: trainer "
                  f"{trainer['pid']} children {len(kids)} "
                  f"(spawn_main {len(spawn_main)}), peak "
                  f"{census['spawn_children_count']}")
            if len(best["children"]) >= 8:
                break  # contract satisfied
            time.sleep(1.5)
            continue
        if census_started and time.time() >= census_deadline:
            break
        time.sleep(1.0)

    rc = proc.wait(timeout=max(60, int(deadline - time.time())))
    fo.close()
    fe.close()
    meta.update({"finished_utc": utcnow(), "exit_code": rc,
                 "duration_s": round(time.time() - t0, 1),
                 "stdout_bytes": stdout_l.stat().st_size,
                 "stderr_bytes": stderr_l.stat().st_size})
    (logs / "workers8_envelope.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # post-run orphan check — recomputed, not asserted
    me = __import__("os").getpid()
    after = cim_python_processes()
    after_pids = sorted(p["pid"] for p in after)
    leftover = [p for p in after_pids
                if p not in baseline_pids and p != me and p != proc.pid]
    orphan = {"stage": "post-run orphan check",
              "captured_utc": utcnow(), "checker_pid": me,
              "all_python_pids": after_pids,
              "baseline_python_pids": baseline_pids,
              "mission_tree_leftover": leftover,
              "orphan_verdict": "CLEAN" if not leftover else "ORPHANS_PRESENT",
              "note": "leftover recomputed = all_python_pids − baseline − "
                      "checker; stored verdict is derived, never authoritative"}
    census.setdefault("captured_utc", utcnow())
    Path(args.census_out).write_text(
        json.dumps(census, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(args.orphan_out).write_text(
        json.dumps(orphan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[orphan] leftover={leftover} verdict={orphan['orphan_verdict']}")
    sys.exit(0 if rc == 0 else 1)


if __name__ == "__main__":
    main()
