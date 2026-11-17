# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N.1 hardened Nightly acceptance engine (mission PHASE 3 §6) —
independent recomputation, fail-closed, CPU-only.

The R22A.5N engine (scripts/r22a5n/nightly_acceptance.py, kept untouched for
historical semantics) consumed stored summaries: `rules_checked.ok` booleans,
`training_counts` counters and `orphan_verdict=CLEAN` strings were authority.
This versioned engine eliminates every stored-summary trust boundary:

  PKG  source policy / family / device wheels / ABI / installed-vs-lock diff
       recomputed from the lock's OWN package records (gp_lib provenance
       functions — no duplicate resolver); `rules_checked` is only DIFFED
  LK   every training-family receipt's wheel-lock binding re-hashed and
       re-verified from the committed lock bytes (a copied hash string is
       not enough — this is the gate that catches the original P0-A defect)
  G0   child-process DLL + finite op, parent/child agreement
  G1   candidate + pre-fix control re-derived from leg facts AND raw log
       bytes: distinct PIDs, in-child DLL identity, cold-cache scratch
       identity, failure signature re-classified from stderr text
  G2   per-gate numeric detail finiteness re-checked (not just status strings)
  G3   AdamW statistics recomputed from per_step_events (ordering, found_inf,
       sentinel deltas, scale transitions) and reconciled with stored counters
  G4   AMP dtype evidence recomputed from the dtype histogram; FP32 fallback
       can never be AMP_PASS; fake scalar summaries detected via series length
  G5   resume core + state-class serialization depth (scheduler/scaler are
       NOT_SERIALIZED_BY_UPSTREAM by design — never claimed as restored)
  G7   worker parentage recomputed from census PID lists; orphan-cleanliness
       recomputed, never read from a stored verdict string

Overall ceiling: R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS.

    python scripts/r22a5n1/nightly_acceptance.py --evidence-root DIR \
        --repo-root REPO --run-id R22A5N1-... --out report.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "windows-golden-path" / "scripts"))
import gp_lib  # noqa: E402
import audit_adamw_amp as adamw_lib  # noqa: E402 — reuse the tested lock gate

# Frozen identity of the audited 2026-11-16 nightly candidate (L2 constants).
FROZEN = {
    "wheel": "rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
    "wheel_sha256": "b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0",
    "miopen_dll_sha256": "f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6",
    "miopen_build": "3.6.3.25f28906",
    "merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
    "torch": "2.16.0a0+rocm10.3.0a20261116",
    "ultralytics": "8.4.214",
    "gfx_target": "gfx1151",
    "channel": "nightly",
}

FORBIDDEN_VERDICTS = (
    "OFFICIAL_STABLE_PASS", "STABLE_SUPPLEMENTAL_PASS",
    "R22_STABLE_DUAL_ARCH_SUPPLEMENTAL_VALIDATED", "CLEAN_WINDOWS_INSTALL",
    "STABLE_USER_ACCEPTANCE_PASS", "R23_RELEASE_READY",
)

G2_GATES = ["cuda_available", "device_identity", "fp32_gemm", "fp16_gemm",
            "autograd", "conv2d_fwd_bwd", "batchnorm_fwd_bwd",
            "torchvision_nms_gpu", "tensor_lifetime"]


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


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


