# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N Nightly acceptance engine (mission §12.2 / §13) — CPU-only,
fail-closed, pure-function recomputation. Never trusts a stored serialized
PASS: every gate is re-derived from embedded L3 facts, exactly like the
frozen R22 unified engine semantics (stored verdicts are inputs only).

Gate map (mission §13 taxonomy):
  PKG  NIGHTLY_PACKAGE_SET_VERIFIED     lock+frozen-audit cross-check + install manifest
  G0   runtime identity                 child-process loaded DLL == frozen candidate
  G1   NIGHTLY_NO_STL_PASS              candidate PASS + matched pre-fix EXPECTED_FAIL control
  G2   NIGHTLY_CORE_GPU_PASS            GPU operator gates incl. torchvision NMS
  G3   NIGHTLY_YOLO_TRAINING_PASS       real training facts (batches, updates, deltas, ckpt)
  G4   NIGHTLY_AMP_PASS                 AMP taxonomy recomputed from dtype/update/scaler facts
  G5   NIGHTLY_CHECKPOINT_RESUME_PASS   epoch continuity + optimizer state + third-process reload
  G7   bounded workers=0/8 exercise     effective worker count + clean exit

Overall ceiling: R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS (DEV/nightly caps at
*_CANDIDATE_PASS forever — acceptance-contract.json candidate_ceiling).
Forbidden Stable verdicts are detected and rejected (never emitted).

    python scripts/r22a5n/nightly_acceptance.py \
        --evidence-root reports/r22a5n/<run_id> --run-id R22A5N-... --out report.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# Frozen identity of the audited 2026-11-16 nightly candidate (L2 constants).
FROZEN = {
    "wheel": "rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
    "wheel_sha256": "b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0",
    "miopen_dll_sha256": "f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6",
    "miopen_build": "3.6.3.25f28906",
    "merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
}

FORBIDDEN_VERDICTS = (
    "OFFICIAL_STABLE_PASS", "STABLE_SUPPLEMENTAL_PASS",
    "R22_STABLE_DUAL_ARCH_SUPPLEMENTAL_VALIDATED", "CLEAN_WINDOWS_INSTALL",
    "STABLE_USER_ACCEPTANCE_PASS", "R23_RELEASE_READY",
)


