# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N gfx1100 hardened Nightly acceptance engine — mission PHASE B/J.

Versioned mission-profile engine (default profile: gfx1100). Reuses the pure
recomputation kernels of the R22A.5N.1 engine by import (mission §5 "reuse,
do not duplicate"); every gate that binds physical identity is parameterized
by the frozen profile instead of the historical module-global FROZEN. Two
gates are hardened beyond R22A.5N.1 per mission §1.2 (the R22A.5N.2
fail-closed closure, not present in PR #22 HEAD 568981d — dependency
recorded):

  G5 (hardened)  fail-closed when ANY key epoch fact is missing (total_epochs,
                 rows_at_kill, final_epoch_rows, last_epoch_value, resume_exit,
                 resume_done_marker, infer_exit, checkpoint SHA at kill);
                 epoch continuity must recompute strictly True (a stored
                 boolean is never sufficient); FULL_TRAINING_STATE_RESTORE_PASS
                 is impossible unless the scheduler state is ACTUALLY
                 serialized — with scheduler NOT_SERIALIZED_BY_UPSTREAM the
                 verdict ceiling is RESUME_PASS_CORE_STATE_VERIFIED
  G7 (hardened)  worker identity recomputed per raw python_tree snapshot:
                 trainer = deepest audit_adamw_amp process; every counted
                 worker must (a) be a child of that trainer PID (PPID
                 re-derived), (b) carry multiprocessing.spawn_main in its
                 command line, (c) coexist in ONE single snapshot (splicing
                 PIDs observed at different times can never satisfy >=8);
                 stored spawn_children list / orphan verdict strings are
                 DIFFED, never authority; missing snapshots/baseline is
                 fail-closed

  G1 (extended)  TWO independent cold candidate trials required (distinct
                 child PIDs pairwise, distinct cold-cache scratch dirs
                 pairwise, in-child DLL identity on every trial)

All other gates re-derive from raw evidence with the gfx1100 frozen identity.
Overall ceiling: R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS.

    python scripts/r22a5n1100/nightly_acceptance.py --evidence-root DIR \
        --repo-root REPO --run-id R22A5N-GFX1100-... --out report.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "windows-golden-path" / "scripts"))

import gp_lib  # noqa: E402
import audit_adamw_amp as adamw_lib  # noqa: E402 — reuse the tested lock gate
from mission_profile import (FORBIDDEN_VERDICTS, N1,  # noqa: E402
                             get_profile)

_recompute_lock_rules = N1.recompute_lock_rules
_recompute_step_statistics = N1.recompute_step_statistics
_gate = N1.gate
_j = N1._j


def _log_text(p: Path) -> str | None:
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


# ================================================================ PKG
def evaluate_pkg(profile: dict, lock, audit, manifest) -> dict:
    frozen = profile["frozen"]
    f: dict = {"lock_present": lock is not None, "audit_present": audit is not None,
               "manifest_present": manifest is not None}
    if not (lock and audit and manifest):
        return _gate("PKG", False, f, "missing lock/audit/manifest evidence")
    r = _recompute_lock_rules(lock)
    a = (audit.get("audits") or [{}])[0]
    f.update({
        "recomputed": {k: v for k, v in r.items() if k != "rules_checked_diff"},
        "origin_violations": r["origin_violations"][:8],
        "abi_violations": r["abi_violations"][:8],
        "audit_wheel_sha256": a.get("wheel_sha256"),
        "audit_dll_sha256": (a.get("miopen_dll") or {}).get("sha256"),
        "audit_dll_build": (a.get("miopen_dll") or {}).get("build_commit"),
        "ancestry": a.get("ancestry"),
        "python_tag_expected": profile["python_tag"],
    })
    anc = a.get("ancestry") or {}
    installed = {}
    for s in (manifest.get("all_distributions") or []):
        if isinstance(s, str) and "==" in s:
            n, v = s.split("==", 1)
            installed[gp_lib.dist_key(n)] = v
    lock_pairs = {gp_lib.dist_key(p.get("name", "")): p.get("version")
                  for p in lock.get("packages") or []}
    missing = {n: v for n, v in lock_pairs.items() if installed.get(n) != v}
    rogue_native = [n for n in installed
                    if gp_lib.is_native_amd_gpu_stack(n) and n not in lock_pairs]
    f["installed_missing_vs_lock"] = missing
    f["rogue_native_installed"] = rogue_native
    gpu_stack = manifest.get("gpu_stack") or {}
    f["gpu_stack"] = gpu_stack
    ok = (
        lock.get("channel") == frozen["channel"]
        and lock.get("gfx_target") == frozen["gfx_target"]
        and (lock.get("python_tag") or "") == profile["python_tag"]
        and r["origin_ok"] and r["family_ok"] and r["device_wheel_ok"]
        and r["torch_is_amd_hip"] and r["abi_ok"]
        and r["sdk_wheel_sha256"] == frozen["wheel_sha256"]
        and a.get("wheel_sha256") == frozen["wheel_sha256"]
        and (a.get("miopen_dll") or {}).get("sha256") == frozen["miopen_dll_sha256"]
        and (a.get("miopen_dll") or {}).get("build_commit") == frozen["miopen_build"].split(".")[-1]
        and a.get("fix_present") is True and a.get("verdict") == "POST_FIX_LIBRARIES"
        and anc.get("behind_by") == 0 and (anc.get("ahead_by") or 0) > 0
        and not missing and not rogue_native
        and "No broken requirements" in (manifest.get("pip_check") or "")
        and gpu_stack.get("torch") == frozen["torch"]
        and gpu_stack.get("ultralytics") == frozen["ultralytics"]
    )
    return _gate("PKG", ok, f,
                 "NIGHTLY_PACKAGE_SET_VERIFIED (gfx1100 profile, independently "
                 "recomputed)" if ok
                 else "package set failed independent recomputation")


