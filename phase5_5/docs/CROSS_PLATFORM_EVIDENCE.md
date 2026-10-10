# Cross-Platform Evidence Map — Phase 5.5 Upstream PR Submission

This PR's validation rests on three platforms. Their claims are kept strictly
separate: **Linux source A/B validates the frozen R2 payload and provides
no-regression evidence only** — it is not a claim that the latest-develop
replay tree was independently rebuilt on Linux. Windows is the authoritative
positive no-STL environment.

## Platform A — Windows 11, Radeon 8060S (gfx1151), ROCm 7.14.0 wheel stack

| Evidence | Where | Verdict |
|---|---|---|
| Field failure reproduced (unpatched) | phase5_1_r2 logs; negative/unpatched matrix cell (fb023f80) | exact `'type_traits' file not found` signature |
| Genuine no-STL regression test | `phase5_5/logs/ci/ci_ctest_run.log` (fresh, dcd05f33) + R2/P5.4 logs | **Passed, not skipped** |
| 13/13 adversarial matrix | `phase5_5/logs/ci/ci_matrix_phase5_5.json` (fresh) + P5.4/R2 equivalents | PASS |
| Bare-env ctest (DLL resolution) | `phase5_5/logs/ci/ci_ctest_bare_env.log` | PASS |
| Source-built MIOpen.dll + in-process SHA256 provenance | phase5_4 logs (payload-identical tree) | PASS (dll 44d43887…) |
| BatchNorm fwd/bwd numerics vs CPU | phase5_4 logs (payload-identical tree) | within pre-registered tolerances |
| YOLO26n coco8 1-epoch (amp=False) | phase5_4 logs | PASS |
| YOLO26n coco8 1-epoch (default AMP, genuine that run) | phase5_4 logs | PASS; AMP precheck is environment-flaky and NOT claimed as the fix's effect |

AMP disclosure: the frozen-R2 default-AMP leg once fell back to FP32
(precheck failure); the P5.4 latest-develop replay completed genuine AMP. Raw
logs for both preserved. No causal claim is made either way.

## Platform B — Linux, Radeon PRO W7900 (gfx1100), ROCm 7.14.1

Branch `linux-w7900/phase5_3-r2-final-ab`, evidence SHA `166c33de…`, verdict
`PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP` (merged via RCA PR #8).

- Exact R2 source identity; unpatched/patched source-built MIOpen A/B.
- Kthvalue 3/3, BatchNorm 6/6 — no numerical regression.
- YOLO26n patched-MIOpen smoke PASS.
- Ordinary / with-STL controls PASS.
- **Linux no-STL CTest: legitimately SKIPPED** — real STL isolation
  unavailable on that toolchain (probe-documented, exit 4 semantics).

## Platform C — Linux, Radeon 8060S (gfx1151), ROCm 7.14.0

Branch `linux-gfx1151/phase5.3b-r2-crossos-closure`, evidence SHA `c486ec20…`,
publication SHA `29b19def…`, verdict `P53B_GFX1151_R2_CROSSOS_PASS_WITH_CTEST_SKIP`.

- Frozen-R2 source tree reconstruction; Kthvalue 3/3 and BatchNorm 6/6 A/B.
- **BF16 Kthvalue real-GPU execution PASS.**
- Freestanding `initializer_list` canary PASS; tensor_view/radix RTC
  compilation controls PASS.
- YOLO26n 1-epoch patched-MIOpen smoke PASS; correct source-built libMIOpen
  binding verified.
- **Linux no-STL CTest: legitimately SKIPPED** (same probe semantics).
- Disclosure: local H01 adversarial matrix was **19/20** — one
  environment-limited control not executable due to the local partial Git
  object store. Not described as 20/20.

## Submission-day (Phase 5.5) fresh Windows revalidation

`phase5_5/evidence/submission_windows_validation.json` — configure/build/
ctest/matrix/bare-env all PASS on the actual submission candidate
`dcd05f33` (base `fb023f80`), 2026-10-10. Patch payload delta from frozen R2:
NONE (10/10 blob-identical; series `abbe7b89…` vs R2 `48308f6d…`).