# ================================================================ PKG
def recompute_lock_rules(lock: dict) -> dict:
    """Recompute the package-set rules from the lock's OWN records.

    A serialized `rules_checked.ok=True` is never an input here — forging it
    changes nothing. Uses the proven gp_lib provenance functions (no duplicate
    resolver)."""
    pkgs = lock.get("packages") or []
    channel = lock.get("channel")
    gfx = lock.get("gfx_target")
    out: dict = {"package_count": len(pkgs), "channel": channel, "gfx_target": gfx}
    origins = [gp_lib.classify_package_origin(p.get("name"), p.get("version"),
                                              p.get("url"), p.get("sha256"), channel)
               for p in pkgs]
    out["origin_violations"] = [v for o in origins for v in o.get("violations", [])]
    out["origin_ok"] = not out["origin_violations"]
    native = [p for p in pkgs if gp_lib.is_native_amd_gpu_stack(p.get("name", ""))]
    fams = {f for f in (gp_lib.rocm_family_of(p.get("name", ""),
                                               p.get("version", ""))
                        for p in native) if f}
    out["native_families"] = sorted(fams)
    out["family_ok"] = len(fams) == 1
    names = {gp_lib.dist_key(p.get("name", "")): p for p in pkgs}
    dev = [f"rocm-sdk-device-{gfx}", f"amd-torch-device-{gfx}",
           f"amd-torchvision-device-{gfx}"]
    out["device_wheels_present"] = {d: d in names for d in dev}
    out["device_wheel_ok"] = all(out["device_wheels_present"].values())
    torch_rec = names.get("torch") or {}
    out["torch_is_amd_hip"] = gp_lib.torch_wheel_is_amd_hip(
        torch_rec.get("version", ""), torch_rec.get("url"))
    # ABI: platform-tagged wheels must carry a compatible python tag; native
    # AMD stack wheels must additionally be win_amd64. Third-party pure-Python
    # wheels are legitimately py3-none-any; abi3 wheels (cp37-abi3 etc.) are
    # forward-compatible; sdists (.tar.gz) have no tags to check.
    want_tag = (lock.get("python_tag") or "").lower()
    want_minor = int(want_tag[2:]) if want_tag.startswith("cp") and \
        want_tag[2:].isdigit() else None
    bad_abi = []
    for p in pkgs:
        fn = p.get("wheel_filename") or ""
        if not fn:
            continue
        if not fn.endswith(".whl"):
            continue  # sdist — ABI tags not applicable
        parsed = gp_lib.parse_wheel_filename(fn)
        if not parsed:
            bad_abi.append(f"{p.get('name')}: unparseable wheel filename {fn!r}")
            continue
        tag = parsed["python_tag"].lower()
        abi3_ok = False
        if parsed["abi_tag"] == "abi3" and tag.startswith("cp") \
                and tag[2:].isdigit() and want_minor is not None:
            abi3_ok = int(tag[2:]) <= want_minor
        if tag not in (want_tag, "py3", "py2.py3") and not abi3_ok:
            bad_abi.append(f"{p.get('name')}: python tag {parsed['python_tag']}"
                           f" incompatible with lock {want_tag}")
        if gp_lib.is_native_amd_gpu_stack(p.get("name", "")) \
                and not parsed["win_amd64"]:
            bad_abi.append(f"{p.get('name')}: not a win_amd64 wheel ({fn})")
    out["abi_violations"] = bad_abi
    out["abi_ok"] = not bad_abi
    sdk = names.get("rocm-sdk-libraries") or {}
    out["sdk_wheel_sha256"] = sdk.get("sha256")
    out["rules_checked_diff"] = {  # stored values DIFFED, never authority
        "stored_family_ok": ((lock.get("rules_checked") or {})
                             .get("rocm_family_mix") or {}).get("ok"),
        "stored_device_wheel": (lock.get("rules_checked") or {})
            .get("device_wheel_present"),
        "stored_origin_ok": ((lock.get("rules_checked") or {})
                             .get("gpu_stack_origin_official_channel") or {}).get("ok"),
    }
    return out


def evaluate_pkg(lock, audit, manifest) -> dict:
    f: dict = {"lock_present": lock is not None, "audit_present": audit is not None,
               "manifest_present": manifest is not None}
    if not (lock and audit and manifest):
        return gate("PKG", False, f, "missing lock/audit/manifest evidence")
    r = recompute_lock_rules(lock)
    a = (audit.get("audits") or [{}])[0]
    f.update({
        "recomputed": {k: v for k, v in r.items() if k != "rules_checked_diff"},
        "origin_violations": r["origin_violations"][:8],
        "abi_violations": r["abi_violations"][:8],
        "audit_wheel_sha256": a.get("wheel_sha256"),
        "audit_dll_sha256": (a.get("miopen_dll") or {}).get("sha256"),
        "audit_dll_build": (a.get("miopen_dll") or {}).get("build_commit"),
        "ancestry": a.get("ancestry"),
        "ancestry_recomputed": False,
        "ancestry_note": "externally recorded by the bounded gh audit; "
                         "consistency-checked only (wheel/DLL byte identity is "
                         "the load-bearing evidence)",
    })
    anc = a.get("ancestry") or {}
    # installed-vs-lock diff: every lock record must be installed at the exact
    # version; no native-stack dist may exist outside the lock
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
        lock.get("channel") == FROZEN["channel"]
        and lock.get("gfx_target") == FROZEN["gfx_target"]
        and r["origin_ok"] and r["family_ok"] and r["device_wheel_ok"]
        and r["torch_is_amd_hip"] and r["abi_ok"]
        and r["sdk_wheel_sha256"] == FROZEN["wheel_sha256"]
        and a.get("wheel_sha256") == FROZEN["wheel_sha256"]
        and (a.get("miopen_dll") or {}).get("sha256") == FROZEN["miopen_dll_sha256"]
        and (a.get("miopen_dll") or {}).get("build_commit") == "25f28906"
        and a.get("fix_present") is True and a.get("verdict") == "POST_FIX_LIBRARIES"
        and anc.get("behind_by") == 0 and (anc.get("ahead_by") or 0) > 0
        and not missing and not rogue_native
        and "No broken requirements" in (manifest.get("pip_check") or "")
        and gpu_stack.get("torch") == FROZEN["torch"]
        and gpu_stack.get("ultralytics") == FROZEN["ultralytics"]
    )
    return gate("PKG", ok, f,
                "NIGHTLY_PACKAGE_SET_VERIFIED (independently recomputed)" if ok
                else "package set failed independent recomputation")