# ================================================================ LK
def evaluate_lk(profile: dict, training_receipts: list[tuple[str, dict]],
                lock_path: Path) -> dict:
    frozen = profile["frozen"]
    f: dict = {"lock_path": str(lock_path), "receipts": []}
    if not lock_path.is_file():
        return _gate("LK", False, f, f"lock file not found: {lock_path}")
    sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    f["lock_sha256_recomputed"] = sha
    f["lock_identity"] = {"channel": lock.get("channel"),
                          "gfx_target": lock.get("gfx_target"),
                          "python_tag": lock.get("python_tag")}
    all_ok = lock.get("gfx_target") == frozen["gfx_target"]
    if not all_ok:
        f["lock_identity_mismatch"] = (f"lock gfx_target {lock.get('gfx_target')!r} "
                                       f"!= profile {frozen['gfx_target']!r}")
    for label, rec in training_receipts:
        entry = {"receipt": label, "recorded_sha": rec.get("wheel_lock_sha256"),
                 "has_binding": "wheel_lock_sha256" in rec}
        if not entry["has_binding"]:
            entry["status"] = "NO_LOCK_FIELD"
            all_ok = False
        elif rec.get("wheel_lock_sha256") != sha:
            entry["status"] = "SHA_MISMATCH"
            all_ok = False
        elif rec.get("wheel_lock_channel") != frozen["channel"] \
                or rec.get("wheel_lock_gfx") != frozen["gfx_target"]:
            entry["status"] = "MISSION_IDENTITY_MISMATCH"
            entry["violations"] = [
                f"receipt channel {rec.get('wheel_lock_channel')!r}/gfx "
                f"{rec.get('wheel_lock_gfx')!r} != profile "
                f"{frozen['channel']!r}/{frozen['gfx_target']!r}"]
            all_ok = False
        else:
            binding = adamw_lib.verify_lock_binding(
                lock, sha, rec.get("wheel_lock_channel") or frozen["channel"],
                rec.get("wheel_lock_gfx") or rec.get("gfx_target"),
                rec.get("runtime_package_versions") or {})
            entry["status"] = "BOUND" if binding["ok"] else "BINDING_VIOLATION"
            entry["violations"] = binding["violations"]
            all_ok = all_ok and binding["ok"]
        f["receipts"].append(entry)
    return _gate("LK", all_ok, f,
                 "all training receipts bound to the exact gfx1100 lock bytes"
                 if all_ok
                 else "wheel-lock binding failed (wrong/dev/mutated/foreign-"
                      "profile lock recorded)")


# ================================================================ G0
def evaluate_g0(profile: dict, g0) -> dict:
    frozen = profile["frozen"]
    f = {"present": g0 is not None}
    if not g0:
        return _gate("G0", False, f, "missing G0 evidence")
    f.update({
        "verdict": g0.get("verdict"),
        "child_dll_sha256": g0.get("child_dll_sha256"),
        "frozen_dll_sha256": frozen["miopen_dll_sha256"],
        "child_gpu_name": g0.get("child_gpu_name"),
        "gfx_target": g0.get("gfx_target"),
        "child_op_finite": g0.get("child_op_finite"),
        "parent_child_agree": g0.get("parent_and_child_dll_agree"),
        "runtime_class": g0.get("runtime_class"),
        "exit_code": g0.get("exit_code"),
        "child_dll_marker": g0.get("child_marker_count"),
    })
    if g0.get("verdict") == "BLOCKED_DLL_CONTAMINATION":
        return _gate("G0", False, f, "BLOCKED_DLL_CONTAMINATION")
    ok = (
        g0.get("verdict") == "G0_RUNTIME_IDENTITY_PASS"
        and g0.get("child_dll_sha256") == frozen["miopen_dll_sha256"]
        and g0.get("child_op_finite") is True
        and g0.get("gfx_target") == frozen["gfx_target"]
        and g0.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and g0.get("parent_and_child_dll_agree") is True
        and str(g0.get("child_dll_path", "")).endswith("_rocm_sdk_libraries\\bin\\MIOpen.dll")
        and (g0.get("child_marker_count") or 0) > 0
    )
    return _gate("G0", ok, f, "runtime identity verified in child process on "
                 f"{frozen['gfx_target']}" if ok
                 else "runtime identity not established")


