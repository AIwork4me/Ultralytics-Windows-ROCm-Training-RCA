## Motivation: Unblocking YOLO Training on Windows Radeon GPUs

For developers using AMD Radeon GPUs on Windows, successfully installing PyTorch and Ultralytics does not always mean model training will work. We investigated a real-world case where PyTorch detected the Radeon GPU and YOLO inference ran fine, but Ultralytics YOLO training failed the moment MIOpen tried to JIT-compile a BatchNorm kernel through hipRTC. The underlying compilation error was:

```
fatal error: 'type_traits' file not found
```

surfacing at the framework layer as `miopenStatusUnknownError`. The stack is Ultralytics YOLO → PyTorch → MIOpen → hipRTC → Radeon GPU; the failure is in MIOpen's runtime kernel-compilation path, not in the application. Users should not have to patch their training framework to work around a missing host C++ standard library inside MIOpen's RTC kernel includes.

## Background / Reproduction

On Windows runtime-only ROCm installs (e.g. the PyTorch pip wheels, which depend on `hip-runtime-amd` but not `hip-dev`/MSVC), runtime-compiled MIOpen kernels fail to build because kernel headers include host C++ standard-library headers that hipRTC cannot resolve. Reproduction on Radeon 8060S (gfx1151), ROCm 7.14.0 wheel stack, Windows 11 (the field report `ROCm/MIOpen#3956`, gfx1200 / ROCm 7.2.1, shows the same signature):

```python
import torch, torch.nn as nn
m = nn.BatchNorm2d(100).cuda()
m(torch.randn(20, 100, 35, 45, device="cuda"))
# unpatched: RuntimeError: miopenStatusUnknownError
# hipRTC log: miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found
```

With this PR the same workload proceeds on that class of installation (validated: BatchNorm fwd/bwd numerics vs CPU reference, plus a full YOLO26n coco8 1-epoch training run using the patched MIOpen library).

## Root Cause