# ================================================================ LK
def evaluate_lk(training_receipts: list[tuple[str, dict]], lock_path: Path) -> dict:
    """Re-hash the committed lock bytes and re-verify every training receipt's
    binding. Catches the exact P0-A defect class (a receipt whose recorded lock
    SHA belongs to a different package set)."""
    f: dict = {"lock_path": str(lock_path), "receipts": []}
    if not lock_path.is_file():
        return gate("LK", False, f, f"lock file not found: {lock_path}")
    sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    f["lock_sha256_recomputed"] = sha
    all_ok = True
    for label, rec in training_receipts:
        entry = {"receipt": label, "recorded_sha": rec.get("wheel_lock_sha256"),
                 "has_binding": "wheel_lock_sha256" in rec}
        if not entry["has_binding"]:
            entry["status"] = "NO_LOCK_FIELD"
            all_ok = False
        elif rec.get("wheel_lock_sha256") != sha:
            entry["status"] = "SHA_MISMATCH"
            all_ok = False
        elif rec.get("wheel_lock_channel") != FROZEN["channel"] \
                or rec.get("wheel_lock_gfx") != FROZEN["gfx_target"]:
            entry["status"] = "MISSION_IDENTITY_MISMATCH"
            entry["violations"] = [
                f"receipt channel {rec.get('wheel_lock_channel')!r}/gfx "
                f"{rec.get('wheel_lock_gfx')!r} != mission "
                f"{FROZEN['channel']!r}/{FROZEN['gfx_target']!r}"]
            all_ok = False
        else:
            binding = adamw_lib.verify_lock_binding(
                lock, sha, rec.get("wheel_lock_channel") or FROZEN["channel"],
                rec.get("wheel_lock_gfx") or rec.get("gfx_target"),
                rec.get("runtime_package_versions") or {})
            entry["status"] = "BOUND" if binding["ok"] else "BINDING_VIOLATION"
            entry["violations"] = binding["violations"]
            all_ok = all_ok and binding["ok"]
        f["receipts"].append(entry)
    return gate("LK", all_ok, f,
                "all training receipts bound to the exact lock bytes" if all_ok
                else "wheel-lock binding failed (wrong/dev/mutated lock recorded)")


# ================================================================ G0
def evaluate_g0(g0) -> dict:
    f = {"present": g0 is not None}
    if not g0:
        return gate("G0", False, f, "missing G0 evidence")
    f.update({
        "verdict": g0.get("verdict"),
        "child_dll_sha256": g0.get("child_dll_sha256"),
        "frozen_dll_sha256": FROZEN["miopen_dll_sha256"],
        "child_gpu_name": g0.get("child_gpu_name"),
        "gfx_target": g0.get("gfx_target"),
        "child_op_finite": g0.get("child_op_finite"),
        "parent_child_agree": g0.get("parent_and_child_dll_agree"),
        "runtime_class": g0.get("runtime_class"),
        "exit_code": g0.get("exit_code"),
        "child_dll_marker": g0.get("child_marker_count"),
    })
    if g0.get("verdict") == "BLOCKED_DLL_CONTAMINATION":
        return gate("G0", False, f, "BLOCKED_DLL_CONTAMINATION")
    ok = (
        g0.get("verdict") == "G0_RUNTIME_IDENTITY_PASS"
        and g0.get("child_dll_sha256") == FROZEN["miopen_dll_sha256"]
        and g0.get("child_op_finite") is True
        and g0.get("gfx_target") == FROZEN["gfx_target"]
        and g0.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and g0.get("parent_and_child_dll_agree") is True
        and str(g0.get("child_dll_path", "")).endswith("_rocm_sdk_libraries\\bin\\MIOpen.dll")
        and (g0.get("child_marker_count") or 0) > 0
    )
    return gate("G0", ok, f, "runtime identity verified in child process" if ok
                else "runtime identity not established")


