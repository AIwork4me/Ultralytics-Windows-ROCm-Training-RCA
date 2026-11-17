# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Run ONE official YOLO26 model per fresh Windows process with raw, immutable receipts.

This is a community *experiment harness*, not proof of official Windows training
support. Never report success from returncode alone, an AMP flag or CPU fallback.
Use under a previously verified physical gfx1201 Nightly preflight.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import uuid

REPO = Path(__file__).resolve().parents[2]
MATRIX = REPO / "validation/gfx1201-rx9070xt/yolo26_model_matrix.json"

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

def choose_case(case_id: str) -> dict:
    m = json.loads(MATRIX.read_text(encoding="utf-8"))
    found = [x for x in m["mandatory"] + m["optional"] if x["id"] == case_id]
    if len(found) != 1:
        raise ValueError("UNKNOWN_MODEL_ID; enumerate via yolo26_model_matrix.json")
    return found[0]

def verify_preflight(path: Path, lock_path: Path, device: int) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if x.get("status") != "PHYSICAL_GFX1201_PREFLIGHT_PASS" or not x.get("physical_gpu_identity_verified"):
        raise ValueError("BLOCKED_GPU_IDENTITY: preflight did not physically pass")
    if x.get("wheel_lock_sha256") != digest(lock_path):
        raise ValueError("BLOCKED_PACKAGE: wheel lock differs from preflight bytes")
    if lock.get("channel") != "nightly" or lock.get("gfx_target") != "gfx1201":
        raise ValueError("BLOCKED_PACKAGE: wrong channel or gfx")
    gpu = x.get("devices", [])[device] if len(x.get("devices", [])) > device >= 0 else None
    if not gpu or "gfx1201" not in gpu.get("gcn_arch_name", "").lower() or "9070" not in gpu.get("name", ""):
        raise ValueError("BLOCKED_GPU_IDENTITY: wrong selected GPU")
    return x

def capture_child(args: argparse.Namespace) -> int:
    case = choose_case(args.model)
    pre = verify_preflight(Path(args.preflight), Path(args.wheel_lock), args.device)
    if args.phase == "train" and case["model"].endswith(".yaml") and not args.allow_scratch:
        raise ValueError("Training architecture-only YAML requires explicit --allow-scratch")
    if args.phase == "resume" and not args.checkpoint:
        raise ValueError("Resume requires a genuinely interrupted --checkpoint; not a completed stripped checkpoint")
    if args.phase == "train" and (args.epochs < 1 or args.batch < 1 or args.workers < 0):
        raise ValueError("Invalid train arguments")
    if not args.sample_image or not Path(args.sample_image).is_file():
        raise ValueError("--sample-image must be an existing local image; no hidden network fallback")
    root = Path(args.out_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    tag = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    run = root / case["id"] / tag
    run.mkdir(parents=True, exist_ok=False)
    cfg = {"case": case, "phase": args.phase, "preflight": str(Path(args.preflight).resolve()),
           "preflight_sha256": digest(Path(args.preflight)), "wheel_lock_sha256": digest(Path(args.wheel_lock)),
           "device": args.device, "epochs": args.epochs, "batch": args.batch, "workers": args.workers,
           "imgsz": args.imgsz or case.get("smoke_imgsz", 320),
           "sample_image": str(Path(args.sample_image).resolve()),
           "sample_sha256": digest(Path(args.sample_image)),
           "checkpoint": str(Path(args.checkpoint).resolve()) if args.checkpoint else None,
           "checkpoint_sha256": digest(Path(args.checkpoint)) if args.checkpoint else None,
           "run_dir": str(run), "created_utc": utc()}
    write_json(run / "config.json", cfg)
    cmd = [sys.executable, str(Path(__file__).resolve()), "_child", "--config", str(run / "config.json")]
    started = time.monotonic()
    envelope = {"schema_version": "r22a7-run-envelope-v1", "status": "INCONCLUSIVE",
                "start_utc": utc(), "command": cmd, "cwd": str(REPO), "parent_pid": os.getpid(),
                "preflight_sha256": cfg["preflight_sha256"], "wheel_lock_sha256": cfg["wheel_lock_sha256"],
                "git_source": subprocess.run(["git","rev-parse","HEAD"],cwd=REPO,capture_output=True,text=True).stdout.strip()}
    proc = None
    try:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=run, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                creationflags=flags)
        envelope["child_pid"] = proc.pid
        try:
            stdout, stderr = proc.communicate(timeout=args.timeout_seconds)
            envelope["exit_code"] = proc.returncode
            envelope["status"] = "CHILD_EXIT_0" if proc.returncode == 0 else "CHILD_FAILED"
        except subprocess.TimeoutExpired:
            # Windows: terminate only our tracked child PID and descendants.
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               capture_output=True, timeout=30)
            else:
                proc.kill()
            stdout, stderr = proc.communicate(timeout=45)
            envelope["status"] = "TIMEOUT"
            envelope["exit_code"] = None
            envelope["orphan_check_required"] = True
        (run / "stdout.raw").write_bytes(stdout)
        (run / "stderr.raw").write_bytes(stderr)
    except Exception as ex:
        envelope["status"] = "ENVELOPE_ERROR"
        envelope["error"] = f"{type(ex).__name__}: {ex}"
        envelope["exit_code"] = None
        if proc is not None and proc.poll() is None:
            proc.kill()
        for name in ("stdout.raw", "stderr.raw"):
            (run / name).touch(exist_ok=True)
    finally:
        envelope["finish_utc"] = utc()
        envelope["duration_seconds"] = round(time.monotonic()-started, 3)
        envelope["stdout_sha256"] = digest(run / "stdout.raw") if (run / "stdout.raw").exists() else None
        envelope["stderr_sha256"] = digest(run / "stderr.raw") if (run / "stderr.raw").exists() else None
        child_result = run / "child_result.json"
        envelope["child_result_sha256"] = digest(child_result) if child_result.is_file() else None
        write_json(run / "envelope.json", envelope)
    result = json.loads((run / "child_result.json").read_text(encoding="utf-8")) if (run / "child_result.json").exists() else {}
    print(json.dumps({"case":case["id"],"phase":args.phase,"attempt":str(run),
                      "envelope_status":envelope["status"],"child_status":result.get("status", "MISSING"),
                      "elapsed_s":envelope["duration_seconds"]},ensure_ascii=False))
    return 0 if envelope["exit_code"] == 0 and result.get("status") == "PASS" else 2

