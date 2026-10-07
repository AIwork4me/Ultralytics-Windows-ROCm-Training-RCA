# Phase-2 LEVEL-3 Root Cause Analysis (Gate 39)

Date: 2026-10-07. Every claim cites raw evidence under `evidence/phase2/raw/`
(P2-Cxxx IDs in `docs/PHASE2_CLAIMS_AND_EVIDENCE.md`).

## The ten Gate-39 questions

1. **Can standalone HIPRTC compile `<type_traits>`?**
   Before the remedy: **NO** — a ctypes reproducer calling
   `hiprtcCreateProgram`/`hiprtcCompileProgram` directly on the wheel's
   `hiprtc0714.dll` (no PyTorch, no MIOpen, no Ultralytics) fails on
   `<type_traits>`, `<utility>`, `<limits>`, `<cstdint>`,
   `<initializer_list>` — every standard C++ header — with
   `HIPRTC_ERROR_COMPILATION (6)`, `'file' not found`, while a no-include
   control compiles AND executes correctly on the GPU
   (`hiprtc/header_matrix.json`, `hiprtc/control_exec.txt`). After MSVC
   install: all six compile (`msvc/gate27_armA_plain_shell.txt`).

2. **Does installing/presenting MSVC STL change the result?**
   **YES — sufficient, in a plain shell, via clang's automatic MSVC
   toolchain detection** (no dev shell, no INCLUDE): wheel clang `-v -E`
   shows the search list gaining
   `C:\BuildTools\VC\Tools\MSVC\14.44.35207\include` + Windows SDK dirs.
   The full failure chain (minimal BN → YOLO training) flips to PASS with
   no other change (Gate-27 arm A).

3. **Does a VS Developer shell change it?**
   Also passes (arm B), but is NOT required — plain shell passes (arm A).
   `INCLUDE`-only injection in an otherwise plain child process also
   passes (arm C). Auto-discovery, env propagation, and explicit `-I` are
   three independently sufficient channels.

4. **Is the defect specific to MIOpen compile options?**
   **NO** — the standalone reproducer (no MIOpen options involved) fails
   identically. MIOpen's option construction is not the proximate cause;
   however MIOpen's *source-level* decision to require real std headers in
   runtime-compiled kernels for HIP ≥ 7.0 is the trigger (see 5).
   Additionally proven: MIOpen's `-I$ROCM_PATH/include` option is honored
   by the wheel (poisoned-header experiment) and shadows auto-discovery —
   a viable injection channel.