# ================================================================ G1
def evaluate_g1(cand, ctrl, cand_log: str | None, ctrl_log: str | None) -> dict:
    f: dict = {"candidate_present": cand is not None,
               "control_present": ctrl is not None}
    if not cand:
        return gate("G1", False, f, "missing G1 candidate evidence")
    ld = cand.get("leg_detail") or {}
    cld = (ctrl or {}).get("leg_detail") or {}
    f.update({
        "candidate_classification": cand.get("classification"),
        "candidate_exit": cand.get("exit_code"),
        "candidate_child_dll": (ld.get("child_miopen") or {}).get("sha256"),
        "candidate_pid": ld.get("pid"),
        "control_child_dll": (cld.get("child_miopen") or {}).get("sha256"),
        "control_pid": cld.get("pid"),
        "candidate_scratch": ld.get("scratch"),
        "control_scratch": cld.get("scratch"),
        "control_failure_class": (ctrl or {}).get("failure_classification"),
        "control_dll_marker": ((ctrl or {}).get("miopen_identity_in_parent") or {})
            .get("pr13437_marker_miopen_initializer_list"),
    })
    distinct_procs = bool(ld.get("pid")) and bool(cld.get("pid")) \
        and ld.get("pid") != cld.get("pid")
    distinct_scratch = bool(ld.get("scratch")) and bool(cld.get("scratch")) \
        and ld.get("scratch") != cld.get("scratch")
    f["distinct_processes"] = distinct_procs
    f["distinct_cold_cache_identity"] = distinct_scratch
    cand_ok = (
        cand.get("classification") == "OFFICIAL_CANDIDATE_PASS"
        and cand.get("expectation") == "CANDIDATE"
        and cand.get("exit_code") == 0
        and not cand.get("ambient_hiprtc_shim")
        and cand.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and cand.get("gfx_target") == FROZEN["gfx_target"]
        and ld.get("exit_code") == 0
        and (ld.get("child_miopen") or {}).get("sha256") == FROZEN["miopen_dll_sha256"]
    )
    if not cand_ok:
        return gate("G1", False, f, "candidate no-STL leg not a genuine PASS "
                    "(in-child DLL identity required — parent-only capture is "
                    "insufficient)")
    if not ctrl:
        return gate("G1", False, f, "NIGHTLY_NO_STL_POSITIVE_ONLY_CONTROL_PENDING")
    # failure signature RE-DERIVED from RAW LOG BYTES when available; a stored
    # stderr_tail alone is NOT byte verification (missing raw log ⇒ fail-closed)
    f["control_raw_log_available"] = ctrl_log is not None
    f["candidate_raw_log_available"] = cand_log is not None
    ctrl_stderr = ctrl_log if ctrl_log is not None \
        else (cld.get("stderr_tail") or "")
    recomputed_class = gp_lib.classify_nostl_failure(ctrl_stderr or "")
    f["control_failure_reclassified"] = recomputed_class
    signature_in_log = ("type_traits" in (ctrl_stderr or "")
                        or "HIPRTC_ERROR_COMPILATION" in (ctrl_stderr or "")) \
        and ctrl_log is not None
    f["control_signature_in_raw_bytes"] = signature_in_log
    f["candidate_log_has_no_prefix_signature"] = \
        (cand_log is None) or ("type_traits" not in cand_log)
    ctrl_ok = (
        ctrl.get("classification") == "OFFICIAL_PRE_FIX_EXPECTED_FAIL"
        and ctrl.get("failure_classification") == "MIOPEN_HIPRTC_COMPILATION"
        and recomputed_class == "MIOPEN_HIPRTC_COMPILATION"
        and signature_in_log
        and ctrl.get("expectation") == "FAIL"
        and ((ctrl.get("miopen_identity_in_parent") or {})
             .get("pr13437_marker_miopen_initializer_list") == 0)
        and (cld.get("child_miopen") or {}).get("sha256") not in (
            None, FROZEN["miopen_dll_sha256"])
    )
    if not (distinct_procs and distinct_scratch):
        return gate("G1", False, f, "candidate/control processes or cold-cache "
                    "identities not distinct")
    if not ctrl_ok:
        return gate("G1", False, f,
                    "negative control not the matched pre-fix failure "
                    "(signature re-classification or control DLL identity failed)")
    return gate("G1", True, f,
                "NIGHTLY_NO_STL_REGRESSION_CONFIRMED — strong source-lineage + "
                "behavioral paired control (pre-fix and nightly stacks differ in "
                "more than one component; this is NOT a single-variable "
                "intervention)")