def _child(cfg: dict) -> int:
    run = Path(cfg["run_dir"])
    result = {"schema_version":"r22a7-child-result-v1", "status":"FAIL", "case_id":cfg["case"]["id"],
              "phase":cfg["phase"],"started_utc":utc(),"gpu_verified_during_training":False,
              "amp_low_precision_observed":"NOT_INSTRUMENTED", "checkpoints":{},
              "stage_status": {"train":"NOT_RUN","val":"NOT_RUN","reload":"NOT_RUN","predict":"NOT_RUN","resume":"NOT_RUN"}}
    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
        i=cfg["device"]
        if not torch.cuda.is_available():
            raise RuntimeError("GPU_UNAVAILABLE")
        prop=torch.cuda.get_device_properties(i)
        if "gfx1201" not in str(getattr(prop,"gcnArchName","")).lower() or "9070" not in prop.name:
            raise RuntimeError("NOT_PHYSICAL_RX9070XT")
        torch.cuda.set_device(i)
        result["runtime"]={"torch":torch.__version__,"hip":torch.version.hip,
                           "ultralytics":ultralytics.__version__,"gpu_name":prop.name,
                           "gfx":str(getattr(prop,"gcnArchName","")),"gpu_index":i}
        cfg_case=cfg["case"]
        device=str(i)
        if cfg["phase"] == "train":
            model = YOLO(cfg_case["model"])
            result["resolved_task"] = model.task
            if model.task != cfg_case["task"]:
                raise RuntimeError("TASK_MISMATCH: pretrained model does not match matrix")
            src=Path(cfg_case["model"])
            result["official_pretrained_weight_sha256"] = digest(src) if src.is_file() else "NOT_LOCALLY_IDENTIFIED"
            observations={"gpu_train_batch_events":0}
            def observe(trainer):
                try:
                    p=next(trainer.model.parameters())
                    if p.device.type=="cuda" and p.device.index==i:
                        observations["gpu_train_batch_events"] += 1
                except Exception:
                    pass
            model.add_callback("on_train_batch_end", observe)
            model.train(data=cfg_case["dataset"], device=device, epochs=cfg["epochs"],
                        imgsz=cfg["imgsz"], batch=cfg["batch"], workers=cfg["workers"],
                        project=str(run / "ultralytics"), name="train",
                        exist_ok=False, amp=True, seed=0, save=True, val=True, cache=False)
            result["gpu_verified_during_training"] = observations["gpu_train_batch_events"] > 0
            result["gpu_train_batch_events"] = observations["gpu_train_batch_events"]
            result["stage_status"]["train"]="PASS" if result["gpu_verified_during_training"] else "FAIL"
            if not result["gpu_verified_during_training"]:
                raise RuntimeError("CPU_FALLBACK_OR_TRAIN_GPU_UNVERIFIED")
            saved=Path(model.trainer.save_dir)
            metrics=saved/"results.csv"
            if metrics.is_file():
                with metrics.open(encoding="utf-8",newline="") as fh:
                    result["epoch_rows"] = sum(1 for _ in csv.DictReader(fh))
            if result.get("epoch_rows",0) < cfg["epochs"]:
                raise RuntimeError("TRAIN_EPOCH_INCOMPLETE")
            checkpoint=saved/"weights"/"best.pt"
            last=saved/"weights"/"last.pt"
            for key,path in (("best",checkpoint),("last",last)):
                if not path.is_file() or path.stat().st_size == 0:
                    raise RuntimeError(f"MISSING_CHECKPOINT_{key}")
                result["checkpoints"][key]={"path":str(path),"bytes":path.stat().st_size,"sha256":digest(path)}
            result["gpu_process_peak_allocated_bytes"]=torch.cuda.max_memory_allocated(i)
        elif cfg["phase"] == "resume":
            checkpoint=Path(cfg["checkpoint"])
            model=YOLO(str(checkpoint))
            result["source_checkpoint_sha256"]=digest(checkpoint)
            model.train(resume=True,device=device)
            result["stage_status"]["resume"]="PASS"
            saved=Path(model.trainer.save_dir)
            checkpoint=saved/"weights"/"best.pt"
            if not checkpoint.is_file():
                raise RuntimeError("NO_POST_RESUME_CHECKPOINT")
        else:
            raise RuntimeError("UNKNOWN_PHASE")
        # Both train and resume must independently reload and validate the saved model.
        reload_model=YOLO(str(checkpoint))
        result["stage_status"]["reload"]="PASS"
        reload_model.val(data=cfg_case["dataset"],device=device,batch=1,
                         imgsz=cfg["imgsz"],workers=0,verbose=False)
        result["stage_status"]["val"]="PASS"
        predictions=reload_model.predict(source=cfg["sample_image"],device=device,save=False,verbose=False)
        if not predictions:
            raise RuntimeError("NO_INFERENCE_RESULT")
        predictor_dev=getattr(reload_model.predictor,"device",None)
        if predictor_dev is None or predictor_dev.type!="cuda" or predictor_dev.index!=i:
            raise RuntimeError("INFERENCE_CPU_FALLBACK")
        result["stage_status"]["predict"]="PASS"
        result["predicted_frames"]=len(predictions)
        result["status"]="PASS"
    except Exception as e:
        result["error_type"]=type(e).__name__
        result["error"]=str(e)
        result["traceback"]=traceback.format_exc()
        if "out of memory" in str(e).lower() or "OutOfMemory" in type(e).__name__:
            result["status"]="OOM"
    finally:
        result["finished_utc"]=utc()
        write_json(run/"child_result.json",result)
    return 0 if result["status"]=="PASS" else 2

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    r=sub.add_parser("run")
    r.add_argument("--model",required=True)
    r.add_argument("--phase",choices=["train","resume"],default="train")
    r.add_argument("--preflight",required=True)
    r.add_argument("--wheel-lock",required=True)
    r.add_argument("--out-root",required=True)
    r.add_argument("--sample-image",required=True)
    r.add_argument("--device",type=int,default=0)
    r.add_argument("--epochs",type=int,default=3)
    r.add_argument("--imgsz",type=int,default=None)
    r.add_argument("--batch",type=int,default=1)
    r.add_argument("--workers",type=int,default=0)
    r.add_argument("--timeout-seconds",type=int,default=3600)
    r.add_argument("--allow-scratch",action="store_true")
    r.add_argument("--checkpoint",default=None)
    c=sub.add_parser("_child")
    c.add_argument("--config",required=True)
    args=p.parse_args()
    if args.command=="_child":
        return _child(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.timeout_seconds<60 or args.timeout_seconds>86400:
        raise ValueError("timeout must be 60..86400 seconds")
    return capture_child(args)

if __name__=="__main__":
    sys.exit(main())
