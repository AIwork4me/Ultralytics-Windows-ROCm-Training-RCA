# R33 Reviewer A — MIOpen maintainer merge-readiness review

Reviewer: fresh-context subagent (agent_3969dd09) against HEAD d758aed7
(pre-R33-fix interim). VERDICT: CONDITIONAL PASS — 2 MAJOR, 6 MINOR, 4 NIT.

## MAJOR findings → RESOLVED (commit 3 regenerated as f18c4de9; identities
regenerated: tree b983cadd, patch 0003 df7c3c3a…, series 48308f6d…; all
affected gates re-run: CI integration, clean-env ctest, matrix 13/13, BF16
parity, DLL rebuild + runtime + YOLO revalidation):

1. Linux PATH corruption: PATH prepend used the Windows `;` separator
   unconditionally → on Linux the test env got one garbage entry (latent:
   test execs nothing, RPATH resolves, but semantically wrong + unvalidated
   leg). RESOLUTION: derivation + append now wrapped in `if(WIN32)` —
   non-Windows tests keep the inherited environment (exact helper parity);
   comment states the Windows-loader rationale. Windows fix re-verified:
   clean-env ctest Passed rc 0 on f18c4de9.
2. Coverage overclaim: block comment claimed the test guards "runtime-
   compiled kernels stay self-contained" while positive mode compiles only
   MIOpenBatchNormFwdTrainSpatial.cpp (miopen_type_traits closure); the
   utility/radix/tensor_view sites have no default-suite coverage.
   RESOLUTION (within mission scope — test C++ source immutable): comment
   rescoped to "the kernel whose RTC failure reported the bug … the other
   self-containment sites belong to the A/B validation harnesses, like the
   negative control". PR draft updated likewise. (Extending the compile set
   would require modifying hiprtc_selfcontained.cpp — outside this
   mission's frozen scope; noted as future-upstream option.)

## MINOR findings → resolutions
1. Unqualified `#3803` in commit-1 message GitHub-links to the wrong repo's
   issue → PR draft now carries a repo-scope clarification (commit hashes
   frozen; regenerating identities for a message nit is not justified).
2. Internal artifact reference ("Phase-3 canary G57-7") in
   miopen_freestanding_initializer_list.hpp → kernel headers are production
   source (out of edit scope); PR-draft reviewer-notes section rephrases
   the provenance neutrally.
3. Copyright holder vs AMD convention → expected maintainer question;
   RIGHT_TO_CONTRIBUTE documented (carried from R1).
4. MIOPEN_USER_DB_PATH parity on a MIOpen-less test → documented NIT.
5. PR-draft mechanism mislabel (radix/tensor_view) → PR draft corrected
   (radix = miopen_cstdint + __INT32_MAX__/__INT64_MAX__; tensor_view =
   freestanding initializer_list fallback; utility = __has_include
   fallbacks).
6. Skipped-test stderr suppression → PR draft notes ctest -VV.

## NITs: clang-format continuation indents (formatter run deferred to
submission day — repo-pinned clang-format 18.1.4 venv documented in phase-5
evidence), std::isdigit, footer_error_count scan-width, adjacent
MIOPEN_HIP_RUNTIME_COMPILE conditionals in radix.hpp — none blocking;
production headers outside this mission's edit scope.

Post-fix re-verification performed by the primary agent on f18c4de9
(configure/build/ctest/clean-env/matrix/BF16 all PASS); Reviewer C/D
reviews below run against the FINAL state.
