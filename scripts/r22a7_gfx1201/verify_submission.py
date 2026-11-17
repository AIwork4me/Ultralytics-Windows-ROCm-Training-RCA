# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""CPU-only independent structural audit of the gfx1201 community evidence.

No physical experiments are generated or simulated. PASS is a strict claim
over committed stdout/stderr + child receipts, never over a handwritten CSV.
This verifier does not prove AMP dtype/optimizer numerical parity; that
requires the separate audited runtime instrumentation described in the guide.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
MATRIX = REPO / "validation/gfx1201-rx9070xt/yolo26_model_matrix.json"
SIZES = ("n","s","m","l","x")
TASKS = ("detect","segment","semantic","depth","classify","pose","obb")

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def matrix_ids() -> dict:
    m=load_json(MATRIX)
    cases=m.get("mandatory",[])
    ids=[c.get("id") for c in cases]
    if len(ids)!=35 or len(set(ids))!=35:
        raise ValueError("MATRIX_NOT_35_UNIQUE_MODELS")
    pairs={(c.get("task"),c.get("size")) for c in cases}
    if pairs!={(task,size) for task in TASKS for size in SIZES}:
        raise ValueError("MATRIX_TASK_SIZE_CROSS_PRODUCT_INCOMPLETE")
    return {c["id"]:c for c in cases}

def verify_attempt(path: Path, entry: dict) -> dict:
    facts={"path":str(path),"verdict":"REJECTED","issues":[],"phase":None}
    required=["config.json","envelope.json","child_result.json","stdout.raw","stderr.raw"]
    missing=[x for x in required if not (path/x).is_file()]
    if missing:
        facts["issues"].append("MISSING_RAW_OR_RECEIPT:"+",".join(missing))
        return facts
    try:
        cfg=load_json(path/"config.json")
        env=load_json(path/"envelope.json")
        child=load_json(path/"child_result.json")
    except Exception as e:
        facts["issues"].append("CORRUPT_JSON:"+str(e))
        return facts
    facts["phase"]=cfg.get("phase")
    if cfg.get("case",{}).get("id")!=entry["id"] or child.get("case_id")!=entry["id"]:
        facts["issues"].append("CASE_ID_MISMATCH")
    if cfg.get("case",{}).get("model")!=entry["model"]:
        facts["issues"].append("MODEL_IDENTITY_MISMATCH")
    child_status=child.get("status")
    envelope_status=env.get("status")
    # Authentic failed attempts must remain visible, but are never positive
    # evidence for a model. A retry does not erase previous failure receipts.
    for name,key in (("stdout.raw","stdout_sha256"),("stderr.raw","stderr_sha256"),
                     ("child_result.json","child_result_sha256")):
        if env.get(key)!=hash_file(path/name):
            facts["issues"].append("RAW_SHA_MISMATCH:"+name)
    if env.get("wheel_lock_sha256")!=cfg.get("wheel_lock_sha256"):
        facts["issues"].append("LOCK_SHA_MISMATCH")
    if cfg.get("preflight_sha256")!=env.get("preflight_sha256"):
        facts["issues"].append("PREFLIGHT_SHA_MISMATCH")
    if child_status!="PASS" or envelope_status!="CHILD_EXIT_0" or env.get("exit_code")!=0:
        if child_status in ("FAIL","OOM") and envelope_status=="CHILD_FAILED" \
                and isinstance(env.get("exit_code"),int) and env["exit_code"]!=0:
            if not facts["issues"]:
                facts["verdict"]="FAILED_ATTEMPT_AUDITED"
                facts["failure_class"]=child.get("error_type")
                return facts
        facts["issues"].append("CONTRADICTORY_OR_INCOMPLETE_RESULT")
        return facts
    rt=child.get("runtime",{})
    if "gfx1201" not in str(rt.get("gfx","")).lower() or "9070" not in str(rt.get("gpu_name","")):
        facts["issues"].append("WRONG_GPU")
    if not rt.get("hip") or not rt.get("torch") or not rt.get("ultralytics"):
        facts["issues"].append("RUNTIME_PROVENANCE_ABSENT")
    states=child.get("stage_status",{})
    if facts["phase"]=="train":
        for stage in ("train","val","reload","predict"):
            if states.get(stage)!="PASS":
                facts["issues"].append("MISSING_STAGE:"+stage)
        if child.get("gpu_verified_during_training") is not True or                 not isinstance(child.get("gpu_train_batch_events"),int) or                 child.get("gpu_train_batch_events",0)<1:
            facts["issues"].append("TRAIN_GPU_NOT_VERIFIED")
        if not isinstance(child.get("epoch_rows"),int) or child.get("epoch_rows",0)<cfg.get("epochs",999999):
            facts["issues"].append("EPOCHS_NOT_COMPLETED")
        if child.get("resolved_task")!=entry["task"]:
            facts["issues"].append("TASK_MISMATCH")
        for name in ("best","last"):
            ck=child.get("checkpoints",{}).get(name,{})
            if not isinstance(ck.get("bytes"),int) or ck.get("bytes",0)<=0 or                     not isinstance(ck.get("sha256"),str) or len(ck.get("sha256"))!=64:
                facts["issues"].append("CHECKPOINT_PROVENANCE_MISSING:"+name)
    elif facts["phase"]=="resume":
        for stage in ("resume","val","reload","predict"):
            if states.get(stage)!="PASS":
                facts["issues"].append("MISSING_RESUME_STAGE:"+stage)
        if not cfg.get("checkpoint_sha256") or                 cfg.get("checkpoint_sha256")!=child.get("source_checkpoint_sha256"):
            facts["issues"].append("RESUME_INPUT_SHA_MISMATCH")
        # A resume marker alone never proves optimizer or GradScaler restoration.
        facts["resume_strength"]="CORE_RESUME_EXECUTED_NOT_FULL_STATE_AUDITED"
    else:
        facts["issues"].append("UNRECOGNIZED_PHASE")
    facts["verdict"]="STRUCTURALLY_VERIFIED" if not facts["issues"] else "REJECTED"
    return facts

