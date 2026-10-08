# Linux Final Validation Handoff — P5.1-CANDIDATE-R1 (Phase 5.1, Gate 08)

**Status: `LINUX_VALIDATION = PENDING`** — authoritative manifest:
`findings/phase5_1/FINAL_HANDOFF.json` (this file is GENERATED from it;
do not hand-edit SHA lists here).

Supersedes `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md` (P5-CANDIDATE-R1,
corrected and marked superseded). Historical Phase-3/4/5 evidence is
immutable; nothing there is rewritten.

## Candidate identity (fail closed on any mismatch)

```text
candidate ID:              P5.1-CANDIDATE-R1
frozen upstream base SHA:  7c5866144ac4b879be442563e2b49fa1c142ea36
ordered candidate commits:  d4003de1a7cabc3715f73e48d3fd414f312a40de
                           3b18a0655b991890b63587ee18cb0950234a47f0
                           e7ff6d75fac3e7b683e81e671555ada99af13b74
ordered patch paths:       patches/phase5_1/canonical/
  0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch
  0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch
  0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch
individual SHA256:         14719b8b4ae7b4370afa42249b56c130d7d42b9447701e57a702570eb12ed7e2
                           7d40c314dcac87085178ba9d0c84bb2eced8f33ba8e9bd3a6151903d6ee4751e
                           3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4
series SHA256 (concat):    797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d
source head tree SHA1:     605d0d214acdbc06086fdb27c61fec970c0f2798
```

Verify each patch SHA256 and the series SHA256
(`sha256_file_concat_v1` = SHA256 over the three patch files' LF bytes
concatenated in order, no separator) BEFORE building. If any value
differs, STOP — wrong candidate.

## Linux consumer rules

1. Use ONLY this manifest as the identity authority. Any mismatch of
   base SHA, commit SHAs, patch hashes, series hash or reconstructed
   tree → FAIL CLOSED (do not proceed to "close enough" testing).
2. Apply with exact blob bytes (no email-client/clipboard mangling, no
   CRLF conversion):
   `git checkout 7c5866144ac4b879be442563e2b49fa1c142ea36 && git apply < 0001 && git apply < 0002 && git apply < 0003`
   (sequential, ordered; `git am` also reproduces the identical tree —
   proven on Windows: tree `605d0d214acdbc06086fdb27c61fec970c0f2798`). When reproducing patches
   with `git format-patch`, write PER-FILE output into a directory;
   `--stdout` mode appends two extra LF bytes and breaks byte-exact
   reproduction (Reviewer A NIT A-2).
3. Reconstruct-verify: after applying, the source tree identity must
   equal head tree `605d0d214acdbc06086fdb27c61fec970c0f2798` (e.g. `git write-tree` on the staged
   result of a clean base + patches).

## P5 → P5.1 delta (what Linux is actually validating)

P5.1 = P5 + copyright attribution only: 4 files, 1 comment line each
(placeholder → `Copyright (c) 2026 AIwork4me`), MIT text preserved.
All other bytes identical to the P5-CANDIDATE-R1 series that carries
the full Windows validation history. Linux validates the FINAL bytes.

## Minimum Linux validation set (targeted)

1. **Build both libraries from source**: clean checkout of `7c586614`,
   apply the ordered series, configure + build MIOpen the Phase-3 way;
   ALSO build the UNPATCHED library from the bare base.
2. **HIPRTC regression A/B** (the point of the patch):
   - `test_hiprtc_selfcontained <kernels-dir> --mode=negative` on the
     UNPATCHED tree → PASS with the exact `'type_traits' file not found`
     signature (Linux may need `--isolate=-nostdinc++`);
   - `--mode=positive` on the PATCHED tree → PASS with non-empty code
     object;
   - `--mode=ordinary` both trees → PASS;
   - in-tree `ctest -R ^test_hiprtc_selfcontained$` (anchored regex)
     on the patched build → PASS.
3. **Kthvalue runtime — DIRECT MIOpen harness (authoritative method;
   NOT torch.topk/torch.kthvalue)**: execute
   `miopenKthvalueForward` directly via the validated Phase-3 harness
   (`scripts/phase3/linux/kthvalue_runtime_harness.cpp`; closure doc
   `docs/phase3/linux/KTHVALUE_RUNTIME_CLOSURE.md`). Required chain and
   proof:
   - chain `miopenKthvalueForward` → solver `KthvalueFwd` →
     `MIOpenKthvalue.cpp` → `radix.hpp` (the patched file);
   - run against source-built UNPATCHED and PATCHED `libMIOpen.so`,
     isolated via `LD_PRELOAD`, using the SAME harness binary on both
     sides (record its SHA256; the two runs must differ ONLY in which
     library was preloaded — Reviewer B B-N1);
   - prove which library was loaded: `dladdr` on the exact
     `miopenKthvalueForward` function pointer used (+ wrapper on
     `miopenCreate`);
   - fresh isolated `MIOPEN_CUSTOM_CACHE_DIR` per run (no cached
     binaries can hide compile behavior);
   - kernel dispatch evidence in logs ("Invoker registered … solver
     KthvalueFwd"; `kernel_name = KthvalueFwd`; RTC
     LoadBinary(miss) → HIPRTC compile → SaveBinary for
     `MIOpenKthvalue.cpp.o`). These are Info2-level lines: set
     `MIOPEN_LOG_LEVEL=6` (a default release build logs only warnings,
     which would silently omit the required dispatch evidence —
     Reviewer B B-M1);
   - deterministic cases: [{"shape": [100, 500], "dtype": "FP32", "dim": -1, "k": 10, "keepDim": false}, {"shape": [10, 20, 300], "dtype": "FP32", "dim": 2, "k": 137, "keepDim": true}, {"shape": [8, 3, 10, 2000], "dtype": "FP16", "dim": -1, "k": 2000, "keepDim": true}]
     (fixed-seed pairwise-distinct inputs — Phase-3 set);
   - verify values AND indices vs CPU reference (exact equality
     expected, as in Phase 3);
   - compare patched vs unpatched outputs byte-for-byte;
   - record real exit codes and raw logs.
   `torch.topk`/`torch.kthvalue` may be run as SUPPLEMENTAL evidence
   only — never as primary proof of the MIOpen radix path.
4. **BatchNorm spot-check**: BN train fwd/bwd + running stats, finite +
   vs CPU tolerances (Phase-3 method).
5. Optional end-to-end: one-epoch YOLO26n coco8 (`amp=False`).

Record PASS/FAIL with raw logs under `evidence/phase5_1-linux/` on the
Linux evidence branch; until then this status stays PENDING.