5. **Is the HIP ≥ 7 MIOpen header-gating assumption involved?**
   **YES — it is the regression trigger.** Upstream commit
   `ce14dab3b92a82aca14c3477619157f41928fe99` (PR ROCm/MIOpen#3803, "All
   7.0 hipRTC fixes", merged 2025-06-16) wrapped `miopen_type_traits.hpp`
   (and `miopen_utility.hpp`) so that for
   `HIP_PACKAGE_VERSION_FLAT >= 7000000000ULL` the no-STL compatibility
   shim is disabled and real `<type_traits>` is included **even in
   runtime-compile mode**. The PR's premise — hiprtc 7.0 consumers can use
   real std headers — holds on Linux (system STL always present) but not
   on Windows wheels without MSVC.

6. **Which layer is the strongest owner?**
   **Jointly: (a) AMD's Windows wheel distribution** — ships an
   msvc-triple clang + hiprtc with no C++ stdlib, no include-path
   configuration, and no documented MSVC runtime prerequisite (Phase-1
   C028); and **(b) MIOpen's HIP≥7.0 RTC gating** (PR #3803) — made
   runtime-compiled kernels dependent on an STL that the Windows wheel
   environment cannot guarantee. Either layer closing its gap removes the
   user-visible failure; neither alone is "the" defect. Proximate
   machine-level cause: no discoverable C++ STL.

7. **Which alternatives were falsified?**
   - Dirty base environment (P2-H1) — falsified (Gate 23, clean env
     reproduces identically).
   - MSVC presence insufficient / needs dev shell (P2-H3 narrow reading) —
     falsified (plain shell auto-discovery).
   - HIPRTC cannot use host STL even when present (P2-H2) — falsified
     (arms A/B/C).
   - MIOpen-option-specific failure — falsified (standalone repro).
   - "Naive gate-number flip suffices" (Candidate D) — falsified
     experimentally: length-preserving DLL patch `<7000000000ULL` →
     `<8000000000ULL` still fails at `miopen_type_traits.hpp:112` +
     `std::enable_if` — the historical shim is version-rotted
     (window-gated trait block; `__hip_internal::enable_if` dependency).
   - "Fixing only the first header" — for the BN closure, empirically
     sufficient: `<type_traits>` is the ONLY std header in the 13-file
     BN closure (extracted-tree analysis); a type_traits-only shim
     passes all BN variants.

8. **What candidate fix passes?**
   - **Candidate A (STL provision/discovery)** — validated three ways
     (MSVC install; INCLUDE injection; `ROCM_PATH`→`-I` freestanding
     48-line shim, cache-isolated, no MSVC). All BN cases, controls, and
     variants PASS.
   - **Candidate B (MIOpen self-contained RTC)** — principally validated:
     freestanding shim content compiles+runs the real kernels through the
     real MIOpen path (via A's injection channel); the upstream patch
     must repair the rotted shim (unconditional traits, proper
     `enable_if`) — shape documented in
     `patches/candidate_B_miopen_type_traits.patch`.
   - **Candidate D naive form — falsified** (see 7).

9. **Is the candidate a workaround or upstream-quality source fix?**
   - MSVC Build Tools presence = **documented-prerequisite remedy**
     (workaround-grade for existing installs; docs-grade upstream action).
   - Wheel-bundled freestanding `type_traits` + automatic
     `-I<wheel>\include` = **packaging fix** (upstream: wheel pipelines).
   - Repaired unconditional RTC shim in MIOpen sources = **upstream-quality
     source fix** (rocm-libraries PR), restoring the pre-#3803
     self-containment property for runtime-compiled kernels on ALL
     platforms.
   - The `ROCM_PATH` shim-dir recipe validated here is a **user-level
     workaround** (no admin, no MSVC), NOT a source fix.

10. **Does YOLO training close end-to-end?**
    **YES**: `yolo26n.pt` coco8 epochs=1 imgsz=640 device=0 workers=0 —
    amp=False AND default AMP both: AMP checks pass, epoch completes,
    validation completes (Box P=0.545 R=0.963 mAP50=0.942 mAP50-95=0.668
    on the default run), `best.pt`/`last.pt` saved, exit 0, GPU device
    confirmed (AMD Radeon 8060S), no MIOpen compile failure, no CPU
    fallback (`yolo_closure/train_amp_off.txt`, `train_default_amp.txt`;
    fresh-shell re-validation in `restart/gate36_fresh_shell.txt`).

## LEVEL-3 status

**LEVEL 3 PROVEN** — the exact defective assumption is identified with
upstream commit, mechanism, and validated remedies:

> *MIOpen PR #3803 assumed that, for HIP ≥ 7.0, runtime-compiled kernels
> may include the real C++ standard library; on AMD's Windows pip wheels
> the bundled msvc-triple clang/HIPRTC has no C++ stdlib, no discovery
> configuration, and no documented MSVC prerequisite, so the assumption
> fails and every MIOpen spatial-BatchNorm runtime compilation aborts with
> `HIPRTC_ERROR_COMPILATION (6)` (`'type_traits' file not found`), which
> PyTorch surfaces as `miopenStatusUnknownError`.*

Confidence: High. Falsification attempts (independent subagent audits at
Gates 20/23; reviewer panel at Gate 45) and the naive-flip falsification
experiment all support the reading.

## Remaining risks / open items

- MIOpen #3956 correlation remains *external* (signature-identical;
  mechanism now locally proven here, but the gfx1200/ROCm-7.2.1 machine
  was not tested locally).
- The non-BN std-using kernels (composable-kernel `functional*.hpp`
  consumers: reduction/layernorm/etc. runtime-compiled kernels referencing
  `<utility>`) would need the same remedy; this RCA validated the BN
  closure only (type_traits-only need) — a full shim set for all kernels
  is an upstream-PR consideration (the rotted-shim repair handles it
  uniformly).
- Reboot persistence: NOT TESTED (no reboot possible within this session;
  Gate 37).
