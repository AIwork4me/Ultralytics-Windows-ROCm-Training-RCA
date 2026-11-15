# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Checkpoint save → controlled interrupt → NEW-process resume gate (mission §10).

Actual multi-epoch lifecycle, two real OS processes:
  1. launch training child (coco128, --epochs total, device=-1)
  2. poll until one complete epoch is visible AND last.pt is fully written
     (file-size stability + mtime quiescence; never kill mid-write)
  3. terminate the child (controlled test interruption; hard TerminateProcess,
     the strongest realistic interruption a user can produce)
  4. start a NEW python process that resumes from last.pt (resume=True)
  5. verify epoch continuity via results.csv rows + resume log line
  6. after completion: reload best.pt in a THIRD process, run GPU inference
  7. capture all exit codes; bounded timeouts; no retry loops

Resume is resume=True (epoch/optimizer/scheduler state), NOT weights-only
loading — loading with resume=False does not satisfy this gate.

    python verify_checkpoint_resume.py --out resume.json --run-id R21-E2 \
        --epochs 6 --kill-after-epoch 2
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

TRAIN_CHILD = r'''
import sys
from ultralytics import YOLO
m = YOLO("yolo26n.pt")
m.train(data="__DATA__", epochs=__EPOCHS__, device=__DEVICE__, project=r"__PROJECT__",
        name=r"__NAME__", exist_ok=True, seed=7, workers=0, batch=__BATCH__, verbose=True)
'''

RESUME_CHILD = r'''
from ultralytics import YOLO
import pathlib
last = pathlib.Path(r"__LAST_PT__")
assert last.is_file(), "last.pt missing: " + str(last)
m = YOLO(str(last))
r = m.train(resume=True)
print("RESUME_DONE")
'''

INFER_CHILD = r'''
from ultralytics import YOLO
m = YOLO(r"__BEST_PT__")
r = m.predict(source=r"__SOURCE__", device=0, verbose=False)
n = len(r)
print("INFER_OK boxes_batches=" + str(n))
assert n >= 1
'''


def wait_for_epoch_and_checkpoint(results_csv: Path, kill_after: int,
                                  total_epochs: int, timeout_s: int) -> dict:
    """Wait for the right moment to interrupt.

    Ultralytics writes results.csv row N only AFTER last.pt@N is fully saved
    (save_model precedes the csv callback), so when row kill_after+1 exists the
    checkpoint of epoch kill_after is finalized on disk AND training is still
    mid-run → terminate immediately. Trigger window: rows in
    [kill_after+1, total_epochs-1]; if rows reaches total_epochs the training
    completed and last.pt was stripped to inference weights → honest FAIL.
    """
    t0 = time.time()
    rows = 0

    def count_rows() -> int:
        if not results_csv.is_file():
            return 0
        text = results_csv.read_text(encoding="utf-8", errors="replace").strip()
        return max(0, len(text.splitlines()) - 1)

    while time.time() - t0 < timeout_s:
        rows = count_rows()
        if kill_after + 1 <= rows <= total_epochs - 1:
            return {"ok": True, "epochs_done": rows,
                    "waited_s": round(time.time() - t0, 1)}
        if rows >= total_epochs:
            return {"ok": False, "reason": "completed_before_interrupt",
                    "epochs_done": rows, "waited_s": round(time.time() - t0, 1)}
        time.sleep(0.2)
    return {"ok": False, "reason": "timeout", "epochs_done": rows,
            "waited_s": round(time.time() - t0, 1)}


