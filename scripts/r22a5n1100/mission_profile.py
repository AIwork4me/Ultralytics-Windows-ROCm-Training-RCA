# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5N gfx1100 versioned mission profiles (mission §5).

Minimal versioned mission-profile parameterization of the R22A.5N.1 engine
family: the gfx1151 profile re-exports the ORIGINAL frozen semantics of
scripts/r22a5n1/nightly_acceptance.py untouched (imported, never copied or
mutated — historical receipts keep their verifier), while the gfx1100 profile
carries its own frozen candidate identity, evidence layout and verdict ceiling
for this mission. A profile is plain frozen data: no runtime mutation of any
engine's globals is possible or needed.

Design contracts (mission §5):
  1. gfx1151 historical tests still PASS (r22a5n1 engine + tests untouched)
  2. the gfx1100 profile rejects gfx1151 physical receipts (gfx identity is
     checked in every gate)
  3. a gfx1100 lock cannot be substituted by the gfx1151 lock (python_tag
     cp312 vs cp313 + gfx_target + device-wheel names all bind)
  4. both GPUs may share the byte-identical SDK Libraries wheel (py3-none
     wheel, GPU-independent) but NEVER GPU-specific device wheels
  5. a successful gfx1151 JSON cannot be relabeled gfx1100 PASS (every
     receipt's gfx_target is re-derived)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_R22A5N1 = Path(__file__).resolve().parents[1] / "r22a5n1" / "nightly_acceptance.py"


def _load_r22a5n1():
    """Load the historical engine module WITHOUT importing it as a shared
    global (keeps its FROZEN semantics immutable for its own tests)."""
    spec = importlib.util.spec_from_file_location("r22a5n1_nightly_acceptance_ro",
                                                  _R22A5N1)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


N1 = _load_r22a5n1()

# gfx1151 profile = the historical engine's own frozen identity, re-exported
# by reference (asserted equal at import time so drift is impossible).
PROFILE_GFX1151 = {
    "profile_name": "gfx1151",
    "mission_id": "R22A5N1-GFX1151",
    "frozen": dict(N1.FROZEN),
    "python_tag": "cp313",
    "evidence_run_id": "R22A5N-GFX1151-20261117-A",
    "lock_filename": "resolved_wheel_lock_nightly_gfx1151.json",
    "ceiling": "R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS",
}

# gfx1100 profile — frozen identity of THIS mission's audited 2026-11-16
# nightly snapshot on the cp312 ABI (mission §2.2 table). The SDK Libraries
# wheel and its embedded MIOpen.dll are the byte-identical artifacts audited
# for gfx1151 (py3-none-win_amd64 wheel is GPU-independent); per §2.3 the
# actual downloaded bytes must re-verify to exactly these hashes or a NEW
# provenance record is required — silent substitution is not allowed.
PROFILE_GFX1100 = {
    "profile_name": "gfx1100",
    "mission_id": "R22A5N_GFX1100_OFFICIAL_NIGHTLY",
    "frozen": {
        "wheel": "rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl",
        "wheel_sha256": "b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0",
        "miopen_dll_sha256": "f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6",
        "miopen_build": "3.6.3.25f28906",
        "merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
        "torch": "2.16.0a0+rocm10.3.0a20261116",
        "torchvision": "0.30.0a0+rocm10.3.0a20261116",
        "ultralytics": "8.4.214",
        "gfx_target": "gfx1100",
        "channel": "nightly",
    },
    "python_tag": "cp312",
    "evidence_run_id": "R22A5N-GFX1100-20261117-A",
    "lock_filename": "resolved_wheel_lock_nightly_gfx1100.json",
    "wheel_audit_filename": "wheel_audit_gfx1100.json",
    "ceiling": "R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS",
    # evidence layout (mission §12.1)
    "paths": {
        "lock": "01_package_provenance/resolved_wheel_lock_nightly_gfx1100.json",
        "wheel_audit": "01_package_provenance/wheel_audit_gfx1100.json",
        "manifest": "01_package_provenance/installed_manifest.json",
        "g0": "02_runtime_identity/g0_child_identity.json",
        "candidates": ["03_nostl_candidate/nostl_candidate_trial1.json",
                       "03_nostl_candidate/nostl_candidate_trial2.json"],
        "candidate_logs": ["03_nostl_candidate/raw/candidate_trial1_leg.log",
                           "03_nostl_candidate/raw/candidate_trial2_leg.log"],
        "control": "04_nostl_negative_control/nostl_prefit_control.json",
        "control_log": "04_nostl_negative_control/raw/negctrl_leg.log",
        "ops": "05_gpu_primitives/torchvision_ops.json",
        "amp": "06_yolo_training_amp/adamw_amp.json",
        "ckpt": "07_checkpoint_resume/checkpoint_resume.json",
        "ckpt_envelope": "07_checkpoint_resume/lifecycle_envelope.json",
        "workers_rel": "08_workers_reliability/workers8_amp_v2.json",
        "workers_census": "08_workers_reliability/workers8_midrun_census.json",
        "workers_orphan": "08_workers_reliability/workers8_postrun_orphan_check.json",
        "workers_envelope": "08_workers_reliability/workers8_envelope.json",
    },
    "minimum_candidate_trials": 2,
}

MISSION_PROFILES = {"gfx1151": PROFILE_GFX1151, "gfx1100": PROFILE_GFX1100}

# verdicts no nightly mission may ever produce (mission §16)
FORBIDDEN_VERDICTS = tuple(N1.FORBIDDEN_VERDICTS) + (
    "R22A5N_GFX1100_VS_GFX1151_STABLE_CLAIM",)


def get_profile(name: str) -> dict:
    if name not in MISSION_PROFILES:
        raise KeyError(f"unknown mission profile {name!r}; "
                       f"known: {sorted(MISSION_PROFILES)}")
    return MISSION_PROFILES[name]
