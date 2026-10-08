# Kthvalue Harness Readiness — W7900 Linux Prep (G06)

Date: 2026-10-08 | Status: **BASELINE PASS (unpatched, source-built MIOpen)**

## Why this harness (and not torch.topk/kthvalue)

`torch.topk()`/`torch.kthvalue()` do NOT prove that MIOpen's
`MIOpenKthvalue.cpp`/`radix.hpp` ran (PyTorch may use its own kernels).
The Phase-3 RCA harness calls the public MIOpen C API directly:

```text
miopenKthvalueForward            (public API, miopen.h:7753 @ b68f894)
  -> KthvalueForward dispatcher  (kthvalue_api.cpp)
  -> KthvalueFwd solver          (forward_kthvalue.cpp; log-proven)
  -> MIOpenKthvalue.cpp          (RTC compile, -mcpu=gfx1100, cache-proven)
  -> radix.hpp machinery         (encode/GetBitFieldImpl/SetBitFieldImpl)
```

The RTC kernel database of the fresh per-run cache contains:

```text
id=1 MIOpenKthvalue.cpp.o -DMIOPEN_USE_FP32=1 ... -DLOCAL_SIZE=256
     -mcpu=gfx1100  blob=4232B  hash=ebb749a659a503cc597e697a0ffe1dbd
id=2 MIOpenKthvalue.cpp.o -DMIOPEN_USE_FP16=1 ... -DLOCAL_SIZE=256
     -mcpu=gfx1100  blob=4272B  hash=050ca32ffc91f96382299bef789a9cb3
```

=> the exact radix-path kernel was compiled at runtime for gfx1100 and
executed through the source-built library.

## Harness provenance

- Original Phase-3 harness preserved byte-identical at
  `scripts/phase3-original/kthvalue_runtime_harness.cpp`
  (source: RCA repo `main` @ `013f6f0`, tarball-acquired).
- Preparatory copy `scripts/kthvalue_runtime_harness_gfx1100.cpp`
  differs ONLY in the banner string (gfx1151 -> gfx1100/W7900) — no
  functional changes needed for gfx1100.
- Binary: `build/kthvalue-harness/kthvalue_runtime_harness_gfx1100`
  sha256 `b830b37a5aa7aef37da8c79e3ceb30435fd631b99dda29516f2ed36c152e7ef8`.
- Link-time deps on MIOpen/HIP: NONE (all symbols via `dlsym(RTLD_DEFAULT)`;
  `ldd` confirms). Binding control is 100% runtime-side:
  `scripts/run_validation_leg.sh <leg> <label> <cmd>` performs
  LD_PRELOAD(leg soname) + LD_LIBRARY_PATH(leg first) + fresh
  MIOPEN_CUSTOM_CACHE_DIR/MIOPEN_USER_DB_PATH/XDG_CACHE_HOME per label.

## Baseline result (unpatched, source-built 3.6.2 @ b68f894)

dladdr provenance (in-stream): `miopenCreate` and `miopenKthvalueForward`
both resolve to `install/baseline/lib/libMIOpen.so.1`
(sha256 `6af347af...90697`).

| Case | Shape | dtype | k | Result |
|---|---|---|---|---|
| FP32-2D-nokeep | 100x500 | FP32 | 10 | PASS (0 val / 0 idx mismatches, max_abs_err 0) |
| FP32-3D-keep-explicit-dim | 10x20x300 | FP32 | 137 | PASS (0 / 0, 0) |
| FP16-4D-keep-kmax | 8x3x10x2000 | FP16 | 2000 | PASS (0 / 0, 0) |

Exit code 0. Full log `logs/G06_kthvalue_baseline.log`; deterministic dumps
under `runtime/baseline-cache/kthv-baseline/dumps/` for future byte-level
A/B (same binary + fixed seeds => identical inputs across legs by
construction; pairwise-distinct permutation values eliminate tie ambiguity
so exact index comparison is valid).

## What is deliberately NOT claimed

- No patched-leg run (Phase-5.1 patch NOT applied — not authorized yet).
- No A/B comparison executed.
- No claim about `torch.kthvalue`/`topk` dispatch anywhere in this gate.

## Future final-validation invocation (ready)

```bash
# leg A (unpatched):
scripts/run_validation_leg.sh baseline final <harness>
# leg B (patched, after FINAL_HANDOFF freeze + build):
scripts/run_validation_leg.sh patched  final <harness>
```
