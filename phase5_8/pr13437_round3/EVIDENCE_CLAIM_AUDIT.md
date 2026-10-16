# Independent Functional and Evidence-Claim Audit — Agent B

Audit date: 2026-10-17 (Asia/Shanghai). Initial evidence checkout: `b0a52dd14e58af39aecd5c67bd080aeeba43de45`, branch `evidence/pr13437-round3-d4b574ac-windows`. Package paths below are relative to `phase5_8/pr13437_round3/`.

> This is the initial audit, retained to expose findings rather than erase them.
> [Re-review supplement](AGENT_B_REVIEW_SUPPLEMENT.md) corrects its repeated-hang
> interpretation and blanket swap-restoration statement; the current functional matrix,
> performance report and gfx942 RCA state the supported final claims.

## Verdict and scope

- **Phase 1 semantic review: PASS — freeze production at `d4b574ac8a039f39976c5f9f4e18adcb074dc237`.** No new material functional defect found in supported configurations. No production file or binary was modified during this audit.
- **Phase 2 original claims: FAIL pending documentation corrections below.** The no-STL positive and negative controls, BatchNorm forward/backward tolerance results, kthvalue 27/27 and YOLO FP32 smoke completion are supported. Several stronger interpretations in the original documents are unsupported.
- **Phase 5 final acceptance: pending examination of the repaired committed payload.** This report does not certify a future manifest, future CI execution, GitHub approval, or evidence merge.
- No fresh GPU run or wheel swap was performed. This is an audit of original recorded runs, source semantics, existing source/build trees and extant binary bytes.

## Independently examined material

Read the package README, functional matrix, performance report, gfx942 RCA, historical final audit, cross-platform report, source-change justification and PR-facing drafts. Read every functional runner and the relevant benchmark/swap code. Examined original HIPRTC, negative-control, BatchNorm, kthvalue, YOLO and AMP logs and swap transcripts. Reviewed frozen production headers, regression gtest and current call sites in `C:/w58` against Git history.

Read-only checks executed on this machine:

```powershell
git -C C:/w58 rev-parse HEAD
git -C C:/w58 status --porcelain=v1 --untracked-files=all
git -C C:/w58 diff f0f330c4837a3c4ca9736a8059410cca1a7c2b85..d4b574ac8a039f39976c5f9f4e18adcb074dc237 -- projects/miopen/src/kernels
git -C C:/w58 diff b8cf0e7b..d4b574ac -- projects/miopen/src/kernels/radix.hpp projects/miopen/src/kernels/tensor_view.hpp
Get-FileHash -Algorithm SHA256 C:/b58/bin/MIOpen.dll,C:/b58/bin/test_hiprtc_selfcontained.exe,C:/b58/bin/test_kthvalue.exe
```

`C:/w58` reports exact frozen HEAD and no tracked/untracked changes. `C:/b58/CMakeCache.txt` points `CMAKE_HOME_DIRECTORY` at `C:/w58/projects/miopen`, RelWithDebInfo, wheel clang++, `MIOPEN_USE_HIPRTC=ON`, `BUILD_DEV=OFF`. `build/toolchain.txt` and `build/configure_b58.log` record AMD Clang **23.0.0git**, not the matrix's “20.1-ish” compiler. All three extant binary hashes match the published record:

| Binary | SHA256 independently recomputed |
|---|---|
| MIOpen.dll | `42d261caec77bf3149b336d55b12dd388e988da97a84cf79688a6f4af19b23cc` |
| test_hiprtc_selfcontained.exe | `b1f130a01500265a3386ceff2c1bd7817f65d798ef6c81bb3ea6d54239f51f63` |
| test_kthvalue.exe | `47e0fa30778c3d4ee3b407125a6551c8b9264bcb38eb333120d621a5a6df1045` |

This corroborates the recorded build/run chain. It is not a signed build attestation or proof that a historical working tree had no untracked files. The runtime version label identifies the compiled revision label; it does not alone certify source cleanliness or arbitrary binary contents.

## Claim-by-claim evidence

All Windows rows refer to Windows 11, Radeon 8060S/gfx1151, PyTorch `2.12.0+rocm7.14.0`, HIP `7.14.60850`, wheel HIPRTC `9.0`, unless otherwise stated.

