# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N gfx1100 CPU-only adversarial contract tests (mission §13.1
falsification classes) — no GPU, no network, no torch import.

Every fixture mirrors the gfx1100 receipt schema of the r22a5n1100 profile
engine; every tampering below must be rejected (or classified INCONCLUSIVE /
fail-closed) by the hardened acceptance engine. The gfx1151 profile and the
historical r22a5n1 engine are IMPORTED, never copied — and must stay
untouched (their own test files keep guarding that).

    python -m pytest windows-golden-path/tests/test_r22a5n1100_cpu.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mp = load_module("r22a5n1100_mission_profile",
                 REPO_ROOT / "scripts" / "r22a5n1100" / "mission_profile.py")
na = load_module("r22a5n1100_acceptance",
                 REPO_ROOT / "scripts" / "r22a5n1100" / "nightly_acceptance.py")

P = mp.PROFILE_GFX1100
F = P["frozen"]
PREFIX_DLL = "a" * 64  # stand-in pre-fix DLL identity (≠ frozen nightly DLL)


# ---------------------------------------------------------------- fixtures
def lock_packages():
    nightly = "https://nightly.repo.amd.com/rocm"
    return [
        {"name": "torch", "version": F["torch"],
         "wheel_filename": "torch-2.16.0a0+rocm10.3.0a20261116-cp312-cp312-win_amd64.whl",
         "url": f"{nightly}/pytorch/whl-next/torch/torch-2.16.0a0%2Brocm10.3.0a20261116-cp312-cp312-win_amd64.whl",
         "sha256": "e1" + "0" * 62, "size_bytes": 121540948},
        {"name": "amd-torch-device-gfx1100", "version": F["torch"],
         "wheel_filename": "amd_torch_device_gfx1100-2.16.0a0+rocm10.3.0a20261116-cp312-cp312-win_amd64.whl",
         "url": f"{nightly}/pytorch/whl-next/amd-torch-device-gfx1100/amd_torch_device_gfx1100-2.16.0a0%2Brocm10.3.0a20261116-cp312-cp312-win_amd64.whl",
         "sha256": "e5" + "0" * 62, "size_bytes": 43513232},
        {"name": "amd-torchvision-device-gfx1100", "version": F["torchvision"],
         "wheel_filename": "amd_torchvision_device_gfx1100-0.30.0a0+rocm10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/pytorch/whl-next/amd-torchvision-device-gfx1100/amd_torchvision_device_gfx1100-0.30.0a0%2Brocm10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": "e6" + "0" * 62, "size_bytes": 134909},
        {"name": "torchvision", "version": F["torchvision"],
         "wheel_filename": "torchvision-0.30.0a0+rocm10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/pytorch/whl-next/torchvision/torchvision-0.30.0a0%2Brocm10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": "e2" + "0" * 62, "size_bytes": 3000000},
        {"name": "rocm-sdk-libraries", "version": "10.3.0a20261116",
         "wheel_filename": F["wheel"],
         "url": f"{nightly}/core/whl-next/rocm-sdk-libraries/rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": F["wheel_sha256"], "size_bytes": 900000},
        {"name": "rocm-sdk-core", "version": "10.3.0a20261116",
         "wheel_filename": "rocm_sdk_core-10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/core/whl-next/rocm-sdk-core/rocm_sdk_core-10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": "e3" + "0" * 62, "size_bytes": 100000},
        {"name": "rocm-sdk-device-gfx1100", "version": "10.3.0a20261116",
         "wheel_filename": "rocm_sdk_device_gfx1100-10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/core/whl-next/rocm-sdk-device-gfx1100/rocm_sdk_device_gfx1100-10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": "e4" + "0" * 62},
        {"name": "rocm", "version": "10.3.0a20261116",
         "wheel_filename": "rocm-10.3.0a20261116.tar.gz",
         "url": f"{nightly}/core/whl-next/rocm/rocm-10.3.0a20261116.tar.gz",
         "sha256": "e9" + "0" * 62},
        {"name": "ultralytics", "version": F["ultralytics"],
         "wheel_filename": "ultralytics-8.4.214-py3-none-any.whl",
         "url": "https://files.pythonhosted.org/packages/xx/ultralytics-8.4.214-py3-none-any.whl",
         "sha256": "e7" + "0" * 62},
        {"name": "numpy", "version": "2.5.5",
         "wheel_filename": "numpy-2.5.5-cp312-cp312-win_amd64.whl",
         "url": "https://files.pythonhosted.org/packages/xx/numpy.whl",
         "sha256": "e8" + "0" * 62},
    ]


