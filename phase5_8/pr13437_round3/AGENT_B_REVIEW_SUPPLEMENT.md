# Agent B — Closure Re-review and Final Acceptance Supplement

Date: 2026-10-17 (Asia/Shanghai). This supplement supersedes inaccurate interpretations in the initial `EVIDENCE_CLAIM_AUDIT.md`; it does not rewrite the historical recorded audit or original scripts.

## Current review status

- Production semantic review: **PASS; freeze d4b574ac8a039f39976c5f9f4e18adcb074dc237.** No production edits or GPU reruns were needed.
- Phase 2 corrected claim review: **conditional pending the final edits listed below** at this intermediate reread.
- Phase 5 final integrity: **PENDING** final frozen manifest and committed payload review.

## Corrections independently confirmed

Re-read corrected README, functional matrix, performance report, gfx942 RCA, cross-platform review, historical final audit, reproduction guide and PR-facing drafts from the actual evidence working tree.

1. No-STL positive now distinguishes three isolated and two ambient compiles; PASS/no-SKIP and the original negative signature remain supported.
2. The functional matrix records AMD Clang 23.0.0git and explains that the runtime label is not alone a clean-source attestation.
3. BatchNorm A/B statements generally identify matching printed error summaries, not tensorwise identity. Running-variance estimator limitation is explicitly documented and executed script preserved.
4. FP32 end-to-end success is explicit. AMP fails for all three controls; no AMP training PASS or proven environmental root cause is asserted in the current summary.
5. The swap provenance now describes trap-based restoration with actual archived restored hashes.
6. Generated-code evidence is scoped to ten retained ELF artifact pairs. Kthvalue cache extraction is reproducible; the seven BatchNorm pairs lack archived originating cache rows/options, so their source association relies on original labels/narrative. ISA identity does not exclude all performance effects.
7. YOLO paired performance remains NOT_RUN. Cold and sub-ms timings remain INCONCLUSIVE; parent is incorporating additional GPU-bound timer-invalidity findings.
8. Reproduction guide identifies pinned source SHAs, the intentionally injected baseline regression test, historical machine-specific paths, dependencies, expected verdicts, safeguards when adapting cache/swap runners and independent offline verification.
9. Current-head Linux testing is not claimed complete. gfx942 remains a hypothesis with no matched develop/PR comparison.
10. Historical agent verdicts are explicitly historical. Current closure is not represented as maintainer approval or completed upstream CI.

## Additional raw-log findings that supersede the initial audit

### gfx942 output replay is not a demonstrated immediate retry

The initial audit repeated the package's claim of a retry; that interpretation is incorrect. Agent C challenged it, and Agent B independently checked `raw/ci/gfx942_job.log`:

- Line 3526 executes one `ctest ... -V --output-on-failure` invocation.
- Lines 3919–3922 show last completed softrelu id_43, start of id_47, GPU Hang and subprocess abort after 38.80 seconds.
- Lines 4299–4302 replay the same id_43 result (same 427 ms), id_47 and GPU Hang within approximately 18 milliseconds of output replay start.
- Line 4311 still records total test time 38.80 seconds. This is consistent with verbose streaming plus output-on-failure replay, not evidence of a second execution.

No immediate retry or deterministic repeat hang is established by this log. The gfx942 failure remains unresolved regardless of this correction.

### Actual CI offline compilation is not established by direct include inspection

`C:/w58/projects/miopen/CMakeLists.txt` lines 303–315 default COMGR/HIPRTC on for the HIP backend; `src/comgr.cpp` line 805 adds `-DMIOPEN_HIP_RUNTIME_COMPILE` on the HIPRTC path. A direct grep of kernel includes or this test job log does not establish the actual build configuration. Unless a retained TheRock configuration proves offline compilation, the RCA should state the conditional selection behavior rather than assert that these kernels actually compiled offline. Source inspection still finds no direct dependency on modified headers in the listed BN/Activation inference source path.

### GPU-bound timing is also inconclusive

The final retained `perf2_B_3.log` includes a negative CUDA-event minimum for backward `(32,256,56,56)` (`min_ms=-3.21978`), in addition to negative sub-ms measurements in the other legs. This invalidates using a clean-PASS classification for GPU-bound warm performance. Report medians as limited observations only; no confirmed material regression does not establish non-regression. Retain original data and disclose the timer anomaly.

## Outstanding edits at intermediate reread

1. Remove duplicated Running-stat reference limitation section from the functional matrix.
2. Replace unsupported literal “782/782” completion count with recorded `build rc=0`; explicitly cite the two ambient runtime controls as host-STL coverage.
3. Qualify the PR-facing BatchNorm running-stat row with the biased-reference limitation or direct link to it.
4. Remove all current warm BatchNorm PASS classifications; incorporate the negative GPU-bound minimum and use INCONCLUSIVE. Fix malformed sentence about “GPU machine code Round-3 ships” to describe retained artifacts only.
5. Replace retry/determinism interpretation with the ctest replay interpretation above; correct historical broad wording by a conspicuous supplement where preserving the original report.
6. Qualify actual-CI-offline statements unless configuration evidence is archived. Retain conditional offline/STL selection reasoning and the absent matched gfx942 comparison.

The report will receive a final acceptance entry only after the final files and manifest are frozen and independently re-read. This intermediate supplement is not a publication approval.

## Additional correction from original swap transcripts

The initial audit's blanket archived-swap restoration statement was too broad. D/F/AMP
functional transcripts show successful hash restoration, but abandoned perf_bn swap/restore
attempts include busy-file errors and retained A's library. Those B-labelled measurements
are invalid and excluded. Later A restoration succeeded; final perf2 timings preload
per-process libraries and are independently limited by their negative timer minima.
