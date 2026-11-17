# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 checkpoint lifecycle verifier v2 (mission PHASE 4 §7.4).

Versioned successor of windows-golden-path/scripts/verify_checkpoint_resume.py
(kept untouched for historical receipts). New evidence depth:

  * state-class introspection on the checkpoint AT THE INTERRUPT: which state
    classes this Ultralytics version actually serializes (model / optimizer /
    scheduler / GradScaler / epoch / best_fitness / trainer args / EMA).
    Absent-by-design classes are reported NOT_SERIALIZED_BY_UPSTREAM —
    the raw observed key set is recorded so nothing is invented.
  * checkpoint SHA256 at kill time (before resume) in addition to final hashes
  * resume child instruments the RESTORED optimizer (state entries present
    after load — a fresh optimizer has an empty state) and counts EFFECTIVE
    parameter updates after resume via sentinel deltas
  * writes the lifecycle_summary.log it references (v1 never did — root cause
    of one lost raw log)
  * resume start_epoch printed by the child for independent epoch-continuity

Only checkpoints created by this controlled experiment are loaded
(weights_only=False is safe here BY CONSTRUCTION — no untrusted pickle).

    python scripts/r22a5n1/verify_checkpoint_resume_v2.py --out resume.json \
        --run-id R22A5N1-G5 --work-dir DIR --epochs 4 --kill-after-epoch 1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "windows-golden-path" / "scripts"))
import gp_lib  # noqa: E402
from verify_checkpoint_resume import wait_for_epoch_and_checkpoint  # noqa: E402

TRAIN_CHILD = r'''
import sys
from ultralytics import YOLO
m = YOLO("yolo26n.pt")
m.train(data="__DATA__", epochs=__EPOCHS__, device=__DEVICE__, project=r"__PROJECT__",
        name=r"__NAME__", exist_ok=True, seed=7, workers=0, batch=__BATCH__, verbose=True)
'''