# ================================================================ G2
def evaluate_g2(ops) -> dict:
    f = {"present": ops is not None}
    if not ops:
        return gate("G2", False, f, "missing G2 evidence")
    gates = ops.get("gates") or {}
    statuses = {g: (gates.get(g) or {}).get("status") for g in G2_GATES}
    # numeric detail finiteness re-checked independently
    nonfinite = []
    for g in G2_GATES:
        det = (gates.get(g) or {}).get("detail") or {}
        for k, v in (det.items() if isinstance(det, dict) else []):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if not _finite(v):
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
        and gfx == FROZEN["gfx_target"]
        and not nonfinite
        and not ops.get("cpu_fallback_used")
        and ops.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and (ops.get("miopen_identity") or {}).get("sha256") == FROZEN["miopen_dll_sha256"]
        and ops.get("exit_code") == 0
    )
    return gate("G2", ok, f, "NIGHTLY_CORE_GPU_PASS (details re-checked)" if ok
                else "core GPU gate failed")


# ================================================================ G3/G4
def recompute_step_statistics(per_step: list, scale_history: list) -> dict:
    """Independent AdamW/GradScaler statistics from the raw per-step series.
    Nothing here hardcodes any historical count (11/7/4 etc.)."""
    out: dict = {"attempts": len(per_step)}
    effective = [i for i, s in enumerate(per_step)
                 if float(s.get("sentinel_max_abs_delta") or 0) > 0.0]
    inf_skips = [i for i, s in enumerate(per_step)
                 if s.get("found_inf_any") is True]
    unexplained = [i for i, s in enumerate(per_step)
                   if float(s.get("sentinel_max_abs_delta") or 0) <= 0.0
                   and s.get("found_inf_any") is not True]
    out.update({"effective_updates": len(effective), "inf_skips": len(inf_skips),
                "unexplained_no_update_steps": len(unexplained),
                "unexplained_indices": unexplained[:8]})
    # a found_inf step must NOT show parameter movement; an effective step MUST
    # have finite grads
    moved_on_skip = [i for i in inf_skips
                     if float(per_step[i].get("sentinel_max_abs_delta") or 0) > 0.0]
    nonfinite_on_effective = [i for i in effective
                              if per_step[i].get("grads_all_finite") is not True]
    out["moved_on_inf_skip"] = moved_on_skip
    out["nonfinite_grads_on_effective"] = nonfinite_on_effective
    # ordering + per-step context presence
    batches = [s.get("batch_index") for s in per_step]
    out["batch_index_monotonic"] = all(
        b is not None and (i == 0 or b > batches[i - 1])
        for i, b in enumerate(batches))
    out["all_invoked"] = all(s.get("invoked") is True for s in per_step)
    out["lr_recorded"] = all(s.get("lr_first_group") is not None for s in per_step)
    out["accumulate_recorded"] = all(s.get("accumulate_now") is not None
                                     for s in per_step)
    sh = [float(x) for x in (scale_history or [])]
    out["scale_history_len"] = len(sh)
    out["scale_history_matches_attempts"] = len(sh) == out["attempts"]
    out["backoffs_recomputed"] = sum(1 for i in range(1, len(sh))
                                     if sh[i] < sh[i - 1])
    # GradScaler contract: every inf skip at step i (except a trailing one)
    # must be followed by a scale decrease at the next observation
    missed_backoffs = [i for i in inf_skips
                       if i + 1 < len(sh) and sh[i + 1] >= sh[i]]
    out["inf_skips_without_scale_backoff"] = missed_backoffs
    return out


