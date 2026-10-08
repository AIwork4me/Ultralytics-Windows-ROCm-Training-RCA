# G06 Independent Subagent Review — Kthvalue Runtime Path Audit

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## VERDICT: PASS

## Independently reproduced
- Harness has ZERO link-time ROCm/MIOpen deps (ldd: only libc/libstdc++;
  nm -D: 0 undefined miopen/hip symbols) — no PyTorch involvement possible.
- sha256 matches for harness binary and baseline libMIOpen.
- Independent re-run with a DIFFERENT fresh cache label: rc=0, 3/3 PASS,
  identical slice0 values/indices, identical dladdr provenance
  (miopenCreate + miopenKthvalueForward <- install/baseline/lib/libMIOpen.so.1),
  FindSolutionImpl KthvalueFwd x3, HIPRTC v9.0.
- Reviewer's fresh cache got a NEW gfx1100 ukdb whose kernel_hash entries are
  IDENTICAL to the claim run's (deterministic RTC output); decompressed blob
  = ELF AMD GPU gfx1100 with symbols KthvalueFwd + KthvalueFwd.kd — i.e.
  compiled at runtime from MIOpenKthvalue.cpp (no code object shipped in
  install/baseline; find confirmed none).
- Source chain verified in tree: kthvalue_api.cpp:73 -> kthvalue.cpp:70-71
  (KthvalueFwd) -> solver/kthvalue/forward_kthvalue.cpp:88
  (kernel_file=MIOpenKthvalue.cpp) -> MIOpenKthvalue.cpp:37 (#include
  "radix.hpp").
- Wheel libMIOpen also exports miopenKthvalueForward (expected); LD_PRELOAD
  binding deterministically selected the source-built one (dladdr in-stream).
- Dumps: 100 expected values, slice0 -60.25/idx 263 matches; constant-per-slice
  values are correct by construction (same permutation value set per slice;
  indices vary and matched exactly). Reviewer's dumps byte-identical (cmp).
- Cache isolation: per-leg runtime/<leg>-cache/<label> roots verified; A/B
  caches cannot mix.

## Findings
- NIT — wrapper allowed reuse of non-empty cache dirs. RESOLVED:
  run_validation_leg.sh now refuses non-empty cache dirs unless
  FRESH_CACHE_FORCE=1.
- NIT — "blob=4232B" is the bzip2-compressed stored size (uncompressed 9208B).
  Cosmetic; evidence JSON wording accepted.

Gate G06 verdict: PASS (baseline-only; no patched claims made — scope honest).