| Document / claim | Exact supporting record | Source/binary | Result actually supported | Remaining limitation |
|---|---|---|---|---|
| README / functional matrix: no-STL HIPRTC PASS | `raw/hiprtc/B_r3_gtest_run.log`; frozen `test/gtest/hiprtc_selfcontained.cpp` lines 39–57, 90–118, 128–154, 165–202 | d4b574ac, DLL path `C:/b58/bin`, runtime cache `3.6.2.d4b574ac`; hashes above | 1 test PASSED, no SKIP; five distinct nonce/cache-miss compiles; isolated absence probe succeeds; selfcontained kernel launches under isolation and ambient environment; gtest assertions check 3/5/9/11 | Three compiles use `-nostdinc`; two are ambient controls. Do not say all five compile under `-nostdinc`. Covers this toolchain/GPU; Linux may SKIP when STL injection cannot be disabled. |
| Functional matrix: host-STL control | Same HIPRTC positive log: ambient `gtest_rtc_stl_use.cpp.obj` and `gtest_rtc_selfcontained.cpp.obj` SaveBinary/launch; `build/configure_b58.log`, `build/build_b58.log` | d4b574ac | Ambient STL-use probe and selfcontained kernel succeed; MIOpen and two selected gtest binaries link, `build rc=0` | Build log alone does not compile every GPU kernel TU offline. CMake `src/CMakeLists.txt` lines 44–45, 780–838 embeds kernel sources as data in `inlined_kernels`; embedding is not per-kernel GPU compilation. |
| README / matrix: original missing-STL negative EXPECTED_FAIL | `raw/negative_control/C_r3_pristine_run.log` | b8cf0e7b-labeled MIOpen DLL in `C:/bwp/bin`; regression test is deliberately added to original source | Trivial and absence probes compile; isolated selfcontained compilation fails exactly `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found`; gtest reports 1 failed; ambient selfcontained leg succeeds | “Pristine” refers to library implementation; baseline test executable necessarily includes the new regression test. Negative runner echoes exit code outside retained raw gtest log; gtest failure/signature are retained. |
| Matrix: BatchNorm train forward/backward numerical correctness | `raw/batchnorm/D_r3.log`; `scripts/d_batchnorm.py`; `raw/batchnorm/D_r3.log.swap_transcript` | d4b574ac DLL hash `42d261ca…`; in-process wheel-bin module path | Shape `(20,100,35,45)` FP32. All finite. Output max abs error `9.537e-07`; x/w/b gradients `1.174e-12`, `5.588e-09`, `6.580e-10`; running mean `6.985e-10`, running variance `3.338e-06`; each below script threshold `1e-3`; exit 0 | Output/grads compare with CPU train-mode module; stats use hand formulas. Running-var reference uses biased variance, inconsistent with PyTorch running buffer's unbiased convention. Therefore exact running-var semantics are not independently established by this script. The tolerance smoke result remains valid as recorded. |
| README / matrix: Round-2/3 BatchNorm “numerically identical” | `raw/batchnorm/D_r2_ab.log` and `D_r3.log`, their `.swap_transcript` files | A f0f330c4 DLL `c739cb0e…`; B d4b574ac DLL `42d261ca…` | Same six printed max-error summaries and finite flags under same script/seeds | Raw tensors were not retained or directly compared. Identical rounded errors relative to CPU do not establish tensorwise or bitwise identity. |
| Matrix: kthvalue 27/27 | `raw/kthvalue/E_r3_kthvalue_warm.log`, `E_r3_kthvalue_cold.time`; `scripts/run_r3_tests.sh` | d4b574ac selected binary, matching hash | All 27 tests pass: FP32, FP16 and BFP16, nine each | First attempted timed run never executed: `/usr/bin/time` missing. File named “warm” is the first successful run in script-created fresh home. Raw log lacks verbose compile/cache label; fresh-cache claim relies on runner and retained cache provenance. Preserve failure disclosure; do not cite empty cold log as PASS. No signed per-run executable hash. |
| README / matrix: YOLO26n COCO8 one-epoch training | `raw/yolo/F_r3.log`, `.swap_transcript`; `scripts/f_yolo26n_coco8.py` | d4b574ac hash installed and restored; in-process DLL path; Ultralytics `8.4.174`, Python `3.13.16` | One epoch completed, finite printed losses and validation, mAP50 `0.9427124183006536`; `YOLO_SMOKE_VALIDATION: PASS`, transcript exit 0. **FP32 training after AMP precheck disables AMP.** | Smoke completion, not general model-quality validation or paired performance. Script prints PASS if train returns, without explicit finite-loss assertions; original raw loss/metric values must be audited. Raw log records two `EvaluateInvokers elapsed <= 0` errors during later validation; successful continuation does not prove cause or universal harmlessness. |
| Matrix: AMP anomaly triple control | `raw/yolo/AMP_B1.log`, `AMP_A1.log`, `AMP_WHEEL.log`, all three `.swap_transcript` files; full F log | B d4b574ac `42d261ca…`, A f0f330c4 `c739cb0e…`, shipping wheel `74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a` | Each standalone check prints FAIL and transcript exit 1. Full F log reports anomalies and disables AMP | This shows anomaly is not specific to Round-3 in this machine/session. Three boolean verdicts do not prove identical numerical failure details or environmental root cause. **Round-3 AMP training PASS is unsupported.** |
| Matrix / provenance: tested DLL matches source | `provenance/binary_sha256_b58.txt`, build logs, build runner, swap transcripts and runtime paths; extant C:/w58 and C:/b58 checks above | exact d4b574ac | Convergent source/build/binary/version/path/hash evidence; local hashes independently verified | No hermetic rebuild, signed attestation or independent reproduction of historical build. Avoid “clean-tree provenance” from version label alone and “guaranteed restore” from trap alone. Actual archived hash transcripts support restoration for these legs. |
| Performance report: ten matched kernel variants instruction-identical | `raw/perf/kth_*_{A,B}.elf`, `bnx0..6_{A,B}.elf`, retained `.isa`/`.body`, `scripts/cache_blob_compare.py`, cache DBs | A f0f330c4 cache label vs B d4b574ac | Scope: three kthvalue dtypes plus seven BN train variants; Agent C responsible for independent extraction/disassembly comparison | ISA identity cannot rule out compile-time, host, selection, scheduling, loading, cache, or unmeasured performance differences. Do not infer blanket non-regression or impossible patch cause. |
| Performance: warm GPU-bound BN no confirmed material regression | `raw/perf/perf2_A_1.log`, `perf2_B_2.log`, `perf2_B_3.log`, `perf2_A_4.log`; `scripts/perf_bn2.py` | A/B preloaded DLL paths recorded in each process | Four GPU-bound median deltas approximately −1.1%, −3.9%, −3.3%, +0.7%; no confirmed material regression in these measurements | Few legs, within-config spread up to ~17%; final logs identify preloaded handles but do not independently prove absence of all background GPU work. Avoid “proven-clean machine state”. |
| Performance: cold compilation/sub-ms noise | `raw/perf/it_A1..A3.log`, `it_B1..B3.log`, `interleaved_gtest.txt`; same perf2 logs | A/B Round-2/3 | **INCONCLUSIVE**, including +11% cold median and +17.6% sub-ms forward median; opposite backward sign and time drift observed | Neither ISA identity nor opposite signs prove timing noise causality. Need more controlled matched repetition to exclude regression. |
| Performance: YOLO paired A/B | Single `raw/yolo/F_r3.log` only | B d4b574ac | **NOT_RUN** as complete paired performance experiment | No valid cross-run speedup/non-regression conclusion. |
| gfx942: likely infrastructure hypothesis | Original GitHub run `38596620066`, job `116645608429`; referenced raw `evidence/gfx942_job.log` absent from initial package; external original available in local `r3_mission/evidence/` | Failure is on f0f330c4, Linux gfx942, not fresh d4b574ac test | Repeat GPU Hang in BN+Activation inference; inspected listed kernel sources have no direct modified-header include; offline compilation selects real-STL branch if MIOPEN_HIP_RUNTIME_COMPILE absent | Grep/direct include analysis does not prove no indirect cause. Matched develop/PR gfx942 experiment missing. “LIKELY_INFRASTRUCTURE” must remain tentative, unresolved. Add raw log or resolvable source reference; do not claim conclusive exclusion. |
| Cross-platform: Linux coverage | `PHASE6_CROSS_PLATFORM.md`, historical f0f330c4 GitHub checks | Historical Round-2, not d4b574ac local validation | No local Linux run. Current-head CI state must come from Agent D's fresh GitHub data | Historical check success and Linux no-STL SKIP are not proof of Round-3 no-STL pass or present CI success. |

