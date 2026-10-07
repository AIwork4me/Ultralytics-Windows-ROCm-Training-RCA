# Linux Validation Summary — Phase 3 (run 2 final: 2026-10-08)

```text
STATUS: LINUX INDEPENDENT REGRESSION VALIDATION — PASS
```

Run 1 (2026-10-07) completed the pre-handoff baseline and exited
BLOCKED_ON_PATCH_HANDOFF (marker content preserved in git history 07959f8).
Run 2 (2026-10-08) consumed the Windows producer's final patch series and
completed Gates L20–L49.

## Coordination identity

```text
SOURCE_SHA   b68f8944300f104875d953fc8e4510908c9aaf0b
PATCH_ID     P3-FINAL
PATCH_SHA256 0001 f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20
             0002 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532
```

## Results (single-variable: same SHA, same flags, only the patch differs)

- **Source acquisition**: exact SHA via blobless fetch + per-blob
  SHA-1-verified raw backfill (git smart protocol was down); independent
  reviewer re-verified 8032/8032 blobs; baseline tree clean, patched tree
  byte-identical to HEAD+0001+0002 (reviewer round-trip).
- **Builds**: unpatched + patched MIOpen 3.6.2 from source with the 7.14
  wheel toolchain; configure/build logs + both CMakeCaches archived; zero
  /opt/rocm references (system 7.2.1 coexistence neutralized by explicit
  cache pins + controlled LD_LIBRARY_PATH; contained first-configure
  incident documented).
- **Load proof**: LD_PRELOAD + dladdr(miopenCreate) per run (harness now
  echoes binding in-stream).
- **BatchNorm**: 8/8 → 8/8 on fresh isolated caches with direct RTC-compile
  proof; wheel stack had already reproduced the Windows-failing kernel
  compiling fresh on Linux in run 1.
- **Numerics**: BIT-IDENTICAL (max_abs 0.0, 37 tensors, CPU-referenced).
- **no-STL canaries**: with-STL token equivalence (incl. reviewer-extended
  files); partial-STL environment: unpatched FAILS through real comgr RTC
  ('utility' not found — Windows failure class reproduced on Linux),
  patched fires its designed guard; zero-STL fallback arms all PASS;
  facilities execute on GPU; patch-0002 paths (tensor_view/radix/initlist)
  compile-level PASS with radix value-equivalence static-asserted;
  Kthvalue TU compiles from both trees.
- **Non-BN RTC matrix**: 11/11 → 11/11 (g68 mirror).
- **YOLO**: predict + train (amp-default-self-fp32 AND amp=False) PASS
  bound to the patched build (v2 rerun with in-stream binding + fresh cache).
- **Independent reviews**: regression attacker NO_REGRESSION_CONFIRMED;
  provenance auditor PROVENANCE_CLEAN; maintainer simulation
  ADEQUATE_WITH_CONDITIONS — all validator-side conditions remediated
  same-session; remaining conditions are producer/CI-side.

## Residual conditions (recorded for the maintainer/producer)

1. Runtime execution of a kthvalue-class op under both source builds
   (compile + value-equivalence coverage provided instead; same decision
   as the Windows leg).
2. CI breadth: ≥1 more arch (gfx94x/gfx110x/gfx120x) and a 10.x line —
   the patch edits a HIP-version gate.
3. Producer fills author/DCO identity in the patch series.
4. static-CK RTC wrappers runtime-unexercised in this config (CK off,
   mirroring Windows; wheel CK plugin fails symmetrically in both legs).

## Cross-platform picture

```text
             UNPATCHED       PATCHED
Windows        FAIL            PASS   (producer, live A/B)
Linux          PASS            PASS   (this validation)
```

Details: docs/phase3/linux/LINUX_REGRESSION_MATRIX.md,
docs/phase3/CROSS_PLATFORM_VALIDATION.md.
