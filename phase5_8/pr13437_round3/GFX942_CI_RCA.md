# GFX942 CI FAILURE — ROOT-CAUSE CLASSIFICATION (Phase 7)

**Failing run:** [TheRock Multi-Arch CI #38596620066](https://github.com/ROCm/rocm-libraries/actions/runs/38596620066) (PR #13437 @ f0f330c4, 2026-10-14T16:16Z push; failure logged 2026-10-15T20:12Z)
**Failing job:** [116645608429](https://github.com/ROCm/rocm-libraries/actions/runs/38596620066/job/116645608429) — `Linux::release / Test gfx94X-dcgpu / Test miopen / Test miopen (shard 3/4) (gfx94X-dcgpu)`

## 1. What actually happened (from the full job log, [archived job log](raw/ci/gfx942_job.log))

- `miopen_gtest_standard_suite`, shard 3/4 of 4, 5660 tests, PRNG seed 12345678, timeout 3600s.
- **Last completed test** (20:12:23.58Z): `Standard/GPU_bn_activ_infer_per_act_FP32.PortTest/BNPerActivation_NHWC_N64_C256_H14_W14_softrelu_test_id_43` — OK, 427 ms.
- **Hung test** (started 20:12:23.58Z): `Standard/GPU_bn_activ_infer_per_act_FP32.PortTest/BNPerActivation_NHWC_N64_C512_H28_W28_softrelu_test_id_47`.
- 20:12:32.63Z: `HW Exception by GPU node-3 (Agent handle: 0x62c17e0b8d90) reason :GPU Hang` → `Subprocess aborted`, 38.80 s into the suite.
- **Only one failed invocation is established.** The later `GPU Hang` text is ctest's failure-output replay (`-V --output-on-failure`), not evidence of a second execution. Earlier tests reappear with identical durations while their replay is emitted in milliseconds; total test time remains 38.80 s. The initial report's immediate-retry/determinism inference was incorrect and is withdrawn.
- The failure is a **hardware exception reported by the runtime**, not a software assert, compile error, or numerical mismatch. It is NOT the original `'type_traits' file not found` defect class.

## 2. Kernel-path analysis

The hung test exercises MIOpen BatchNorm+Activation **inference**, per-activation, FP32, NHWC
(N64 C512 H28 W28), softrelu. Kernel sources on this path:
`MIOpenBatchNormActivInfer.cpp`, `MIOpenBatchNormFwdInferPerAct.cpp`,
`MIOpenBatchNormFwdInferSpatial.cpp` (+ activation fusion helpers).

- **None of these sources include any header modified by this PR**
  (`miopen_type_traits.hpp` / `miopen_utility.hpp` / `miopen_initializer_list.hpp` /
  `tensor_view.hpp` / `radix.hpp`) — verified by grep over `projects/miopen/src/kernels/`.
  `tensor_view.hpp` consumers: Getitem, Kthvalue, MultiMarginLoss, PReLU, ReduceSum,
  SoftMarginLoss — no BatchNorm.
- The actual TheRock compile mode/STL reachability is not established by this log.
  Offline compilation would use real standard headers; runtime compilation also selects
  them when reachable. MIOpen can use COMGR/HIPRTC, so the earlier assertion that this
  CI invocation was certainly offline is withdrawn. Direct header-dependency inspection
  remains useful but does not exclude indirect effects.
- The earlier `Standard/GPU_bn_activ_infer_per_act_FP32` cases in the same shard
  (C2048, C64, C256 variants, logistic/tanh/relu/softrelu) all PASSED on the same binary
  — including the immediately preceding softrelu C256 case.

## 3. Baseline / fleet comparison (live GitHub queries, 2026-10-16)

| Evidence | Detail |
|---|---|
| Develop nightly (41cbd75e, 2026-10-15) | FAILED — `Test gfx125X-dcgpu / Test Sanity Check / Test sanity` (hardware-class flake on a *sanity* run; run 38697600236) |
| Develop nightlies 2026-10-11…10-15 | 5 consecutive `schedule` runs all failed |
| Unrelated PR runs same day | 38897643230: hipkernelprovider shards fail (gfx110X + gfx94X); 38861155255 (develop push b3eca660): hipkernelprovider gfx110X+gfx94X; 38895794439: rocsparse + rocfft + hipkernelprovider |
| Repo state | A `TMP gfx942 thread diagnostic` workflow (id 335832155) exists — maintainers are actively chasing gfx942 runner instability |
| Same test on develop? | No matching green/red pair isolatable from available logs; nightly jobs listing partially blocked by API 502s — **disclosed, not hidden** |

## 4. Reproducibility

- No gfx942 Linux runner is accessible from this Windows machine → **baseline A/B on gfx942
  NOT executed** (mission §12 forbids claiming otherwise).
- The exact TheRock reproduction command (from the job log) for a maintainer with runner access:
  ```
  python build_tools/github_actions/reproduce_test_failure.py --run-id 38596620066 \
    --repository ROCm/rocm-libraries --amdgpu-family gfx94X-dcgpu \
    --test-script "python build_tools/github_actions/test_executable_scripts/test_runner.py" \
    --amdgpu-targets gfx942 --output-dir "./build" --shard-index 3 --total-shards 4 \
    --test-type standard --fetch-artifact-args="--blas --miopen --rand --tests"
  ```

## 5. Classification

**LIKELY_INFRASTRUCTURE — reasoned hypothesis, not a proven root cause.** Reasoning:

1. Failure mode is a runtime-reported GPU hang. This alone does not distinguish hardware, infrastructure, runtime or code causes.
2. No direct modified-header dependency was identified in the analyzed inference source
   path. The actual compile mode and indirect runtime effects were not fully established.
3. The same runner fleet shows contemporaneous failures in unrelated components
   (hipkernelprovider, rocsparse, rocfft, gfx1250 sanity) across unrelated PRs and on
   develop itself; maintainers run a gfx942 diagnostic workflow.
4. Same-suite siblings of the hung case passed seconds earlier on the same binary.

Not classifiable as `BASELINE_FAILURE` (the identical test was not observed failing on a
matched develop run in available logs) and not established as `RELATED_REGRESSION` (no direct dependency on modified headers was
identified in the analyzed kernel path). Residual uncertainty acknowledged: GPU hangs can be
triggered by timing/occupancy shifts from unrelated code changes; a matched develop-versus-PR test on gfx942 is still needed to assess that residual — requested below.

## 6. Scope restrictions honored

No changes to TheRock CI definitions, BatchNorm algorithms, rocProfiler, drivers, scheduling,
or timeouts. No CI override requested. The ask to the maintainer (Phase 10 reply): rerun the
failed job (or approve TheRock on the new head) and, if it recurs, compare the same shard on
develop.

**Gate B+D: PASS (review)** — classification is evidence-based, reproducer command recorded,
residual risk disclosed rather than assumed away.
