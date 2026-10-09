# UPSTREAM MERGE READINESS — Linux Phase 5.3 Conclusion

## Verdict

The exact Windows R2 candidate (P5.1-CANDIDATE-R2, tree `b983cadd…`) is **technically
ready for upstream submission FROM THE LINUX PERSPECTIVE**, subject to the explicit
conditions and boundaries below. No upstream action was taken (no PR, no issue/comment,
no DCO sign-off) — all remain unauthorized by design.

## Linux evidence supporting readiness

1. Builds cleanly on Linux gfx1100 with ROCm 7.14.1, no manual workarounds.
2. The three CI-portability defects found in R1 (F-C2-1/2/3) are fixed and empirically
   verified: capability-aware `hiprtc::hiprtc` link builds without include/link hacks;
   direct `add_test` + `SKIP_RETURN_CODE 4` yields honest Skipped semantics with ctest
   rc 0; restricted-list policy parity preserved (BF16 configure re-checked).
3. No regression in covered workloads: kthvalue (3 cases, byte-identical A/B dumps) and
   BatchNorm fwd/bwd (6/6 within predeclared tolerances, identical A/B), plus a
   patched-MIOpen YOLO26n end-to-end smoke.
4. Source identity chain is airtight: patches/series hashes, tree reconstruction by three
   independent methods, per-file blob identity, wrapper authenticity vs the published
   Phase-5.2.1 manifest.

## CONDITIONS PRECEDENT for any upstream PR (human/governance actions, out of Linux scope)

- **DCO**: commits are UNSIGNED_BY_DESIGN; `authorization_to_submit_upstream` is false in
  the frozen manifest. A human must provide Signed-off-by and update the candidate
  manifest on the Windows side before submission (Reviewer A B1).
- **No-STL positive control**: must be executed once on an isolation-capable host
  (e.g., the Windows wheel environment that reproduced MIOpen#3956) and attached to the
  PR; on stock Linux it permanently SKIPs (libhiprtc-builtins embeds C++ headers)
  (Reviewer A B2). This is why the Linux verdict is PASS_WITH_CTEST_SKIP, not PASS.

## Coverage boundaries of the no-regression claim (Reviewer A)

- The freestanding `initializer_list` arm is runtime-covered via the A/B harnesses but is
  not compile-tested by the default ctest suite (upstream improvement: extend the
  compile-only test to PReLU/ReduceSum closures).
- Radix int32/int64 encode branches and BF16 kthvalue compiled but not executed by the
  covered cases; BatchNorm non-FP32-spatial variants not A/B'd.
- No full MIOpen gtest suite on the patched leg; no conv/pooling A/B beyond the YOLO smoke
  (B-leg only).
- Likely upstream review objections to pre-empt: skip-policy duplication vs a shared
  helper (refactor request); test define-set divergence from production RTC defines
  (comment or align); permanent-SKIP value on Linux CI (state in PR description);
  copyright header attribution review for the 4 new files.

## Prohibited actions — status

Frozen Windows R2 artifacts: UNMODIFIED. R1/Phase-5.2 history: UNREWRITTEN. Frozen
manifest `linux_validation_status`: still PENDING in the frozen commit (this branch is
the Linux reporting authority per the R2 handoff §6). No DCO. No upstream PR/issue/comment.