def evaluate_g34(amp) -> tuple[dict, dict]:
    f: dict = {"present": amp is not None}
    if not amp:
        return gate("G3", False, f, "missing training evidence"), \
               gate("G4", False, f, "missing AMP evidence")
    tc = amp.get("training_counts") or {}
    per_step = tc.get("per_step_events") or []
    scale_history = (amp.get("gradscaler") or {}).get("scale_history") or []
    r = recompute_step_statistics(per_step, scale_history)
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
        and amp.get("loaded_miopen_dll_sha256") == FROZEN["miopen_dll_sha256"]
        and amp.get("gfx_target") == FROZEN["gfx_target"]
        and amp.get("exit_code") == 0
        and amp.get("runtime_class") == "OFFICIAL_CANDIDATE"
        and lowp_recomputed == int(lpe.get("samples_low_precision") or -1)
        and lowp_recomputed > 0
        and (amp.get("optimizer") or {}).get("requested") == "auto"
        and (amp.get("optimizer") or {}).get("resolved_class") == "AdamW"
    )
    g3 = gate("G3", g3_ok, f, "NIGHTLY_YOLO_TRAINING_PASS (statistics recomputed "
              "from per-step facts)" if g3_ok
              else "training facts failed independent recomputation")
    # AMP taxonomy: FP32 fallback is NEVER AMP_PASS; dtype counts must reconcile
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
    g4 = gate("G4", amp_verdict == "AMP_PASS", f,
              f"NIGHTLY_AMP_PASS ({amp_verdict})" if amp_verdict == "AMP_PASS"
              else reason)
    g4["amp_verdict"] = amp_verdict
    return g3, g4


# ================================================================ G5
def evaluate_g5(ckpt, artifacts: list | None = None) -> dict:
    f = {"present": ckpt is not None}
    if not ckpt:
        return gate("G5", False, f, "missing checkpoint/resume evidence")
    # checkpoint bytes anchored against execution-time artifact hashes when the
    # envelope provides them (tampering a recorded SHA is then detectable)
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
    # epoch continuity RECOMPUTED from numeric facts (stored boolean only diffed)
    total = st.get("total_epochs")
    f["epoch_continuity_recomputed"] = (
        (total is not None
         and st.get("last_epoch_value") == total
         and (st.get("final_epoch_rows") or 0) > (st.get("rows_at_kill") or 0)
         and st.get("resume_exit") == 0) if total is not None else None)
    core_ok = (
        ckpt.get("pass_fail_skip") == "PASS"
        and resumable.get("has_optimizer_state") is True
        and st.get("resume_exit") == 0
        and st.get("resume_done_marker") is True
        and st.get("epoch_continuity") is True
        and (f["epoch_continuity_recomputed"] is not False)
        and (st.get("resume_start_epoch") is None
             or (total is None or st.get("resume_start_epoch") < total))
        and st.get("infer_ok") is True and st.get("infer_exit") == 0
        and (st.get("last_epoch_value") or 0) >= 3
        and bool(ckpt.get("checkpoint_sha256")) and sha_hex_ok
        and all(v is not False for v in anchored.values())
        and ckpt.get("gfx_target") == FROZEN["gfx_target"]
        and (st.get("resume_effective_updates") or 0) > 0
        and (st.get("optimizer_state_entries") or 0) > 0
    )
    # serialization-depth classification — never invent upstream fields.
    # Observed 8.4.214 reality: optimizer/epoch/best_fitness/train_args/EMA and
    # the GradScaler ARE serialized; the LR scheduler is NOT (rebuilt from
    # train_args on resume). Honest claims follow the observations.
    serialized = {k: (v or {}).get("serialized") for k, v in sc.items()
                  if isinstance(v, dict)}
    full_state = (
        serialized.get("model_weights") is True
        and serialized.get("optimizer") is True
        and serialized.get("epoch") is True
        and serialized.get("best_fitness") is True
        and serialized.get("trainer_args") is True
        and serialized.get("scheduler") == "NOT_SERIALIZED_BY_UPSTREAM"
        and serialized.get("gradscaler") is True
    )
    f["state_verdict"] = (
        "FULL_TRAINING_STATE_RESTORE_PASS" if (core_ok and full_state
            and serialized.get("scheduler") is not None)
        else "RESUME_PASS_CORE_STATE_VERIFIED"
        if core_ok else "RESUME_INCOMPLETE")
    f["not_serialized_classes"] = {k: v for k, v in serialized.items()
                                   if v == "NOT_SERIALIZED_BY_UPSTREAM"}
    ok = core_ok and f["state_verdict"] in (
        "FULL_TRAINING_STATE_RESTORE_PASS", "RESUME_PASS_CORE_STATE_VERIFIED")
    reason = ("NIGHTLY_CHECKPOINT_RESUME_PASS — core resume verified; "
              + "; ".join(f"{k}: {v}" for k, v in f["not_serialized_classes"].items())
              ) if ok else "checkpoint save/resume/reload facts incomplete"
    return gate("G5", ok, f, reason)


