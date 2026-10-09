# PHASE 5.3 SUMMARY — Linux W7900 Final R2 A/B Validation

Mission ID: **W7900-PHASE53-R2-FINAL-AB**
Candidate: **P5.1-CANDIDATE-R2** (Windows-frozen, evidence commit `c8417161125dc33275b7ac615298b449a81e7cf8`)
Host: AMD Radeon PRO W7900 (gfx1100, marketing name W7900D), Ubuntu 24.04.4, ROCm 7.14.1
isolated wheel SDK, PyTorch 2.12.0+rocm7.14.1. System ROCm 7.2.1 remained isolated (zero
contamination in every runtime gate).

## FINAL VERDICT

**PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP**

All required Linux build, runtime, and numerical checks PASSED. The single test limitation
is the genuine, fixture-documented Linux no-STL isolation unavailability (ROCm 7.14.1
libhiprtc-builtins embeds the C++ headers): the R2 regression test's own probe reports
INCONCLUSIVE (exit 4) and CTest renders **Skipped / Not Run** with process exit 0 — never
counted as a no-STL PASS. The Windows no-STL evidence remains the Windows RCA's claim.

## Gate results (each with an independent fresh-subagent review; see reviews/)

| Gate | Scope | Result |
|---|---|---|
| L00 | Environment reconciliation | PASS (legA lib + harness hashes pre-verified; disk gated) |
| L01 | R2 evidence identity | PASS — patch identity 25/25; handoff 39/39 (1 documented tree-identity substitution); all hashes independently verified |
| L02 | R2 handoff consumer + adversarial matrix | PASS — 20/20 (16 required checks + regression tests) |
| L03 | Frozen source reconstruction | PASS — git am AND git apply→write-tree both produce tree `b983cadd…`; 10/10 blobs |
| L04 | Leg A frozen baseline audit | PASS — frozen binary reused, sha `7e045dc0…` |
| L05 | Leg B (R2) build | PASS — no manual CTest workarounds needed; semantic CMake identity with Leg A |
| L06 | Dynamic library provenance | PASS — in-process dladdr both legs; 0× 7.2.1 contamination after real GPU init |
| L07 | CTest portability | PASS — target builds w/o workarounds; ctest Skipped rc 0; ordinary/with-stl PASS; exit-code fixture 0/1/2/4 verified |
| L08 | Direct Kthvalue A/B | PASS — 3/3 cases both legs, 0 mismatches, 15/15 byte-identical dumps, fresh caches, dispatch proven |
| L09 | BatchNorm fwd/bwd | PASS — all 6 checks with 4–6 orders of margin, identical both legs, direct public API |
| L10 | Optional YOLO26n smoke | EXECUTED/PASS — in-process proof of patched-MIOpen binding; amp=False |
| L11 | False-pass attack matrix | PASS — 14/14 (incl. real-checker A15 after review) |
| L12 | Four-reviewer panel | A: CONDITIONAL PASS (upstream-governance scoped), B/C/D: PASS |

## Key identities

- Upstream base: `7c5866144ac4b879be442563e2b49fa1c142ea36` (tree `8b0bf035…`)
- R2 tree: `b983caddf9f9f561e7d1b590deadb16267c2de15` (reconstructed by 3 independent methods)
- Patch SHA256s: `816946b4…`, `46044d8c…`, `df7c3c3a…`; series concat: `48308f6d…`
- Leg A libMIOpen: `7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d`
- Leg B libMIOpen: `bf21a5fa4abc5ff77b0f50756a69dccf7a077970603a846300f0ea077d61eac1`
- Kthvalue harness: `b830b37a5aa7aef37da8c79e3ceb30435fd631b99dda29516f2ed36c152e7ef8`

## ERRATUM (published Phase-5.2 artifacts)

`linux-w7900/phase5_2/evidence/B08_ab_readiness.json`,
`B09_kthvalue_harness_handoff.json`, and
`linux-w7900/phase5_2/docs/FINAL_AB_VALIDATION_RUNBOOK.md:82` carry the harness hash with a
trailing `f` (65 hex chars — not a valid SHA-256). The true digest is the 64-char value
above; the published strings are a transcription typo (length analysis in
`evidence/L00_environment.json`, `harness_identity_note`). Historical published artifacts
are intentionally NOT rewritten; this erratum is the correction of record.

## Boundary statement

This mission proves: R2 builds on Linux gfx1100; runtime behavior is preserved (no
regression) in the covered workloads; the CTest portability fixes work honestly on Linux.
It does NOT reproduce the Windows no-STL failure and does not certify DCO or authorize any
upstream action (frozen manifest remains `linux_validation_status: PENDING`, owned by this
Linux evidence branch per the R2 handoff's reporting rules).
