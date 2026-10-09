# OPEN ISSUES after Phase 5.3B

1. (governance, human) DCO/author identity and submission authorization for
   the R2 series — unchanged, owned by the producer.
2. (upstream review, minor) M3 skip-policy duplication vs an
   add_test_command-style refactor; m1 test-define divergence from
   production RTC defines — candidate-revision notes; do NOT modify frozen
   R2 for these without a new freeze cycle.
3. (coverage, residual) radix int32/int64 KEY-encode arms have only
   static-assert + compile-level closure (runtime covered for FP32/FP16/BF16
   encode arms and 64-bit index outputs).
4. (fixture, documented) Linux no-STL isolation unavailability on ROCm 7.14.x
   wheel stacks (both 7.14.0 and 7.14.1 observed) keeps the positive no-STL
   control Skipped on Linux CI; the Windows RCA owns that claim. An upstream
   CI image with a genuinely STL-free hipRTC environment would be needed to
   run it on Linux.
5. (erratum candidate, other branch) the W7900 summary's "4-6 orders of
   margin" phrase for BatchNorm is inaccurate (true margins 1.4-7.6 orders);
   flagged back to that branch by the H09 audit; no verdicts affected.
6. (environment, this mission) H01 adversarial test 16b (consumer --apply
   full-checkout positive) not executable on this machine's intentionally
   partial object store; compensating controls recorded (three independent
   tree reconstructions). A full clone would close it mechanically.
