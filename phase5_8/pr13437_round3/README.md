# phase5_8 — PR #13437 Round-3 maintainer-closure evidence (d4b574ac)

Upstream PR: https://github.com/ROCm/rocm-libraries/pull/13437
Round-3 commit under test: `d4b574ac8a039f39976c5f9f4e18adcb074dc237`
("MIOpen: minimize HIPRTC fallback diff per maintainer review", on f0f330c4 / develop b8cf0e7b)
Reviewer: `averinevg`, review #5537906287 ("Thanks, round 2 looks good.") + 8 inline comments.

## Contents

| Path | What |
|---|---|
| `PHASE0_BASELINE.md` | Live PR/CI/threads state, revision identities, environment |
| `PHASE1_COMMENT_MATRIX.md` | All 8 third-round comments → exact changes → verification |
| `ROUND3_CHANGE_JUSTIFICATION.md` | Hunk-by-hunk justification (4 files, +46/−65) |
| `FUNCTIONAL_REGRESSION_MATRIX.md` | B/C/D/E/F results incl. Round-2↔Round-3 numeric identity and AMP triple-control |
| `PERFORMANCE_AB_REPORT.md` | ISA-identity evidence (10/10 kernels), ABBA warm benchmarks, cold-compile data |
| `PHASE6_CROSS_PLATFORM.md` | Linux/cross-platform code-level review + CI evidence categories |
| `GFX942_CI_RCA.md` | gfx942 GPU-Hang classification (LIKELY_INFRASTRUCTURE) + maintainer reproduce command |
| `PHASE8_FINAL_AUDIT.md` | Final minimal-diff audit + independent reviewer verdicts (A/B/C/D) |
| `REPLIES_R3.md` / `pr_body_new.md` | Reviewer-facing replies and updated PR description |
| `raw/` | All run logs (hiprtc, negative control, batchnorm + swap transcripts, kthvalue, yolo incl. AMP controls, perf legs, ISA dumps) |
| `provenance/` | Binary SHA256s (build C:\b58 @ d4b574ac) |
| `build/` | Configure/build logs + toolchain versions |
| `scripts/` | Every script that produced the above (build, runs, swap driver, benchmarks, cache-blob compare) |

## Headline results

- Functional: no-STL gtest PASS (cache label `3.6.2.d4b574ac`), negative control EXPECTED_FAIL
  with exact original signature, BatchNorm A/B vs Round-2 **numerically identical**, kthvalue
  27/27 fresh cache, YOLO26n 1-epoch PASS (AMP-check anomaly reproduced on the pristine
  shipping wheel ⇒ environment condition).
- Performance: FP32/FP16/BF16 kthvalue + 7 BatchNorm training kernels
  **instruction-identical machine code** vs f0f330c4; warm GPU-bound A/B within ±5% (mixed
  sign); sub-ms and cold-compile comparisons classified INCONCLUSIVE (noise), none reproducible.
- gfx942 CI GPU Hang: LIKELY_INFRASTRUCTURE (no causal path — hung test's kernels consume no
  changed header and compile offline in CI; same-day unrelated fleet failures).

Integrity: `SHA256SUMS.txt` covers every file; subtree `.gitattributes` is `* -text`
(byte-exact checkout; see phase5_7 for the CRLF rationale).
