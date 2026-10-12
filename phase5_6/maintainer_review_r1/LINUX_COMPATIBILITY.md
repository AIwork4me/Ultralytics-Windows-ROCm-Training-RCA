# G10 — Linux compatibility — 2026-10-12

STATUS: NOT RERUN — ENVIRONMENT UNAVAILABLE (during this mission window).
No Linux hardware was reachable from this session (the W7900/gfx1100 and
gfx1151 Linux environments of phases 5.1-R2/5.5 are remote/unattended).

Predicted Linux behavior of the new gtest (from frozen R2/5.5 evidence of the
equivalent standalone probe and from the production-path mechanics):
- Linux comgr/hiprtc injects host include paths internally; even under
  -nostdinc the STL probe finds <type_traits> (R2 evidence: probe exit-4
  INCONCLUSIVE = "host C++ stdlib still reachable" on gfx1100 and gfx1151).
- Mapping to the new test: P1 (negative probe) FAILS to compile (#error fires),
  P2 (positive ambient probe) COMPILES → the test takes GTEST_SKIP with the
  explicit message "host C++ standard library is still reachable ... the no-STL
  self-containment condition is NOT tested by this run". CTest (4.4.4) renders
  it as "(Skipped)"; JUnit records result="skipped" with that message
  (empirically verified on Windows via the forced-skip variant, g06 logs).
- If some Linux configuration does NOT inject host STL, P1 compiles and the
  main no-STL assertion runs (hard verdict), which is exactly the intended
  capability-aware behavior.

Frozen prior evidence (unchanged, immutable):
- R2 Linux no-regression evidence: series 48308f6d (phase5.1-R2 freeze),
  Kthvalue/BatchNorm compile checks on gfx1100/gfx1151 — see RCA repo
  phase5.1-R2 records.
- The production source-fix payload is byte-identical to the R2-validated
  payload (G09 verified: src/ untouched by this mission's commits).
- Linux CI will exercise the test through the YAML CPU_* tier entries /
  MIOPEN_TEST_ALL lanes; first actual Linux run will come from upstream CI.

Checks NOT rerun on Linux this mission: native gtest build, discovery,
ordinary control, with-STL control, probe classification, Kthvalue/BatchNorm
targeted checks. These remain covered by frozen R2 evidence for the source
payload and by the predicted-skip analysis above for the new test harness.