def good_lock(**over):
    lock = {
        "set_name": "r22a5n-nightly-20261116-gfx1100-cp312",
        "channel": "nightly", "gfx_target": "gfx1100", "python_tag": "cp312",
        "packages": lock_packages(),
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
    a = {"audits": [{
        "wheel_sha256": F["wheel_sha256"],
        "miopen_dll": {"sha256": F["miopen_dll_sha256"], "build_commit": "25f28906"},
        "ancestry": {"status": "ahead", "ahead_by": 1074, "behind_by": 0},
        "fix_present": True, "verdict": "POST_FIX_LIBRARIES",
    }]}
    a.update(over)
    return a


def good_manifest(**over):
    m = {
        "gpu_stack": {"torch": F["torch"], "ultralytics": F["ultralytics"]},
        "pip_check": "No broken requirements found.",
        "all_distributions": [f'{p["name"]}=={p["version"]}' for p in lock_packages()]
                            + ["pip==25.0", "setuptools==75.0"],
    }
    m.update(over)
    return m


def good_g0(**over):
    g = {
        "verdict": "G0_RUNTIME_IDENTITY_PASS",
        "child_dll_sha256": F["miopen_dll_sha256"],
        "child_dll_path": r"C:\r22a5n1100\venv\Lib\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll",
        "child_gpu_name": "AMD Radeon RX 7900 XTX",
        "gfx_target": "gfx1100", "child_op_finite": True,
        "parent_and_child_dll_agree": True, "runtime_class": "OFFICIAL_CANDIDATE",
        "child_marker_count": 2, "exit_code": 0,
    }
    g.update(over)
    return g


def good_cand(pid, scratch, **over):
    c = {
        "classification": "OFFICIAL_CANDIDATE_PASS", "expectation": "CANDIDATE",
        "exit_code": 0, "ambient_hiprtc_shim": None,
        "runtime_class": "OFFICIAL_CANDIDATE", "gfx_target": "gfx1100",
        "leg_detail": {"exit_code": 0, "pid": pid, "scratch": scratch,
                       "child_miopen": {"sha256": F["miopen_dll_sha256"]}},
    }
    c.update(over)
    return c


CTRL_STDERR = ("MIOpen(HIP): Error [Compile] hiprtcCompileProgram "
               "MIOpenBatchNormFwdTrainSpatial.cpp: HIPRTC_ERROR_COMPILATION (6) "
               "miopen_type_traits.hpp:151:10: fatal error: 'type_traits' "
               "file not found")


def good_ctrl(**over):
    c = {
        "classification": "OFFICIAL_PRE_FIX_EXPECTED_FAIL",
        "failure_classification": "MIOPEN_HIPRTC_COMPILATION",
        "expectation": "FAIL",
        "miopen_identity_in_parent": {
            "pr13437_marker_miopen_initializer_list": 0},
        "leg_detail": {"exit_code": 1, "pid": 42002,
                       "scratch": r"C:\r22a5n1100\scratch\g1_ctrl",
                       "stderr_tail": CTRL_STDERR,
                       "child_miopen": {"sha256": PREFIX_DLL}},
    }
    c.update(over)
    return c


def good_ops(**over):
    o = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1100", "exit_code": 0,
        "runtime_class": "OFFICIAL_CANDIDATE", "cpu_fallback_used": False,
        "miopen_identity": {"sha256": F["miopen_dll_sha256"]},
        "gates": {g: {"status": "PASS"} for g in mp.N1.G2_GATES},
    }
    o["gates"]["device_identity"] = {"status": "PASS",
                                     "detail": {"gfx_target": "gfx1100",
                                                "name": "AMD Radeon RX 7900 XTX"}}
    o["gates"]["fp32_gemm"] = {"status": "PASS", "detail": {"sum": 10053.771}}
    o["gates"]["fp16_gemm"] = {"status": "PASS", "detail": {"sum": -3979.85}}
    o.update(over)
    if "gfx_target" in over:  # keep the nested identity consistent with the override
        o["gates"]["device_identity"]["detail"]["gfx_target"] = over["gfx_target"]
    return o


def per_step_series():
    ev = []
    for i in range(4):
        ev.append({"invoked": True, "found_inf_any": True, "grad_scale": None,
                   "grad_tensors_checked": 366, "grads_all_finite": False,
                   "sentinel_max_abs_delta": 0.0, "param_checksum_changed": False,
                   "lr_first_group": 0.0 if i == 0 else 7.4e-06,
                   "accumulate_now": 1, "batch_index": i})
    for i in range(4, 11):
        ev.append({"invoked": True, "found_inf_any": False, "grad_scale": 4096.0,
                   "grad_tensors_checked": 366, "grads_all_finite": True,
                   "sentinel_max_abs_delta": 1.2e-05 + i * 1e-07,
                   "param_checksum_changed": True,
                   "lr_first_group": 7.4e-06 + (i - 4) * 1e-06,
                   "accumulate_now": 1, "batch_index": i})
    return ev


SCALE_HISTORY = [65536.0, 32768.0, 16384.0, 8192.0] + [4096.0] * 7


