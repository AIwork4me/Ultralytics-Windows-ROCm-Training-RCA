## Motivation

Real Windows Radeon GPU training failure: with runtime-only Windows ROCm stacks, MIOpen's hipRTC compilation of e.g. BatchNorm training kernels failed with `fatal error: 'type_traits' file not found`, surfacing in PyTorch as `miopenStatusUnknownError` and breaking YOLO training on affected Radeon GPUs (see [ROCm/MIOpen#3956](https://github.com/ROCm/MIOpen/issues/3956)).

Minimal reproducer:

```python
import torch, torch.nn as nn
m = nn.BatchNorm2d(100).cuda()
m(torch.randn(20, 100, 35, 45, device="cuda"))
```

## Root cause

The runtime compiler does not necessarily have a host C++ standard library on its include path. Kernel headers that unconditionally include `<type_traits>` / `<utility>` / `<initializer_list>` therefore fail to runtime-compile, independent of GPU architecture.

## Minimal implementation

Three commits, 7 files changed (+317 / −21), on `develop` (`b8cf0e7b`):

- **`miopen_type_traits.hpp`** — prefer the real `<type_traits>` whenever it is reachable (`__has_include`); otherwise provide the minimal trait fallback (previously gated behind the obsolete HIP < 7 version check) inline, with compile-time self-checks. Develop's original definitions keep their original order and spelling; only the real changes are visible in the diff.
- **`miopen_utility.hpp`** — same selection; minimal `std::forward` fallback built on the type-traits fallback.
- **`miopen_initializer_list.hpp` (new)** — selects the real `<initializer_list>` or a freestanding definition with the exact clang braced-init-list lowering layout; `tensor_view.hpp` now simply includes it.
- **`radix.hpp`** — include-what-you-use (`miopen_cstdint.hpp`, `miopen_type_traits.hpp`); integer radix encoding keeps the compiler-provided `__INT32_MAX__` / `__INT64_MAX__` macros (no `<limits>`).
- **`src/CMakeLists.txt`** — registers `miopen_initializer_list.hpp` for kernel-source shipping.

There are no separate freestanding headers: each fallback lives inside the header it backs, selected by header availability rather than HIP version.

## Regression test

`test/gtest/hiprtc_selfcontained.cpp` — `CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl`, in the style of `miopen_cstdint_lp64.cpp`:

- A minimal inline kernel includes the three headers and exercises `conditional_t`, `is_trivially_copyable_v`, `std::forward` (lvalue and rvalue) and brace-init construction of `tensor_layout_t`; the kernel launches and the host verifies the written values.
- Paired-polarity probes prove the host STL is unreachable under the isolation option before any verdict counts; environments that inject the STL anyway (comgr on Linux) report SKIP, never a pass.
- Per-run nonce options keep the options-keyed kernel-binary cache from satisfying any compile.
- Clear PASS / FAIL / SKIP semantics; a broken or inconsistent toolchain fails rather than skips.

## Validation

Fresh validation of the current HEAD `d4b574ac` (Windows 11, Radeon 8060S / gfx1151, ROCm 7.14.0 PyTorch wheel stack, hipRTC v9.0, clean source-worktree build; kernel-cache label `3.6.2.d4b574ac` in the run logs):

| Environment | Test | Result | Notes |
| --- | --- | --- | --- |
| Windows gfx1151 | No-STL regression gtest | PASS | 5 fresh hipRTC compiles (3 isolated under `-nostdinc`, 2 ambient controls), `-mcpu=gfx1151`, fresh cache home; kernel launched and output values verified |
| Windows gfx1151 | Negative control (unpatched tree + same test) | FAIL as intended | exact original signature `miopen_type_traits.hpp:151: fatal error: 'type_traits' file not found` |
| Windows gfx1151 | BatchNorm2d(100) train fwd+bwd vs CPU | PASS | all outputs/grads/running stats finite, max err 9.537e-07 (output) / ≤3.4e-06 (running stats); identical printed max-error summaries to the previous head under the same seeds; patched library load proven in-process; running-var reference uses biased variance, so its residual is a tolerance smoke check (see FUNCTIONAL_REGRESSION_MATRIX.md) |
| Windows gfx1151 | kthvalue gtest (FP32/FP16/BFP16) | PASS | 27/27 through the real runtime-compilation path (radix.hpp), fresh kernel cache |
| Windows gfx1151 | YOLO26n COCO8 one-epoch training | PASS | no missing-STL error, no MIOpen compile failure; trained in fp32 after Ultralytics' AMP check reported an anomaly — that check fails identically on the untouched shipping-wheel library on this machine right now, arguing against a Round-3-specific cause; the anomaly's root cause and AMP training remain unvalidated |
| Windows gfx1151 | Codegen equivalence | PASS | FP32/FP16/BF16 kthvalue code objects of this head vs the previous head: instruction-identical disassembly |

The identical functional suite passed on the previous head `f0f330c4` (two-commit state after the second review round); detailed logs for both: [AIwork4me/Ultralytics-Windows-ROCm-Training-RCA](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA) (`phase5_7/` for `f0f330c4`, `phase5_8/` for `d4b574ac`).

Historical supporting evidence (earlier patch revisions, not fresh validation of the current head): Linux gfx1100 / Radeon PRO W7900 / ROCm 7.14.1 and Linux gfx1151 / ROCm 7.14.0 — unpatched-vs-patched A/B, kthvalue, BatchNorm and YOLO26n smoke all passed; the no-STL isolation test was SKIPPED there (comgr injects the host STL).

Not executed locally: Linux revalidation of the current head (no Linux runner available; the PR's CI covers Linux configurations).

## Scope

- Headers made self-contained: `miopen_type_traits.hpp`, `miopen_utility.hpp`, `miopen_initializer_list.hpp` (consumers: `tensor_view.hpp`, `radix.hpp` and the kernels they back).
- Workloads validated on the current code: BatchNorm training forward/backward, kthvalue, YOLO26n training — on gfx1151 / Windows.
- This is not a claim of universal Windows Radeon support; other GPU configurations (e.g. gfx1200) were not tested.

## Related issue and evidence

- Issue: https://github.com/ROCm/MIOpen/issues/3956
- Detailed reproduction, controls and numerical evidence: [AIwork4me/Ultralytics-Windows-ROCm-Training-RCA](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA)

## Review updates

First round (resolved): AMD attribution with SPDX headers; migration into the existing gtest infrastructure; evidence-specific comments removed; `radix.hpp` `<limits>` removal.

Second round (resolved in `c6ed8131` + `f0f330c4`): freestanding headers merged into the headers they back with `!__has_include(...)`-based selection, HIP < 7 dropped; `miopen_initializer_list.hpp` selection moved inside; `radix.hpp` include-what-you-use; inline-kernel regression test; rebased on the then-latest `develop` (`b8cf0e7b`).

Third round (resolved in `d4b574ac`; no functional change in supported configurations — the only behavioral delta is that artificial partial-STL include setups no longer hit the dropped `#error` diagnostics): develop's original definition order and `typedef` spelling restored in the type-traits fallback (`integral_constant`/`true_type`/`false_type` back after `remove_cv`; `conditional`/`is_pointer_helper` in develop's form); the partial-STL `#error` diagnostics dropped; header comments reduced to 1–2 lines; `std::forward` bodies back to the repo's clang-format form (this is the exact fix for the clang-format finding that failed the pre-commit check on the previous push).