# ================================================================ G1
def evaluate_g1(profile: dict, trials: list[dict | None], ctrl,
                trial_logs: list[str | None], ctrl_log: str | None) -> dict:
    """Extended G1: >= profile['minimum_candidate_trials'] independent cold
    candidate trials + matched pre-fix negative control, all re-derived from
    raw log bytes."""
    frozen = profile["frozen"]
    need = profile.get("minimum_candidate_trials", 2)
    f: dict = {"candidate_trials_present": sum(t is not None for t in trials),
               "control_present": ctrl is not None,
               "required_trials": need}
    live = [t for t in trials if t is not None]
    if not live:
        return _gate("G1", False, f, "missing G1 candidate evidence")
    legs = [t.get("leg_detail") or {} for t in live]
    pids = [ld.get("pid") for ld in legs]
    scratches = [ld.get("scratch") for ld in legs]
    f["candidate_pids"] = pids
    f["candidate_scratches"] = scratches
    f["candidate_classifications"] = [t.get("classification") for t in live]
    f["candidate_child_dlls"] = [(ld.get("child_miopen") or {}).get("sha256")
                                 for ld in legs]
    f["candidate_raw_logs_available"] = [x is not None for x in trial_logs]
    if len(live) < need:
        return _gate("G1", False, f,
                     f"INSUFFICIENT_COLD_TRIALS — {len(live)}/{need} independent "
                     "cold candidate trials recorded")
    for i, t in enumerate(live):
        ld = legs[i]
        trial_ok = (
            t.get("classification") == "OFFICIAL_CANDIDATE_PASS"
            and t.get("expectation") == "CANDIDATE"
            and t.get("exit_code") == 0
            and not t.get("ambient_hiprtc_shim")
            and t.get("runtime_class") == "OFFICIAL_CANDIDATE"
            and t.get("gfx_target") == frozen["gfx_target"]
            and ld.get("exit_code") == 0
            and (ld.get("child_miopen") or {}).get("sha256") == frozen["miopen_dll_sha256"]
        )
        if not trial_ok:
            return _gate("G1", False, f, f"candidate trial #{i + 1} not a genuine "
                        "PASS (in-child DLL identity required)")
        if trial_logs[i] is not None and "type_traits" in trial_logs[i]:
            return _gate("G1", False, f, f"candidate trial #{i + 1} raw log "
                        "carries the pre-fix failure signature")
    if len(set(pids)) != len(pids):
        return _gate("G1", False, f, "candidate trials not run in distinct "
                    "processes (PID collision)")
    if len(set(scratches)) != len(scratches):
        return _gate("G1", False, f, "candidate trials did not use distinct "
                    "cold-cache scratch identities")
    if not ctrl:
        return _gate("G1", False, f, "NIGHTLY_NO_STL_POSITIVE_ONLY_CONTROL_PENDING")
    cld = ctrl.get("leg_detail") or {}
    f.update({
        "control_pid": cld.get("pid"),
        "control_child_dll": (cld.get("child_miopen") or {}).get("sha256"),
        "control_scratch": cld.get("scratch"),
        "control_failure_class": ctrl.get("failure_classification"),
        "control_dll_marker": ((ctrl.get("miopen_identity_in_parent") or {})
                               .get("pr13437_marker_miopen_initializer_list")),
        "control_raw_log_available": ctrl_log is not None,
    })
    ctrl_stderr = ctrl_log if ctrl_log is not None else (cld.get("stderr_tail") or "")
    recomputed_class = gp_lib.classify_nostl_failure(ctrl_stderr or "")
    f["control_failure_reclassified"] = recomputed_class
    f["control_signature_in_raw_bytes"] = (
        ("type_traits" in (ctrl_stderr or "")
         or "HIPRTC_ERROR_COMPILATION" in (ctrl_stderr or ""))
        and ctrl_log is not None)
    f["control_batchnorm_source_in_raw_bytes"] = (
        "MIOpenBatchNormFwdTrainSpatial" in (ctrl_stderr or "")
        and ctrl_log is not None)
    f["candidate_control_distinct_processes"] = (
        bool(cld.get("pid")) and cld.get("pid") not in pids)
    f["candidate_control_distinct_scratch"] = (
        bool(cld.get("scratch")) and cld.get("scratch") not in scratches)
    ctrl_ok = (
        ctrl.get("classification") == "OFFICIAL_PRE_FIX_EXPECTED_FAIL"
        and ctrl.get("failure_classification") == "MIOPEN_HIPRTC_COMPILATION"
        and recomputed_class == "MIOPEN_HIPRTC_COMPILATION"
        and f["control_signature_in_raw_bytes"]
        and ctrl.get("expectation") == "FAIL"
        and ((ctrl.get("miopen_identity_in_parent") or {})
             .get("pr13437_marker_miopen_initializer_list") == 0)
        and (cld.get("child_miopen") or {}).get("sha256") not in (
            None, frozen["miopen_dll_sha256"])
    )
    if not (f["candidate_control_distinct_processes"]
            and f["candidate_control_distinct_scratch"]):
        return _gate("G1", False, f, "candidate/control processes or cold-cache "
                    "identities not distinct")
    if not ctrl_ok:
        return _gate("G1", False, f,
                     "negative control not the matched pre-fix failure "
                     "(signature re-classification or control DLL identity failed)")
    return _gate("G1", True, f,
                 "NIGHTLY_NO_STL_REGRESSION_CONFIRMED — strong source-lineage + "
                 "behavioral paired control (pre-fix and nightly stacks differ in "
                 "more than one component; this is NOT a single-variable "
                 "intervention)")