def good_amp(**over):
    a = {
        "training_counts": {
            "batches_completed": 48, "scaler_step_attempts": 11,
            "confirmed_update_events": 7, "skipped_found_inf_flagged": 4,
            "grads_finite_on_stepped_updates": True,
            "per_step_events": per_step_series(),
        },
        "optimizer": {"requested": "auto", "resolved_class": "AdamW"},
        "amp": {"autocast_dtype_observed": "float16",
                "stem_conv_output_dtypes_observed": {"float16": 96},
                "autocast_forward_samples": {"sampled": 48, "enabled": 48}},
        "low_precision_evidence": {"samples_low_precision": 96,
                                   "samples_total": 96},
        "gradscaler": {"scale_history": SCALE_HISTORY, "scale_history_len": 11,
                       "backoff_events_observed": 4},
        "loaded_model_delta": {"tensors_changed_beyond_1e-9": 248,
                               "all_finite": True},
        "checkpoint": {"exists": True, "sha256": "c1" + "0" * 62},
        "loaded_miopen_dll_sha256": F["miopen_dll_sha256"],
        "gpu_name": "AMD Radeon RX 7900 XTX", "gfx_target": "gfx1100",
        "exit_code": 0, "runtime_class": "OFFICIAL_CANDIDATE",
        "pass_fail_skip": "ADAMW_AMP_MULTISTEP_PASS",
        "epoch_observations": [{"epoch": i} for i in range(3)],
    }
    a.update(over)
    return a


def good_ckpt(**over):
    c = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1100",
        "checkpoint_sha256": {"last.pt": "ab" + "0" * 62, "best.pt": "cd" + "0" * 62},
        "resume_semantics": "resume=True (training state), not weights-only load",
        "stages": {
            "checkpoint_resumability": {"has_optimizer_state": True},
            "total_epochs": 4, "kill_after_epoch": 1, "rows_at_kill": 2,
            "checkpoint_sha256_at_kill": "ab" + "0" * 62,
            "resume_exit": 0, "resume_done_marker": True,
            "resume_start_epoch": 2, "optimizer_state_entries": 366,
            "resume_effective_updates": 6, "resume_step_attempts": 8,
            "final_epoch_rows": 4, "last_epoch_value": 4,
            "epoch_continuity": True,
            "infer_exit": 0, "infer_ok": True,
        },
        "state_classes": {
            "model_weights": {"serialized": True, "observed_fields": ["ema"]},
            "optimizer": {"serialized": True},
            "scheduler": {"serialized": "NOT_SERIALIZED_BY_UPSTREAM"},
            "gradscaler": {"serialized": True},
            "epoch": {"serialized": True},
            "best_fitness": {"serialized": True},
            "trainer_args": {"serialized": True},
            "ema": {"serialized": True},
        },
    }
    c.update(over)
    return c


def good_rel(**over):
    r = {
        "harness_train_args": "epochs=3, imgsz=256, batch=8, optimizer='auto', device=-1, workers=8",
        "training_counts": {"batches_completed": 48,
                            "confirmed_update_events": 7,
                            "scaler_step_attempts": 11,
                            "skipped_found_inf_flagged": 4,
                            "per_step_events": per_step_series()},
        "gradscaler": {"scale_history": SCALE_HISTORY},
        "exit_code": 0, "pass_fail_skip": "ADAMW_AMP_MULTISTEP_PASS",
    }
    r.update(over)
    return r


def snapshot_tree(trainer_pid=4242, worker_pids=(50100, 50101, 50102, 50103,
                                                  50104, 50105, 50106, 50107),
                  extra_children=(), utc="2026-11-17T20:01:00+00:00",
                  orchestrator_pid=777):
    """One raw Win32 python_tree snapshot: orchestrator → trainer → workers."""
    tree = [
        {"pid": orchestrator_pid, "ppid": 111,
         "cmdline": "python worker_stage.py --python v"},
        {"pid": trainer_pid, "ppid": orchestrator_pid,
         "cmdline": "C:/r22a5n1100/venv/Scripts/python.exe -X utf8 "
                    "windows-golden-path/scripts/audit_adamw_amp.py --workers 8"},
    ]
    for wp in worker_pids:
        tree.append({"pid": wp, "ppid": trainer_pid,
                     "cmdline": "python -c from multiprocessing.spawn import "
                                "spawn_main; spawn_main(...)"})
    for cp in extra_children:  # children WITHOUT spawn_main — not workers
        tree.append({"pid": cp, "ppid": trainer_pid,
                     "cmdline": "python helper.py"})
    return {"captured_utc": utc, "python_tree": tree, "trainer_pid": trainer_pid,
            "children": list(worker_pids)}