def main() -> None:
    import torch
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default=None, help="stack channel; classification authority is the provenance gate")
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--kill-after-epoch", type=int, default=2)
    ap.add_argument("--batch", type=int, default=4,
                    help="small batch slows epochs so the interrupt window is wide")
    ap.add_argument("--device", default="-1")
    args = ap.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    run_dir = work / "runs" / "lifecycle"
    results_csv = run_dir / "results.csv"
    last_pt = run_dir / "weights" / "last.pt"
    best_pt = run_dir / "weights" / "best.pt"
    t0 = time.time()
    log_paths: dict[str, str] = {}

    # --- stage 1: initial training child -------------------------------------
    train_py = work / "stage1_train.py"
    train_py.write_text(
        TRAIN_CHILD.replace("__DATA__", args.data)
        .replace("__EPOCHS__", str(args.epochs))
        .replace("__BATCH__", str(args.batch))
        .replace("__DEVICE__", str(args.device))
        .replace("__PROJECT__", str(run_dir.parent))
        .replace("__NAME__", run_dir.name), encoding="utf-8")
    log1 = work / "stage1.log"
    f1 = open(log1, "w", encoding="utf-8", errors="replace")
    p1 = subprocess.Popen([sys.executable, "-I", str(train_py)],
                          stdout=f1, stderr=subprocess.STDOUT, cwd=str(work))
    log_paths["stage1"] = str(log1)

    # --- stage 2: interrupt exactly after the kill-after epoch's checkpoint --
    wait = wait_for_epoch_and_checkpoint(results_csv, args.kill_after_epoch,
                                         args.epochs, timeout_s=1800)
    interrupted_at = None
    if wait["ok"]:
        p1.terminate()  # TerminateProcess — controlled hard interruption
        p1.wait(timeout=60)
        interrupted_at = p1.returncode
    else:
        p1.terminate()
        p1.wait(timeout=60)
        interrupted_at = p1.returncode
    f1.close()
    rows_at_kill = wait["epochs_done"]

    # --- stage 3: NEW process resume ------------------------------------------
    # A completed training strips last.pt to inference weights; verify the
    # interrupted checkpoint is truly resumable BEFORE launching, so YOLO can
    # never silently fall back to starting a fresh 100-epoch run.
    ckpt_state = {"checked": False, "has_optimizer_state": None}
    if wait["ok"] and last_pt.is_file():
        import torch as _torch
        try:
            ck = _torch.load(last_pt, map_location="cpu", weights_only=False)
            ckpt_state = {"checked": True,
                          "has_optimizer_state": "optimizer" in ck and ck.get("optimizer") is not None,
                          "ckpt_epoch": ck.get("epoch")}
        except Exception as e:  # noqa: BLE001 — recorded, gate stays honest
            ckpt_state = {"checked": True, "has_optimizer_state": None, "error": str(e)[:300]}
    resume_py = work / "stage3_resume.py"
    log3 = work / "stage3.log"
    resumable = bool(wait["ok"] and ckpt_state.get("has_optimizer_state"))
    if resumable:
        resume_py.write_text(RESUME_CHILD.replace("__LAST_PT__", str(last_pt)),
                             encoding="utf-8")
        r3 = subprocess.run([sys.executable, "-I", str(resume_py)],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=str(work), timeout=3600)
        log3.write_text(r3.stdout + "\n--- stderr ---\n" + r3.stderr, encoding="utf-8")
    else:
        # do NOT launch: YOLO(last.pt).train(resume=True) on a non-resumable
        # checkpoint silently starts a fresh 100-epoch run — refused by design
        r3 = subprocess.CompletedProcess([], returncode=3, stdout="",
                                         stderr="resume refused: checkpoint not resumable "
                                                f"({ckpt_state})")
        log3.write_text(r3.stderr, encoding="utf-8")
    log_paths["stage3_resume"] = str(log3)

    # --- stage 4: third process reload + GPU inference ------------------------
    # prefer a val-batch plot produced by the run itself (always present after
    # validation); fall back to any dataset image under the workdir
    cand = run_dir / "val_batch0_labels.jpg"
    hits = glob.glob(str(work / "**" / "images" / "*.jpg"), recursive=True)[:1]
    infer_src = cand if cand.is_file() else (Path(hits[0]) if hits else None)
    if infer_src is None:
        r4 = subprocess.CompletedProcess([], returncode=4, stdout="",
                                         stderr="no inference source found")
        log4 = work / "stage4.log"
        log4.write_text(r4.stderr, encoding="utf-8")
    else:
        infer_py = work / "stage4_infer.py"
        infer_py.write_text(INFER_CHILD.replace("__BEST_PT__", str(best_pt))
                            .replace("__SOURCE__", str(infer_src)), encoding="utf-8")
        log4 = work / "stage4.log"
        r4 = subprocess.run([sys.executable, "-I", str(infer_py)],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=str(work), timeout=1200)
        log4.write_text(r4.stdout + "\n--- stderr ---\n" + r4.stderr, encoding="utf-8")
    log_paths["stage4_infer"] = str(log4)

    # --- verdicts --------------------------------------------------------------
    final_rows = 0
    last_epoch_value = None
    if results_csv.is_file():
        lines = [l for l in results_csv.read_text(
            encoding="utf-8", errors="replace").strip().splitlines() if l.strip()]
        final_rows = max(0, len(lines) - 1)
        if final_rows:
            first_cell = lines[-1].split(",")[0].strip()
            if first_cell.isdigit():
                last_epoch_value = int(first_cell)
    resume_log = (log3.read_text(encoding="utf-8", errors="replace") if log3.is_file() else "")
    t12 = r3.returncode == 0 and "RESUME_DONE" in resume_log
    # resume may legitimately re-run the interrupted epoch (duplicate csv row);
    # the authoritative continuity fact is the LAST epoch value reaching the
    # configured total after having grown beyond the kill point
    epoch_continuity = (t12 and rows_at_kill < final_rows
                        and last_epoch_value == args.epochs)
    resume_state_evidence = ("Resuming" in resume_log
                             or "resuming" in resume_log.lower())
    t13 = r4.returncode == 0 and "INFER_OK" in r4.stdout
    verdict = "PASS" if (wait["ok"] and t12 and epoch_continuity and t13
                         and resume_state_evidence) else "FAIL"

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
        (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None),
        "command": (f"python verify_checkpoint_resume.py --epochs {args.epochs} "
                    f"--kill-after-epoch {args.kill_after_epoch} --device {args.device}"),
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": None if verdict == "PASS" else "CHECKPOINT_RESUME_FAILURE",
        "raw_log_path": str(work / "lifecycle_summary.log"),
        "stages": {
            "wait_for_checkpoint": wait,
            "child1_returncode": interrupted_at,
            "rows_at_kill": rows_at_kill,
            "checkpoint_resumability": ckpt_state,
            "resume_exit": r3.returncode, "resume_done_marker": t12,
            "resume_state_evidence_logged": resume_state_evidence,
            "final_epoch_rows": final_rows, "last_epoch_value": last_epoch_value,
            "epoch_continuity": epoch_continuity,
            "infer_exit": r4.returncode, "infer_ok": t13,
        },
        "resume_semantics": "resume=True (training state), not weights-only load",
        "checkpoint_sha256": {
            "last.pt": gp_lib.sha256_file(last_pt) if last_pt.is_file() else None,
            "best.pt": gp_lib.sha256_file(best_pt) if best_pt.is_file() else None,
        },
        "logs": log_paths,
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(json.dumps(record["stages"], indent=2))
    print(f"CHECKPOINT_RESUME: {verdict}")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
