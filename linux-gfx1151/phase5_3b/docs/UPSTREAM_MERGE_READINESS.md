# UPSTREAM MERGE READINESS — after Phase 5.3B (Linux gfx1151 cross-OS closure)

Candidate: **P5.1-CANDIDATE-R2** (series `48308f6d…`, tree `b983cadd…`).
This mission added a third platform to the R2 validation base: the SAME GPU
architecture as the Windows RCA (gfx1151) under a different OS, plus targeted
coverage beyond the W7900 (gfx1100) validation.

## What the three platforms now jointly establish

| Claim | Evidence owner |
|---|---|
| The no-STL RTC breakage is real and R2 fixes it (FAIL→PASS) | Windows gfx1151 (frozen evidence c841716…) |
| R2 causes no regression on Linux/HIPRTC for kthvalue, batchnorm, YOLO | Linux gfx1100 (W7900) AND Linux gfx1151 (this mission) |
| The portable test builds and reports honestly without workarounds | all three platforms |
| BF16 kthvalue radix arm runs correctly under R2 | Linux gfx1151 (this mission — new) |
| Partial-STL failure class is the patch's designed guard behavior | Linux gfx1151 (real comgr RTC reproduction — new) |

## Technical readiness assessment (maintainer objections ledger)

Objections carried from the W7900 maintainer review and their current state:

- **M1 initializer_list freestanding arm not compile-tested** → ADDRESSED:
  zero-STL offline chain (type_traits+utility+tensor_view+initializer_list)
  compiles from the R2 tree (E3 canary), and the freestanding headers
  genuinely resolve with no std headers reachable (negative control).
- **M2 radix int32/int64 + BF16 untested** → PARTIALLY ADDRESSED: BF16 now
  RUNTIME-validated on both legs (values+indices exact vs CPU); int32/int64
  KEY-encode arms remain static-assert + compile-level only (documented
  limitation, not silently claimed).
- **M3 skip-policy duplication vs add_test_command refactor** → unchanged
  (upstream style preference; candidate-revision note, not a validation gap).
- **M4 no full gtest suite / conv / pooling A/B** → unchanged (out of the
  runtime fix's blast radius; recorded as scope boundary).
- **B1 DCO unsigned / submission authorization** → UNCHANGED, human action
  (explicitly out of this mission's scope; no DCO trailers added here).
- **B2 no-STL positive never executes on Linux** → CONFIRMED as a
  fixture-documented Linux limitation on BOTH 7.14.0 and 7.14.1 wheel stacks
  (stdlib reachable under -nostdinc via the comgr staging dir; independently
  reproduced by an auditor-written driver). The Windows evidence remains the
  no-STL claim owner. PASS_WITH_CTEST_SKIP is the honest verdict form.

## Merge-readiness statement

Technical validation for R2 is now three-platform, two-OS, two-GPU-family,
with byte-exact patch identity proven at every hop and no unresolved
technical BLOCKER/MAJOR findings from any independent reviewer (see
reviews/gate_reviews/ and the H10 panel records). Remaining items before an
upstream PR are governance and producer-side, not validation:

1. DCO/author identity completion (human).
2. Submission authorization (human).
3. Optional producer-side: consider the M3 style refactor and the m1 define
   divergence note during upstream review.

This mission performed NO upstream actions (no PR, no issue, no comment, no
DCO trailers) and did not modify the frozen R2 bytes or any historical
evidence branch.