# ================================================================ G2
def evaluate_g2(profile: dict, ops) -> dict:
    frozen = profile["frozen"]
    f = {"present": ops is not None}
    if not ops:
        return _gate("G2", False, f, "missing G2 evidence")
    gates = ops.get("gates") or {}
    statuses = {g: (gates.get(g) or {}).get("status") for g in N1.G2_GATES}
    nonfinite = []
    for g in N1.G2_GATES:
        det = (gates.get(g) or {}).get("detail") or {}
        for k, v in (det.items() if isinstance(det, dict) else []):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if not N1._finite(v):
                    nonfinite.append(f"{g}.{k}={v}")
    gfx = ((gates.get("device_identity") or {}).get("detail") or {}).get("gfx_target")
    f.update({"gate_statuses": statuses, "nonfinite_details": nonfinite,
              "gfx_target": gfx, "pass_fail_skip": ops.get("pass_fail_skip"),
              "runtime_class": ops.get("runtime_class"),
              "cpu_fallback_used": ops.get("cpu_fallback_used"),
              "loaded_dll_sha256": (ops.get("miopen_identity") or {}).get("sha256"),
              "exit_code": ops.get("exit_code")})
    ok = (
        all(v == "PASS" for v in statuses.values())
        and gfx == frozen["gfx_target"]
        and not nonfinite
        and not ops.get("cpu_fallback_used")
        and ops.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and (ops.get("miopen_identity") or {}).get("sha256") == frozen["miopen_dll_sha256"]
        and ops.get("exit_code") == 0
    )
    return _gate("G2", ok, f, "NIGHTLY_CORE_GPU_PASS (details re-checked)" if ok
                 else "core GPU gate failed")


# ================================================================ G3/G4
def evaluate_g34(profile: dict, amp) -> tuple[dict, dict]:
    frozen = profile["frozen"]
    f: dict = {"present": amp is not None}
    if not amp:
        return _gate("G3", False, f, "missing training evidence"), \
               _gate("G4", False, f, "missing AMP evidence")
    tc = amp.get("training_counts") or {}
    per_step = tc.get("per_step_events") or []
    scale_history = (amp.get("gradscaler") or {}).get("scale_history") or []
    r = _recompute_step_statistics(per_step, scale_history)
    ampf = amp.get("amp") or {}
    lpe = amp.get("low_precision_evidence") or {}
    lmd = amp.get("loaded_model_delta") or {}
    dtypes = ampf.get("stem_conv_output_dtypes_observed") or {}
    lowp_recomputed = sum(int(v) for k, v in dtypes.items()
                          if k in adamw_lib.LOW_PRECISION_DTYPES)
    f.update({
        "recomputed": r,
        "stored_counts": {"attempts": tc.get("scaler_step_attempts"),
                          "effective": tc.get("confirmed_update_events"),
                          "inf_skips": tc.get("skipped_found_inf_flagged"),
                          "scale_len": (amp.get("gradscaler") or {})
                              .get("scale_history_len")},
        "counts_reconcile": (
            r["attempts"] == int(tc.get("scaler_step_attempts") or -1)
            and r["effective_updates"] == int(tc.get("confirmed_update_events") or -1)
            and r["inf_skips"] == int(tc.get("skipped_found_inf_flagged") or -1)
            and r["scale_history_len"] == int(
                (amp.get("gradscaler") or {}).get("scale_history_len") or -1)),
        "batches_completed": tc.get("batches_completed"),
        "dtype_histogram": dtypes,
        "low_precision_samples_recomputed": lowp_recomputed,
        "low_precision_samples_stored": lpe.get("samples_low_precision"),
        "optimizer_requested": (amp.get("optimizer") or {}).get("requested"),
        "optimizer_resolved": (amp.get("optimizer") or {}).get("resolved_class"),
        "param_tensors_changed": lmd.get("tensors_changed_beyond_1e-9"),
        "param_all_finite": lmd.get("all_finite"),
        "checkpoint": amp.get("checkpoint"),
        "loaded_miopen_dll_sha256": amp.get("loaded_miopen_dll_sha256"),
        "gpu_name": amp.get("gpu_name"), "gfx_target": amp.get("gfx_target"),
        "exit_code": amp.get("exit_code"), "runtime_class": amp.get("runtime_class"),
        "epoch_observations_len": len(amp.get("epoch_observations") or []),
    })
    stats_ok = (
        r["attempts"] > 0 and r["effective_updates"] > 0
        and not r["unexplained_no_update_steps"]
        and not r["moved_on_inf_skip"] and not r["nonfinite_grads_on_effective"]
        and r["batch_index_monotonic"] and r["all_invoked"]
        and r["scale_history_matches_attempts"]
        and not r["inf_skips_without_scale_backoff"]
        and f["counts_reconcile"]
    )
    g3_ok = (
        stats_ok
        and (tc.get("batches_completed") or 0) > 0
        and tc.get("grads_finite_on_stepped_updates") is True
        and (lmd.get("tensors_changed_beyond_1e-9") or 0) > 0
        and lmd.get("all_finite") is True
        and (amp.get("checkpoint") or {}).get("exists") is True
        and amp.get("loaded_miopen_dll_sha256") == frozen["miopen_dll_sha256"]
        and amp.get("gfx_target") == frozen["gfx_target"]
        and amp.get("exit_code") == 0
        and amp.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and lowp_recomputed == int(lpe.get("samples_low_precision") or -1)
        and lowp_recomputed > 0
        and (amp.get("optimizer") or {}).get("requested") == "auto"
        and (amp.get("optimizer") or {}).get("resolved_class") == "AdamW"
    )
    g3 = _gate("G3", g3_ok, f, "NIGHTLY_YOLO_TRAINING_PASS (statistics recomputed "
               "from per-step facts)" if g3_ok
               else "training facts failed independent recomputation")
    dtype = ampf.get("autocast_dtype_observed")
    lowp = lowp_recomputed > 0
    fwd = ampf.get("autocast_forward_samples") or {}
    autocast_ok = int(fwd.get("enabled") or 0) > 0 \
        and fwd.get("enabled") == fwd.get("sampled")
    if not g3_ok:
        amp_verdict, reason = "AMP_INCONCLUSIVE", "training gate failed — AMP not evaluable"
    elif dtype == "float16" and lowp and autocast_ok and stats_ok:
        amp_verdict, reason = "AMP_PASS", (
            f"genuine FP16 execution recomputed from dtype histogram "
            f"({lowp_recomputed} low-precision samples); "
            f"{r['effective_updates']}/{r['attempts']} effective updates, "
            f"{r['inf_skips']} inf skips, {r['backoffs_recomputed']} scale "
            f"backoffs re-derived from the series")
    elif dtype is None and r["effective_updates"] > 0:
        amp_verdict, reason = "AMP_DISABLED", "no low-precision sample; FP32 trained"
    elif dtype == "float16":
        amp_verdict, reason = "AMP_FAIL", "low-precision execution without correct update behavior"
    else:
        amp_verdict, reason = "AMP_INCONCLUSIVE", "dtype observation incomplete"
    g4 = _gate("G4", amp_verdict == "AMP_PASS", f,
              f"NIGHTLY_AMP_PASS ({amp_verdict})" if amp_verdict == "AMP_PASS"
              else reason)
    g4["amp_verdict"] = amp_verdict
    return g3, g4