# ================================================================ G7
def evaluate_g7(rel, supp, orphan, trainer_receipt) -> dict:
    """trainer_receipt: either {"envelope": {...child_pid...}} or the workers
    envelope record itself (run_envelope child_pid / worker_stage trainer_pid —
    both accepted, chain-verified against the census tree)."""
    if trainer_receipt and isinstance(trainer_receipt, dict) \
            and "envelope" not in trainer_receipt:
        trainer_receipt = {"envelope": {
            "child_pid": trainer_receipt.get("child_pid")
            or trainer_receipt.get("trainer_pid")}}
    """Recompute worker facts from the recorded process observations; the
    census/orphan verdict strings are never authority."""
    f = {"present": rel is not None}
    if not rel:
        return gate("G7", False, f, "missing workers exercise evidence")
    tc = rel.get("training_counts") or {}
    per_step = tc.get("per_step_events") or []
    r = recompute_step_statistics(
        per_step, (rel.get("gradscaler") or {}).get("scale_history") or [])
    f.update({
        "harness_train_args": rel.get("harness_train_args"),
        "exit_code": rel.get("exit_code"),
        "recomputed_stats": r,
        "census_present": supp is not None, "orphan_present": orphan is not None,
    })
    census_ok = False
    leftover_recomputed: list = []
    if supp:
        kids = supp.get("spawn_children_of_trainer") or []
        trainer_pid = supp.get("trainer_pid")
        preexisting = supp.get("preexisting_zombies_disclosed") or []
        f.update({"trainer_pid": trainer_pid,
                  "spawn_children": kids,
                  "spawn_children_count": len(kids),
                  "census_captured_utc": supp.get("captured_utc"),
                  "preexisting_disclosed": preexisting})
        census_ok = (
            isinstance(trainer_pid, int)
            and len(kids) >= 8
            and all(isinstance(k, int) for k in kids)
            and len(set(kids)) == len(kids)
        )
        # trainer identity must tie to the training receipt's process envelope
        # (directly, or through a venv-launcher ancestor chain recorded in the
        # census tree snapshots — a venv redirector pid may sit between)
        env_pid = ((trainer_receipt or {}).get("envelope") or {}).get("child_pid")
        f["envelope_child_pid"] = env_pid
        chain = [trainer_pid]
        ppid_of = {}
        for s in (supp.get("snapshots") or []):
            for p in s.get("python_tree") or []:
                ppid_of[p.get("pid")] = p.get("ppid")
        cur = trainer_pid
        while cur in ppid_of and ppid_of.get(cur) is not None:
            cur = ppid_of[cur]
            chain.append(cur)
        f["trainer_ancestry_chain"] = chain
        f["trainer_pid_ties_to_envelope"] = (
            env_pid is None or env_pid == trainer_pid or env_pid in chain)
        census_ok = census_ok and f["trainer_pid_ties_to_envelope"]
    if orphan:
        all_pids = orphan.get("all_python_pids") or []
        preexisting = (supp or {}).get("preexisting_zombies_disclosed") or []
        checker = orphan.get("checker_pid")
        leftover_recomputed = [p for p in all_pids
                               if p not in preexisting and p != checker]
        f.update({"orphan_all_pids": all_pids,
                  "orphan_checker_pid": checker,
                  "leftover_recomputed": leftover_recomputed,
                  "stored_mission_tree_leftover": orphan.get("mission_tree_leftover")})
    clean = bool(orphan) and not leftover_recomputed
    workers8 = "workers=8" in str(rel.get("harness_train_args"))
    train_ok = (
        rel.get("exit_code") == 0
        and rel.get("pass_fail_skip") == "ADAMW_AMP_MULTISTEP_PASS"
        and (tc.get("batches_completed") or 0) > 0
        and r["effective_updates"] > 0
        and not r["unexplained_no_update_steps"]
    )
    ok = workers8 and train_ok and census_ok and clean
    return gate("G7", ok, f,
                "bounded workers=8 exercise verified from live census + "
                "recomputed orphan check" if ok
                else "workers exercise incomplete (census/orphan recomputation failed)")


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