RESUME_CHILD = r'''
from ultralytics import YOLO
import pathlib, torch
last = pathlib.Path(r"__LAST_PT__")
assert last.is_file(), "last.pt missing: " + str(last)
m = YOLO(str(last))
obs = {"effective": 0, "attempts": 0, "state_entries": None, "opt_class": None,
       "start_epoch": None}

def on_train_start(trainer):
    opt = trainer.optimizer
    obs["opt_class"] = type(opt).__name__
    obs["state_entries"] = len(getattr(opt, "state", {}) or {})
    obs["start_epoch"] = int(getattr(trainer, "start_epoch", -1))
    print("RESUME_OPTIMIZER class=%s state_entries=%s start_epoch=%s" %
          (obs["opt_class"], obs["state_entries"], obs["start_epoch"]))
    live = {n: p for n, p in trainer.model.named_parameters()}
    id2name = {id(p): n for n, p in live.items()}
    sents = {}
    for gi, group in enumerate(opt.param_groups):
        cands = sorted(((p.numel(), j, id2name.get(id(p), f"u[{gi}:{j}]"))
                        for j, p in enumerate(group["params"])), key=lambda t: t[0])
        for _, _, n in cands[:2]:
            sents[f"g{gi}:{n}"] = live.get(n)
    before = {k: v.detach().clone() for k, v in sents.items() if v is not None}
    orig = opt.step
    def counting_step(*a, **kw):
        obs["attempts"] += 1
        r = orig(*a, **kw)
        moved = max(float((v.detach() - before[k]).abs().max().item())
                    for k, v in sents.items() if k in before)
        if moved > 0.0:
            obs["effective"] += 1
        for k, v in sents.items():
            before[k] = v.detach().clone()
        return r
    opt.step = counting_step

def on_train_end(trainer):
    print("RESUME_EFFECTIVE_UPDATES attempts=%s effective=%s" %
          (obs["attempts"], obs["effective"]))

m.add_callback("on_train_start", on_train_start)
m.add_callback("on_train_end", on_train_end)
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

# state classes this Ultralytics version is expected to serialize; the ones it
# does NOT are reported NOT_SERIALIZED_BY_UPSTREAM (observed key set recorded —
# the classification is derived from observation, never assumed).
# Ultralytics 8.4.x observed behavior: mid-training checkpoints store the
# weights under 'ema' (model=None); the FINAL save moves them into 'model'
# (ema=None) and strips optimizer/scaler. Both fields count as model weights.
STATE_CLASSES = {
    "model_weights": ("model", "ema"),
    "optimizer": ("optimizer",),
    "scheduler": ("scheduler", "lr_scheduler", "scheduler_state"),
    "gradscaler": ("scaler", "gradscaler", "grad_scaler"),
    "epoch": ("epoch",),
    "best_fitness": ("best_fitness",),
    "trainer_args": ("train_args",),
    "ema": ("ema",),
}


def classify_state_classes(ckpt: dict) -> dict:
    keys = set(ckpt.keys())
    out: dict = {}
    for cls, names in STATE_CLASSES.items():
        present = [n for n in names if n in keys and ckpt.get(n) is not None]
        out[cls] = {
            "serialized": True if present else "NOT_SERIALIZED_BY_UPSTREAM",
            "observed_fields": present,
        }
    out["_raw_top_level_keys"] = sorted(k for k in keys)
    return out


def main() -> None:
    import torch
    import importlib.metadata as im
    import subprocess

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--channel", default="nightly")
    ap.add_argument("--mission", default="R22A.5N.1")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--data", default="coco128.yaml")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--kill-after-epoch", type=int, default=1)
    ap.add_argument("--batch", type=int, default=4)
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
    summary_lines: list[str] = [f"# lifecycle summary {gp_lib.now_utc()}",
                                f"# run_id={args.run_id}"]

    def summary(line: str) -> None:
        summary_lines.append(f"{gp_lib.now_utc()} {line}")
        print(f"[lifecycle] {line}")

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
    summary(f"stage1 train child pid={p1.pid}")

    # --- stage 2: controlled interrupt after a SAFE checkpoint ----------------
    wait = wait_for_epoch_and_checkpoint(results_csv, args.kill_after_epoch,
                                         args.epochs, timeout_s=1800)
    p1.terminate()  # terminate ONLY the owned training child
    p1.wait(timeout=60)
    f1.close()
    interrupted_at = p1.returncode
    rows_at_kill = wait["epochs_done"]
    summary(f"interrupted child rc={interrupted_at} rows_at_kill={rows_at_kill}")

    # checkpoint facts AT THE INTERRUPT (sha + state classes + epoch)
    ckpt_state = {"checked": False, "has_optimizer_state": None}
    state_classes: dict = {}
    ckpt_sha_at_kill = None
    if wait["ok"] and last_pt.is_file():
        ckpt_sha_at_kill = gp_lib.sha256_file(last_pt)
        try:
            ck = torch.load(last_pt, map_location="cpu", weights_only=False)
            ckpt_state = {"checked": True,
                          "has_optimizer_state": "optimizer" in ck and ck.get("optimizer") is not None,
                          "ckpt_epoch": ck.get("epoch")}
            state_classes = classify_state_classes(ck)
        except Exception as e:  # noqa: BLE001 — recorded; gate stays honest
            ckpt_state = {"checked": True, "has_optimizer_state": None,
                          "error": str(e)[:300]}
    summary(f"checkpoint_at_kill sha={ckpt_sha_at_kill} state={ckpt_state}")

    # --- stage 3: NEW process resume ------------------------------------------
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
        r3 = subprocess.CompletedProcess([], returncode=3, stdout="",
                                         stderr="resume refused: checkpoint not resumable "
                                                f"({ckpt_state})")
        log3.write_text(r3.stderr, encoding="utf-8")
    log_paths["stage3_resume"] = str(log3)
    resume_log = log3.read_text(encoding="utf-8", errors="replace") if log3.is_file() else ""
    m_opt = __import__("re").search(r"RESUME_OPTIMIZER class=(\S+) state_entries=(\d+) "
                                    r"start_epoch=(-?\d+)", resume_log)
    m_eff = __import__("re").search(r"RESUME_EFFECTIVE_UPDATES attempts=(\d+) "
                                    r"effective=(\d+)", resume_log)
    resume_start_epoch = int(m_opt.group(3)) if m_opt else None
    optimizer_state_entries = int(m_opt.group(2)) if m_opt else None
    resume_effective = int(m_eff.group(2)) if m_eff else None
    resume_attempts = int(m_eff.group(1)) if m_eff else None
    summary(f"resume rc={r3.returncode} start_epoch={resume_start_epoch} "
            f"optimizer_state_entries={optimizer_state_entries} "
            f"effective={resume_effective}/{resume_attempts}")

    # --- stage 4: third process reload + GPU inference ------------------------
    infer_src = run_dir / "val_batch0_labels.jpg"
    import glob as _glob
    hits = _glob.glob(str(work / "**" / "images" / "*.jpg"), recursive=True)[:1]
    src = infer_src if infer_src.is_file() else (Path(hits[0]) if hits else None)
    if src is None:
        r4 = subprocess.CompletedProcess([], returncode=4, stdout="",
                                         stderr="no inference source found")
        log4 = work / "stage4.log"
        log4.write_text(r4.stderr, encoding="utf-8")
    else:
        infer_py = work / "stage4_infer.py"
        infer_py.write_text(INFER_CHILD.replace("__BEST_PT__", str(best_pt))
                            .replace("__SOURCE__", str(src)), encoding="utf-8")
        log4 = work / "stage4.log"
        r4 = subprocess.run([sys.executable, "-I", str(infer_py)],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=str(work), timeout=1200)
        log4.write_text(r4.stdout + "\n--- stderr ---\n" + r4.stderr, encoding="utf-8")
    log_paths["stage4_infer"] = str(log4)
    summary(f"stage4 infer rc={r4.returncode}")

    # --- verdicts --------------------------------------------------------------
    final_rows = 0
    last_epoch_value = None
    if results_csv.is_file():
        lines = [row for row in results_csv.read_text(
            encoding="utf-8", errors="replace").strip().splitlines() if row.strip()]
        final_rows = max(0, len(lines) - 1)
        if final_rows:
            first_cell = lines[-1].split(",")[0].strip()
            if first_cell.isdigit():
                last_epoch_value = int(first_cell)
    t12 = r3.returncode == 0 and "RESUME_DONE" in resume_log
    epoch_continuity = (t12 and rows_at_kill < final_rows
                        and last_epoch_value == args.epochs)
    t13 = r4.returncode == 0 and "INFER_OK" in r4.stdout
    verdict = "PASS" if (wait["ok"] and t12 and epoch_continuity and t13
                         and (resume_effective or 0) > 0
                         and (optimizer_state_entries or 0) > 0) else "FAIL"

    summary_log = work / "lifecycle_summary.log"
    summary_log.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata["Name"] == "torchvision"
                               for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": gp_lib.classify_runtime(
            gp_lib.detect_workarounds(), args.channel,
            (_m if (_m := gp_lib.loaded_miopen_identity()).get("loaded") else None)),
        "command": (f"python verify_checkpoint_resume_v2.py --epochs {args.epochs} "
                    f"--kill-after-epoch {args.kill_after_epoch} --device {args.device}"),
        "exit_code": 0 if verdict == "PASS" else 1,
        "duration_s": round(time.time() - t0, 1),
        "pass_fail_skip": verdict,
        "failure_classification": None if verdict == "PASS"
        else "CHECKPOINT_RESUME_FAILURE",
        "raw_log_path": str(summary_log),
        "stages": {
            "wait_for_checkpoint": wait,
            "child1_returncode": interrupted_at,
            "total_epochs": args.epochs,
            "kill_after_epoch": args.kill_after_epoch,
            "rows_at_kill": rows_at_kill,
            "checkpoint_resumability": ckpt_state,
            "checkpoint_sha256_at_kill": ckpt_sha_at_kill,
            "resume_exit": r3.returncode, "resume_done_marker": t12,
            "resume_start_epoch": resume_start_epoch,
            "optimizer_state_entries": optimizer_state_entries,
            "resume_effective_updates": resume_effective,
            "resume_step_attempts": resume_attempts,
            "resume_state_evidence_logged": ("Resuming" in resume_log
                                             or "resuming" in resume_log.lower()),
            "final_epoch_rows": final_rows, "last_epoch_value": last_epoch_value,
            "epoch_continuity": epoch_continuity,
            "infer_exit": r4.returncode, "infer_ok": t13,
        },
        "state_classes": state_classes,
        "state_class_note": "state classes classified from the OBSERVED "
                            "checkpoint dict at the interrupt. Observed "
                            "8.4.214 reality: optimizer/epoch/best_fitness/"
                            "train_args/EMA and GradScaler (key 'scaler') ARE "
                            "serialized; the LR scheduler is NOT (rebuilt from "
                            "train_args on resume) — reported "
                            "NOT_SERIALIZED_BY_UPSTREAM, never assumed",
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
    print(f"CHECKPOINT_RESUME_V2: {verdict}")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
