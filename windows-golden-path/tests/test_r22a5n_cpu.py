# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N CPU-only adversarial contract tests (mission §14) — no GPU, no
network, no torch import. Every forged-evidence class from the mission list
is pinned: a stored serialized PASS can never survive recompute.

    python -m pytest windows-golden-path/tests/test_r22a5n_cpu.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
REPO_ROOT = SCRIPTS.parent.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


na = load_module("r22a5n_nightly_acceptance", REPO_ROOT / "scripts" / "r22a5n" / "nightly_acceptance.py")


# ---------------------------------------------------------------- fixtures
def good_lock(**over):
    lock = {
        "channel": "nightly", "gfx_target": "gfx1151", "python_tag": "cp313",
        "packages": [
            {"name": "torch", "version": "2.16.0a0+rocm10.3.0a20261116",
             "sha256": "e1495611828bca9f", "url": "https://nightly.repo.amd.com/rocm/whl-next/torch/x.whl"},
            {"name": "rocm-sdk-libraries", "version": "10.3.0a20261116",
             "sha256": na.FROZEN["wheel_sha256"], "url": "https://nightly.repo.amd.com/rocm/whl-next/rocm-sdk-libraries/x.whl"},
        ],
        "rules_checked": {
            "rocm_family_mix": {"ok": True},
            "device_wheel_present": True, "torchvision_device_wheel_present": True,
            "torch_is_amd_hip": True,
            "gpu_stack_origin_official_channel": {"ok": True},
        },
    }
    lock.update(over)
    return lock


def good_audit(**over):
    a = {
        "audits": [{
            "wheel_sha256": na.FROZEN["wheel_sha256"],
            "miopen_dll": {"sha256": na.FROZEN["miopen_dll_sha256"],
                           "build_commit": "25f28906"},
            "ancestry": {"status": "ahead", "ahead_by": 1074, "behind_by": 0},
            "fix_present": True, "verdict": "POST_FIX_LIBRARIES",
        }]
    }
    a.update(over)
    return a


def good_manifest(**over):
    m = {
        "gpu_stack": {"torch": "2.16.0a0+rocm10.3.0a20261116",
                      "ultralytics": "8.4.214"},
        "pip_check": "No broken requirements found.",
    }
    m.update(over)
    return m


def good_g0(**over):
    g = {
        "verdict": "G0_RUNTIME_IDENTITY_PASS",
        "child_dll_sha256": na.FROZEN["miopen_dll_sha256"],
        "child_dll_path": r"C:\r22a5n\venv\Lib\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll",
        "child_gpu_name": "AMD Radeon(TM) 8060S Graphics",
        "gfx_target": "gfx1151", "child_op_finite": True,
        "parent_and_child_dll_agree": True, "runtime_class": "OFFICIAL_CANDIDATE",
        "exit_code": 0,
    }
    g.update(over)
    return g


def good_cand(**over):
    c = {
        "classification": "OFFICIAL_CANDIDATE_PASS", "expectation": "CANDIDATE",
        "exit_code": 0, "ambient_hiprtc_shim": None,
        "runtime_class": "OFFICIAL_CANDIDATE", "gfx_target": "gfx1151",
        "leg_detail": {"exit_code": 0},
    }
    c.update(over)
    return c


def good_ctrl(**over):
    c = {
        "classification": "OFFICIAL_PRE_FIX_EXPECTED_FAIL",
        "failure_classification": "MIOPEN_HIPRTC_COMPILATION",
        "expectation": "FAIL",
        "miopen_identity_in_parent": {
            "pr13437_marker_miopen_initializer_list": 0},
    }
    c.update(over)
    return c


def good_ops(**over):
    o = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1151",
        "gates": {g: {"status": "PASS"} for g in [
            "cuda_available", "device_identity", "fp32_gemm", "fp16_gemm",
            "autograd", "conv2d_fwd_bwd", "batchnorm_fwd_bwd",
            "torchvision_nms_gpu", "tensor_lifetime"]},
    }
    o["gates"]["device_identity"] = {
        "status": "PASS", "detail": {"gfx_target": "gfx1151"}}
    o.update(over)
    return o