## Semantic review

Source references below are frozen files in `projects/miopen/src/kernels/` at d4b574ac.

| Topic | Review and independent check | Classification |
|---|---|---|
| `enable_if` substitution | `miopen_type_traits.hpp` lines 110–120: false primary has no `type`, true specialization has requested type. Independent isolated Clang probe verifies false has no type and true has type. | NO ISSUE |
| `conditional` | Lines 137–153: both bool specializations cover permitted template argument; `_t` names selected type. In-header assertions select both branches. | NO ISSUE |
| `is_pointer` | Lines 122–135 removes pointer-level cv before helper pointer specialization; pointee cv preserved; references/member pointers do not match T*. Existing static assertions cover common cv cases. | NO ISSUE |
| `is_trivially_copyable` | Lines 155–161 delegates Clang builtin; array/nontrivial controls in lines 194–200. Supported RTC compiler is Clang; no new regression vs Round-2. | NO ISSUE in supported toolchain |
| `forward` valid calls | `miopen_utility.hpp` lines 35–44, same overload bodies as develop: reference collapsing and casts preserve lvalue/const-lvalue/rvalue categories. Independent `decltype` probe passes. Existing RTC gtest launches actual lvalue and rvalue cases. | NO ISSUE for valid callers |
| `forward` invalid call diagnostic | Standard's second overload disallows lvalue-reference T. Fallback omits that diagnostic: isolated `std::forward<int&>(1)` compiles with dangling-reference warning. Identical omission in b8cf0e7b; searched current consumers and found no invalid use. | MINOR pre-existing diagnostic/conformance limitation; not evidence of a supported-call regression, no fourth-round patch recommended |
| initializer-list ABI | `miopen_initializer_list.hpp` lines 20–30 preserves pointer then `__SIZE_TYPE__`, constructor and accessors. Body unchanged from Round-2. Isolated Clang constexpr two-element construction, size and element assertions pass; RTC GPU gtest validates `{3,5}` through tensor layout. | NO ISSUE |
| Host/fallback selection | Type traits line 29, utility line 29, initializer-list line 9 preserve runtime-macro plus `!__has_include`. Offline/no runtime macro uses real STL; partial-STL #error removal is deliberate reviewer request. | NO ISSUE for complete/no STL configurations |
| Partial STL | Per-header selection does not mathematically prove cross-header consistency; guard removal cannot justify “duplicate definitions impossible” for arbitrary partial header environments. Typical complete distributions avoid mix. | MINOR documentation limitation; no speculative production change |
| Radix signed encoding | `radix.hpp` lines 65–72: Clang `__INT32_MAX__` / `__INT64_MAX__` are exact signed maxima; cast to corresponding unsigned then add v and 1 retains original modulo mapping `v - min`. Negative/min/zero/max semantic mapping unchanged. Floating/half branches unchanged. | NO ISSUE; integer paths assessed by source, 27 gtests cover floating dtypes |

