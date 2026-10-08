# OFFICE W7900 READINESS — Linux Validation Preparation (W7900-LINUX-PREP-R1)

Date: 2026-10-08 | **FINAL STATUS: OFFICE_W7900_ENV_READY**

## Machine

- Ubuntu 24.04.4 LTS, kernel 6.8.0-79-generic, amdgpu 6.16.13 (DKMS)
- AMD EPYC 9334 (128 threads), 503 GiB RAM, 56+ GiB free workspace
- **1x AMD Radeon PRO W7900, gfx1100** (PCI 1002:744b subsys 1002:0e0c;
  rocminfo Chip ID 0x744b; torch 7.14.1 stack reports "AMD Radeon Pro
  W7900D"; 48 GiB VRAM pool). No HSA overrides ever set.

## Environment (two-stack discipline; nothing system-level modified)

| Stack | ROCm | Torch | Use |
|---|---|---|---|
| system (untouched) | 7.2.1 | 2.9.1+gitff65f5b | G02 machine baseline only |
| isolated venv | 7.14.1 wheels | 2.12.0+rocm7.14.1 | all prep builds + final legs |

The isolated venv is contamination-hardened (RUNPATH patches + soname
symlinks; clean-env ldd resolves ZERO system ROCm libraries) and every
session routes through `scripts/env_rocm7141.sh`.

## Completed preparation evidence (all independently subagent-audited)

| Gate | Result |
|---|---|
| G00 machine inventory | gfx1100 confirmed; PASS |
| G01 ROCm audit + 7.14.1 SDK install | PASS (contamination MAJOR found & fixed) |
| G02 GPU baseline (matmul + BatchNorm fwd/bwd) | PASS both stacks (97–100% GPU utilization proven by reviewer) |
| G03 network readiness | PASS (github git transport UNSTABLE documented; api.github.com stable) |
| G04 pristine MIOpen 3.6.2 baseline build | PASS (zero /opt/rocm in cache; shadowing MAJORs found & fixed) |
| G05 HIPRTC smoke + STL probes | PASS (gfx1100 code object executed; -nostdinc ≡ -nostdinc++ partial-isolation finding) |
| G06 direct Kthvalue harness baseline | **PASS 3/3 exact** (dladdr-proven source-built MIOpen; RTC MIOpenKthvalue.cpp.o -mcpu=gfx1100 in fresh cache; dumps byte-identical across reruns 15/15) |
| G07 A/B leg infrastructure | READY (single-variable discipline; B reserved EMPTY) |
| G08 handoff consumer | READY (adversarially hardened; FINAL_HANDOFF absent -> FALSE) |
| G09 machine hygiene | PASS (system untouched; no credentials; reproducible probes) |
| G10 3-reviewer panel | all findings resolved; no unresolved blockers |

## What remains for the FINAL validation session (post-freeze only)

1. Acquire `findings/phase5_1/FINAL_HANDOFF.json` from the RCA repo
   (currently absent — 404).
2. `check_final_handoff.py --check-only --rca-root <rca>` must PASS.
3. Fetch frozen `upstream_base_sha` into `repos/rocm-libraries` (retry
   tooling provided; tarball+verification fallback documented).
4. `prepare_validation_legs.sh leg-a <frozen_sha>` then
   `leg-b <handoff>` (ENABLE_APPLY=1).
5. Run harness on both legs via `run_validation_leg.sh`; compare dumps
   byte-level + CPU reference; emit comparison evidence.

## Explicitly NOT done (mission boundary)

- No Phase-5.1 patch applied; no patched build; no A/B comparison executed;
  no upstream PR/issue/comment; no claim of final Linux patched PASS.