Since the HIP 7.0 hipRTC rework (MIOpen#3803), runtime-compiled kernels include the *real* host standard headers (`<type_traits>`, `<utility>`, `<limits>`, `<initializer_list>`) unconditionally in the `HIP_PACKAGE_VERSION_FLAT >= 7` RTC quadrant. hipRTC's include environment only guarantees the HIP/ROCm headers; whether a host C++ standard library resolves is a property of the installation, not of the compiler. Runtime-only installs have none, so any kernel whose include closure touches those headers fails to JIT.

## What This PR Changes

Three commits, ten files (6 modified, 4 added):

1. **`MIOpen: keep RTC type traits self-contained when no host STL is reachable`** — `miopen_type_traits.hpp` / `miopen_utility.hpp` select the real `<type_traits>` / `<utility>` via `__has_include` when reachable (ordinary installs unchanged) and fall back to new freestanding drop-ins otherwise (`miopen_freestanding_type_traits.hpp` with self-tests, `miopen_freestanding_utility.hpp` with `std::forward`). Partial-STL inconsistencies become loud `#error`s; only the (RTC ∧ HIP ≥ 7) quadrant changes.
2. **`MIOpen: make remaining RTC kernel std includes self-contained`** — `radix.hpp` uses `miopen_cstdint.hpp` in RTC mode and replaces `numeric_limits<…>::max()` with the definitionally identical `__INT32_MAX__` / `__INT64_MAX__`; `tensor_view.hpp` falls back to a freestanding `initializer_list`; the three new headers join the kernel shipping list.
3. **`MIOpen: add portable HIPRTC no-host-STL regression test`** — `test/hiprtc_selfcontained.cpp` + CTest registration: compiles the real `MIOpenBatchNormFwdTrainSpatial.cpp` through hipRTC with the host STL unreachable, passing only when the closure stays self-contained and a code object is produced, with substituted/truncated-kernel detection, an isolation probe, and a negative mode requiring the exact field signature as the sole error.

## Benefits for Radeon Developers

- **Unblocks a real training workload** — addresses a confirmed MIOpen hipRTC compilation blocker affecting Ultralytics YOLO training on Windows Radeon hardware; not merely a synthetic C++ header test.
- **Improves out-of-box compatibility** — the affected RTC kernel paths no longer assume a host C++ standard library reachable by hipRTC, reducing environment-specific friction on runtime-only installs.
- **No application source patch** — validated underneath unmodified PyTorch/Ultralytics; public ROCm binaries do not contain this fix until it is merged and shipped.
- **Shared infrastructure value** — the change is in MIOpen, not an Ultralytics workaround; other AI workloads using these kernel include paths may benefit (no universal coverage claimed).
- **Regression prevention** — a capability-aware regression test guards the affected include closure: hard PASS or FAIL on genuine no-STL environments, honest SKIPPED where the STL cannot be hidden.

## Windows and Linux Validation

- **Windows 11, Radeon 8060S (gfx1151), ROCm 7.14.0 wheel stack** — genuine (non-skipped) no-STL regression test **PASS**; negative-control matrix 13/13 including an unpatched-tree control that reproduces the exact field failure signature; bare-environment CTest PASS (hiprtc DLL resolution via the test's CMake `ENVIRONMENT`, not ambient PATH). From the full validation cycle on the byte-identical payload: source-built `MIOpen.dll` verified in-process by SHA256, BatchNorm fwd/bwd numerics within pre-registered tolerances vs CPU reference, YOLO26n coco8 1-epoch training PASS (`amp=False` and a genuine-AMP default run). The no-STL CTest gate and the 13-check control matrix were re-run fresh on submission day against develop @ `54b079ca` (2026-10-10) on the replayed tree, with all ten changed-file blobs identical to the frozen patch. AMP precheck outcomes have varied across historical runs and depend on the environment; they are not claimed as an effect of this fix.
- **Linux, Radeon PRO W7900 (gfx1100), ROCm 7.14.1** — unpatched/patched source-built MIOpen A/B: kthvalue 3/3, BatchNorm 6/6, no numerical regression; ordinary and with-STL controls PASS; YOLO26n smoke on the patched source-built library PASS. The no-STL CTest is legitimately **SKIPPED** there (stock toolchain cannot hide the STL — documented by a toolchain capability probe).
- **Linux, Radeon 8060S (gfx1151), ROCm 7.14.0** — source reconstruction from the frozen evidence tree + A/B: kthvalue 3/3, BatchNorm 6/6, BF16 kthvalue on real GPU PASS, freestanding `initializer_list` canary PASS, RTC compilation controls PASS, YOLO26n 1-epoch smoke PASS; no-STL CTest legitimately SKIPPED. Disclosure: this machine's local control matrix was 19/20 — one environment-limited check (partial Git object store) was not executable.

Windows is the authoritative positive no-STL environment; the Linux SKIPPED results are honest capability-probe outcomes, not passes and not failures.

## Regression Test Design

Exit-code contract: `0` pass, `1`/`2` fail, `4` skip. On genuine no-STL hosts (Windows runtime-only installs): hard PASS or FAIL — skip is impossible unless the isolation probe proves the host cannot reproduce the no-STL condition. On stock Linux toolchains (`libhiprtc-builtins` embeds the C++ headers) the probe reports INCONCLUSIVE and CTest shows **Skipped**, never a silent pass. CI note: a runner exporting `CPATH` or `CPLUS_INCLUDE_PATH` (conda/LLVM images) makes the host STL reachable and the no-STL leg will likewise report Skipped — that leg should run without ambient `CPATH`.

## Known Limitations

Validated on gfx1151/gfx1100; the reporter's gfx1200 was not directly tested (the fix contains no arch-conditional code). BF16 kthvalue and the integer radix encodings are template-generic and value-unchanged; BF16 was GPU-validated on Linux gfx1151. This PR addresses only the hipRTC host-header availability defect — not other Windows training failures — and does not resolve all possible Windows ROCm training issues.

## Related Issue / Evidence

Addresses `ROCm/MIOpen#3956`

Immutable evidence in [`AIwork4me/Ultralytics-Windows-ROCm-Training-RCA`](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA):

- Windows R2 freeze — `phase5.1/windows-r2-ci-portability-freeze` @ `c841716` (full gate chain, control matrices, DLL provenance, numerics, YOLO logs)
- Linux W7900 A/B — PR #8 · Linux gfx1151 cross-OS closure — `linux-gfx1151/phase5.3b-r2-crossos-closure` @ `29b19def`
- Latest-develop replay + submission-day refresh — `phase5.4/windows-upstream-merge-readiness` @ `c213342` and `phase5.5/upstream-pr-submission` (published with this PR)

Patch integrity: the submission series hashes to SHA256 `4f65dafb39f5f65ce6166be4eedfa49f0296be2ac9615ba8edf050da22ddc4dc`, byte-identical in diff payload to the frozen series `48308f6dccfd80f099a458ad5033f815d95f86d2ab54dba1a0344c976b5a3f02`. Two commit messages reference `#3956` / `#3803`, which are MIOpen issue/PR numbers, not rocm-libraries items.