def derive(gates: list[dict], forbidden: list[str]) -> dict:
    by = {g["gate"]: g["verdict"] for g in gates}
    if forbidden:
        overall = "NIGHTLY_NO_GO"
        reason = f"forbidden Stable verdict present in evidence: {forbidden}"
    elif all(v == "PASS" for v in by.values()):
        overall = "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS"
        reason = ("all gates independently recomputed PASS on physical gfx1151 "
                  "with audited nightly bytes and byte-bound lock provenance")
    elif by.get("G1") == "PASS":
        overall = "NIGHTLY_PARTIAL_PASS"
        reason = "G1 proven independently; downstream gates incomplete"
    else:
        overall = "NIGHTLY_NO_GO"
        reason = "G1 not established"
    return {"overall": overall, "reason": reason, "gate_verdicts": by,
            "ceiling": "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS",
            "forbidden_verdict_hits": forbidden,
            "note": "nightly/dev artifacts cap at candidate-level verdicts; no "
                    "Stable/dual-arch/clean-install claim is possible from this "
                    "single-GPU nightly mission"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.evidence_root)
    repo = Path(args.repo_root)
    lock_path = root / "01_package_provenance/resolved_wheel_lock_nightly_gfx1151.json"
    lock = _j(lock_path)
    audit = _j(repo / "release-provenance/r22a5a/nightly_wheel_audit_20261117.json")
    manifest = _j(root / "01_package_provenance/installed_manifest.json")
    g0 = _j(root / "02_runtime_identity/g0_child_identity.json")
    cand = _j(root / "02_nostl_candidate/nostl_candidate.json")
    ctrl = _j(root / "03_nostl_negative_control/nostl_prefit_control_v2.json")
    ops = _j(root / "04_gpu_primitives/torchvision_ops.json")
    amp = _j(root / "05_yolo_training_amp/adamw_amp.json")
    ckpt = _j(root / "06_checkpoint_resume/checkpoint_resume.json")
    ckpt_env = _j(root / "06_checkpoint_resume/lifecycle_envelope.json")
    rel = _j(root / "07_reliability/workers8_amp_v2.json") \
        or _j(root / "07_reliability/workers8_amp.json")
    supp = _j(root / "07_reliability/workers8_midrun_census.json")
    orphan = _j(root / "07_reliability/workers8_postrun_orphan_check.json")
    rel_env = _j(root / "07_reliability/workers8_envelope.json")

    def _log(p: Path) -> str | None:
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None

    training_receipts = [
        (n, r) for n, r in (
            ("05_yolo_training_amp/adamw_amp.json", amp),
            ("07_reliability/workers8_amp_v2.json", rel),
        ) if r is not None
    ]
    gates = [evaluate_pkg(lock, audit, manifest),
             evaluate_lk(training_receipts, lock_path),
             evaluate_g0(g0),
             evaluate_g1(cand, ctrl,
                         _log(root / "02_nostl_candidate/raw/candidate_leg.log"),
                         _log(root / "03_nostl_negative_control/raw/negctrl_v2_leg.log")),
             evaluate_g2(ops),
             *evaluate_g34(amp),
             evaluate_g5(ckpt, (ckpt_env or {}).get("artifact_hashes")),
             evaluate_g7(rel, supp, orphan, rel_env)]
    forbidden = scan_forbidden_verdicts(root)
    result = derive(gates, forbidden)
    result.update({
        "run_id": args.run_id, "mission": "R22A.5N.1",
        "engine_version": "r22a5n1-acceptance-v2",
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
        print(f"  {g['gate']:4s} {g['verdict']:4s} {g['reason'][:110]}")
    sys.exit(0 if result["overall"] == "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS"
             else 3)


if __name__ == "__main__":
    main()
