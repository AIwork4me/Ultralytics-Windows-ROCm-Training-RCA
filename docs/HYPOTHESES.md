# Hypotheses & Falsification Table (Phase 12)

Statuses: **Supported** (local experimental evidence for), **Falsified**
(local experimental evidence against), **Plausible** (consistent with
evidence, not directly tested), **Unresolved** (insufficient evidence).
Confidence: High/Medium/Low.

| ID | Hypothesis | Supporting evidence | Contradicting evidence | Decisive experiment | Status | Confidence |
|---|---|---|---|---|---|---|
| H1 | Ultralytics-specific training bug | — | P4: 8-line pure-PyTorch `BatchNorm2d` reproduces identical signature; P3c: CPU Ultralytics training completes | Phase 4 minimal repro | **Falsified** | High |
| H2 | YOLO26 model/checkpoint bug | — | Same failure with random-init `BatchNorm2d` (no checkpoint, no YOLO26); P3c CPU training of yolo26n.pt succeeds | Phase 4 | **Falsified** | High |
| H3 | COCO8 dataset problem | — | Failure occurs on synthetic `torch.randn` input with no dataset; dataset scans cleanly in P3 | Phase 4 | **Falsified** | High |
| H4 | AMP problem | — | P3b: identical failure with `amp=False`; matrix case D fails in fp32 | Phase 6 | **Falsified** | High |
| H5 | General PyTorch ROCm GPU failure | — | P1 GEMM, matrix A/H (GEMM, Linear+backward), F (Conv2d) all pass on GPU | Phase 1/5 | **Falsified** | High |
| H6 | MIOpen BatchNorm path failure (component level) | Matrix C/D/G: every MIOpen BN kernel (Infer + Train spatial) fails; E: bypassing MIOpen BN passes; MIOpen API log shows `miopenBatchNormForwardTrainingActivation_V2` then HIPRTC failure | none | Matrix + P8 logging | **Supported** (component localized) | High |
| H7 | HIPRTC runtime compilation fails because `<type_traits>` cannot be resolved (mechanism level) | P3/P4 logs: `hiprtcCompileProgram` → `HIPRTC_ERROR_COMPILATION (6)` with `fatal error: 'type_traits' file not found` in `miopen_type_traits.hpp:151`; same across 3 shapes and both kernels | none | Phases 3/4/5/8 | **Supported** (mechanism localized) | High |
| H8 | Python 3.13-specific defect | — | External only: MIOpen #3956 used Python 3.12.7 with same signature (external evidence, not a local experiment) | none local (no second interpreter with ROCm wheels available without installing) | **Falsified (external evidence), UNPROVEN locally** | Medium |
| H9 | gfx1151-specific defect | gfx1151 is the local compile target | External: #3956 hit gfx1200 (RX 9060 XT) with identical signature; #2169 reports also on other hw via Ubuntu OpenCL path | none local (single GPU machine) | **Not gfx1151-exclusive (external evidence); local single-target UNRESOLVED** | Medium |
| H10 | Missing host MSVC/Windows C++ standard-library prerequisite | P9: no `cl`/MSVC/LLVM STL on machine; no `type_traits` anywhere; wheel's clang targets `x86_64-pc-windows-msvc` (expects MSVC STL); `INCLUDE` unset | Cannot test VS-dev-shell A/B (no VS installed; installing is out of Phase-1 scope). Not yet proven HIPRTC *would* find `type_traits` if MSVC were installed | Phase 9 probe | **Plausible** (physically absent locally; sufficiency unproven) | Medium |
| H11 | ROCm Windows wheel packaging/include-path defect (wheel should ship or discover a C++ STL for HIPRTC, or MIOpen sources should not require it) | Wheel ships no C++ STL (`_rocm_sdk_libraries` + `_rocm_sdk_core` have no `type_traits`); AMD Windows install docs state no MSVC prerequisite; same signature on stock installs from #3956 (gfx1200, ROCm 7.2.1); failure persists into ROCm 7.14; embedded `miopen_type_traits.hpp` disables its no-STL shim for HIP ≥ 7.0; #2169's TheRock Windows build (Oct 2025) resolved the full include chain — an AMD Windows build that did NOT hit this defect; MIOpen 3.5.1-era cache compiled BN via OpenCL `.cl` path successfully on this same machine | Not proven that AMD ever intended wheels to be self-contained for HIPRTC; maybe MSVC is an undeclared prerequisite (that is H10's reading of the same facts) | TheRock-vs-rockrel wheel diff; standalone hiprtc reproducer; INCLUDE-redirect A/B; VS-installed A/B | **Plausible** (evidence strengthened post-review; ownership between H10/H11 unresolved) | Medium |
| H12 | Pre-existing pip dependency conflicts (conda/paddlex/pydantic) cause the failure | — | Conflicts are pure metadata (`pip check`); failure is inside native HIPRTC compile; unrelated packages | none needed | **Falsified** (no mechanism; no evidence linking) | High |
| H13 | GameViewer virtual display adapter interferes with GPU selection | — | `torch.cuda.device_count()==1`; correct device used in all runs; failure is a compile error, not device-selection error | Phase 0 probe | **Falsified** (no evidence of interference) | Medium |

## Reading of H10 vs H11 (kept separate deliberately)

Both describe the same observed gap — HIPRTC on this Windows box has no C++
standard library to compile MIOpen's embedded sources against — but they
differ in **which layer owns the fix**:

- H10: user machines must have an MSVC STL (undeclared prerequisite).
- H11: AMD's Windows wheels should either bundle a usable STL for HIPRTC,
  configure include paths to the bundled clang resources, or MIOpen's
  HIPRTC sources should avoid C++ standard headers.

Phase 1 cannot decide between them without an A/B experiment on a machine
with Visual Studio installed (forbidden to install here). This is exactly
the LEVEL 3 boundary documented in `docs/RCA.md`.