Audit probes are saved outside production/evidence repositories as `agent_b_semantics_probe.cpp` and `agent_b_forward_invalid_probe.cpp`. Compiler: the same installed wheel `clang++.exe`; command flags `-std=c++17 -fsyntax-only -nostdinc -IC:/w58/projects/miopen/src/kernels`. Positive probe exit 0; invalid-forward probe exit 0 with `-Wreturn-stack-address`. No executable or GPU run was required.

Primary documentation used to verify interpretation: [PyTorch BatchNorm2d running variance convention](https://docs.pytorch.org/docs/stable/generated/torch.nn.modules.batchnorm.BatchNorm2d.html) and [C++ working draft forward requirements](https://eel.is/c++draft/forward). The installed historical script remains authoritative for what actually ran.

## Required exact documentation corrections

Preserve executed raw logs and scripts. Corrections should explain their limits, not retroactively rewrite an executed program.

1. README headline and functional-matrix numeric comparison; also cross-platform report, historical final-audit claims and PR-facing draft:

   Replace “BatchNorm A/B numerically identical” with **“BatchNorm forward/backward passed the recorded tolerance checks; the six printed maximum-error summaries match Round-2. No direct tensorwise/bitwise A/B comparison was retained.”**

2. Matrix host-STL row:

   **“The d4b574ac MIOpen library and selected gtests built successfully (`build rc=0`). The ambient STL-use probe and selfcontained kernel compile/launch in `raw/hiprtc/B_r3_gtest_run.log` provide the runtime host-STL control. The library build embeds GPU kernel source as data and does not prove that every kernel translation unit compiled offline.”**

3. Matrix no-STL row and PR-facing draft:

   **“Five fresh nonce-keyed compile/cache misses: three with `-nostdinc` (trivial, STL-absence probe, selfcontained) and two ambient STL controls (STL-use, selfcontained). Both selfcontained launches satisfy gtest output assertions; no SKIP.”**

4. Matrix BatchNorm stats limitation:

   **“Historical `d_batchnorm.py` compares running variance with a biased-variance formula although PyTorch updates its running variance with the unbiased estimator. The recorded `3.338e-06` residual passes the script's `1e-3` threshold; this is a tolerance/finiteness smoke check, not an exact running-variance reference test. The script is preserved as executed.”**

5. README and all YOLO summary rows:

   **“YOLO26n COCO8 one epoch completed in FP32 after AMP was disabled by its precheck. The precheck returned FAIL with Round-2, Round-3 and pristine shipping-wheel DLLs in this session; this is not specific to Round-3, but the root cause is unproven. Round-3 AMP training PASS is not claimed.”**

6. Matrix binary provenance:

   Replace label-only “clean-tree provenance” with **“revision label corroborated by build logs, DLL hashes, swap transcripts and module paths; the label alone is not a clean-tree attestation.”** Replace “guaranteed restore” with **“trap-based restoration; all archived swap transcripts show the original shipping-wheel hash restored.”**

7. Performance §1 and §4:

   Replace “performance differences therefore cannot originate from the patch” / “code cause impossible” with **“The ten compared variants have identical GPU instructions. This supports unchanged generated instructions for those variants; it does not rule out compile-time, host-side, scheduling, cache, or unmeasured performance effects. No confirmed material regression was established in the retained warm GPU-bound measurements; cold and sub-ms comparisons remain INCONCLUSIVE.”**

8. gfx942 README headline / RCA:

   **“LIKELY_INFRASTRUCTURE is a tentative hypothesis. Source inspection found no direct dependency of the identified BN/Activation inference kernel sources on modified headers; no matched develop-versus-PR gfx942 run was available, so a PR regression has not been conclusively excluded.”** Remove “confidence: high”, “no causal path exists” and unsupported “hardware hang is not a code-defect signature”. Keep the immediate repeat hang and baseline limitation. Prefer original job raw log archived with source URL.

9. Cross-platform duplicate-STL row:

   **“Real headers are selected independently with `__has_include`; this avoids fallback use when each header is available. Complete standard libraries are the supported normal environment. After requested guard removal, arbitrary partial-header consistency is not enforced; no such failing supported configuration was observed.”**

10. Historical final-audit blanket PASS:

    Label its findings as a 2026-10-16 historical review, then add the current closure audit and repaired-manifest verification. Do not present “all PASS” as excluding AMP FAIL, unresolved gfx942, current CI authorization or a previously broken manifest. No new production changes are recommended.

11. README integrity sentence after repair:

    **“SHA256SUMS covers all tracked evidence payload files except the manifest itself, whose version is identified by the Git commit.”** Verify independently after every final edit.

12. Matrix environment compiler version:

    Replace “clang 20.1-ish wheel LLVM” with **“AMD Clang 23.0.0git, target x86_64-pc-windows-msvc (recorded in `build/toolchain.txt`; ROCm llvm-project commit `46fcb339fb61119b337f973c7ca9e710a319fdd0`, patched build).”** The `_20` in a MIOpen cache filename must not be treated as LLVM version evidence.

## Acceptance conditions and independent handoff

Agent B approves freezing production. Agent B does not veto preserved historical failures or inconclusive results: they must be disclosed faithfully. Publication approval for the evidence requires correcting unsupported claims, resolving missing referenced raw paths, repairing the manifest, preserving historical Phase 5.7, and rechecking final committed files. Agent C owns the full independent hash/ISA re-extraction; Agent D owns live CI/merge state. Their acceptance is not implied by this report.