# ================================================================ G5 (hardened)
G5_REQUIRED_EPOCH_FACTS = ("total_epochs", "rows_at_kill", "final_epoch_rows",
                           "last_epoch_value", "resume_exit",
                           "resume_done_marker", "infer_exit",
                           "checkpoint_sha256_at_kill")


def evaluate_g5_hardened(profile: dict, ckpt, artifacts: list | None = None) -> dict:
    frozen = profile["frozen"]
    f: dict = {"present": ckpt is not None}
    if not ckpt:
        return _gate("G5", False, f, "missing checkpoint/resume evidence")
    anchored: dict[str, bool | None] = {}
    if artifacts is not None:
        by_sha = {a.get("sha256"): a.get("path") for a in artifacts
                  if isinstance(a, dict)}
        for k in ("last.pt", "best.pt"):
            want = (ckpt.get("checkpoint_sha256") or {}).get(k)
            anchored[k] = (want in by_sha) if want else None
    f["checkpoint_bytes_anchored"] = anchored if artifacts is not None else None
    sha_hex_ok = all(
        isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)
        for v in (ckpt.get("checkpoint_sha256") or {}).values() if v is not None)
    st = ckpt.get("stages") or {}
    sc = ckpt.get("state_classes") or {}

    # --- HARDENING 1: fail-closed on missing key epoch facts -----------------
    missing_facts = [k for k in G5_REQUIRED_EPOCH_FACTS if st.get(k) is None]
    f["missing_epoch_facts"] = missing_facts
    if missing_facts:
        return _gate("G5", False, f,
                     f"EPOCH_FACTS_MISSING (fail-closed): {missing_facts}")

    total = st.get("total_epochs")
    # --- HARDENING 2: epoch continuity recomputed STRICTLY -------------------
    f["epoch_continuity_recomputed"] = (
        st.get("last_epoch_value") == total
        and (st.get("final_epoch_rows") or 0) > (st.get("rows_at_kill") or 0)
        and st.get("resume_exit") == 0)
    if f["epoch_continuity_recomputed"] is not True:
        return _gate("G5", False, f, "EPOCH_CONTINUITY_NOT_RECOMPUTABLE "
                     f"(recomputed={f['epoch_continuity_recomputed']}; stored "
                     f"epoch_continuity={st.get('epoch_continuity')!r} is never "
                     "authority)")

    f.update({
        "pass_fail_skip": ckpt.get("pass_fail_skip"),
        "checkpoint_resumable": st.get("checkpoint_resumability"),
        "resume_exit": st.get("resume_exit"),
        "resume_done_marker": st.get("resume_done_marker"),
        "epoch_continuity": st.get("epoch_continuity"),
        "final_epoch_rows": st.get("final_epoch_rows"),
        "last_epoch_value": st.get("last_epoch_value"),
        "infer_exit": st.get("infer_exit"), "infer_ok": st.get("infer_ok"),
        "checkpoint_sha256": ckpt.get("checkpoint_sha256"),
        "ckpt_sha_at_kill": st.get("checkpoint_sha256_at_kill"),
        "gfx_target": ckpt.get("gfx_target"),
        "resume_semantics": ckpt.get("resume_semantics"),
        "resume_effective_updates": st.get("resume_effective_updates"),
        "optimizer_state_entries_after_resume": st.get("optimizer_state_entries"),
        "state_classes": sc,
    })
    resumable = st.get("checkpoint_resumability") or {}
    core_ok = (
        ckpt.get("pass_fail_skip") == "PASS"
        and resumable.get("has_optimizer_state") is True
        and st.get("resume_exit") == 0
        and st.get("resume_done_marker") is True
        and st.get("epoch_continuity") is True
        and st.get("resume_start_epoch") is not None
        and st.get("resume_start_epoch") < total
        and st.get("infer_ok") is True and st.get("infer_exit") == 0
        and (st.get("last_epoch_value") or 0) >= 3
        and bool(ckpt.get("checkpoint_sha256")) and sha_hex_ok
        and all(v is not False for v in anchored.values())
        and ckpt.get("gfx_target") == frozen["gfx_target"]
        and (st.get("resume_effective_updates") or 0) > 0
        and (st.get("optimizer_state_entries") or 0) > 0
    )
    # --- HARDENING 3: FULL restore requires an ACTUALLY serialized AND
    # restored scheduler; NOT_SERIALIZED_BY_UPSTREAM caps at CORE_STATE ------
    serialized = {k: (v or {}).get("serialized") for k, v in sc.items()
                  if isinstance(v, dict)}
    others = ("model_weights", "optimizer", "epoch", "best_fitness",
              "trainer_args", "gradscaler")
    f["not_serialized_classes"] = {k: v for k, v in serialized.items()
                                   if v == "NOT_SERIALIZED_BY_UPSTREAM"}
    scheduler_state = serialized.get("scheduler")
    f["scheduler_serialization"] = scheduler_state
    if not core_ok:
        state_verdict = "RESUME_INCOMPLETE"
    elif scheduler_state is True and all(serialized.get(k) is True for k in others):
        state_verdict = "FULL_TRAINING_STATE_RESTORE_PASS"
    else:
        state_verdict = "RESUME_PASS_CORE_STATE_VERIFIED"
        f["full_restore_blocked_because"] = (
            f"scheduler serialization state = {scheduler_state!r}; full "
            "training-state restore is unprovable and NOT claimed")
    f["state_verdict"] = state_verdict
    ok = core_ok and state_verdict in (
        "FULL_TRAINING_STATE_RESTORE_PASS", "RESUME_PASS_CORE_STATE_VERIFIED")
    reason = ("NIGHTLY_CHECKPOINT_RESUME_PASS — core resume verified; "
              + "; ".join(f"{k}: {v}" for k, v in f["not_serialized_classes"].items())
              ) if ok else "checkpoint save/resume/reload facts incomplete"
    return _gate("G5", ok, f, reason)


