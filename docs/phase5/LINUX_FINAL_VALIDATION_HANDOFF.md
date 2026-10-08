# Linux Final Validation Handoff (Gate P5-14)

**Status: `LINUX_PHASE5_TARGETED_REVALIDATION = PENDING`**

> **SUPERSEDED (Phase 5.1, 2026-10-08).** This Phase-5 document is
> retained as historical record with its factual errors corrected. The
> single authoritative Linux validation instruction is now
> `findings/phase5_1/FINAL_HANDOFF.json` +
> `docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md` for candidate
> **P5.1-CANDIDATE-R1** (copyright-attribution applied to the four new
> files; new commit SHAs and patch hashes). Do NOT validate using the
> P5-CANDIDATE-R1 series below unless specifically re-aimed at it.

The Phase-5 candidate is NOT byte-identical to the Linux-validated
P3-FINAL-R3 (4 of 8 source files changed by audited hygiene edits; base
moved b68f894 → 7c58661). Historical Linux PASS evidence for P3-FINAL-R3
remains fully valid FOR THAT CONTENT; it must not be re-labeled as
Phase-5 validation. Phase 5 executes on Windows and does not invent a
Linux PASS.

## Why the changes are expected not to affect Linux runtime

1. Dead-macro removal (`MIOPEN_FREESTANDING_TRAITS_ACTIVE`): zero
   references in any tree; no `#ifdef` exists anywhere (verified in P5
   candidate + upstream develop by two independent reviews).
2. Formatting: clang-format 18.1.4 (repo config) whitespace/alignment
   only — token streams identical (P504 adversarial review, byte- and
   token-level proof).
3. Commit-2 message rewrite: metadata only, no tree bytes.
4. Upstream base drift (b68f894→7c58661): upstream's own changes; our 8
   files untouched; the only kernel-relevant change is the
   `use_amdgcn`→`use_gfx9_dpp` rename in BN spatial kernels (an upstream
   semantic-neutral rename of a gfx9-DPP gate; include closure of the
   regression-test kernel unchanged).
5. CI test (commit 3): test-only addition, not compiled into MIOpen.dll.

Residual Linux risk surface, honestly stated: the DLL now compiled from
upstream's newer BN kernel sources (the rename above) — which Linux CI
would compile anyway from current develop; and any latent upstream
regression in the 9 drifted MIOpen files is outside our patch's control
but inside the validation surface of the revalidation below.

## Handoff for the independent Linux validator

Environment: reuse the working Linux setup at `~/Desktop/YOLO_AMD`
(ROCm ≥ 7, gfx1151-class AMD GPU). Do NOT reinstall ROCm or repeat the
original RCA.

```text
frozen upstream base SHA:  7c5866144ac4b879be442563e2b49fa1c142ea36
phase5 candidate commits:  135f775e855bc40185d0a39e13d0a1a97105c1b9
                           66f66944f171628076785e5b89b4a1334d5a987d
                           29846fc4fb736800ff0ad91af95c7cc32f1373ad
ordered patch paths:       patches/phase5/canonical/
  0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch
  0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch
  0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch
individual SHA256:         76fd6623958fb58fc71a9fabbf662bc28a22cfd19aeacba76ca9eee841abc586
                           d37376c9318c79f750b456ff6491ed1e6978d0eafa45a49a34fc66cf85f7a9ea
                           593061053e113c5005040d6d9b1dee39c4d0d7cb2d0c27626749815ed6877821
series SHA256 (concat):    5ad951c716fbf986e627a94f65db679f4f49519d672912cb2e407bf3b714391d
```

(Corrected 2026-10-08 by Phase 5.1 Gate 02: this block previously listed
two obsolete intermediate Phase-5 commit IDs and the pre-amendment
patch-2/patch-3 and series hashes. The values above are recomputed from
the actual Git objects and canonical patch bytes; the obsolete values
are recorded in `evidence/phase5_1/consistency/pre_fix_findings.json`.)

Note: patch 0003 adds a CTest; on Linux the expected default-suite
behavior is the positive mode only (compile-only, no GPU needed), plus
the manual A/B modes available to the harness.

## Minimum Linux validation set (targeted, not the full Phase-3 RCA)

1. **Apply & build**: clean checkout of develop `7c58661`, apply the
   ordered series (exact blob bytes; sequential `git apply` 0001→0002→0003),
   configure + build MIOpen the same way Phase-3 did on Linux.
2. **HIPRTC regression A/B** (the point of the patch):
   - `test_hiprtc_selfcontained <kernels-dir> --mode=negative` against the
     UNPATCHED tree → PASS with the exact `'type_traits' file not found`
     signature (on Linux the isolation option may need
     `--isolate=-nostdinc++`; the probe verifies whichever is used);
   - `--mode=positive` against the PATCHED tree → PASS with non-empty
     code object;
   - `--mode=ordinary` both trees → PASS;
   - in-tree `ctest -R test_hiprtc_selfcontained` on the patched build →
     PASS.
3. **Kthvalue runtime — DIRECT MIOpen harness, not PyTorch operators**
   (radix.hpp consumer; the Phase-3 Linux PASS→PASS check).
   `torch.topk`/`torch.kthvalue` do NOT prove MIOpen's radix kernel ran
   (PyTorch ships its own topk kernels); they are supplemental only.
   The authoritative method is the validated Phase-3 direct harness
   (`docs/phase3/linux/KTHVALUE_RUNTIME_CLOSURE.md`, harness source
   `scripts/phase3/linux/kthvalue_runtime_harness.cpp`), which must:
   - call the public API `miopenKthvalueForward` directly (execution
     chain `miopenKthvalueForward` → `KthvalueFwd` solver →
     `MIOpenKthvalue.cpp` → `radix.hpp`);
   - run against SOURCE-BUILT unpatched AND patched `libMIOpen.so`
     (build both from the exact base + series under test);
   - prove which library was loaded via `dladdr` on the exact
     `miopenKthvalueForward` pointer used (LD_PRELOAD isolation);
   - use a fresh isolated `MIOPEN_CUSTOM_CACHE_DIR` per run;
   - capture kernel compile + dispatch evidence (MIOpen logging:
     "Invoker registered … solver KthvalueFwd", `kernel_name =
     KthvalueFwd`, RTC LoadBinary(miss)→HIPRTC compile→SaveBinary for
     `MIOpenKthvalue.cpp.o`);
   - use the known deterministic Phase-3 cases (FP32 {100,500} dim=-1
     k=10 no-keep; FP32 {10,20,300} dim=2 k=137 keep; FP16 {8,3,10,2000}
     dim=-1 k=2000 keep — fixed-seed pairwise-distinct inputs);
   - verify values AND indices against a CPU reference, and compare
     patched vs unpatched outputs byte-for-byte;
   - record real exit codes and raw logs.
4. **BatchNorm spot-check** (BN train fwd/bwd + running stats, finite +
   vs CPU tolerances as in Phase 3).
5. Optional but cheap: one-epoch YOLO26n coco8 train (`amp=False`) as the
   end-to-end workload.

Record PASS/FAIL with raw logs under a new `evidence/phase5-linux/`
directory on the Linux evidence branch; until that exists, this file's
status line stays PENDING.