def good_amp(**over):
    a = {
        "training_counts": {
            "batches_completed": 48, "scaler_step_attempts": 11,
            "confirmed_update_events": 7, "skipped_found_inf_flagged": 4,
            "grads_finite_on_stepped_updates": True, "per_step_events": [{}]*7},
        "optimizer": {"requested": "auto", "resolved_class": "AdamW"},
        "amp": {"autocast_dtype_observed": "float16"},
        "low_precision_evidence": {"samples_low_precision": 96,
                                   "samples_total": 96},
        "gradscaler": {"scale_history_len": 11,
                       "backoff_events_observed": 4},
        "loaded_model_delta": {"tensors_changed_beyond_1e-9": 248,
                               "all_finite": True},
        "checkpoint": {"exists": True, "sha256": "x"},
        "loaded_miopen_dll_sha256": na.FROZEN["miopen_dll_sha256"],
        "gpu_name": "AMD Radeon(TM) 8060S Graphics", "gfx_target": "gfx1151",
        "exit_code": 0, "runtime_class": "OFFICIAL_CANDIDATE",
        "pass_fail_skip": "ADAMW_AMP_MULTISTEP_PASS",
    }
    a.update(over)
    return a


def good_ckpt(**over):
    c = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1151",
        "checkpoint_sha256": {"last.pt": "aa", "best.pt": "bb"},
        "resume_semantics": "resume=True (training state), not weights-only load",
        "stages": {
            "checkpoint_resumability": {"has_optimizer_state": True},
            "resume_exit": 0, "resume_done_marker": True,
            "epoch_continuity": True, "final_epoch_rows": 4,
            "last_epoch_value": 3, "infer_exit": 0, "infer_ok": True,
        },
    }
    c.update(over)
    return c


def good_rel(**over):
    r = {
        "harness_train_args": "epochs=3, imgsz=256, batch=8, optimizer='auto', device=-1, workers=8",
        "training_counts": {"batches_completed": 48,
                            "confirmed_update_events": 7},
        "exit_code": 0, "pass_fail_skip": "ADAMW_AMP_MULTISTEP_PASS",
    }
    r.update(over)
    return r


def good_supp():
    return {"spawn_children_count": 16}


def good_orphan():
    return {"orphan_verdict": "CLEAN"}


def all_gates(**mut):
    """Evaluate the full fixture set; `mut` names fixture-override callables."""
    args = {
        "lock": good_lock(), "audit": good_audit(), "manifest": good_manifest(),
        "g0": good_g0(), "cand": good_cand(), "ctrl": good_ctrl(),
        "ops": good_ops(), "amp": good_amp(), "ckpt": good_ckpt(),
        "rel": good_rel(),
    }
    for k, fn in mut.items():
        args[k] = fn(args[k])
    return [
        na.evaluate_pkg(args["lock"], args["audit"], args["manifest"]),
        na.evaluate_g0(args["g0"]),
        na.evaluate_g1(args["cand"], args["ctrl"]),
        na.evaluate_g2(args["ops"]),
        *na.evaluate_g34(args["amp"]),
        na.evaluate_g5(args["ckpt"]),
        na.evaluate_g7(args["rel"], args.get("supp", good_supp()),
                       args.get("orphan", good_orphan())),
    ]


# ---------------------------------------------------------------- tests
def test_honest_fixture_full_pass():
    gates = all_gates()
    res = na.derive(gates, [])
    assert res["overall"] == "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS"


def test_forged_nightly_pass_stored_verdict_with_contradicting_facts():
    # stored PASS everywhere, but training exited 1 and no updates happened
    gates = all_gates(amp=lambda a: good_amp(
        pass_fail_skip="ADAMW_AMP_MULTISTEP_PASS", exit_code=1,
        training_counts={"batches_completed": 0, "scaler_step_attempts": 0,
                         "confirmed_update_events": 0,
                         "skipped_found_inf_flagged": 0,
                         "grads_finite_on_stepped_updates": False,
                         "per_step_events": []}))
    res = na.derive(gates, [])
    assert res["overall"] != "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS"


def test_incorrect_wheel_hash_rejected():
    g = na.evaluate_pkg(
        good_lock(), good_audit(audits=[good_audit()["audits"][0] |
                                       {"wheel_sha256": "deadbeef"}]),
        good_manifest())
    assert g["verdict"] == "FAIL"


def test_wrong_miopen_dll_hash_rejected():
    g = na.evaluate_g0(good_g0(child_dll_sha256="cafebabe"))
    assert g["verdict"] == "FAIL"


def test_dll_contamination_classification_surfaces():
    g = na.evaluate_g0(good_g0(verdict="BLOCKED_DLL_CONTAMINATION"))
    assert g["verdict"] == "FAIL" and "CONTAMINATION" in g["reason"]