# ================================================================ G7 (hardened)
def _recompute_snapshot(tree: list[dict]) -> dict:
    """Recompute trainer/worker identity from ONE raw python_tree snapshot."""
    audits = [p for p in tree if "audit_adamw_amp" in (p.get("cmdline") or "")]
    trainer = None
    if audits:
        deepest = [p for p in audits
                   if not any((q.get("ppid") == p.get("pid")) for q in audits)]
        trainer = (deepest[0] if deepest else audits[0])
    if trainer is None:
        return {"trainer_pid": None, "workers": [], "spawn_workers": [],
                "non_spawn_children": []}
    tpid = trainer.get("pid")
    workers = [p for p in tree if p.get("ppid") == tpid]
    spawn_workers = [p for p in workers
                     if "spawn_main" in (p.get("cmdline") or "")]
    non_spawn = [p.get("pid") for p in workers
                 if "spawn_main" not in (p.get("cmdline") or "")]
    return {
        "trainer_pid": tpid,
        "workers": [{"pid": p.get("pid"), "ppid": p.get("ppid"),
                     "spawn_main": "spawn_main" in (p.get("cmdline") or "")}
                    for p in workers],
        "spawn_workers": [{"pid": p.get("pid"), "ppid": p.get("ppid")}
                          for p in spawn_workers],
        "non_spawn_children": non_spawn,
    }