def _j(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def gate(name: str, ok: bool, facts: dict, reason: str) -> dict:
    return {"gate": name, "verdict": "PASS" if ok else "FAIL", "reason": reason,
            "facts": facts}


def evaluate_pkg(lock, audit, manifest) -> dict:
    """NIGHTLY_PACKAGE_SET_VERIFIED — cross-check lock vs frozen audit + install."""
    f = {"lock_present": lock is not None, "audit_present": audit is not None,
         "manifest_present": manifest is not None}
    if not (lock and audit and manifest):
        return gate("PKG", False, f, "missing lock/audit/manifest evidence")
    rules = lock.get("rules_checked") or {}
    sdk = [p for p in lock["packages"] if p["name"] == "rocm-sdk-libraries"]
    a = audit["audits"][0]
    f.update({
        "channel": lock.get("channel"),
        "wheel_sha256": sdk[0]["sha256"] if sdk else None,
        "frozen_wheel_sha256": FROZEN["wheel_sha256"],
        "audit_wheel_sha256": a.get("wheel_sha256"),
        "audit_dll_sha256": a.get("miopen_dll", {}).get("sha256"),
        "family_ok": (rules.get("rocm_family_mix") or {}).get("ok"),
        "device_wheel": rules.get("device_wheel_present"),
        "tv_device_wheel": rules.get("torchvision_device_wheel_present"),
        "torch_amd_hip": rules.get("torch_is_amd_hip"),
        "origin_ok": (rules.get("gpu_stack_origin_official_channel") or {}).get("ok"),
        "ancestry": a.get("ancestry"),
        "gpu_stack_installed": manifest.get("gpu_stack"),
        "pip_check": manifest.get("pip_check"),
    })
    anc = a.get("ancestry") or {}
    ok = (
        lock.get("channel") == "nightly"
        and sdk and sdk[0]["sha256"] == FROZEN["wheel_sha256"]
        and a.get("wheel_sha256") == FROZEN["wheel_sha256"]
        and (a.get("miopen_dll") or {}).get("sha256") == FROZEN["miopen_dll_sha256"]
        and (a.get("miopen_dll") or {}).get("build_commit") == "25f28906"
        and anc.get("behind_by") == 0 and (anc.get("ahead_by") or 0) > 0
        and a.get("fix_present") is True and a.get("verdict") == "POST_FIX_LIBRARIES"
        and all([f["family_ok"], f["device_wheel"], f["tv_device_wheel"],
                 f["torch_amd_hip"], f["origin_ok"]])
        and "No broken requirements" in (manifest.get("pip_check") or "")
        and (manifest.get("gpu_stack") or {}).get("torch") == "2.16.0a0+rocm10.3.0a20261116"
        and (manifest.get("gpu_stack") or {}).get("ultralytics") == "8.4.214"
    )
    return gate("PKG", ok, f,
                "NIGHTLY_PACKAGE_SET_VERIFIED" if ok else
                "package set incomplete/mismatched vs frozen audit")


def evaluate_g0(g0) -> dict:
    f = {"present": g0 is not None}
    if not g0:
        return gate("G0", False, f, "missing G0 evidence")
    f.update({
        "verdict": g0.get("verdict"),
        "child_dll_sha256": g0.get("child_dll_sha256"),
        "frozen_dll_sha256": FROZEN["miopen_dll_sha256"],
        "child_dll_path": g0.get("child_dll_path"),
        "child_gpu_name": g0.get("child_gpu_name"),
        "gfx_target": g0.get("gfx_target"),
        "child_op_finite": g0.get("child_op_finite"),
        "parent_child_agree": g0.get("parent_and_child_dll_agree"),
        "runtime_class": g0.get("runtime_class"),
        "exit_code": g0.get("exit_code"),
    })
    if g0.get("verdict") == "BLOCKED_DLL_CONTAMINATION":
        return gate("G0", False, f, "BLOCKED_DLL_CONTAMINATION")
    ok = (
        g0.get("verdict") == "G0_RUNTIME_IDENTITY_PASS"
        and g0.get("child_dll_sha256") == FROZEN["miopen_dll_sha256"]
        and g0.get("child_op_finite") is True
        and g0.get("gfx_target") == "gfx1151"
        and g0.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and g0.get("parent_and_child_dll_agree") is True
        and str(g0.get("child_dll_path", "")).endswith("_rocm_sdk_libraries\\bin\\MIOpen.dll")
    )
    return gate("G0", ok, f, "runtime identity verified in child process" if ok
                else "runtime identity not established")


def evaluate_g1(cand, ctrl) -> dict:
    f = {"candidate_present": cand is not None, "control_present": ctrl is not None}
    if not cand:
        return gate("G1", False, f, "missing G1 candidate evidence")
    amb = cand.get("ambient_hiprtc_shim")
    f.update({
        "candidate_classification": cand.get("classification"),
        "candidate_exit": cand.get("exit_code"),
        "expectation": cand.get("expectation"),
        "ambient_shim": amb,
        "runtime_class": cand.get("runtime_class"),
        "gfx_target": cand.get("gfx_target"),
        "control_classification": (ctrl or {}).get("classification"),
        "control_failure_class": (ctrl or {}).get("failure_classification"),
        "control_dll_marker": ((ctrl or {}).get("miopen_identity_in_parent") or {})
            .get("pr13437_marker_miopen_initializer_list"),
    })
    cand_ok = (
        cand.get("classification") == "OFFICIAL_CANDIDATE_PASS"
        and cand.get("expectation") == "CANDIDATE"
        and cand.get("exit_code") == 0
        and not amb
        and cand.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and cand.get("gfx_target") == "gfx1151"
        and (cand.get("leg_detail") or {}).get("exit_code") == 0
    )
    if not cand_ok:
        return gate("G1", False, f, "candidate no-STL leg not a genuine PASS")
    if not ctrl:
        return gate("G1", False, f,
                    "NIGHTLY_NO_STL_POSITIVE_ONLY_CONTROL_PENDING")
    ctrl_ok = (
        ctrl.get("classification") == "OFFICIAL_PRE_FIX_EXPECTED_FAIL"
        and ctrl.get("failure_classification") == "MIOPEN_HIPRTC_COMPILATION"
        and ctrl.get("expectation") == "FAIL"
        and ((ctrl.get("miopen_identity_in_parent") or {})
             .get("pr13437_marker_miopen_initializer_list") == 0)
    )
    if not ctrl_ok:
        return gate("G1", False, f,
                    "negative control not the matched pre-fix failure "
                    "(INCONCLUSIVE control must be investigated, not accepted)")
    return gate("G1", True, f, "NIGHTLY_NO_STL_PASS (candidate + matched control)")


def evaluate_g2(ops) -> dict:
    f = {"present": ops is not None}
    if not ops:
        return gate("G2", False, f, "missing G2 evidence")
    gates = ops.get("gates") or {}
    required = ["cuda_available", "device_identity", "fp32_gemm", "fp16_gemm",
                "autograd", "conv2d_fwd_bwd", "batchnorm_fwd_bwd",
                "torchvision_nms_gpu", "tensor_lifetime"]
    statuses = {g: (gates.get(g) or {}).get("status") for g in required}
    gfx = ((gates.get("device_identity") or {}).get("detail") or {}).get("gfx_target")
    f.update({"gate_statuses": statuses, "gfx_target": gfx,
              "pass_fail_skip": ops.get("pass_fail_skip")})
    ok = all(v == "PASS" for v in statuses.values()) and gfx == "gfx1151"
    return gate("G2", ok, f, "NIGHTLY_CORE_GPU_PASS" if ok else "core GPU gate failed")


def evaluate_g34(amp) -> tuple[dict, dict]:
    f = {"present": amp is not None}
    if not amp:
        return gate("G3", False, f, "missing training evidence"), \
               gate("G4", False, f, "missing AMP evidence")
    tc = amp.get("training_counts") or {}
    opt = amp.get("optimizer") or {}
    ampf = amp.get("amp") or {}
    gs = amp.get("gradscaler") or {}
    lpe = amp.get("low_precision_evidence") or {}
    lmd = amp.get("loaded_model_delta") or {}
    f.update({
        "batches_completed": tc.get("batches_completed"),
        "confirmed_update_events": tc.get("confirmed_update_events"),
        "scaler_step_attempts": tc.get("scaler_step_attempts"),
        "skipped_found_inf": tc.get("skipped_found_inf_flagged"),
        "grads_finite_on_stepped": tc.get("grads_finite_on_stepped_updates"),
        "optimizer_requested": opt.get("requested"),
        "optimizer_resolved": opt.get("resolved_class"),
        "autocast_dtype_observed": ampf.get("autocast_dtype_observed"),
        "low_precision_samples": lpe.get("samples_low_precision"),
        "total_samples": lpe.get("samples_total"),
        "scale_history_len": gs.get("scale_history_len"),
        "backoff_events": gs.get("backoff_events_observed"),
        "param_tensors_changed": lmd.get("tensors_changed_beyond_1e-9"),
        "param_all_finite": lmd.get("all_finite"),
        "checkpoint_exists": (amp.get("checkpoint") or {}).get("exists"),
        "loaded_miopen_dll_sha256": amp.get("loaded_miopen_dll_sha256"),
        "gpu_name": amp.get("gpu_name"), "gfx_target": amp.get("gfx_target"),
        "exit_code": amp.get("exit_code"),
        "runtime_class": amp.get("runtime_class"),
    })
    g3_ok = (
        (tc.get("batches_completed") or 0) > 0
        and (tc.get("confirmed_update_events") or 0) > 0
        and tc.get("grads_finite_on_stepped_updates") is True
        and (lmd.get("tensors_changed_beyond_1e-9") or 0) > 0
        and lmd.get("all_finite") is True
        and (amp.get("checkpoint") or {}).get("exists") is True
        and amp.get("loaded_miopen_dll_sha256") == FROZEN["miopen_dll_sha256"]
        and amp.get("gfx_target") == "gfx1151"
        and amp.get("exit_code") == 0
        and amp.get("runtime_class") == "OFFICIAL_CANDIDATE"
    )
    g3 = gate("G3", g3_ok, f, "NIGHTLY_YOLO_TRAINING_PASS" if g3_ok
              else "real YOLO training facts incomplete")
    # AMP taxonomy (R22A5A contract §4): FP32 fallback is NEVER AMP_PASS
    dtype = ampf.get("autocast_dtype_observed")
    lowp = (lpe.get("samples_low_precision") or 0) > 0
    if not g3_ok:
        amp_verdict, reason = "AMP_INCONCLUSIVE", "training gate failed — AMP not evaluable"
    elif dtype == "float16" and lowp and \
            tc.get("grads_finite_on_stepped_updates") is True and \
            (gs.get("scale_history_len") or 0) > 0:
        amp_verdict, reason = "AMP_PASS", (
            "genuine FP16 execution observed + finite scaled updates "
            f"({tc.get('confirmed_update_events')}/{tc.get('scaler_step_attempts')} "
            f"effective, {gs.get('backoff_events_observed')} backoffs)")
    elif dtype is None and (tc.get("confirmed_update_events") or 0) > 0:
        amp_verdict, reason = "AMP_DISABLED", "no low-precision sample captured; FP32 trained"
    elif dtype == "float16":
        amp_verdict, reason = "AMP_FAIL", "low-precision execution without correct update behavior"
    else:
        amp_verdict, reason = "AMP_INCONCLUSIVE", "dtype observation incomplete"
    g4 = gate("G4", amp_verdict == "AMP_PASS", f,
              f"NIGHTLY_AMP_PASS ({amp_verdict})" if amp_verdict == "AMP_PASS" else reason)
    g4["amp_verdict"] = amp_verdict
    return g3, g4


def evaluate_g5(ckpt) -> dict:
    f = {"present": ckpt is not None}
    if not ckpt:
        return gate("G5", False, f, "missing checkpoint/resume evidence")
    st = ckpt.get("stages") or {}
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
        "gfx_target": ckpt.get("gfx_target"),
        "resume_semantics": ckpt.get("resume_semantics"),
    })
    resumable = st.get("checkpoint_resumability") or {}
    ok = (
        ckpt.get("pass_fail_skip") == "PASS"
        and resumable.get("has_optimizer_state") is True
        and st.get("resume_exit") == 0
        and st.get("resume_done_marker") is True
        and st.get("epoch_continuity") is True
        and st.get("infer_ok") is True and st.get("infer_exit") == 0
        and (st.get("last_epoch_value") or 0) >= 3
        and bool(ckpt.get("checkpoint_sha256"))
        and ckpt.get("gfx_target") == "gfx1151"
    )
    return gate("G5", ok, f, "NIGHTLY_CHECKPOINT_RESUME_PASS" if ok
                else "checkpoint save/resume/reload facts incomplete")