def audit(root: Path) -> dict:
    cases=matrix_ids()
    result={"schema_version":"r22a7-gfx1201-submission-audit-v1",
            "experiment_type":"community_unofficial_nightly_training_evidence",
            "verdict":"NOT_READY","mandatory_total":len(cases),"verified_train":0,
            "verified_resume":0,"not_run":[],"rejected":[],"failed_attempts":[],"cases":{},
            "note":"Structural audit of raw byte receipts; not AMD Stable training support or independent AMP numerical certification."}
    for cid,case in cases.items():
        path=root/cid
        attempts=sorted(path.glob("*/child_result.json")) if path.exists() else []
        # Any directory without child_result must remain visible as a failed attempt.
        all_dirs=sorted(p for p in path.iterdir() if p.is_dir()) if path.exists() else []
        checked=[verify_attempt(p,case) for p in all_dirs]
        passing_train=[x for x in checked if x["verdict"]=="STRUCTURALLY_VERIFIED" and x["phase"]=="train"]
        passing_resume=[x for x in checked if x["verdict"]=="STRUCTURALLY_VERIFIED" and x["phase"]=="resume"]
        if passing_train:result["verified_train"]+=1
        if passing_resume:result["verified_resume"]+=1
        if not all_dirs:result["not_run"].append(cid)
        result["rejected"] += [{"model":cid,**x} for x in checked if x["verdict"]=="REJECTED"]
        result["failed_attempts"] += [{"model":cid,**x} for x in checked if x["verdict"]=="FAILED_ATTEMPT_AUDITED"]
        result["cases"][cid]={"train":bool(passing_train),"resume":bool(passing_resume),
                              "attempt_count":len(all_dirs),"attempts":checked}
    if result["verified_train"]==35 and not result["rejected"]:
        result["verdict"]="TRAIN_VALIDATE_RELOAD_PREDICT_MATRIX_35_STRUCTURALLY_COMPLETE"
    # No false promotion: full-state resume/AMP needs separate physical audit.
    return result

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-root",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--report-only",action="store_true",help="Generate gap report; do not return full-matrix success")
    args=p.parse_args()
    output=Path(args.out)
    if output.exists():
        raise SystemExit("Refusing to overwrite an existing audit result")
    summary=audit(Path(args.evidence_root))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("verdict","mandatory_total","verified_train",
                                             "verified_resume","not_run")},ensure_ascii=False))
    return 0 if args.report_only or (summary["verified_train"]==35 and not summary["rejected"]) else 2

if __name__=="__main__":
    sys.exit(main())