def evaluate_g7_hardened(profile: dict, rel, supp, orphan, trainer_receipt) -> dict:
    frozen = profile["frozen"]
    if trainer_receipt and isinstance(trainer_receipt, dict) \
            and "envelope" not in trainer_receipt:
        trainer_receipt = {"envelope": {
            "child_pid": trainer_receipt.get("child_pid")
            or trainer_receipt.get("trainer_pid")}}
    f: dict = {"present": rel is not None}
    if not rel:
        return _gate("G7", False, f, "missing workers exercise evidence")
    tc = rel.get("training_counts") or {}
    per_step = tc.get("per_step_events") or []
    r = _recompute_step_statistics(
        per_step, (rel.get("gradscaler") or {}).get("scale_history") or [])
    f.update({
        "harness_train_args": rel.get("harness_train_args"),
        "exit_code": rel.get("exit_code"),
        "recomputed_stats": r,
        "census_present": supp is not None, "orphan_present": orphan is not None,
    })

    # --- HARDENING: recompute worker identity from RAW snapshots -------------
    if not supp or not (supp.get("snapshots") or []):
        return _gate("G7", False, f,
                     "fail-closed: no raw python_tree snapshots recorded — "
                     "worker identity cannot be recomputed")
    per_snap = []
    for snap in supp.get("snapshots") or []:
        rc = _recompute_snapshot(snap.get("python_tree") or [])
        rc["captured_utc"] = snap.get("captured_utc")
        per_snap.append(rc)
    peak = max(per_snap, key=lambda s: len(s["spawn_workers"]))
    f["snapshots_recomputed"] = [
        {"captured_utc": s["captured_utc"], "trainer_pid": s["trainer_pid"],
         "children": len(s["workers"]),
         "spawn_workers": len(s["spawn_workers"])} for s in per_snap]
    f["peak_snapshot_utc"] = peak["captured_utc"]
    f["peak_trainer_pid_recomputed"] = peak["trainer_pid"]
    f["peak_spawn_worker_pids"] = [w["pid"] for w in peak["spawn_workers"]]
    f["peak_non_spawn_children"] = peak["non_spawn_children"]
    # every counted worker: PPID == trainer (recomputed) + spawn_main cmdline
    f["all_workers_ppid_ok"] = all(
        w["ppid"] == peak["trainer_pid"] for w in peak["spawn_workers"])
    f["all_workers_spawn_main"] = all(
        w["spawn_main"] for w in peak["workers"]
        if w["pid"] in {x["pid"] for x in peak["spawn_workers"]})
    pids = [w["pid"] for w in peak["spawn_workers"]]
    f["worker_pids_distinct"] = len(set(pids)) == len(pids) and len(pids) >= 8
    # stored list DIFFED (never authority)
    stored_kids = supp.get("spawn_children_of_trainer") or []
    f["stored_spawn_children"] = stored_kids
    f["stored_list_matches_peak_snapshot"] = (
        sorted(x for x in stored_kids) ==
        sorted(w["pid"] for w in peak["spawn_workers"]))
    # trainer identity cross-checks
    trainer_pid_stored = supp.get("trainer_pid")
    f["trainer_pid_stored"] = trainer_pid_stored
    f["trainer_pid_stored_matches_recomputed"] = (
        trainer_pid_stored == peak["trainer_pid"])
    env_pid = ((trainer_receipt or {}).get("envelope") or {}).get("child_pid")
    f["envelope_child_pid"] = env_pid
    ppid_of = {}
    for s in (supp.get("snapshots") or []):
        for p in s.get("python_tree") or []:
            ppid_of[p.get("pid")] = p.get("ppid")
    chain = [peak["trainer_pid"]]
    cur = peak["trainer_pid"]
    cycle = False
    while cur in ppid_of and ppid_of.get(cur) is not None:
        cur = ppid_of[cur]
        if cur in chain:  # adversarial cyclic parentage — terminate honestly
            cycle = True
            break
        chain.append(cur)
    f["trainer_ancestry_chain"] = chain
    f["trainer_ancestry_cycle_detected"] = cycle
    f["trainer_pid_ties_to_envelope"] = (
        env_pid is None or env_pid == peak["trainer_pid"] or env_pid in chain)
    census_ok = (
        f["all_workers_ppid_ok"] and f["all_workers_spawn_main"]
        and f["worker_pids_distinct"]
        and f["trainer_pid_stored_matches_recomputed"]
        and f["trainer_pid_ties_to_envelope"])

    # --- orphan recomputation (baseline required — fail-closed) --------------
    leftover_recomputed: list | None = None
    if orphan:
        all_pids = orphan.get("all_python_pids") or []
        baseline = (supp or {}).get("preexisting_zombies_disclosed") or []
        checker = orphan.get("checker_pid")
        f["orphan_baseline_present"] = supp is not None \
            and "preexisting_zombies_disclosed" in (supp or {})
        f["orphan_checker_pid"] = checker
        if checker is None:
            return _gate("G7", False, f,
                         "fail-closed: orphan checker pid missing")
        leftover_recomputed = [p for p in all_pids
                               if p not in baseline and p != checker]
        f.update({"orphan_all_pids": all_pids,
                  "leftover_recomputed": leftover_recomputed,
                  "stored_mission_tree_leftover": orphan.get("mission_tree_leftover"),
                  "stored_verdict_diffed": orphan.get("orphan_verdict")})
    clean = bool(orphan) and leftover_recomputed == []
    workers8 = "workers=8" in str(rel.get("harness_train_args"))
    train_ok = (
        rel.get("exit_code") == 0
        and rel.get("pass_fail_skip") == "ADAMW_AMP_MULTISTEP_PASS"
        and (tc.get("batches_completed") or 0) > 0
        and r["effective_updates"] > 0
        and not r["unexplained_no_update_steps"]
    )
    ok = workers8 and train_ok and census_ok and clean
    return _gate("G7", ok, f,
                 "bounded workers=8 exercise verified from raw snapshot "
                 "recomputation (PID/PPID/spawn_main per worker, single-"
                 "snapshot coexistence) + recomputed orphan check" if ok
                 else "workers exercise incomplete (raw-snapshot recomputation "
                      "failed)")


# ================================================================ derive
def scan_forbidden_verdicts(evidence_root: Path) -> list[str]:
    hits = []
    for p in evidence_root.rglob("*.json"):
        try:
            txt = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for v in FORBIDDEN_VERDICTS:
            if re.search(rf'"{v}"', txt):
                hits.append(f"{p.relative_to(evidence_root)}:{v}")
    return hits