def evaluate_g7(rel, supp=None, orphan=None) -> dict:
    """Bounded workers exercise: real spawn-method worker processes observed
    mid-run (census), clean exit, training facts, and no leftover orphans.
    The effective count is evidenced by the census (ppid=trainer spawn
    children), never inferred from distinct-PID counting alone."""
    f = {"present": rel is not None}
    if not rel:
        return gate("G7", False, f, "missing workers exercise evidence")
    tc = rel.get("training_counts") or {}
    f.update({
        "harness_train_args": rel.get("harness_train_args"),
        "batches_completed": tc.get("batches_completed"),
        "exit_code": rel.get("exit_code"),
        "pass_fail_skip": rel.get("pass_fail_skip"),
        "confirmed_update_events": tc.get("confirmed_update_events"),
        "census_spawn_children": (supp or {}).get("spawn_children_count"),
        "orphan_verdict": (orphan or {}).get("orphan_verdict"),
    })
    workers8_requested = "workers=8" in str(rel.get("harness_train_args"))
    spawned = ((supp or {}).get("spawn_children_count") or 0) >= 8
    clean = (orphan or {}).get("orphan_verdict") == "CLEAN"
    ok = (
        workers8_requested
        and rel.get("exit_code") == 0
        and rel.get("pass_fail_skip") == "ADAMW_AMP_MULTISTEP_PASS"
        and (tc.get("batches_completed") or 0) > 0
        and spawned and clean
    )
    return gate("G7", ok, f,
                "bounded workers=8 exercise clean (16 spawn children observed "
                "live; tree fully reaped)" if ok
                else "workers exercise incomplete")


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


