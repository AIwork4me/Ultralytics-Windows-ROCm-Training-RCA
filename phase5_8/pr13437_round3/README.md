# PR #13437 — Round-3 Windows evidence

Upstream: [ROCm/rocm-libraries#13437](https://github.com/ROCm/rocm-libraries/pull/13437).
Tested implementation: **`d4b574ac8a039f39976c5f9f4e18adcb074dc237`**.
Comparator: Round-2 `f0f330c4837a3c4ca9736a8059410cca1a7c2b85`; negative control:
unpatched `b8cf0e7b526f4a25c0623f5b2a4fe41e03ede179` with the regression test injected.
Windows 11, Radeon 8060S / gfx1151, ROCm 7.14.0 wheels, torch 2.12.0+rocm7.14.0.
This package changes evidence only; production code remains frozen.

## Results and limits

| Check | Result | Supporting evidence |
|---|---|---|
| No-STL HIPRTC gtest | PASS; kernel launch/output assertions, no skip; 5 fresh compiles: 3 isolated, 2 ambient controls | [positive log](raw/hiprtc/B_r3_gtest_run.log) |
| Unpatched negative control | EXPECTED_FAIL, original missing `type_traits` signature | [negative log](raw/negative_control/C_r3_pristine_run.log) |
| BatchNorm forward/backward | PASS vs CPU for outputs/gradients; A/B printed error summaries match. Running-variance reference has an estimator limitation | [functional matrix](FUNCTIONAL_REGRESSION_MATRIX.md), [R3 log](raw/batchnorm/D_r3.log), [R2 log](raw/batchnorm/D_r2_ab.log) |
| kthvalue | PASS 27/27, FP32/FP16/BF16; actual first successful run has a historical `warm` filename | [27-case log](raw/kthvalue/E_r3_kthvalue_warm.log) |
| YOLO26n COCO8 one epoch | PASS **FP32** smoke training, finite logged losses and completed validation | [training log](raw/yolo/F_r3.log), [redaction disclosure](provenance/LOG_REDACTION.md) |
| AMP | Precheck anomaly on Round-2, Round-3 and shipping wheel; AMP training unvalidated, root cause unproven | [A](raw/yolo/AMP_A1.log), [B](raw/yolo/AMP_B1.log), [wheel](raw/yolo/AMP_WHEEL.log) |
| Generated code | Ten matched variants have instruction-identical ISA; scoped device-code evidence | [performance report](PERFORMANCE_AB_REPORT.md), [claim audit](EVIDENCE_CLAIM_AUDIT.md) |
| Warm GPU-bound BatchNorm | INCONCLUSIVE timing quality (negative event minima); no confirmed material regression in reported medians | [ABBA legs](raw/perf/), [performance report](PERFORMANCE_AB_REPORT.md) |
| Cold compilation / sub-ms timing | INCONCLUSIVE; drift/noise and small sample | [performance report](PERFORMANCE_AB_REPORT.md) |
| YOLO paired performance A/B | NOT_RUN; no paired performance claim | [performance report](PERFORMANCE_AB_REPORT.md) |
| Current-head Linux / gfx942 | Linux local testing unavailable. Previous gfx942 hang remains a LIKELY_INFRASTRUCTURE hypothesis; matched develop-vs-PR testing missing | [cross-platform limits](PHASE6_CROSS_PLATFORM.md), [gfx942 analysis](GFX942_CI_RCA.md) |

## Review, reproduce and verify

- [Reproduction guide](REPRODUCE.md): pinned sources, environment prerequisites, build/run scripts and offline evidence checks.
- [Claim-by-claim independent audit](EVIDENCE_CLAIM_AUDIT.md): raw logs, source SHA, environment and limitations.
- [Final code audit](FINAL_CODE_AUDIT.md) and [review-thread matrix](REVIEW_THREAD_MATRIX.md): all eight requests addressed, no new implementation change.
- [Retention/security audit](EVIDENCE_RETENTION_AUDIT.md) and [final package audit](EVIDENCE_FINAL_AUDIT.md).
- [Binary hashes](provenance/binary_sha256_b58.txt), [build logs](build/), [scripts](scripts/), [raw measurements](raw/).
- [Current CI snapshot](CI_STATUS.md): on 2026-10-17 all seven major workflows at `d4b574ac` remain ACTION_REQUIRED. Maintainer workflow approval and subsequent real results remain outstanding; local pre-commit does not certify GitHub Actions success. No formal APPROVED review exists.

SHA256SUMS covers all tracked evidence payload files except the manifest itself, whose
version is identified by the Git commit. This includes `.gitattributes`; its `* -text`
rule preserves payload bytes across Windows/POSIX checkouts. Verify from a fresh Git checkout:

```powershell
python phase5_8/pr13437_round3/scripts/verify_manifest.py
```

Historical implementation-round notes (`PHASE0_BASELINE.md`, `PHASE8_FINAL_AUDIT.md`, reply
drafts) preserve earlier snapshots. The closure audits above supply the current interpretation.
Phase 5.7 is retained unchanged.

Raw logs and diff snapshots retain original trailing spaces. The package-local
`raw/** -whitespace` attribute scopes Git whitespace diagnostics to preserve forensic
bytes; it does not change payload hashing, workflow definitions or test execution.
New audit/API records and tools are stored with LF endings.