def derive(profile: dict, gates: list[dict], forbidden: list[str]) -> dict:
    by = {g["gate"]: g["verdict"] for g in gates}
    ceiling = profile["ceiling"]
    if forbidden:
        overall = "NIGHTLY_NO_GO"
        reason = f"forbidden Stable verdict present in evidence: {forbidden}"
    elif all(v == "PASS" for v in by.values()):
        overall = ceiling
        reason = (f"all gates independently recomputed PASS on physical "
                  f"{profile['frozen']['gfx_target']} with audited nightly "
                  f"bytes and byte-bound lock provenance")
    elif by.get("G1") == "PASS":
        overall = "NIGHTLY_PARTIAL_PASS"
        reason = "G1 proven independently; downstream gates incomplete"
    else:
        overall = "NIGHTLY_NO_GO"
        reason = "G1 not established"
    return {"overall": overall, "reason": reason, "gate_verdicts": by,
            "ceiling": ceiling,
            "forbidden_verdict_hits": forbidden,
            "note": "nightly artifacts cap at candidate-level verdicts; no "
                    "Stable/dual-arch/clean-install claim is possible from "
                    "this single-GPU nightly mission"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--profile", default="gfx1100",
                    choices=["gfx1100", "gfx1151"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    profile = get_profile(args.profile)
    root = Path(args.evidence_root)
    repo = Path(args.repo_root)
    p = profile.get("paths", {})
    lock_path = root / p.get("lock", "01_package_provenance/"
                                        "resolved_wheel_lock_nightly_gfx1100.json")
    lock = _j(lock_path)
    audit = _j(root / p.get("wheel_audit",
                            "01_package_provenance/wheel_audit_gfx1100.json"))
    manifest = _j(root / p.get("manifest",
                               "01_package_provenance/installed_manifest.json"))
    g0 = _j(root / p.get("g0", "02_runtime_identity/g0_child_identity.json"))
    trials = [_j(root / c) for c in p.get("candidates",
               ["03_nostl_candidate/nostl_candidate_trial1.json",
                "03_nostl_candidate/nostl_candidate_trial2.json"])]
    trial_logs = [_log_text(root / c) for c in p.get("candidate_logs",
                  ["03_nostl_candidate/raw/candidate_trial1_leg.log",
                   "03_nostl_candidate/raw/candidate_trial2_leg.log"])]
    ctrl = _j(root / p.get("control",
                           "04_nostl_negative_control/nostl_prefit_control.json"))
    ctrl_log = _log_text(root / p.get("control_log",
                         "04_nostl_negative_control/raw/negctrl_leg.log"))
    ops = _j(root / p.get("ops", "05_gpu_primitives/torchvision_ops.json"))
    amp = _j(root / p.get("amp", "06_yolo_training_amp/adamw_amp.json"))
    ckpt = _j(root / p.get("ckpt", "07_checkpoint_resume/checkpoint_resume.json"))
    ckpt_env = _j(root / p.get("ckpt_envelope",
                               "07_checkpoint_resume/lifecycle_envelope.json"))
    rel = _j(root / p.get("workers_rel",
                          "08_workers_reliability/workers8_amp_v2.json"))
    supp = _j(root / p.get("workers_census",
                           "08_workers_reliability/workers8_midrun_census.json"))
    orphan = _j(root / p.get("workers_orphan",
                             "08_workers_reliability/workers8_postrun_orphan_check.json"))
    rel_env = _j(root / p.get("workers_envelope",
                              "08_workers_reliability/workers8_envelope.json"))

    training_receipts = [
        (n, rr) for n, rr in (
            ("06_yolo_training_amp/adamw_amp.json", amp),
            ("08_workers_reliability/workers8_amp_v2.json", rel),
        ) if rr is not None
    ]
    gates = [evaluate_pkg(profile, lock, audit, manifest),
             evaluate_lk(profile, training_receipts, lock_path),
             evaluate_g0(profile, g0),
             evaluate_g1(profile, trials, ctrl, trial_logs, ctrl_log),
             evaluate_g2(profile, ops),
             *evaluate_g34(profile, amp),
             evaluate_g5_hardened(profile, ckpt,
                                  (ckpt_env or {}).get("artifact_hashes")),
             evaluate_g7_hardened(profile, rel, supp, orphan, rel_env)]
    forbidden = scan_forbidden_verdicts(root)
    result = derive(profile, gates, forbidden)
    result.update({
        "run_id": args.run_id,
        "mission": "R22A.5N gfx1100 Official Nightly Physical Prequalification",
        "mission_id": profile["mission_id"],
        "engine_version": "r22a5n1100-acceptance-v1",
        "profile": profile["profile_name"],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "evidence_root": str(root), "gates": gates,
        "reliability_census": supp, "reliability_orphan_check": orphan,
        "frozen_candidate": profile["frozen"],
        "g5_g7_hardening": ("R22A.5N.2-style fail-closed closure applied in this "
                            "engine (not present in PR #22 HEAD 568981d); "
                            "dependency on PR #22 recorded in the mission report"),
    })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OVERALL: {result['overall']} — {result['reason']}")
    for g in gates:
        print(f"  {g['gate']:4s} {g['verdict']:4s} {g['reason'][:110]}")
    sys.exit(0 if result["overall"] == profile["ceiling"] else 3)


if __name__ == "__main__":
    main()
