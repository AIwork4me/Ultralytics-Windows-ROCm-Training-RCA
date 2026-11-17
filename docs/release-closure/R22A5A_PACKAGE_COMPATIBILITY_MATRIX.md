# R22A.5A Package Compatibility Matrix — official installation contract

- Generated: 2026-11-17 (mission R22A.5A Phase C, §6)
- Tooling: `scripts/r22a5a/gen_install_plan.py` (classification layer) over
  `windows-golden-path/compatibility-matrix.yaml` (source of truth) and
  `windows-golden-path/scripts/resolve_package_set.py` (resolution +
  hash-pinning + mixing-rule enforcement — REUSED unchanged)
- Outputs this mission: `release-provenance/r22a5a/install_plan_gfx1100.json`,
  `install_plan_gfx1151.json`, `candidate_lock_template.json`
- Historical lock `golden-path/requirements-lock.txt` is intentionally NOT
  modified (it records the verified MODE B run of 2026-11-15).

## 1. Target hardware and what "support" means here

| GPU | gfx | Officially-supported by vendor docs? | Engineering feasibility proven in this RCA |
|---|---|---|---|
| Radeon RX 7900 XTX | gfx1100 | AMD ROCm documentation lists Radeon RX 7900 XTX as a supported dGPU for ROCm on Windows — verify against the current AMD support matrix at install time | YES: physical training functional pass on official DEV wheels (R22A.2); historical official 7.14.1 stack trains with disclosed shim |
| Radeon 8060S | gfx1151 | not present in AMD's published Windows support matrix (UNKNOWN — recorded, not assumed) | YES: physical training functional pass on official DEV wheels (R22A.3); official 7.14.1 MODE B golden path physically executed (P14.3) |

Explicit rule: **official support status and engineering feasibility are
separate facts**. This matrix records both and never lets the second
silently stand in for the first.

## 2. Channel × set state (2026-11-17 scan, frontier rows)

| Channel | Set (frontier) | gfx1100 device wheel | gfx1151 device wheel | Fix in MIOpen | Plan tier (this mission) |
|---|---|---|---|---|---|
| multi-arch (GA) | 7.14.1 (torch 2.12.0+rocm7.14.1) | YES `amd-torch-device-gfx1100` (+gfx110x family) | YES `amd-torch-device-gfx1151` | **NO** (frozen audits) | UNQUALIFIED |
| stable whl-next | 10.1.0 (torch 2.14.0+rocm10.1.0) | YES `rocm-sdk-device-gfx1100` | YES `rocm-sdk-device-gfx1151` | **NO** (P16 byte-identical) | UNQUALIFIED |
| rc whl-next | 10.2.0rc2 (torch 2.15.0+rocm10.2.0rc2) | YES | YES | **NO** (diverged, behind_by=92) | UNQUALIFIED |
| nightly whl-next | 10.3.0a20261116 | YES (appeared since the 11-15 scan) | YES | **YES** (fresh audit 2026-11-17: marker 2, behind_by=0) | OFFICIAL_DEV (pre-release; never Stable) |
| dev whl-next | moving (10.3.0.dev0+git…) | YES | YES | YES in frozen audited builds (4e7d93e3) | OFFICIAL_DEV (moving; frontier pending) |

Other channels: PyTorch official index (`download.pytorch.org/whl/torch/`)
carries **zero ROCm Windows wheels** (re-verified 2026-11-17). TheRock
release tags: latest is still `therock-10.1` (2026-10-05) — all 5 newest
tags' rocm-libraries submodule pointers are **behind** the fix
(compare-based, no date inference).

## 3. Compatibility rules enforced (testable — pinned in CPU tests)

| Rule | Enforcement | Negative test |
|---|---|---|
| no cross-ROCm-generation mixing (7.x + 10.x) | `evaluate_channel` family coherence + resolve_package_set `rocm_family_mix` | `test_conflicting_rocm_generations_rejected` |
| device wheel required for target gfx (+gfx110x family on 7.x — P18 silent-SDPA trap) | required-package list + `device_wheel_present` | `test_wrong_gfx_device_package_rejected` |
| torch must be AMD HIP build from the exact channel | `gp_lib.torch_wheel_is_amd_hip` | plan `torch_is_amd_hip` false → UNQUALIFIED |
| torchvision needs its own device wheel (7.x layout) | required list (multi-arch) | set incomplete |
| python ABI must match (`cp312`/`cp313`/`cp314` observed) | explicit ABI blocker, no silent fallback | `test_wrong_python_abi_blocks_plan` |
| conflicting versions for one package+ABI | explicit conflict blocker | same test family |
| Windows-only (`win_amd64`) | discovery parse | `test_linux_wheel_cannot_qualify_as_windows` |
| per-wheel SHA256 pinning at install time | resolve_package_set lock | (existing R22A.4.1 tests) |
| unknown/unavailable metadata → `UNKNOWN`, never assumed | BLOCKED_METADATA / BLOCKED_NETWORK | `TestIndexFailureClassification` |

## 4. Installation plan semantics

- `OFFICIAL_STABLE` — stable/GA channel, fix-confirmed coherent set.
  Install candidate ONLY; training PASS still requires R22A.5B gates.
- `OFFICIAL_RC` / `OFFICIAL_DEV` — pre-release candidates; commands may be
  emitted for **engineering** validation, never labeled production-ready.
- `UNQUALIFIED` — no installation commands may be emitted at all.
- Current combined verdict (both architectures):
  **`PRE_RELEASE_ONLY_CANDIDATES_OFFICIAL_STABLE_BLOCKED_RELEASE`** —
  nightly offers a fix-confirmed DEV-tier set; stable/GA remains pre-fix.

## 5. Future repaired Stable build — the candidate lock template

`release-provenance/r22a5a/candidate_lock_template.json` pre-shapes the
fields. When a stable candidate qualifies:

1. `scan_official_releases.py` (it will classify
   `STABLE_CANDIDATE_PENDING_GPU_VALIDATION`);
2. `audit_wheel_provenance.py --channel stable` (fresh wheel+DLL+ancestry);
3. `resolve_package_set.py --channel stable …` → the REAL hash-pinned lock
   (`requirements-lock/<set>.txt`);
4. `g9_preflight.py --channel stable` → PROCEED_CANDIDATE;
5. R22A.5B physical gates on gfx1100 AND gfx1151.

Hand-editing a lock file to pretend a future build exists is forbidden and
checked (`candidate_lock_template.json` "forbidden" field).
