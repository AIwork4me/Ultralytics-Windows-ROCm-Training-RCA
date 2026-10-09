# Gate Reviews B07 + B09 — Independent Subagent Audits (W7900-PHASE52-BRIDGE-R1)

## B07 — Independent dynamic-library contamination audit

VERDICT: **PASS** (no BLOCKER/MAJOR)

Reproduced independently:
- static env: 0 /opt/rocm in PATH/LD_LIBRARY_PATH; CMakeCache grep 0
- dynamic auditor re-run (fresh cache label): exit 0, identical dladdr
  provenance, NO_/opt/rocm_IN_maps: PASS, 22 ROCm objects all venv/source
- auditor's OWN cross-check program (plain dlopen, NO LD_PRELOAD):
  miopenCreate=0, source-built lib provenance, maps scan NONE
- LD_DEBUG=libs resolution-order proof: LD_LIBRARY_PATH (venv) precedes the
  ldconfig cache (which does map some ROCm sonames to /opt/rocm-7.2.1)

Findings + resolutions:
- MINOR-1 ldconfig latent mapping: documented in evidence; only reachable by
  processes launched WITHOUT env_rocm7141.sh (forbidden by runbook).
- MINOR-2 wheel-shadowing guard is load-bearing (auditor's adversarial demo:
  soname dlopen without the wrapper resolves to the wheel): encoded as a
  hard rule in FINAL_AB_VALIDATION_RUNBOOK.md (all legs must go through
  run_validation_leg.sh).

## B09 — MIOpen kernel-path provenance audit

VERDICT: **PASS** (no BLOCKER/MAJOR)

Reproduced independently:
- all three sha256 identities (source copy / phase-3 original / binary)
- ldd: no MIOpen/HIP link-time deps (dlsym RTLD_DEFAULT design)
- typedef matches frozen-base miopen.h param-for-param; no dlopen in source
- git diff between bases: projects/miopen/include/ ZERO changes; kthvalue
  kernel+solver unchanged
- determinism verified: fixed seeds, tie-impossible values, zero-init
  outputs, CPU re-check post round-trip, dump files
- SANITY RUN on the unpatched baseline (allowed): exit 0, HARNESS_RESULT
  PASS, dladdr -> install/baseline, FindSolutionImpl KthvalueFwd,
  LoadBinary miss -> HIPRTC compile -> SaveBinary (FP32+FP16), 3/3 cases
  value/index mismatches 0. Log: logs/b09_audit_run.log

Findings + resolutions (all NITs, all fixed):
- NIT-1 FRESH_CACHE_FORCE silent override -> now prints explicit
  "FRESH_CACHE_FORCE=1 OVERRIDE ... NOT fresh-cache-grade evidence" warning
- NIT-2 wrapper did not print harness binary sha256 -> wrapper now prints
  sha256 of the first executable file argument (the A/B invariant)
- NIT-3 frozen leg install dir unreachable by wrapper -> run_validation_leg.sh
  now supports leg name 'legA-frozen' (install/legA-frozen-baseline);
  'baseline' kept as the historical b68f894 preflight leg; 'patched'
  reserved for Leg B
