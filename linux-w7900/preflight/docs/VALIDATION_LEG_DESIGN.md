# Validation Leg Design — Final Phase-5.1 A/B (G07)

Date: 2026-10-08 | Status: infrastructure READY; final legs NOT executed

## Single-variable discipline

| Property | Leg A (unpatched) | Leg B (patched) |
|---|---|---|
| Upstream base SHA | frozen FINAL_HANDOFF `upstream_base_sha` | SAME |
| GPU / driver | W7900 gfx1100 / amdgpu 6.16.13 | SAME |
| ROCm userspace | isolated 7.14.1 wheel SDK venv | SAME |
| HIP toolchain | wheel amdclang++ (HIP 7.14.60850) | SAME |
| CMake flags | `scripts/build_leg_miopen.sh` (one literal) | SAME (env vars change ONLY source/build/install dirs) |
| MIOpen options | HIPRTC=ON COMGR=ON CK=OFF RelWithDebInfo gfx1100 | SAME |
| Test harness | `kthvalue_runtime_harness_gfx1100` (same binary sha256 both legs) | SAME |
| Inputs / seeds | fixed xorshift64* seeds in harness source | SAME |
| Tolerances | exact value+index match vs CPU reference (max_abs_err=0) | SAME |
| **Source patch** | **none** | **FINAL Phase-5.1 series (the independent variable)** |

During preparation, leg A was built from the historical anchor
`b68f8944…` (Phase-3 base, MIOpen 3.6.2). The FINAL validation MUST rebuild
leg A at the frozen FINAL_HANDOFF base SHA (the mission forbids assuming the
anchor equals the final base).

## Directory layout (strictly separated; A never overwrites B)

```text
source/upstream-pristine/     leg-A source (final run: reconstructed at frozen SHA)
source/final-patched/         leg-B source [RESERVED — EMPTY until freeze]
build/baseline-miopen/        leg-A build
build/patched-miopen/         leg-B build [RESERVED — EMPTY]
install/baseline/             leg-A prefix (libMIOpen.so.1)
install/patched/              leg-B prefix [RESERVED — EMPTY]
runtime/baseline-cache/       leg-A kernel caches (per-label subdirs)
runtime/patched-cache/        leg-B kernel caches (per-label subdirs)
```

## Runtime binding & provenance per leg

`scripts/run_validation_leg.sh <baseline|patched> <label> <cmd>`:

1. Sources `scripts/env_rocm7141.sh` (7.14.1 isolation, /opt/rocm scrubbed).
2. Prepends the leg prefix to `LD_LIBRARY_PATH` (neutralizes wheel-MIOpen
   shadowing found in the G04 audit).
3. `LD_PRELOAD`s the leg's `libMIOpen.so.1` soname symlink → source build is
   first in global scope; harness `dladdr` echoes binding in-stream.
4. Fresh per-label `MIOPEN_CUSTOM_CACHE_DIR` + `MIOPEN_USER_DB_PATH` +
   `XDG_CACHE_HOME` under the LEG's cache root; refuses non-empty dirs
   (`FRESH_CACHE_FORCE=1` escape hatch, discouraged).
5. Echoes lib sha256 before exec.

## SHA verification chain (final run)

1. `check_final_handoff.py --check-only` — manifest + per-patch + series
   hashes (raw bytes), stale-anchor rejection, unlisted-file rejection.
2. `prepare_validation_legs.sh leg-a` — rebuild A at frozen SHA, record
   `libMIOpen.so.1` sha256.
3. `prepare_validation_legs.sh leg-b <handoff>` — strict check → clean
   worktree reconstruction (`ENABLE_APPLY=1`) → identical-flag build →
   record sha256.
4. Both legs run the same harness under their own runner; dumps compared
   byte-for-byte (values + indices) and vs CPU reference.
5. JSON evidence per leg + comparison emitted under `evidence/`.

## What is intentionally deferred

- No patched build, no A/B execution (final Phase-5.1 patch not frozen).
- The B directories remain EMPTY; `leg-b` hard-refuses until the handoff
  passes `--check-only` and `ENABLE_APPLY=1` is set post-freeze.
