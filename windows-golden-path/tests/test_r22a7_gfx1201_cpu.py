# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.7 CPU-only falsification: never invent a physical gfx1201 PASS."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/r22a7_gfx1201"))
import verify_submission as ev  # noqa: E402
import run_case as runner  # noqa: E402

def test_matrix_35_mandatory_7_tasks_5_scales():
    cases = ev.matrix_ids()
    assert len(cases) == 35
    assert {c["task"] for c in cases.values()} == set(ev.TASKS)
    assert {c["size"] for c in cases.values()} == set(ev.SIZES)

def test_matrix_15_optional_distinct_from_mandatory():
    m = json.loads(ev.MATRIX.read_text(encoding="utf-8"))
    mand = {c["id"] for c in m["mandatory"]}
    opt = {c["id"] for c in m["optional"]}
    assert len(opt) == 15
    assert not (mand & opt)
    assert all(c["status"] == "NOT_RUN" for c in m["mandatory"] + m["optional"])

@pytest.mark.parametrize("cid,task,ds", [
    ("yolo26n","detect","coco8.yaml"),
    ("yolo26x-seg","segment","coco8-seg.yaml"),
    ("yolo26m-sem","semantic","cityscapes8.yaml"),
    ("yolo26l-depth","depth","depth8.yaml"),
    ("yolo26s-cls","classify","imagenet10"),
    ("yolo26n-pose","pose","coco8-pose.yaml"),
    ("yolo26x-obb","obb","dota8.yaml"),
])
def test_task_specific_datasets(cid,task,ds):
    m=runner.choose_case(cid)
    assert m["task"] == task and m["dataset"] == ds

def test_no_attempts_is_not_pass(tmp_path):
    a=ev.audit(tmp_path)
    assert a["verified_train"] == 0 and a["verified_resume"] == 0
    assert len(a["not_run"]) == 35
    assert a["verdict"] == "NOT_READY"

def test_missing_raw_receipt_must_reject(tmp_path):
    case=next(iter(ev.matrix_ids().values()))
    a=tmp_path/case["id"]/"attempt1"
    a.mkdir(parents=True)
    (a/"child_result.json").write_text('{"status":"PASS"}',encoding="utf-8")
    check=ev.verify_attempt(a,case)
    assert check["verdict"]=="REJECTED"
    assert any(x.startswith("MISSING_RAW_OR_RECEIPT") for x in check["issues"])

def test_forged_completed_stage_with_no_raw_hashes_rejected(tmp_path):
    case=runner.choose_case("yolo26n")
    a=tmp_path/"attempt2"
    a.mkdir()
    raw={"schema_version":"fake", "case_id":"yolo26n","phase":"train","status":"PASS",
         "runtime":{"gfx":"gfx1201","gpu_name":"AMD Radeon RX 9070 XT","hip":"10.3",
                    "torch":"unverified","ultralytics":"unverified"},
         "stage_status":{x:"PASS" for x in ("train","val","reload","predict")},
         "gpu_verified_during_training":True,"gpu_train_batch_events":1,"epoch_rows":3}
    (a/"config.json").write_text(json.dumps({"case":case,"phase":"train","epochs":3}),encoding="utf-8")
    (a/"envelope.json").write_text('{"exit_code":0,"status":"CHILD_EXIT_0"}',encoding="utf-8")
    (a/"child_result.json").write_text(json.dumps(raw),encoding="utf-8")
    (a/"stdout.raw").write_bytes(b"NOT REAL GPU EXECUTION")
    (a/"stderr.raw").write_bytes(b"")
    chk=ev.verify_attempt(a,case)
    assert chk["verdict"]=="REJECTED"
    assert any("RAW_SHA_MISMATCH" in x for x in chk["issues"])

def test_preflight_wrong_channel_rejected_without_gpu(tmp_path):
    lock=tmp_path/"bad.json"
    lock.write_text(json.dumps({"channel":"dev","gfx_target":"gfx1201","packages":[]}),encoding="utf-8")
    pre=tmp_path/"pre.json"
    pre.write_text(json.dumps({"status":"PHYSICAL_GFX1201_PREFLIGHT_PASS",
        "physical_gpu_identity_verified":True,
        "wheel_lock_sha256":runner.digest(lock),
        "devices":[{"name":"RX 9070 XT","gcn_arch_name":"gfx1201"}]}),encoding="utf-8")
    with pytest.raises(ValueError,match="BLOCKED_PACKAGE"):
        runner.verify_preflight(pre,lock,0)

def test_preflight_other_arch_rejected_without_gpu(tmp_path):
    lock=tmp_path/"bad.json"
    lock.write_text(json.dumps({"channel":"nightly","gfx_target":"gfx1100","packages":[]}),encoding="utf-8")
    pre=tmp_path/"pre.json"
    pre.write_text(json.dumps({"status":"PHYSICAL_GFX1201_PREFLIGHT_PASS",
        "physical_gpu_identity_verified":True,
        "wheel_lock_sha256":runner.digest(lock),
        "devices":[{"name":"RX 9070 XT","gcn_arch_name":"gfx1201"}]}),encoding="utf-8")
    with pytest.raises(ValueError,match="BLOCKED_PACKAGE"):
        runner.verify_preflight(pre,lock,0)

def test_unlisted_model_rejected():
    with pytest.raises(ValueError,match="UNKNOWN_MODEL_ID"):
        runner.choose_case("yolo26madeup")

def test_yaml_extension_never_claims_pretrained_weight():
    case=runner.choose_case("yolo26n-p2")
    assert case["from_scratch"] is True
    assert case["weights_available"] is False
    assert case["model"].endswith(".yaml")
