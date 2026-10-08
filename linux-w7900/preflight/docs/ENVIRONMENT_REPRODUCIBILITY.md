# Environment Reproducibility — W7900 Linux Prep (G09)

Date: 2026-10-08

## Machine invariants (verified unchanged across the whole mission)

| Item | Value | Verified by |
|---|---|---|
| Kernel | 6.8.0-79-generic | G00, G09 logs |
| amdgpu module | 6.16.13 (DKMS) | G00, G09 logs |
| System libMIOpen | sha256 bd03b864…d8d77eb4 (unchanged — system MIOpen NOT replaced) | G01, G09 |
| GPU | 1x gfx1100 (W7900, PCI 1002:744b:0e0c) | G00 + subagent |
| HSA_OVERRIDE_GFX_VERSION | unset (never faked) | G00, G09 |
| Global LD_PRELOAD | unset (all preloads are per-run, in wrappers) | G09 |

## Two-stack discipline

- System stack (7.2.1 + torch 2.9.1+gitff65f5b): untouched; used ONLY for the
  G02 machine baseline; `pip check` clean before and after the mission.
- Isolated stack (tools/rocm7141-venv, ROCm 7.14.1 wheels + torch
  2.12.0+rocm7.14.1): used for all builds and validation prep; hardened with
  RUNPATH patches + soname symlinks so it is self-contained even under
  `env -i`; `rocm-sdk test` 27/27; `pip check` clean.
- Cross-contamination prevented by env_rocm7141.sh / env_system721.sh and
  the per-leg runner; every runtime provenance claim was dladdr-proven.

## Environment lock (authoritative versions)

See `evidence/G09_final_machine_audit.json` -> `environment_lock`:
isolated SDK (rocm 7.14.1 components, torch 2.12.0+rocm7.14.1, Python
3.12.3), system stack (ROCm 7.2.1, torch 2.9.1+gitff65f5b, cmake 3.31.10,
ninja 1.13.0, gcc 13.3.0), pinned baseline build (source b68f8944…, MIOpen
3.6.2, libMIOpen sha256 6af347af…90697), apt additions made during prep
(libbz2-dev, nlohmann-json3-dev, libeigen3-dev — user-space build headers
only; no driver/kernel packages).

## Reproducibility scope claims

- WITHIN-machine A/B reproducibility is enforced structurally: identical
  cmake literal (scripts/build_leg_miopen.sh), same harness binary
  (sha256-pinned), fixed seeds, fresh per-label caches, per-leg library
  SHA256 recorded in evidence.
- ACROSS-machine byte-identical binaries are NOT claimed (different
  toolchain instances produce different debug info); the comparison that
  matters is runtime OUTPUT (values/indices byte-comparison + CPU
  reference), which is exactly what the final A/B protocol captures.

## Known transient (non-blocker)

`repos/rocm-libraries` blobless clone: commit/tree objects complete; worktree
file materialization for the pinned SHA is still being backfilled through
the unstable egress proxy (scripts/repo_backfill_loop.sh, cumulative
progress). This does not affect any completed gate: the baseline SOURCE OF
RECORD is the codeload tarball at b68f8944…, whose 8032/8032 real files were
independently blob-hash-verified against the commit by the G04 subagent.
The final validation session must confirm the repo (or re-acquire the
frozen SHA by the same tarball+verification path) before leg reconstruction.

## Invocation documentation (every script)

| Script | Invocation |
|---|---|
| env_rocm7141.sh / env_system721.sh | `source scripts/env_<stack>.sh` |
| build_baseline_miopen.sh | `bash scripts/build_baseline_miopen.sh` |
| build_leg_miopen.sh | `MIOPEN_SOURCE=… MIOPEN_BUILD=… MIOPEN_INSTALL=… bash scripts/build_leg_miopen.sh` |
| prepare_validation_legs.sh | `bash scripts/prepare_validation_legs.sh {preflight\|leg-a\|leg-b <handoff>}` |
| run_validation_leg.sh | `bash scripts/run_validation_leg.sh {baseline\|patched} <label> <cmd…>` |
| check_final_handoff.py | `python3 scripts/check_final_handoff.py --check-only <m> --rca-root <dir>` |
| g02_gpu_baseline.py | `python scripts/g02_gpu_baseline.py <out.json>` (under desired env) |
| g05_hiprtc_smoke.cpp | `hipcc scripts/g05_hiprtc_smoke.cpp -o <bin> --offload-arch=gfx1100 -L… -lhiprtc` (env_rocm7141) |
| g05_stl_probe.cpp / g05_limits_include_test.cpp | same pattern (docs/HIPRTC_BASELINE.md) |
| kthvalue_runtime_harness_gfx1100.cpp | g++ -O2 -std=c++17 -D__HIP_PLATFORM_AMD__ -D__HIP_PLATFORM_HCC__ -I<miopen include> -I<sdk include> -ldl |
| git-retry.sh / clone_loop.sh / repo_backfill_loop.sh | network resilience helpers (see G03/G04) |

## Run-protocol guard (G10 Reviewer A)

- Every 7.14.1-side invocation MUST go through `scripts/env_rocm7141.sh`
  (or `run_validation_leg.sh`, which sources it). The built binaries carry
  no RPATH by design; an ambient shell would resolve `libhiprtc.so.7` from
  `/opt/rocm-7.2.1` via ldconfig. Never run harnesses/compilations from an
  unsourced shell.
- env scripts use `set -euo pipefail`: avoid `... | head -1 && next` chains
  in the same shell (SIGPIPE aborts the chain).