def good_census(**over):
    snap = snapshot_tree()
    c = {
        "trainer_pid": 4242, "orchestrator_pid": 777,
        "captured_utc": snap["captured_utc"],
        "spawn_children_of_trainer": [50100, 50101, 50102, 50103,
                                      50104, 50105, 50106, 50107],
        "spawn_children_count": 8,
        "snapshots": [snap],
        "preexisting_zombies_disclosed": [37120, 12052],
    }
    c.update(over)
    return c


def good_orphan(**over):
    o = {"checker_pid": 999,
         "all_python_pids": [37120, 12052, 999],
         "mission_tree_leftover": [],
         "orphan_verdict": "CLEAN"}
    o.update(over)
    return o


def all_gates(**mut):
    args = {"lock": good_lock(), "audit": good_audit(), "manifest": good_manifest(),
            "g0": good_g0(),
            "trials": [good_cand(41001, r"C:\s\t1"), good_cand(41002, r"C:\s\t2")],
            "ctrl": good_ctrl(), "ops": good_ops(), "amp": good_amp(),
            "ckpt": good_ckpt(), "rel": good_rel()}
    for k, fn in mut.items():
        args[k] = fn(args[k]) if callable(fn) else fn
    trials = args["trials"]
    return [
        na.evaluate_pkg(P, args["lock"], args["audit"], args["manifest"]),
        na.evaluate_g0(P, args["g0"]),
        na.evaluate_g1(P, trials, args["ctrl"],
                       ["BN_NOSTL_REPRO out_finite=True grad_finite=True"] * 2,
                       CTRL_STDERR),
        na.evaluate_g2(P, args["ops"]),
        *na.evaluate_g34(P, args["amp"]),
        na.evaluate_g5_hardened(P, args["ckpt"]),
        na.evaluate_g7_hardened(P, args["rel"], good_census(), good_orphan(),
                                {"envelope": {"child_pid": 4242}}),
    ]


def derive_all(**mut):
    return na.derive(P, all_gates(**mut), [])


# ------------------------------------------------- profile integrity
def test_gfx1151_profile_is_historical_frozen_by_reference():
    assert mp.PROFILE_GFX1151["frozen"] == mp.N1.FROZEN
    assert mp.PROFILE_GFX1151["frozen"]["gfx_target"] == "gfx1151"
    assert mp.PROFILE_GFX1100["frozen"]["gfx_target"] == "gfx1100"


def test_profiles_do_not_share_gpu_specific_identity():
    # the SHARED wheel bytes are allowed to be identical; device identity is not
    assert F["wheel_sha256"] == mp.PROFILE_GFX1151["frozen"]["wheel_sha256"]
    assert F["miopen_dll_sha256"] == mp.PROFILE_GFX1151["frozen"]["miopen_dll_sha256"]
    assert P["python_tag"] != mp.PROFILE_GFX1151["python_tag"]


# ---------------------------------------------------------------- positives
def test_honest_fixture_full_audited_pass():
    res = derive_all()
    assert res["overall"] == P["ceiling"]


def test_engine_recomputes_counts_from_events():
    g3, g4 = na.evaluate_g34(P, good_amp())
    r = g3["facts"]["recomputed"]
    assert r["attempts"] == 11 and r["effective_updates"] == 7 \
        and r["inf_skips"] == 4 and r["backoffs_recomputed"] == 4
    assert g4["amp_verdict"] == "AMP_PASS"