def test_mixed_rocm_family_rejected():
    g = na.evaluate_pkg(
        good_lock(rules_checked={**good_lock()["rules_checked"],
                                 "rocm_family_mix": {"ok": False}}),
        good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"


def test_missing_gpu_observations_rejected():
    g = na.evaluate_g0(good_g0(child_gpu_name=None, gfx_target=None))
    assert g["verdict"] == "FAIL"


def test_fp32_fallback_never_amp_pass():
    g3, g4 = na.evaluate_g34(good_amp(
        amp={"autocast_dtype_observed": None},
        low_precision_evidence={"samples_low_precision": 0,
                                "samples_total": 96}))
    assert g3["verdict"] == "PASS"          # training itself is real
    assert g4["amp_verdict"] == "AMP_DISABLED"  # but never AMP_PASS
    res = na.derive([g3, g4], [])
    assert res["overall"] != "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS"


def test_wrong_architecture_rejected():
    gates = all_gates(g0=lambda g: good_g0(gfx_target="gfx1100", child_gpu_name="AMD Radeon RX 7900 XTX"))
    assert gates[1]["verdict"] == "FAIL"


def test_missing_checkpoint_state_restoration_rejected():
    g = na.evaluate_g5(good_ckpt(stages={**good_ckpt()["stages"],
                                         "checkpoint_resumability": {"has_optimizer_state": False}}))
    assert g["verdict"] == "FAIL"


def test_epoch_reset_rejected():
    g = na.evaluate_g5(good_ckpt(stages={**good_ckpt()["stages"],
                                         "epoch_continuity": False}))
    assert g["verdict"] == "FAIL"


def test_unhealthy_worker_tree_rejected():
    g = na.evaluate_g7(good_rel(), good_supp(),
                       {"orphan_verdict": "ORPHANS_PRESENT"})
    assert g["verdict"] == "FAIL"


def test_worker_census_missing_rejected():
    g = na.evaluate_g7(good_rel(), {"spawn_children_count": 0}, good_orphan())
    assert g["verdict"] == "FAIL"


def test_workers8_not_actually_requested_rejected():
    g = na.evaluate_g7(good_rel(harness_train_args="... workers=0 ..."),
                       good_supp(), good_orphan())
    assert g["verdict"] == "FAIL"


def test_missing_negative_control_is_not_full_pass():
    gates = all_gates()
    gates[2] = na.evaluate_g1(good_cand(), None)
    assert gates[2]["reason"] == "NIGHTLY_NO_STL_POSITIVE_ONLY_CONTROL_PENDING"
    res = na.derive(gates, [])
    assert res["overall"] != "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS"


def test_inconclusive_control_rejected():
    # pre-fix wheel unexpectedly passing = INCONCLUSIVE control
    g = na.evaluate_g1(good_cand(), good_ctrl(
        classification="INCONCLUSIVE", failure_classification=None))
    assert g["verdict"] == "FAIL"


def test_control_with_postfix_dll_is_not_a_valid_prefit_control():
    # control env actually loaded a marker=2 (post-fix) DLL → invalid control
    g = na.evaluate_g1(good_cand(), good_ctrl(
        miopen_identity_in_parent={
            "pr13437_marker_miopen_initializer_list": 2}))
    assert g["verdict"] == "FAIL"


def test_g1_only_pass_is_partial():
    gates = all_gates()
    gates[3] = na.evaluate_g2(None)  # G2 missing
    res = na.derive(gates, [])
    assert res["overall"] == "NIGHTLY_PARTIAL_PASS"


def test_g1_missing_is_no_go():
    gates = all_gates()
    gates[2] = na.evaluate_g1(None, None)
    res = na.derive(gates, [])
    assert res["overall"] == "NIGHTLY_NO_GO"


def test_forbidden_stable_verdict_in_evidence_is_no_go():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        p.write_text(json.dumps({"claim": "OFFICIAL_STABLE_PASS"}), encoding="utf-8")
        hits = na.scan_forbidden_verdicts(Path(td))
    assert hits, "forbidden verdict must be detected"
    res = na.derive(all_gates(), hits)
    assert res["overall"] == "NIGHTLY_NO_GO"
    assert res["forbidden_verdict_hits"]


def test_engine_never_emits_forbidden_verdicts():
    res = na.derive(all_gates(), [])
    for v in na.FORBIDDEN_VERDICTS:
        assert v not in json.dumps(res), f"engine must never emit {v}"


def test_missing_evidence_files_fail_closed():
    assert na.evaluate_pkg(None, None, None)["verdict"] == "FAIL"
    assert na.evaluate_g0(None)["verdict"] == "FAIL"
    assert na.evaluate_g1(None, None)["verdict"] == "FAIL"
    assert na.evaluate_g2(None)["verdict"] == "FAIL"
    assert na.evaluate_g34(None)[0]["verdict"] == "FAIL"
    assert na.evaluate_g5(None)["verdict"] == "FAIL"
    assert na.evaluate_g7(None)["verdict"] == "FAIL"
