# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 CPU-only adversarial contract tests (mission PHASE 6 §9, all 25
falsification classes) + R22A.5N.2 fail-closed G5/G7 classes — no GPU, no
network, no torch import.

Every fixture mirrors the pack-B receipt schema; every tampering below must be
rejected (or classified INCONCLUSIVE) by the hardened acceptance engine, the
lock gate or the evidence-pack verifier. The historical 11/7/4 AMP shape is
used ONLY inside fixtures — the engine itself hardcodes no counts. The
R22A.5N.2 fixtures mirror the real pack-B G7 process facts (trainer 39592,
16 spawn_main workers, single live snapshot) and the G5 numeric schema; two
tests additionally recompute directly from the committed pack-B bytes
(read-only) so authentic physical evidence is regression-locked.

    python -m pytest windows-golden-path/tests/test_r22a5n1_cpu.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
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


na = load_module("r22a5n1_acceptance", REPO_ROOT / "scripts" / "r22a5n1" / "nightly_acceptance.py")
adamw = load_module("r22a5n1_adamw_lib", REPO_ROOT / "windows-golden-path" / "scripts" / "audit_adamw_amp.py")
ep = load_module("r22a5n1_evidence_pack", REPO_ROOT / "scripts" / "r22a5n1" / "evidence_pack.py")

F = na.FROZEN
PREFIX_DLL = "a" * 64  # stand-in pre-fix DLL identity (≠ frozen nightly DLL)


# ---------------------------------------------------------------- fixtures
def lock_packages():
    nightly = "https://nightly.repo.amd.com/rocm/pytorch/whl-next"
    return [
        {"name": "torch", "version": F["torch"],
         "wheel_filename": "torch-2.16.0a0+rocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "url": f"{nightly}/torch/torch-2.16.0a0%2Brocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "sha256": "e1" + "0" * 62, "size_bytes": 121540948},
        {"name": "torchvision", "version": "0.30.0a0+rocm10.3.0a20261116",
         "wheel_filename": "torchvision-0.30.0a0+rocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "url": f"{nightly}/torchvision/torchvision-0.30.0a0%2Brocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "sha256": "e2" + "0" * 62, "size_bytes": 3000000},
        {"name": "rocm-sdk-libraries", "version": "10.3.0a20261116",
         "wheel_filename": "rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/rocm-sdk-libraries/rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": F["wheel_sha256"], "size_bytes": 900000},
        {"name": "rocm-sdk-core", "version": "10.3.0a20261116",
         "wheel_filename": "rocm_sdk_core-10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/rocm-sdk-core/rocm_sdk_core-10.3.0a20261116-py3-none-win_amd64.whl",
         "sha256": "e3" + "0" * 62, "size_bytes": 100000},
        {"name": "rocm-sdk-device-gfx1151", "version": "10.3.0a20261116",
         "wheel_filename": "rocm_sdk_device_gfx1151-10.3.0a20261116-py3-none-win_amd64.whl",
         "url": f"{nightly}/rocm-sdk-device-gfx1151/x.whl", "sha256": "e4" + "0" * 62},
        {"name": "amd-torch-device-gfx1151", "version": F["torch"],
         "wheel_filename": "amd_torch_device_gfx1151-2.16.0a0+rocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "url": f"{nightly}/amd-torch-device-gfx1151/x.whl", "sha256": "e5" + "0" * 62},
        {"name": "amd-torchvision-device-gfx1151", "version": "0.30.0a0+rocm10.3.0a20261116",
         "wheel_filename": "amd_torchvision_device_gfx1151-0.30.0a0+rocm10.3.0a20261116-cp313-cp313-win_amd64.whl",
         "url": f"{nightly}/amd-torchvision-device-gfx1151/x.whl", "sha256": "e6" + "0" * 62},
        {"name": "ultralytics", "version": F["ultralytics"],
         "wheel_filename": "ultralytics-8.4.214-py3-none-any.whl",
         "url": "https://files.pythonhosted.org/packages/xx/ultralytics-8.4.214-py3-none-any.whl",
         "sha256": "e7" + "0" * 62},
        {"name": "numpy", "version": "2.5.5",
         "wheel_filename": "numpy-2.5.5-cp313-cp313-win_amd64.whl",
         "url": "https://files.pythonhosted.org/packages/xx/numpy.whl",
         "sha256": "e8" + "0" * 62},
    ]


def good_lock(**over):
    lock = {
        "set_name": "r22a5n1-nightly-gfx1151", "channel": "nightly",
        "gfx_target": "gfx1151", "python_tag": "cp313",
        "packages": lock_packages(),
        "rules_checked": {  # stored booleans — engine must NOT trust these
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
        "child_dll_path": r"C:\r22a5n1\venv\Lib\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll",
        "child_gpu_name": "AMD Radeon(TM) 8060S Graphics",
        "gfx_target": "gfx1151", "child_op_finite": True,
        "parent_and_child_dll_agree": True, "runtime_class": "OFFICIAL_CANDIDATE",
        "child_marker_count": 2, "exit_code": 0,
    }
    g.update(over)
    return g


def good_cand(**over):
    c = {
        "classification": "OFFICIAL_CANDIDATE_PASS", "expectation": "CANDIDATE",
        "exit_code": 0, "ambient_hiprtc_shim": None,
        "runtime_class": "OFFICIAL_CANDIDATE", "gfx_target": "gfx1151",
        "leg_detail": {"exit_code": 0, "pid": 41001,
                       "scratch": r"C:\r22a5n1\scratch\g1_cand_1",
                       "child_miopen": {"sha256": F["miopen_dll_sha256"]}},
    }
    c.update(over)
    return c


CTRL_STDERR = ("...hiprtc]: HIPRTC_ERROR_COMPILATION: "
               "bn_fw_20x100x35x45: <source>:12:10: fatal error: "
               "'type_traits' file not found")


def good_ctrl(**over):
    c = {
        "classification": "OFFICIAL_PRE_FIX_EXPECTED_FAIL",
        "failure_classification": "MIOPEN_HIPRTC_COMPILATION",
        "expectation": "FAIL",
        "miopen_identity_in_parent": {
            "pr13437_marker_miopen_initializer_list": 0},
        "leg_detail": {"exit_code": 1, "pid": 42002,
                       "scratch": r"C:\r22a5n1\scratch\g1_ctrl",
                       "stderr_tail": CTRL_STDERR,
                       "child_miopen": {"sha256": PREFIX_DLL}},
    }
    c.update(over)
    return c


def good_ops(**over):
    o = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1151", "exit_code": 0,
        "runtime_class": "OFFICIAL_CANDIDATE", "cpu_fallback_used": False,
        "miopen_identity": {"sha256": F["miopen_dll_sha256"]},
        "gates": {g: {"status": "PASS"} for g in na.G2_GATES},
    }
    o["gates"]["device_identity"] = {"status": "PASS",
                                     "detail": {"gfx_target": "gfx1151",
                                                "name": "AMD Radeon(TM) 8060S Graphics"}}
    o["gates"]["fp32_gemm"] = {"status": "PASS", "detail": {"sum": 10053.771}}
    o["gates"]["fp16_gemm"] = {"status": "PASS", "detail": {"sum": -3979.85}}
    o.update(over)
    return o


def per_step_series():
    """Realistic 11-event series: 4 warm-up inf skips then 7 effective updates."""
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
        "gpu_name": "AMD Radeon(TM) 8060S Graphics", "gfx_target": "gfx1151",
        "exit_code": 0, "runtime_class": "OFFICIAL_CANDIDATE",
        "pass_fail_skip": "ADAMW_AMP_MULTISTEP_PASS",
        "epoch_observations": [{"epoch": i, "metrics": {"metrics/mAP50(B)": 0.1 + i / 40}}
                               for i in range(3)],
    }
    a.update(over)
    return a