# --------------------------------------------- PKG falsifications
def test_gfx1151_lock_substitution_rejected():
    lock = good_lock(gfx_target="gfx1151", python_tag="cp313")
    g = na.evaluate_pkg(P, lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"


def test_gfx1151_device_wheels_in_lock_rejected():
    lock = good_lock()
    for p in lock["packages"]:
        if p["name"] == "amd-torch-device-gfx1100":
            p["name"] = "amd-torch-device-gfx1151"
            p["wheel_filename"] = p["wheel_filename"].replace("gfx1100", "gfx1151")
    g = na.evaluate_pkg(P, lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"


def test_wrong_python_abi_rejected():
    lock = good_lock(python_tag="cp313")
    g = na.evaluate_pkg(P, lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"


def test_wrong_wheel_sha_rejected():
    audit = good_audit()
    audit["audits"][0]["wheel_sha256"] = "ff" + "0" * 62
    g = na.evaluate_pkg(P, good_lock(), audit, good_manifest())
    assert g["verdict"] == "FAIL"


def test_family_mix_and_missing_device_wheel_rejected():
    lock = good_lock()
    lock["packages"] = [p for p in lock["packages"]
                        if p["name"] != "rocm-sdk-device-gfx1100"]
    g = na.evaluate_pkg(P, lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"
    assert g["facts"]["recomputed"]["device_wheels_present"][
        "rocm-sdk-device-gfx1100"] is False


def test_rogue_native_install_rejected():
    m = good_manifest()
    m["all_distributions"].append("torch==2.12.0+rocm7.14.1")
    g = na.evaluate_pkg(P, good_lock(), good_audit(), m)
    assert g["verdict"] == "FAIL"
    assert "torch" in g["facts"]["installed_missing_vs_lock"]


# --------------------------------------------- LK falsifications
def test_lk_wrong_lock_sha_rejected(tmp_path):
    lockf = tmp_path / "lock.json"
    lockf.write_text(__import__("json").dumps(good_lock()), encoding="utf-8")
    rec = good_amp(wheel_lock_sha256="dd" + "0" * 62)
    g = na.evaluate_lk(P, [("amp", rec)], lockf)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["receipts"][0]["status"] == "SHA_MISMATCH"


def test_lk_gfx1151_receipt_identity_rejected(tmp_path):
    import json as _json
    lockf = tmp_path / "lock.json"
    lockf.write_text(_json.dumps(good_lock()), encoding="utf-8")
    rec = good_amp(wheel_lock_sha256=__import__("hashlib").sha256(
        lockf.read_bytes()).hexdigest(),
        wheel_lock_channel="nightly", wheel_lock_gfx="gfx1151")
    g = na.evaluate_lk(P, [("amp", rec)], lockf)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["receipts"][0]["status"] == "MISSION_IDENTITY_MISMATCH"


def test_lk_no_binding_rejected(tmp_path):
    import json as _json
    lockf = tmp_path / "lock.json"
    lockf.write_text(_json.dumps(good_lock()), encoding="utf-8")
    rec = good_amp()
    rec.pop("wheel_lock_sha256", None)
    g = na.evaluate_lk(P, [("amp", rec)], lockf)
    assert g["facts"]["receipts"][0]["status"] == "NO_LOCK_FIELD"


# --------------------------------------------- G0 falsifications
def test_g0_gfx1151_receipt_rejected():
    g = na.evaluate_g0(P, good_g0(gfx_target="gfx1151",
                                  child_gpu_name="AMD Radeon(TM) 8060S Graphics"))
    assert g["verdict"] == "FAIL"


def test_g0_dll_contamination_blocked():
    g = na.evaluate_g0(P, good_g0(verdict="BLOCKED_DLL_CONTAMINATION"))
    assert g["verdict"] == "FAIL"
    assert "BLOCKED_DLL_CONTAMINATION" in g["reason"]


def test_g0_wrong_loaded_dll_rejected():
    g = na.evaluate_g0(P, good_g0(child_dll_sha256="b" * 64))
    assert g["verdict"] == "FAIL"


# --------------------------------------------- G1 falsifications
def test_g1_single_trial_insufficient():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1")], good_ctrl(),
                       ["ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"
    assert "INSUFFICIENT_COLD_TRIALS" in g["reason"]


def test_g1_reused_process_identity_rejected():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41001, r"C:\s\t2")], good_ctrl(),
                       ["ok", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_reused_cold_cache_scratch_rejected():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t1")], good_ctrl(),
                       ["ok", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_fake_pass_with_shim_rejected():
    t = good_cand(41001, r"C:\s\t1", ambient_hiprtc_shim="-I x")
    g = na.evaluate_g1(P, [t, good_cand(41002, r"C:\s\t2")], good_ctrl(),
                       ["ok", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_wrong_inchild_dll_rejected():
    t = good_cand(41001, r"C:\s\t1")
    t["leg_detail"]["child_miopen"]["sha256"] = "c" * 64
    g = na.evaluate_g1(P, [t, good_cand(41002, r"C:\s\t2")], good_ctrl(),
                       ["ok", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_missing_control_pending():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t2")], None,
                       ["ok", "ok"], None)
    assert g["verdict"] == "FAIL"
    assert "CONTROL_PENDING" in g["reason"]


def test_g1_missing_raw_control_log_fail_closed():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t2")], good_ctrl(),
                       ["ok", "ok"], None)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["control_signature_in_raw_bytes"] is False


def test_g1_control_unexpectedly_passing_is_inconclusive():
    ctrl = good_ctrl(classification="INCONCLUSIVE", exit_code=0,
                     failure_classification=None)
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t2")], ctrl,
                       ["ok", "ok"], "")
    assert g["verdict"] == "FAIL"


def test_g1_control_with_postfix_dll_rejected():
    # a "control" that actually ran post-fix bytes is not a matched control
    ctrl = good_ctrl()
    ctrl["leg_detail"]["child_miopen"]["sha256"] = F["miopen_dll_sha256"]
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t2")], ctrl,
                       ["ok", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_candidate_log_carrying_prefix_signature_rejected():
    g = na.evaluate_g1(P, [good_cand(41001, r"C:\s\t1"),
                           good_cand(41002, r"C:\s\t2")], good_ctrl(),
                       ["type_traits not found", "ok"], CTRL_STDERR)
    assert g["verdict"] == "FAIL"


# --------------------------------------------- G2 falsifications
def test_g2_cpu_fallback_rejected():
    g = na.evaluate_g2(P, good_ops(cpu_fallback_used=True))
    assert g["verdict"] == "FAIL"


def test_g2_nonfinite_detail_rejected():
    o = good_ops()
    o["gates"]["fp16_gemm"] = {"status": "PASS", "detail": {"sum": float("nan")}}
    g = na.evaluate_g2(P, o)
    assert g["verdict"] == "FAIL"


# --------------------------------------------- G3/G4 falsifications
def test_g34_no_effective_updates_but_pass_claimed_rejected():
    a = good_amp()
    tc = a["training_counts"]
    for ev in tc["per_step_events"]:
        ev["sentinel_max_abs_delta"] = 0.0
        ev["found_inf_any"] = False
    g3, g4 = na.evaluate_g34(P, a)
    assert g3["verdict"] == "FAIL"


def test_g34_per_step_contradiction_rejected():
    a = good_amp()
    a["training_counts"]["confirmed_update_events"] = 5  # stored says 5, series says 7
    g3, g4 = na.evaluate_g34(P, a)
    assert g3["verdict"] == "FAIL"
    assert g3["facts"]["counts_reconcile"] is False


def test_g34_scale_history_contradiction_rejected():
    a = good_amp()
    a["gradscaler"]["scale_history"] = SCALE_HISTORY[:-1]
    g3, g4 = na.evaluate_g34(P, a)
    assert g3["verdict"] == "FAIL"


def test_g34_fp32_impersonating_amp_rejected():
    a = good_amp()
    a["amp"]["autocast_dtype_observed"] = None
    a["amp"]["stem_conv_output_dtypes_observed"] = {"float32": 96}
    a["low_precision_evidence"]["samples_low_precision"] = 0
    g3, g4 = na.evaluate_g34(P, a)
    # a pure-FP32 run cannot satisfy the training gate's low-precision
    # requirement, so AMP is never PASS (AMP_DISABLED when evaluable,
    # AMP_INCONCLUSIVE when the training gate itself fails first)
    assert g4["verdict"] == "FAIL"
    assert g4["amp_verdict"] in ("AMP_DISABLED", "AMP_INCONCLUSIVE")


def test_g34_wrong_gfx_identity_rejected():
    g3, g4 = na.evaluate_g34(P, good_amp(gfx_target="gfx1151"))
    assert g3["verdict"] == "FAIL"


def test_g34_wrong_loaded_dll_rejected():
    g3, g4 = na.evaluate_g34(P, good_amp(loaded_miopen_dll_sha256="d" * 64))
    assert g3["verdict"] == "FAIL"


# --------------------------------------------- G5 hardened falsifications
def test_g5_missing_epoch_fact_fails_closed():
    c = good_ckpt()
    del c["stages"]["last_epoch_value"]
    g = na.evaluate_g5_hardened(P, c)
    assert g["verdict"] == "FAIL"
    assert "EPOCH_FACTS_MISSING" in g["reason"]
    assert "last_epoch_value" in g["facts"]["missing_epoch_facts"]


def test_g5_stored_boolean_epoch_continuity_is_not_authority():
    # stored epoch_continuity=True but numeric facts contradict → FAIL
    c = good_ckpt()
    c["stages"]["final_epoch_rows"] = 2  # no rows after kill
    g = na.evaluate_g5_hardened(P, c)
    assert g["verdict"] == "FAIL"
    assert "EPOCH_CONTINUITY_NOT_RECOMPUTABLE" in g["reason"]


def test_g5_scheduler_not_serialized_never_claims_full_restore():
    g = na.evaluate_g5_hardened(P, good_ckpt())
    assert g["verdict"] == "PASS"
    assert g["facts"]["state_verdict"] == "RESUME_PASS_CORE_STATE_VERIFIED"
    assert "scheduler" in g["facts"]["not_serialized_classes"]


def test_g5_full_restore_only_with_actually_serialized_scheduler():
    c = good_ckpt()
    c["state_classes"]["scheduler"] = {"serialized": True}
    g = na.evaluate_g5_hardened(P, c)
    assert g["facts"]["state_verdict"] == "FULL_TRAINING_STATE_RESTORE_PASS"


def test_g5_bad_checkpoint_sha_rejected():
    c = good_ckpt()
    c["checkpoint_sha256"]["last.pt"] = "ZZ"
    g = na.evaluate_g5_hardened(P, c)
    assert g["verdict"] == "FAIL"


def test_g5_no_effective_post_resume_updates_rejected():
    c = good_ckpt()
    c["stages"]["resume_effective_updates"] = 0
    g = na.evaluate_g5_hardened(P, c)
    assert g["verdict"] == "FAIL"


def test_g5_missing_resume_start_epoch_rejected():
    c = good_ckpt()
    c["stages"]["resume_start_epoch"] = None
    g = na.evaluate_g5_hardened(P, c)
    assert g["verdict"] == "FAIL"


def test_g5_gfx1151_receipt_rejected():
    g = na.evaluate_g5_hardened(P, good_ckpt(gfx_target="gfx1151"))
    assert g["verdict"] == "FAIL"


def test_g5_anchor_mismatch_rejected():
    artifacts = [{"sha256": "ee" + "0" * 62, "path": "x"}]
    ck = good_ckpt()
    ck["checkpoint_sha256"]["last.pt"] = "ab" + "0" * 62
    g = na.evaluate_g5_hardened(P, ck, artifacts)
    assert g["facts"]["checkpoint_bytes_anchored"]["last.pt"] is False
    assert g["verdict"] == "FAIL"


# --------------------------------------------- G7 hardened falsifications
def test_g7_recomputed_from_raw_snapshots_passes():
    g = na.evaluate_g7_hardened(P, good_rel(), good_census(), good_orphan(),
                                {"envelope": {"child_pid": 4242}})
    assert g["verdict"] == "PASS"
    f = g["facts"]
    assert f["peak_trainer_pid_recomputed"] == 4242
    assert len(f["peak_spawn_worker_pids"]) == 8
    assert f["all_workers_ppid_ok"] and f["all_workers_spawn_main"]


def test_g7_missing_raw_snapshots_fails_closed():
    census = good_census()
    del census["snapshots"]
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert g["verdict"] == "FAIL"
    assert "raw python_tree snapshots" in g["reason"]


def test_g7_fake_worker_pid_in_stored_list_not_counted():
    # tampering the STORED summary list cannot change the verdict derived from
    # the raw snapshot: the fake pid is excluded, the fabrication is disclosed
    census = good_census()
    census["spawn_children_of_trainer"] = [50100, 50101, 50102, 50103,
                                           50104, 50105, 50106, 55555]
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    f = g["facts"]
    assert 55555 not in f["peak_spawn_worker_pids"]
    assert f["stored_list_matches_peak_snapshot"] is False
    assert len(f["peak_spawn_worker_pids"]) == 8  # the raw snapshot is authority
    assert g["verdict"] == "PASS"


def test_g7_faked_raw_worker_short_of_eight_fails():
    # if the RAW snapshot itself only shows 7 genuine workers, the gate fails
    snap = snapshot_tree(worker_pids=(50100, 50101, 50102, 50103, 50104,
                                      50105, 50106))
    census = good_census(snapshots=[snap])
    census["spawn_children_of_trainer"] = census["spawn_children_of_trainer"][:7]
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert len(g["facts"]["peak_spawn_worker_pids"]) == 7
    assert g["verdict"] == "FAIL"


def test_g7_wrong_ppid_worker_not_counted():
    # an impostor process (spawn_main cmdline but child of the ORCHESTRATOR,
    # not the trainer) is excluded from worker identity by the PPID recompute
    snap = snapshot_tree()
    snap["python_tree"].append({"pid": 50999, "ppid": 777,
                                "cmdline": "python -c from multiprocessing.spawn "
                                           "import spawn_main; spawn_main(x)"})
    census = good_census(snapshots=[snap])
    census["spawn_children_of_trainer"] = census["spawn_children_of_trainer"] + [50999]
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert 50999 not in g["facts"]["peak_spawn_worker_pids"]
    assert len(g["facts"]["peak_spawn_worker_pids"]) == 8
    assert g["facts"]["stored_list_matches_peak_snapshot"] is False
    assert g["verdict"] == "PASS"  # 8 genuine workers in the raw snapshot


def test_g7_trainer_without_eight_children_fails():
    # raw snapshot: trainer has 7 spawn children + 1 non-spawn child
    snap = snapshot_tree(worker_pids=(50100, 50101, 50102, 50103, 50104,
                                      50105, 50106), extra_children=(50998,))
    census = good_census(snapshots=[snap],
                         spawn_children_of_trainer=[50100, 50101, 50102, 50103,
                                                    50104, 50105, 50106, 50998])
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert 50998 in g["facts"]["peak_non_spawn_children"]
    assert g["verdict"] == "FAIL"


def test_g7_fake_spawn_main_rejected():
    # 8 trainer children but one lacks spawn_main → only 7 workers
    snap = snapshot_tree(worker_pids=(50100, 50101, 50102, 50103, 50104,
                                      50105, 50106, 50998))
    for p in snap["python_tree"]:
        if p["pid"] == 50998:
            p["cmdline"] = "python impostor_helper.py"
    census = good_census(snapshots=[snap])
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert 50998 in g["facts"]["peak_non_spawn_children"]
    assert g["verdict"] == "FAIL"


def test_g7_time_spliced_pids_never_simultaneous():
    # 8 workers total but only 4 alive in ANY single snapshot
    s1 = snapshot_tree(worker_pids=(50100, 50101, 50102, 50103),
                       utc="2026-11-17T20:01:00+00:00")
    s2 = snapshot_tree(worker_pids=(50104, 50105, 50106, 50107),
                       utc="2026-11-17T20:02:00+00:00")
    census = good_census(snapshots=[s1, s2])
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert len(g["facts"]["peak_spawn_worker_pids"]) == 4
    assert g["verdict"] == "FAIL"


def test_g7_forged_orphan_clean_rejected():
    orphan = good_orphan(all_python_pids=[37120, 12052, 999, 50100],
                         mission_tree_leftover=[], orphan_verdict="CLEAN")
    g = na.evaluate_g7_hardened(P, good_rel(), good_census(), orphan, None)
    assert g["facts"]["leftover_recomputed"] == [50100]
    assert g["verdict"] == "FAIL"


def test_g7_missing_checker_pid_fails_closed():
    orphan = good_orphan(checker_pid=None)
    g = na.evaluate_g7_hardened(P, good_rel(), good_census(), orphan, None)
    assert g["verdict"] == "FAIL"


def test_g7_missing_baseline_disclosed_fails_closed():
    census = good_census()
    del census["preexisting_zombies_disclosed"]
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert g["verdict"] == "FAIL"


def test_g7_trainer_not_tied_to_envelope_rejected():
    g = na.evaluate_g7_hardened(P, good_rel(), good_census(), good_orphan(),
                                {"envelope": {"child_pid": 12345}})
    assert g["facts"]["trainer_pid_ties_to_envelope"] is False
    assert g["verdict"] == "FAIL"


def test_g7_venv_redirector_ancestor_chain_accepted():
    # trainer launched through a venv redirector: envelope saw the redirector pid
    snap = snapshot_tree()
    snap["python_tree"].insert(1, {"pid": 5555, "ppid": 777,
                                   "cmdline": "venv redirector"})
    for p in snap["python_tree"]:
        if p["pid"] == 4242:
            p["ppid"] = 5555  # trainer's parent is the redirector
    census = good_census(snapshots=[snap])
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(),
                                {"envelope": {"child_pid": 5555}})
    assert g["facts"]["trainer_pid_ties_to_envelope"] is True


def test_g7_cyclic_ppid_data_cannot_loop_the_engine():
    # adversarial evidence with a PPID cycle must terminate and fail honestly
    snap = snapshot_tree()
    for p in snap["python_tree"]:
        if p["pid"] == 4242:
            p["ppid"] = 50100  # trainer "child of its own worker" — cycle
        if p["pid"] == 50100:
            p["ppid"] = 4242
    census = good_census(snapshots=[snap])
    g = na.evaluate_g7_hardened(P, good_rel(), census, good_orphan(), None)
    assert g["facts"]["trainer_ancestry_cycle_detected"] is True


def test_g7_workers0_receipt_not_accepted():
    g = na.evaluate_g7_hardened(
        P, good_rel(harness_train_args="epochs=3, workers=0"), good_census(),
        good_orphan(), None)
    assert g["verdict"] == "FAIL"


# --------------------------------------------- derive / promotion
def test_forbidden_stable_verdict_forces_no_go(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    (d / "r.json").write_text('{"x": "OFFICIAL_STABLE_PASS"}', encoding="utf-8")
    hits = na.scan_forbidden_verdicts(d)
    assert any("OFFICIAL_STABLE_PASS" in h for h in hits)
    res = na.derive(P, all_gates(), hits)
    assert res["overall"] == "NIGHTLY_NO_GO"


def test_g1_only_yields_partial_pass():
    gates = all_gates(ops=None, amp=None, ckpt=None, rel=None)
    res = na.derive(P, gates, [])
    by = res["gate_verdicts"]
    assert by["G1"] == "PASS" and by["G2"] == "FAIL"
    assert res["overall"] == "NIGHTLY_PARTIAL_PASS"


def test_gfx1151_wholesale_acceptance_copy_cannot_be_relabeled():
    # a FULL gfx1151-shaped gate list re-run under the gfx1100 profile: every
    # identity-bearing gate fails (gfx mismatch), so the copy cannot PASS
    args_gfx1151 = {
        "g0": good_g0(gfx_target="gfx1151",
                      child_gpu_name="AMD Radeon(TM) 8060S Graphics"),
        "ops": good_ops(gfx_target="gfx1151"),
        "amp": good_amp(gfx_target="gfx1151",
                        gpu_name="AMD Radeon(TM) 8060S Graphics"),
        "ckpt": good_ckpt(gfx_target="gfx1151"),
    }
    gates = [na.evaluate_g0(P, args_gfx1151["g0"]),
             na.evaluate_g2(P, args_gfx1151["ops"]),
             *na.evaluate_g34(P, args_gfx1151["amp"]),
             na.evaluate_g5_hardened(P, args_gfx1151["ckpt"])]
    assert all(g["verdict"] == "FAIL" for g in gates)
