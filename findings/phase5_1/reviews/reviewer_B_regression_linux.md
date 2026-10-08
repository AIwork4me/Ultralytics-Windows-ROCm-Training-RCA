# Reviewer B — Adversarial MIOpen/Linux Regression Audit — P5.1-CANDIDATE-R1

- **Reviewer:** B-regression-linux (adversarial; no artifacts of the candidate were produced by this reviewer)
- **Date:** 2026-10-08
- **Verdict:** **PASS**
- **Counts:** BLOCKER 0 | MAJOR 0 | MINOR 1 | NIT 4
- Machine-readable twin: `findings/phase5_1/reviews/reviewer_B_regression_linux.json`

Scope: the final Linux validation is PENDING; this audit covers the governing
handoff (`findings/phase5_1/FINAL_HANDOFF.json` +
`docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md`), the Phase-3 harness/closure
it delegates to, the cited execution chain in the actual candidate source tree,
and the honesty of the Windows evidence under `evidence/phase5_1/`. No Linux
tests were run (Windows reviewer).

## What was independently verified (not taken on trust)

1. **The kthvalue execution chain is real, file:line, in the candidate tree.**
   `miopenKthvalueForward` (src/kthvalue_api.cpp:73 — signature byte-for-byte
   the harness's function-pointer type) → `miopen::KthvalueForward`
   (src/kthvalue.cpp:37; negative `dim` normalized at lines 45–48 exactly as
   the harness's CPU reference does) → `SolverContainer<solver::kthvalue::KthvalueFwd>`
   (kthvalue.cpp:71, registered at solver.cpp:649) → `KthvalueFwd::GetSolution`
   (src/solver/kthvalue/forward_kthvalue.cpp:62; `kernel_file =
   "MIOpenKthvalue.cpp"`, `kernel_name = "KthvalueFwd"` at lines 88–89) →
   `src/kernels/MIOpenKthvalue.cpp` (`#include "radix.hpp"` at line 37) →
   **patched** `radix.hpp` (blob `99c29fda…` == manifest; carries the real
   patch: `MIOPEN_HIP_RUNTIME_COMPILE → miopen_cstdint.hpp` vs `<limits>`,
   `__INT32_MAX__`/`__INT64_MAX__`). Every line number cited in the Phase-3
   closure doc (66, 99, 148, 160) matches the file on disk.
2. **The three handoff cases == the harness case table** (kthvalue_runtime_harness.cpp
   lines 436–438): {100,500} FP32 dim=-1 k=10 nokeep; {10,20,300} FP32 dim=2
   k=137 keep; {8,3,10,2000} FP16 dim=-1 k=2000 keep — shape, dtype, dim, k,
   keepDim all identical, fixed seeds. Solver applicability
   (`rank≥2 && dimStride==1 && dimSize≥300`) is satisfied by all three
   (500/300/2000, contiguous innermost), and `ExecutePrimitive` uses exactly
   one solver — no find/perf-DB path, no silent fallback.
3. **Patch/series hashes recomputed from disk** — all three patch SHA256s and
   the `sha256_file_concat_v1` series hash (`797a69b5…`) match the manifest.
   Candidate worktree `HEAD^{tree}` == `605d0d21…` (manifest head tree);
   pristine worktree confirmed at base `7c586614`; `git_am_roundtrip.json`
   `source_tree_match=true`; independent freeze review: 14/14 PASS including
   3-way reconstruction (git am / git apply / index-only).
4. **Required proof artifacts exist in source**: "Invoker registered … solver"
   (invoker_cache.cpp:115), "kernel_name = …, global_work_dim = {…}"
   (hipoc/hipoc_kernel.cpp:80–82), LoadBinary/SaveBinary cache messages
   (binary_cache.cpp) — see MINOR finding for the catch.

## Check results (14 checks, all PASS; 1 PASS_WITH_MINOR)

| # | Check | Result |
|---|---|---|
| 1 | Direct `miopenKthvalueForward` chain real in candidate tree | PASS |
| 2 | Handoff's 3 cases match harness case table; solver-applicability satisfied | PASS |
| 3 | dladdr on exact pointer + LD_PRELOAD isolation + fresh `MIOPEN_CUSTOM_CACHE_DIR` per run required | PASS |
| 4 | Kernel compile+dispatch log evidence required (invoker, kernel_name, RTC Load→compile→Save) | PASS (MINOR B-M1) |
| 5 | Wrong-candidate isolation: patch/series/tree SHA verification BEFORE build, fail-closed language | PASS |
| 6 | Both source-built UNPATCHED+PATCHED libs; byte-for-byte A/B; values AND indices vs CPU; real exit codes/logs | PASS |
| 7 | HIPRTC ctest AND runtime both in minimum set; negative exact-signature control on unpatched tree | PASS |
| 8 | CI matrix 13/13 with real exit codes (incl. expected-fail exit 1 cells and INCONCLUSIVE exit 4) | PASS |
| 9 | build_provenance `source_git_head` == `e7ff6d75…` (exact final source of the DLL) | PASS |
| 10 | runtime provenance sha == build sha; no-STL env-scrubbed run; pre-fixed tolerances | PASS |
| 11 | YOLO AMP honesty: `amp_genuine=false` recorded; AMP-check failure disclosed | PASS |
| 12 | AMP-check attribution control sound (P5 DLL + pristine wheel both fail in current env) | PASS |
| 13 | `linux_validation_status` PENDING everywhere; no premature claims; no conclusion.json | PASS |
| 14 | Wrong candidate cannot plausibly reach Linux testing under these instructions | PASS |

## Findings

### B-M1 (MINOR) — Log-evidence env var not pinned in the handoff

All three required proof lines are `MIOPEN_LOG_I2` (Info2). Per
`src/logger.cpp` `IsLogging()`, an NDEBUG/RelWithDebInfo build with
`MIOPEN_LOG_LEVEL` unset caps at **Warning** — none of the lines print. The
handoff never mentions `MIOPEN_LOG_LEVEL=6`/`MIOPEN_ENABLE_LOGGING`. An
operator following it literally would capture logs without the mandated
dispatch evidence (blocked/false-fail risk; not a false-PASS risk since absent
lines = unmet proof under the fail-closed rules). **Fix:** add "run with
`MIOPEN_LOG_LEVEL=6` and require the three lines in the captured log" to
handoff item 3.

### Nits

- **B-N1** — handoff doesn't restate the Phase-3 constraint "identical harness
  binary sha256 on both A/B sides" (nor pin the harness source sha).
- **B-N2** — manifest key `yolo_train_amp_default: "PASS"` is skim-misleading;
  the `yolo_amp_note` disambiguates (amp_genuine=false, FP32 fallback). Honest
  as written.
- **B-N3** — `ci_integration.json` has null `test_exe`/`test_exe_sha256`
  (sha lives in ci_matrix); the CPATH/INCONCLUSIVE cell doesn't record the env
  delta that produced it.
- **B-N4** — handoff writes unanchored `ctest -R test_hiprtc_selfcontained`;
  the Windows evidence used `^test_hiprtc_selfcontained$`. Use the anchored
  form for parity.

## Windows evidence honesty — summary

No exaggeration found. The 13-cell CI matrix records real exit codes including
the expected failures (positive/unpatched exit 1 with the exact
`'type_traits' file not found` signature at miopen_type_traits.hpp:151;
negative/patched exit 1 rejecting the expectation; setup-error cells exit 2;
STL-reachable guard exit 4). The DLL was built from the exact final commit
(`e7ff6d75…`) and every runtime artifact (BN numerics, no-STL run, both YOLO
runs) proves in-process provenance sha `9a7744029ccd…` == the built DLL, with
the wheel DLL hash-verified restored. The AMP story is disclosed, not spun:
`amp_genuine=false`, the ultralytics AMP check fails, and the control
experiment shows the previously-passing P5 DLL and the untouched wheel DLL fail
identically in the current environment — environment drift, not a P5.1
regression.

## Conclusion

The handoff genuinely tests the patched radix path directly through the public
API with identity-gated, cache-isolated, provenance-proven A/B methodology, the
minimum set covers both the HIPRTC-ctest and runtime surfaces with the
negative exact-signature control, and Linux status is PENDING everywhere it
should be. The single MINOR gap (logging env) is an instruction-completeness
fix that should be folded in before the Linux run executes, but it does not
change the verdict on the candidate or the validation design.