def good_ckpt(**over):
    c = {
        "pass_fail_skip": "PASS", "gfx_target": "gfx1151",
        "checkpoint_sha256": {"last.pt": "ab" + "0" * 62, "best.pt": "cd" + "0" * 62},
        "resume_semantics": "resume=True (training state), not weights-only load",
        "stages": {
            "checkpoint_resumability": {"checked": True,
                                        "has_optimizer_state": True,
                                        "ckpt_epoch": 1},
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
            "gradscaler": {"serialized": True},  # observed 8.4.214 reality
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


# pack-B-mirroring G7 process facts (mission R22A.5N.2 §5.1: trainer 39592,
# 16 spawn_main workers, direct children, single live snapshot)
TRAINER_PID = 39592
ENV_PID = 6784  # envelope child (venv launcher chain: 55012→52244→53968)
BASELINE_PIDS = [12052, 37120, 52244, 53968, 55012]  # recorded pre-start
WORKER_PIDS = [20660, 30512, 36664, 40360, 44440, 46388, 48436, 48720,
               52876, 52992, 53072, 53516, 54332, 54936, 56100, 57236]


def spawn_cmdline(parent: int, pipe: int) -> str:
    return (f'"C:\\Users\\rocm\\miniconda3\\python.exe" "-X" "utf8" "-c" '
            f'"from multiprocessing.spawn import spawn_main; '
            f'spawn_main(parent_pid={parent}, pipe_handle={pipe})" '
            f'"--multiprocessing-fork"')


def census_tree() -> list[dict]:
    return [
        {"pid": 37120, "ppid": 3268,
         "cmdline": "python.exe C:/P19B/scratch/p1_amp_audit.py (preexisting)"},
        {"pid": 12052, "ppid": 37120,
         "cmdline": "python.exe C:/P19B/scratch/p1_amp_audit.py (preexisting)"},
        {"pid": 53968, "ppid": 54396,
         "cmdline": "python.exe run_envelope.py --name stage_e_workers8"},
        {"pid": 52244, "ppid": 53968,
         "cmdline": "C:/r22a5n1/venv/Scripts/python.exe worker_stage.py"},
        {"pid": 55012, "ppid": 52244,
         "cmdline": "C:/r22a5n1/venv/Scripts/python.exe worker_stage.py (checker)"},
        {"pid": ENV_PID, "ppid": 55012,
         "cmdline": "C:/r22a5n1/venv/Scripts/python.exe audit_adamw_amp.py (envelope child)"},
        {"pid": TRAINER_PID, "ppid": ENV_PID,
         "cmdline": "C:/r22a5n1/venv/Scripts/python.exe audit_adamw_amp.py (trainer)"},
        *[{"pid": w, "ppid": TRAINER_PID,
           "cmdline": spawn_cmdline(TRAINER_PID, 2500 + i)}
          for i, w in enumerate(WORKER_PIDS)],
    ]


def good_census(**over):
    c = {"stage": "mid-run census",
         "captured_utc": "2026-11-17T05:18:34.737321+00:00",
         "trainer_pid": TRAINER_PID,
         "spawn_children_of_trainer": sorted(WORKER_PIDS),
         "checker_pid": 55012, "rows_at_census": 1,
         "orchestrator_pid": ENV_PID,
         "spawn_children_count": len(WORKER_PIDS),
         "spawn_main_children_count": len(WORKER_PIDS),
         "snapshot_count": 1,
         "snapshots": [{"captured_utc": "2026-11-17T05:18:34.737321+00:00",
                        "python_tree": census_tree(),
                        "trainer_pid": TRAINER_PID,
                        "children": sorted(WORKER_PIDS),
                        "spawn_main": sorted(WORKER_PIDS)}],
         "capture_method": "full Win32_Process CIM tree snapshots, every one retained",
         "preexisting_zombies_disclosed": sorted(BASELINE_PIDS)}
    c.update(over)
    return c


def good_envelope(**over):
    e = {"stage": "workers=8 bounded exercise",
         "command": ["python.exe", "-X", "utf8", "audit_adamw_amp.py"],
         "checker_pid": None,
         "baseline_python_pids": sorted(BASELINE_PIDS),
         "started_utc": "2026-11-17T05:17:36.024534+00:00",
         "trainer_pid": ENV_PID,
         "finished_utc": "2026-11-17T05:18:47.106093+00:00",
         "exit_code": 0}
    e.update(over)
    return e


def good_orphan(**over):
    o = {"stage": "post-run orphan check",
         "captured_utc": "2026-11-17T05:18:47.718391+00:00",
         "checker_pid": 55012,
         "all_python_pids": sorted(BASELINE_PIDS),
         "baseline_python_pids": sorted(BASELINE_PIDS),
         "mission_tree_leftover": [],
         "orphan_verdict": "CLEAN"}
    o.update(over)
    return o


def all_gates(**mut):
    args = {"lock": good_lock(), "audit": good_audit(), "manifest": good_manifest(),
            "g0": good_g0(), "cand": good_cand(), "ctrl": good_ctrl(),
            "ops": good_ops(), "amp": good_amp(), "ckpt": good_ckpt(),
            "rel": good_rel()}
    for k, fn in mut.items():
        args[k] = fn(args[k])
    return [
        na.evaluate_pkg(args["lock"], args["audit"], args["manifest"]),
        na.evaluate_g0(args["g0"]),
        na.evaluate_g1(args["cand"], args["ctrl"], "BN_NOSTL_REPRO out_finite=True",
                       CTRL_STDERR),
        na.evaluate_g2(args["ops"]),
        *na.evaluate_g34(args["amp"]),
        na.evaluate_g5(args["ckpt"]),
        na.evaluate_g7(args["rel"], good_census(), good_orphan(), good_envelope()),
    ]


def derive_all(**mut):
    return na.derive(all_gates(**mut), [])


# ---------------------------------------------------------------- positives
def test_honest_fixture_full_audited_pass():
    res = derive_all()
    assert res["overall"] == "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS"


def test_engine_recomputes_counts_from_events():
    g3, g4 = na.evaluate_g34(good_amp())
    r = g3["facts"]["recomputed"]
    assert r["attempts"] == 11 and r["effective_updates"] == 7 \
        and r["inf_skips"] == 4 and r["backoffs_recomputed"] == 4
    assert g4["amp_verdict"] == "AMP_PASS"


def test_pkg_recomputes_rules_not_reads_them():
    # forged rules_checked.ok=True everywhere but packages actually violate
    lock = good_lock()
    for p in lock["packages"]:
        if p["name"] == "torch":
            p["url"] = "https://dev.repo.amd.com/rocm/pytorch/whl-next/torch/x.whl"
    g = na.evaluate_pkg(lock, good_audit(), good_manifest())
    r = g["facts"]["recomputed"]
    assert r["origin_ok"] is False and g["verdict"] == "FAIL"
    # the forged stored booleans remain untouched in the lock — they were simply
    # never consulted


# --------------------------------------------- mission §9 cases 1-25
def test_case1_dev_lock_sha_substituted():
    # historical DEV lock SHA recorded in a nightly receipt → LK must catch it
    with tempfile.TemporaryDirectory() as td:
        lp = Path(td) / "lock.json"
        lp.write_text(json.dumps(good_lock()), encoding="utf-8")
        sha = hashlib.sha256(lp.read_bytes()).hexdigest()
        rec = {"wheel_lock_sha256": "97a2da63" + "0" * 56,
               "wheel_lock_channel": "nightly", "wheel_lock_gfx": "gfx1151",
               "runtime_package_versions": {}}
        g = na.evaluate_lk([("05/adamw_amp.json", rec)], lp)
        assert g["verdict"] == "FAIL" and sha != rec["wheel_lock_sha256"]


def test_case2_forged_rules_checked_ok():
    lock = good_lock()
    lock["packages"] = [p for p in lock["packages"]
                        if p["name"] != "rocm-sdk-device-gfx1151"]  # device wheel gone
    g = na.evaluate_pkg(lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL" and \
        g["facts"]["recomputed"]["device_wheel_ok"] is False


def test_case3_wheel_version_changed():
    lock = good_lock()
    for p in lock["packages"]:
        if p["name"] == "torch":
            p["version"] = "2.16.0a0+rocm10.3.0a20261115"
    # installed manifest still has the 1116 build → lock/installed diff nonempty
    g = na.evaluate_pkg(lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL" and g["facts"]["installed_missing_vs_lock"]


def test_case4_wheel_sha_changed():
    lock = good_lock()
    for p in lock["packages"]:
        if p["name"] == "rocm-sdk-libraries":
            p["sha256"] = "de" + "a" * 62
    g = na.evaluate_pkg(lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL"


def test_case5_miopen_dll_sha_changed():
    gates = all_gates(g0=lambda g: good_g0(child_dll_sha256="cafe" + "0" * 60))
    assert gates[1]["verdict"] == "FAIL"
    gates = all_gates(amp=lambda a: good_amp(
        loaded_miopen_dll_sha256="cafe" + "0" * 60))
    assert gates[4]["verdict"] == "FAIL"


def test_case6_ancestry_behind_by_positive():
    audit = good_audit()
    audit["audits"][0]["ancestry"] = {"status": "behind", "behind_by": 3,
                                      "ahead_by": 0}
    g = na.evaluate_pkg(good_lock(), audit, good_manifest())
    assert g["verdict"] == "FAIL"


def test_case7_dev_wheel_relabelled_nightly():
    lock = good_lock()
    for p in lock["packages"]:
        if p["name"] == "rocm-sdk-core":
            p["url"] = "https://dev.repo.amd.com/rocm/pytorch/whl-next/rocm-sdk-core/x.whl"
    g = na.evaluate_pkg(lock, good_audit(), good_manifest())
    assert g["verdict"] == "FAIL" and g["facts"]["origin_violations"]


def test_case8_training_log_deleted():
    g = na.evaluate_g1(good_cand(), good_ctrl(), "BN_NOSTL_REPRO out_finite=True",
                       None)  # control raw log gone
    assert g["verdict"] == "FAIL"
    assert g["facts"]["control_signature_in_raw_bytes"] is False


def test_case9_log_byte_corrupted():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "raw").mkdir()
        (root / "raw" / "leg.log").write_bytes(b"original bytes")
        ep.gen(root, "RUN-B", None, [], root / ep.MANIFEST_NAME)
        (root / "raw" / "leg.log").write_bytes(b"original bytex")  # 1 byte flipped
        r = ep.verify(root, "RUN-B")
        assert not r["ok"] and any("hash mismatch" in p for p in r["problems"])


def test_case10_forged_pass_zero_updates():
    ev = per_step_series()
    for e in ev:  # every step: no parameter movement, no found_inf excuse
        e["sentinel_max_abs_delta"] = 0.0
        e["found_inf_any"] = False
    g3, g4 = na.evaluate_g34(good_amp(training_counts={
        **good_amp()["training_counts"],
        "confirmed_update_events": 11, "skipped_found_inf_flagged": 0,
        "per_step_events": ev}))
    assert g3["verdict"] == "FAIL"
    assert g3["facts"]["recomputed"]["effective_updates"] == 0


def test_case11_overflow_skip_flipped_to_update():
    ev = per_step_series()
    ev[0]["found_inf_any"] = True
    ev[0]["sentinel_max_abs_delta"] = 5e-05  # moved on an inf skip — impossible
    g3, _ = na.evaluate_g34(good_amp(training_counts={
        **good_amp()["training_counts"], "per_step_events": ev}))
    assert g3["verdict"] == "FAIL" and g3["facts"]["recomputed"]["moved_on_inf_skip"]


def test_case12_sentinel_delta_zeroed_count_kept():
    ev = per_step_series()
    ev[5]["sentinel_max_abs_delta"] = 0.0  # no movement, no inf excuse
    g3, _ = na.evaluate_g34(good_amp(training_counts={
        **good_amp()["training_counts"], "per_step_events": ev}))
    assert g3["verdict"] == "FAIL"
    assert g3["facts"]["recomputed"]["unexplained_no_update_steps"] == 1


def test_case13_scaler_transitions_mismatched():
    sh = [65536.0, 32768.0, 16384.0, 8192.0, 8192.0] + [4096.0] * 6  # skip@3 no backoff
    g3, _ = na.evaluate_g34(good_amp(gradscaler={
        **good_amp()["gradscaler"], "scale_history": sh}))
    assert g3["verdict"] == "FAIL"
    assert g3["facts"]["recomputed"]["inf_skips_without_scale_backoff"]


def test_case14_amp_pass_claimed_on_fp32_only():
    g3, g4 = na.evaluate_g34(good_amp(
        amp={"autocast_dtype_observed": None,
             "stem_conv_output_dtypes_observed": {"float32": 96},
             "autocast_forward_samples": {"sampled": 48, "enabled": 0}},
        low_precision_evidence={"samples_low_precision": 0, "samples_total": 96}))
    assert g4["amp_verdict"] != "AMP_PASS"


def test_case15_gpu_identity_mismatched():
    res = derive_all(g0=lambda g: good_g0(gfx_target="gfx1100",
                                          child_gpu_name="AMD Radeon RX 7900 XTX"))
    assert res["gate_verdicts"]["G0"] == "FAIL"
    res = derive_all(amp=lambda a: good_amp(gfx_target="gfx1100",
                                            gpu_name="AMD Radeon RX 7900 XTX"))
    assert res["gate_verdicts"]["G3"] == "FAIL"


def test_case16_run_id_reuse_conflicting_evidence():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.json").write_text("{}", encoding="utf-8")
        ep.gen(root, "RUN-B-1", None, [], root / ep.MANIFEST_NAME)
        r = ep.verify(root, "RUN-B-2")  # same pack claimed under another run id
        assert not r["ok"] and any("run_id" in p for p in r["problems"])


def test_case17_checkpoint_sha_modified():
    # envelope anchored the real bytes; a tampered receipt SHA must not match
    artifacts = [{"path": "runs/lifecycle/weights/last.pt",
                  "sha256": "ab" + "0" * 62},
                 {"path": "runs/lifecycle/weights/best.pt",
                  "sha256": "cd" + "0" * 62}]
    g = na.evaluate_g5(good_ckpt(checkpoint_sha256={
        "last.pt": "ff" + "0" * 62, "best.pt": "ee" + "0" * 62}), artifacts)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["checkpoint_bytes_anchored"]["last.pt"] is False
    # and with the honest values the anchor holds
    g_ok = na.evaluate_g5(good_ckpt(), artifacts)
    assert g_ok["verdict"] == "PASS"


def test_case18_optimizer_restoration_claimed_without_state():
    g = na.evaluate_g5(good_ckpt(stages={
        **good_ckpt()["stages"],
        "checkpoint_resumability": {"has_optimizer_state": False},
        "optimizer_state_entries": 0}))
    assert g["verdict"] == "FAIL"


def test_case19_resume_epoch_continuity_forged():
    g = na.evaluate_g5(good_ckpt(stages={**good_ckpt()["stages"],
                                         "last_epoch_value": 4, "final_epoch_rows": 2,
                                         "rows_at_kill": 2}))
    # rows never grew past the kill point — stored continuity bool is a lie
    assert g["verdict"] == "FAIL" and \
        g["facts"]["epoch_continuity_recomputed"] is False


def test_case20_workers8_claimed_without_live_evidence():
    g = na.evaluate_g7(good_rel(), None, good_orphan(), good_envelope())
    assert g["verdict"] == "FAIL"
    # census without raw snapshots: 2 stored PIDs, nothing independently
    # observable — the stored list can never substitute for the tree
    g = na.evaluate_g7(good_rel(), good_census(
        snapshots=None,
        spawn_children_of_trainer=[50001, 50002],
        spawn_children_count=2, spawn_main_children_count=2),
        good_orphan(), good_envelope())
    assert g["verdict"] == "FAIL"
    assert g["facts"]["snapshots_examined"] == 0


def test_case21_orphan_clean_forged():
    orphan = good_orphan(all_python_pids=sorted(BASELINE_PIDS) + [556677])
    g = na.evaluate_g7(good_rel(), good_census(), orphan, good_envelope())
    assert g["verdict"] == "FAIL"
    assert g["facts"]["leftover_recomputed"] == [556677]


def test_case22_negative_control_removed():
    res = derive_all(ctrl=lambda c: None)
    assert res["gate_verdicts"]["G1"] == "FAIL"
    assert res["overall"] != "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS"


def test_case23_control_dll_swapped_to_fixed():
    g = na.evaluate_g1(good_cand(), good_ctrl(leg_detail={
        **good_ctrl()["leg_detail"],
        "child_miopen": {"sha256": F["miopen_dll_sha256"]}}),
        "BN_NOSTL_REPRO out_finite=True", CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_case24_hiprtc_shim_while_claiming_no_workaround():
    g = na.evaluate_g1(good_cand(ambient_hiprtc_shim="-I C:/BuildTools/include"),
                       good_ctrl(), "log", CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_case25_nightly_verdict_relabelled_stable():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        p.write_text(json.dumps({"claim": "OFFICIAL_STABLE_PASS"}), encoding="utf-8")
        hits = na.scan_forbidden_verdicts(Path(td))
    res = na.derive(all_gates(), hits)
    assert res["overall"] == "NIGHTLY_NO_GO" and res["forbidden_verdict_hits"]


# ------------------------------------------- lock gate (audit_adamw_amp)
def _write_lock(td, lock=None):
    lp = Path(td) / "lock.json"
    lp.write_text(json.dumps(lock or good_lock()), encoding="utf-8")
    return lp


def test_lock_gate_rejects_missing_lock():
    with pytest.raises(SystemExit) as ei:
        adamw.resolve_wheel_lock(str(Path("NUL:/nope/lock.json")), "nightly",
                                 "gfx1151", {})
    assert ei.value.code == 2


def test_lock_gate_requires_explicit_lock_for_nightly():
    with pytest.raises(SystemExit) as ei:
        adamw.resolve_wheel_lock(None, "nightly", "gfx1151", {})
    assert ei.value.code == 2


def test_lock_gate_channel_mismatch_rejected():
    with tempfile.TemporaryDirectory() as td:
        lp = _write_lock(td)
        rec = {"wheel_lock_sha256": hashlib.sha256(lp.read_bytes()).hexdigest(),
               "wheel_lock_channel": "dev", "wheel_lock_gfx": "gfx1151",
               "runtime_package_versions": {}}
        g = na.evaluate_lk([("r", rec)], lp)
        # channel recorded dev but lock bytes say nightly → binding violation
        assert g["verdict"] == "FAIL"


def test_lock_gate_mutated_lock_rejected():
    with tempfile.TemporaryDirectory() as td:
        lp = _write_lock(td)
        sha = hashlib.sha256(lp.read_bytes()).hexdigest()
        rec = {"wheel_lock_sha256": sha, "wheel_lock_channel": "nightly",
               "wheel_lock_gfx": "gfx1151",
               "runtime_package_versions": {"torch": F["torch"]}}
        g0 = na.evaluate_lk([("r", rec)], lp)
        assert g0["verdict"] == "PASS"
        lp.write_text(json.dumps(good_lock(packages=lock_packages()[:-1])),
                      encoding="utf-8")  # bytes changed post-receipt
        g1 = na.evaluate_lk([("r", rec)], lp)
        assert g1["verdict"] == "FAIL"


def test_lock_gate_wrong_architecture_rejected():
    # an internally-consistent lock+receipt from ANOTHER architecture (gfx1100)
    # must still fail this mission's identity requirement
    with tempfile.TemporaryDirectory() as td:
        lp = _write_lock(td, good_lock(gfx_target="gfx1100"))
        sha = hashlib.sha256(lp.read_bytes()).hexdigest()
        rec = {"wheel_lock_sha256": sha, "wheel_lock_channel": "nightly",
               "wheel_lock_gfx": "gfx1100",
               "runtime_package_versions": {}}
        g = na.evaluate_lk([("r", rec)], lp)
        assert g["verdict"] == "FAIL"
        assert g["facts"]["receipts"][0]["status"] == "MISSION_IDENTITY_MISMATCH"


def test_lock_gate_runtime_version_mismatch_rejected():
    b = adamw.verify_lock_binding(good_lock(), "cf14", "nightly", "gfx1151",
                                  {"torch": "2.15.0+gitxxx"})
    assert not b["ok"] and any("torch" in v for v in b["violations"])


def test_lock_gate_dev_default_preserved():
    # channel dev without explicit lock still resolves the historical DEV lock
    # (backward-compatible historical behavior) — here it must at least not
    # demand an explicit lock
    with tempfile.TemporaryDirectory() as td:
        dev_lock = good_lock(channel="dev", gfx_target="gfx1151")
        lp = Path(td) / "dev.json"
        lp.write_text(json.dumps(dev_lock), encoding="utf-8")
        out = adamw.resolve_wheel_lock(str(lp), "dev", "gfx1151",
                                       {"torch": F["torch"]})
        assert out["ok"] is True


# ------------------------------------------- engine hardening specifics
def test_g7_trainer_ties_via_venv_launcher_chain():
    # census trainer is a DESCENDANT of the envelope pid (venv launchers sit
    # between orchestrator and real interpreter) — the census tree snapshots
    # prove the full ancestry chain including the 16 worker nodes
    census = good_census()
    g = na.evaluate_g7(good_rel(), census, good_orphan(), good_envelope())
    assert g["verdict"] == "PASS"
    assert g["facts"]["trainer_pid_ties_to_envelope"] is True
    assert g["facts"]["trainer_ancestry_chain"][:3] == [TRAINER_PID, ENV_PID, 55012]
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 16
    # without a reachable chain a mismatched pid must fail
    g2 = na.evaluate_g7(good_rel(), census, good_orphan(),
                        good_envelope(trainer_pid=999999))
    assert g2["verdict"] == "FAIL"
    assert g2["facts"]["trainer_pid_ties_to_envelope"] is False


def test_g1_parent_only_dll_capture_rejected():
    # candidate without IN-CHILD dll evidence (the R22A.5N weakness) must fail
    g = na.evaluate_g1(good_cand(leg_detail={**good_cand()["leg_detail"],
                                             "child_miopen": None}),
                       good_ctrl(), "log", CTRL_STDERR)
    assert g["verdict"] == "FAIL"


def test_g1_same_process_identity_rejected():
    g = na.evaluate_g1(good_cand(leg_detail={**good_cand()["leg_detail"],
                                             "pid": 42002}),
                       good_ctrl(), "log", CTRL_STDERR)
    assert g["verdict"] == "FAIL"  # candidate and control share a PID


def test_g2_nonfinite_detail_rejected():
    ops = good_ops()
    ops["gates"]["fp32_gemm"]["detail"]["sum"] = float("inf")
    g = na.evaluate_g2(ops)
    assert g["verdict"] == "FAIL" and g["facts"]["nonfinite_details"]


def test_g5_scheduler_claimed_serialized_is_scrutinized():
    sc = good_ckpt()["state_classes"]
    sc["scheduler"] = {"serialized": True}  # claimed serialized by a fixture
    g = na.evaluate_g5(good_ckpt(state_classes=sc))
    # engine only accepts FULL state when scheduler is honestly absent-by-design;
    # a claimed-serialized scheduler flips the class → not the honest shape
    assert g["facts"]["state_verdict"] != "FULL_TRAINING_STATE_RESTORE_PASS"


def test_historical_pack_a_lock_defect_detected_by_lk():
    # the ACTUAL original receipt field values from pack A
    rec = {"wheel_lock_sha256": "97a2da636a8264887e2f9f89443e43673967e6d8b"
                                "50acb2b5003a626fe089533",
           "runtime_package_versions": {"torch": F["torch"],
                                        "torchvision": "0.30.0a0+rocm10.3.0a20261116",
                                        "ultralytics": F["ultralytics"]}}
    with tempfile.TemporaryDirectory() as td:
        lp = _write_lock(td)  # the genuine nightly lock
        g = na.evaluate_lk([("05_yolo_training_amp/adamw_amp.json", rec)], lp)
        assert g["verdict"] == "FAIL"
        assert g["facts"]["receipts"][0]["status"] == "SHA_MISMATCH"


# ------------------------------------------- evidence pack closure
def test_pack_verify_rejects_stale_extra_file():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.json").write_text("{}", encoding="utf-8")
        ep.gen(root, "RUN-B", None, [], root / ep.MANIFEST_NAME)
        (root / "sneaky.log").write_text("late addition", encoding="utf-8")
        r = ep.verify(root, "RUN-B")
        assert not r["ok"] and any("stale" in p for p in r["problems"])


def test_pack_verify_rejects_case_collision():
    # a manifest (e.g. generated on a case-sensitive FS) listing both A.log and
    # a.log describes an impossible Windows checkout — the verifier rejects it
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "A.log").write_text("x", encoding="utf-8")
        ep.gen(root, "RUN-B", None, [], root / ep.MANIFEST_NAME)
        m = json.loads((root / ep.MANIFEST_NAME).read_text(encoding="utf-8"))
        m["entries"].append({"path": "a.log", "sha256": "0" * 64, "bytes": 1,
                             "kind": "raw"})
        (root / ep.MANIFEST_NAME).write_text(json.dumps(m), encoding="utf-8")
        r = ep.verify(root, "RUN-B")
        assert not r["ok"] and any("duplicate path" in p for p in r["problems"])


def test_pack_verify_rejects_path_traversal_entry():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.json").write_text("{}", encoding="utf-8")
        ep.gen(root, "RUN-B", None, [], root / ep.MANIFEST_NAME)
        m = json.loads((root / ep.MANIFEST_NAME).read_text(encoding="utf-8"))
        m["entries"].append({"path": "../evil.json", "sha256": "0" * 64,
                             "bytes": 1, "kind": "raw"})
        (root / ep.MANIFEST_NAME).write_text(json.dumps(m), encoding="utf-8")
        r = ep.verify(root, "RUN-B")
        assert not r["ok"] and any("traversal" in p for p in r["problems"])


def test_pack_manifest_never_lists_itself():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.json").write_text("{}", encoding="utf-8")
        m = ep.gen(root, "RUN-B", None, [], root / ep.MANIFEST_NAME)
        assert all(e["path"] != ep.MANIFEST_NAME for e in m["entries"])
        r = ep.verify(root, "RUN-B")
        assert r["ok"]


# ============================== R22A.5N.2 — G5 fail-closed resume (mission §4.3)
def _stages(**over):
    st = dict(good_ckpt()["stages"])
    st.update(over)
    return st


def _resumability(**over):
    r = dict(good_ckpt()["stages"]["checkpoint_resumability"])
    r.update(over)
    return r


def _g5(stages=None, **over):
    kw = {"stages": stages if stages is not None else _stages()}
    kw.update(over)
    return na.evaluate_g5(good_ckpt(**kw))


def test_r22a5n2_g5_missing_total_epochs_fails_closed():
    st = _stages()
    del st["total_epochs"]
    g = _g5(stages=st)
    assert g["verdict"] == "FAIL"
    assert "total_epochs" in g["facts"]["epoch_evidence_missing"]
    assert g["facts"]["epoch_continuity_recomputed"] is None


def test_r22a5n2_g5_total_epochs_none_fails_closed():
    g = _g5(stages=_stages(total_epochs=None))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["epoch_evidence_missing"] == ["total_epochs"]


def test_r22a5n2_g5_missing_rows_at_kill_fails_closed():
    st = _stages()
    del st["rows_at_kill"]
    g = _g5(stages=st)
    assert g["verdict"] == "FAIL"
    assert "rows_at_kill" in g["facts"]["epoch_evidence_missing"]


def test_r22a5n2_g5_missing_final_epoch_rows_fails_closed():
    st = _stages()
    del st["final_epoch_rows"]
    g = _g5(stages=st)
    assert g["verdict"] == "FAIL"
    assert "final_epoch_rows" in g["facts"]["epoch_evidence_missing"]


def test_r22a5n2_g5_missing_resume_start_epoch_fails_closed():
    st = _stages()
    del st["resume_start_epoch"]
    g = _g5(stages=st)
    assert g["verdict"] == "FAIL"
    assert "resume_start_epoch" in g["facts"]["epoch_evidence_missing"]


def test_r22a5n2_g5_bool_disguised_as_int_rejected():
    # bool is an int subclass — True must not pass as total_epochs=1
    g = _g5(stages=_stages(total_epochs=True))
    assert g["verdict"] == "FAIL"
    assert any("total_epochs" in p for p in g["facts"]["epoch_evidence_invalid"])


def test_r22a5n2_g5_forged_epoch_continuity_bool_overruled_by_numbers():
    # stored epoch_continuity=True kept, but resume start is discontinuous
    g = _g5(stages=_stages(resume_start_epoch=3))  # != ckpt_epoch(1)+1
    assert g["verdict"] == "FAIL"
    assert g["facts"]["epoch_continuity_recomputed"] is False


def test_r22a5n2_g5_wrong_checkpoint_epoch_rejected():
    # checkpoint epoch inconsistent with the recorded resume start
    g = _g5(stages={**_stages(),
                   "checkpoint_resumability": _resumability(ckpt_epoch=0)})
    assert g["verdict"] == "FAIL"
    assert g["facts"]["epoch_continuity_recomputed"] is False


def test_r22a5n2_g5_resume_reset_to_initial_state_rejected():
    # resume_start_epoch=0 means training restarted from scratch
    g = _g5(stages=_stages(resume_start_epoch=0))
    assert g["verdict"] == "FAIL"
    assert any("resume_start_epoch" in p
               for p in g["facts"]["epoch_evidence_invalid"])


def test_r22a5n2_g5_zero_effective_updates_after_resume_rejected():
    g = _g5(stages=_stages(resume_effective_updates=0))
    assert g["verdict"] == "FAIL"
    assert any("resume_effective_updates" in p
               for p in g["facts"]["epoch_evidence_invalid"])


def test_r22a5n2_g5_wrong_final_epoch_rejected():
    g = _g5(stages=_stages(last_epoch_value=3))  # != total_epochs
    assert g["verdict"] == "FAIL"
    assert g["facts"]["epoch_continuity_recomputed"] is False


def test_r22a5n2_g5_scheduler_not_serialized_never_full():
    # honest 8.4.214 shape: everything else serialized, scheduler rebuilt from
    # train_args → FULL is unreachable, CORE is the honest classification
    g = na.evaluate_g5(good_ckpt())
    assert g["verdict"] == "PASS"
    assert g["facts"]["state_verdict"] == "RESUME_PASS_CORE_STATE_VERIFIED"
    assert g["facts"]["not_serialized_classes"] == \
        {"scheduler": "NOT_SERIALIZED_BY_UPSTREAM"}


def test_r22a5n2_g5_scaler_serialized_is_not_restore_verified():
    # the GradScaler `scaler` key being SERIALIZED does not verify its
    # post-resume state — the two maps must stay distinct claims
    g = na.evaluate_g5(good_ckpt())
    f = g["facts"]
    assert f["state_serialized_map"]["gradscaler"] is True
    assert f["state_restore_verified_map"]["gradscaler"] is not True
    assert f["state_verdict"] != "FULL_TRAINING_STATE_RESTORE_PASS"


def test_r22a5n2_g5_full_requires_per_class_restore_evidence():
    # claiming restore_verified on top of NOT_SERIALIZED is a contradiction
    sc = {k: {**v, "restore_verified": True}
          for k, v in good_ckpt()["state_classes"].items()}
    g1 = na.evaluate_g5(good_ckpt(state_classes=sc))
    assert g1["facts"]["state_verdict"] == "RESUME_PASS_CORE_STATE_VERIFIED"
    # genuinely serialized AND restore-verified everywhere → FULL is earned
    sc["scheduler"] = {"serialized": True, "restore_verified": True}
    g2 = na.evaluate_g5(good_ckpt(state_classes=sc))
    assert g2["verdict"] == "PASS"
    assert g2["facts"]["state_verdict"] == "FULL_TRAINING_STATE_RESTORE_PASS"


def test_r22a5n2_g5_real_pack_b_passes_with_limited_classification():
    # authentic committed pack-B bytes (read-only): strict engine still PASSes
    d = REPO_ROOT / "reports/r22a5n1/R22A5N1-GFX1151-20261117-B/06_checkpoint_resume"
    ckpt = json.loads((d / "checkpoint_resume.json").read_text(encoding="utf-8"))
    env = json.loads((d / "lifecycle_envelope.json").read_text(encoding="utf-8"))
    g = na.evaluate_g5(ckpt, (env or {}).get("artifact_hashes"))
    assert g["verdict"] == "PASS"
    f = g["facts"]
    assert f["epoch_evidence_missing"] == [] and f["epoch_evidence_invalid"] == []
    assert f["epoch_continuity_recomputed"] is True
    assert f["state_verdict"] == "RESUME_PASS_CORE_STATE_VERIFIED"
    assert f["not_serialized_classes"] == \
        {"scheduler": "NOT_SERIALIZED_BY_UPSTREAM"}


# ============================== R22A.5N.2 — G7 worker provenance (mission §5.4)
def _census_tree_mut(fn):
    """good_census with the peak snapshot's python_tree transformed."""
    census = good_census()
    census["snapshots"] = [dict(s, python_tree=fn([dict(p) for p in s["python_tree"]]))
                           for s in census["snapshots"]]
    return census


def _g7(census=None, orphan=None, envelope=None, rel=None):
    return na.evaluate_g7(rel or good_rel(), census or good_census(),
                          orphan or good_orphan(),
                          good_envelope() if envelope is None else envelope)


def test_r22a5n2_g7_forged_pids_absent_from_snapshot_rejected():
    # 16 stored PIDs, none observable in any raw snapshot tree
    census = _census_tree_mut(
        lambda tree: [p for p in tree if p["pid"] not in WORKER_PIDS])
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 0
    assert g["facts"]["worker_count_reconciles"] is False


def test_r22a5n2_g7_worker_ppid_wrong_rejected():
    census = _census_tree_mut(
        lambda tree: [dict(p, ppid=9999) if p["pid"] in WORKER_PIDS else p
                      for p in tree])
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 0


def test_r22a5n2_g7_cmdline_without_spawn_main_rejected():
    census = _census_tree_mut(
        lambda tree: [dict(p, cmdline="python.exe some_unrelated_worker.py")
                      if p["pid"] in WORKER_PIDS else p for p in tree])
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 0


def test_r22a5n2_g7_cmdline_parent_pid_mismatch_rejected():
    def mut(tree):
        out = []
        for p in tree:
            if p["pid"] in WORKER_PIDS:
                p = dict(p, cmdline=spawn_cmdline(48848, 2500))  # ≠ real PPID
            out.append(p)
        return out
    g = _g7(census=_census_tree_mut(mut))
    assert g["verdict"] == "FAIL"
    rejected = g["facts"]["per_snapshot_workers"][0]["rejected_spawn_nodes"]
    assert rejected and rejected[0]["cmdline_parent_pid"] == "48848"


def test_r22a5n2_g7_worker_of_other_python_process_rejected():
    # spawn-shaped workers parented by an unrelated python process (37120)
    census = _census_tree_mut(
        lambda tree: [dict(p, ppid=12052) if p["pid"] in WORKER_PIDS else p
                      for p in tree])
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 0


def test_r22a5n2_g7_pids_scattered_across_snapshots_rejected():
    # 8 stored PIDs split 4+4 over two different-time snapshots — no single
    # snapshot proves 8 simultaneous workers
    base = census_tree()
    snap_a = [dict(p) for p in base if p["pid"] not in WORKER_PIDS[4:16]]
    snap_b = [dict(p) for p in base if p["pid"] not in WORKER_PIDS[:4]
              and p["pid"] not in WORKER_PIDS[8:16]]
    census = good_census(
        snapshots=[{"captured_utc": "2026-11-17T05:18:20+00:00",
                    "python_tree": snap_a, "trainer_pid": TRAINER_PID},
                   {"captured_utc": "2026-11-17T05:18:34+00:00",
                    "python_tree": snap_b, "trainer_pid": TRAINER_PID}],
        snapshot_count=2)
    census["snapshots"][1]["python_tree"] = [
        dict(p, pid=p["pid"] + 1, ppid=TRAINER_PID,
             cmdline=spawn_cmdline(TRAINER_PID, 2600))
        if p["pid"] in WORKER_PIDS[4:8] else p
        for p in census["snapshots"][1]["python_tree"]]
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["peak_snapshot"]["simultaneous_valid_workers"] == 4


def test_r22a5n2_g7_trainer_not_attributable_to_envelope_rejected():
    g = _g7(envelope=good_envelope(trainer_pid=999999))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["trainer_pid_ties_to_envelope"] is False


def test_r22a5n2_g7_missing_envelope_pid_rejected():
    g = _g7(envelope={})  # no child_pid / trainer_pid at all
    assert g["verdict"] == "FAIL"
    assert g["facts"]["trainer_pid_ties_to_envelope"] is False


def test_r22a5n2_g7_ancestry_cycle_rejected():
    # 6784's PPID points back at the trainer → cyclic ancestry
    census = _census_tree_mut(
        lambda tree: [dict(p, ppid=TRAINER_PID) if p["pid"] == ENV_PID else p
                      for p in tree])
    g = _g7(census=census)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["trainer_ancestry_cycle"] is True


def test_r22a5n2_g7_duplicate_worker_pid_rejected():
    kids = sorted(WORKER_PIDS)
    kids[1] = kids[0]  # duplicate entry
    g = _g7(census=good_census(spawn_children_of_trainer=kids))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["worker_count_reconciles"] is False


def test_r22a5n2_g7_stored_count_mismatch_rejected():
    g = _g7(census=good_census(spawn_children_count=15))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["worker_count_reconciles"] is False


def test_r22a5n2_g7_forged_orphan_clean_with_live_worker_rejected():
    # stored verdict CLEAN, but an attributed task worker is still alive
    live = WORKER_PIDS[0]
    g = _g7(orphan=good_orphan(
        all_python_pids=sorted(BASELINE_PIDS) + [live],
        mission_tree_leftover=[], orphan_verdict="CLEAN"))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["attributed_workers_terminated"] is False
    assert g["facts"]["leftover_recomputed"] == [live]


def test_r22a5n2_g7_forged_preexisting_masking_alive_worker_rejected():
    # baseline/disclosure/envelope consistently relabel a live task worker as
    # preexisting — the census tree contradicts: it is the trainer's own child
    live = WORKER_PIDS[0]
    masked = sorted(BASELINE_PIDS + [live])
    g = _g7(census=good_census(preexisting_zombies_disclosed=masked),
            orphan=good_orphan(all_python_pids=masked,
                               baseline_python_pids=masked),
            envelope=good_envelope(baseline_python_pids=masked))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["baseline_contradicts_census_tree"] == [live]
    assert g["facts"]["attributed_workers_terminated"] is False


def test_r22a5n2_g7_missing_recorded_baseline_rejected():
    # orphan record without the recorded pre-start baseline: nothing may be
    # excused, the surviving envelope-chain PIDs become recomputed leftovers
    orphan = {"checker_pid": 55012,
              "all_python_pids": sorted(BASELINE_PIDS),
              "mission_tree_leftover": [], "orphan_verdict": "CLEAN"}
    g = _g7(orphan=orphan)
    assert g["verdict"] == "FAIL"
    assert g["facts"]["leftover_recomputed"] == sorted(
        [p for p in BASELINE_PIDS if p != 55012])


def test_r22a5n2_g7_census_disclosure_disagreeing_with_baseline_rejected():
    g = _g7(census=good_census(preexisting_zombies_disclosed=[37120]))
    assert g["verdict"] == "FAIL"
    assert g["facts"]["baseline_reconciles_census_disclosure"] is False


def test_r22a5n2_g7_real_pack_b_sixteen_workers_verified():
    # authentic committed pack-B bytes (read-only): full strict G7 recompute
    d = REPO_ROOT / "reports/r22a5n1/R22A5N1-GFX1151-20261117-B/07_reliability"
    rel = json.loads((d / "workers8_amp_v2.json").read_text(encoding="utf-8"))
    supp = json.loads((d / "workers8_midrun_census.json").read_text(encoding="utf-8"))
    orphan = json.loads(
        (d / "workers8_postrun_orphan_check.json").read_text(encoding="utf-8"))
    env = json.loads((d / "workers8_envelope.json").read_text(encoding="utf-8"))
    g = na.evaluate_g7(rel, supp, orphan, env)
    assert g["verdict"] == "PASS"
    f = g["facts"]
    assert f["snapshots_examined"] == 1
    assert f["peak_snapshot"]["simultaneous_valid_workers"] == 16
    assert f["recomputed_worker_pids"] == sorted(
        supp["spawn_children_of_trainer"])
    assert f["trainer_pid"] == 39592 and f["trainer_in_peak_snapshot"] is True
    assert f["trainer_ancestry_cycle"] is False
    assert f["trainer_pid_ties_to_envelope"] is True  # env child 6784 in chain
    assert f["worker_count_reconciles"] is True
    assert f["trainer_terminated"] is True
    assert f["attributed_workers_terminated"] is True
    assert f["leftover_recomputed"] == []
    assert f["baseline_contradicts_census_tree"] == []