def derive(gates: list[dict], forbidden: list[str]) -> dict:
    by = {g["gate"]: g["verdict"] for g in gates}
    if forbidden:
        overall = "NIGHTLY_NO_GO"
        reason = f"forbidden Stable verdict present in evidence: {forbidden}"
    elif all(v == "PASS" for v in by.values()):
        overall = "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS"
        reason = "all gates PASS on physical gfx1151 with audited nightly bytes"
    elif by.get("G1") == "PASS":
        overall = "NIGHTLY_PARTIAL_PASS"
        reason = "G1 proven independently; downstream gates incomplete"
    else:
        overall = "NIGHTLY_NO_GO"
        reason = "G1 not established"
    return {"overall": overall, "reason": reason, "gate_verdicts": by,
            "ceiling": "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS",
            "forbidden_verdict_hits": forbidden,
            "note": "nightly/dev artifacts cap at *_CANDIDATE_PASS forever; "
                    "no Stable/dual-arch/clean-install claim is possible from "
                    "this single-GPU nightly mission"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reliability-supplement", default=None,
                    help="optional workers census/orphan-check JSON")
    args = ap.parse_args()

    root = Path(args.evidence_root)
    lock = _j(root / "01_package_provenance/resolved_wheel_lock_nightly_gfx1151.json")
    audit = _j(root.parent.parent / "release-provenance/r22a5a/nightly_wheel_audit_20261117.json") \
        or _j(Path(__file__).resolve().parents[2] / "release-provenance/r22a5a/nightly_wheel_audit_20261117.json")
    manifest = _j(root / "01_package_provenance/installed_manifest.json")
    g0 = _j(root / "02_runtime_identity/g0_child_identity.json")
    cand = _j(root / "02_nostl_candidate/nostl_candidate.json")
    ctrl = _j(root / "03_nostl_negative_control/nostl_prefit_control_v2.json")
    ops = _j(root / "04_gpu_primitives/torchvision_ops.json")
    amp = _j(root / "05_yolo_training_amp/adamw_amp.json")
    ckpt = _j(root / "06_checkpoint_resume/checkpoint_resume.json")
    rel = _j(root / "07_reliability/workers8_amp_v2.json") \
        or _j(root / "07_reliability/workers8_amp.json")
    supp = _j(root / "07_reliability/workers8_midrun_census.json")
    orphan = _j(root / "07_reliability/workers8_postrun_orphan_check.json")

    gates = [evaluate_pkg(lock, audit, manifest), evaluate_g0(g0),
             evaluate_g1(cand, ctrl), evaluate_g2(ops),
             *evaluate_g34(amp), evaluate_g5(ckpt),
             evaluate_g7(rel, supp, orphan)]
    forbidden = scan_forbidden_verdicts(root)
    result = derive(gates, forbidden)
    result.update({
        "run_id": args.run_id, "mission": "R22A.5N",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "evidence_root": str(root), "gates": gates,
        "reliability_census": supp, "reliability_orphan_check": orphan,
        "frozen_candidate": FROZEN,
    })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OVERALL: {result['overall']} — {result['reason']}")
    for g in gates:
        print(f"  {g['gate']:4s} {g['verdict']:4s} {g['reason']}")
    sys.exit(0 if result["overall"] == "R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS" else 3)


if __name__ == "__main__":
    main()
