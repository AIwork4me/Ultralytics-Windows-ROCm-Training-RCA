# ROCM LIBRARY PROVENANCE — Phase 5.3

## Toolchain

- ROCm 7.14.1 isolated wheel SDK venv (`tools/rocm7141-venv`, `rocm_sdk_devel-7.14.1`).
- hipcc 7.14.60850; AMD clang 23.0.0git from the venv SDK.
- System `/opt/rocm-7.2.1` present but isolated: PATH override, zero `/opt/rocm` in both
  CMakeCaches and both configure logs, zero rocm-7.2 mappings in every in-process
  `/proc/self/maps` walk (after real GPU init), zero 7.2.1 strings across all L06–L10 logs.

## Leg binaries

| Leg | Path | SHA256 |
|---|---|---|
| A (frozen, reused) | install/legA-frozen-baseline/lib/libMIOpen.so.1.0 | `7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d` |
| B (R2, built) | install/patched/lib/libMIOpen.so.1.0 | `bf21a5fa4abc5ff77b0f50756a69dccf7a077970603a846300f0ea077d61eac1` |

Wheel MIOpen (NOT used by validation legs): `941a92da…` in `_rocm_sdk_libraries`,
`_rocm_sdk_devel`, and `torch/lib` — shadowing hazard for bare-soname dlopen, neutralized
by the mandatory `run_validation_leg.sh` wrapper (LD_PRELOAD + lib-dir prepend;
attack-verified in L11 A3; the wrapper refused reuse of non-empty caches in L11 A4).

## Runtime dependency set (in-process, post-GPU-init, both legs identical)

`libhiprtc.so.7 cdee97e0…`, `libamdhip64.so.7 db0f21d0…`, `libamd_comgr.so.3 b569ef43…`,
`librocblas.so.5 49518754…`, `libhsa-runtime64.so.1 bb24bcde…`, `libhipblaslt.so.1
12d836c5…`, `libroctx64.so.4 5a0c5380…` — all from the 7.14.1 venv. Verified by the L06
probe (dlopen abs path → dladdr(miopenCreate) → miopenCreate/miopenDestroy real GPU init
→ maps walk + sha256) and re-verified independently.

## Notes

- `libMIOpenCKGroupedConv_gfx1100.so` is not shipped by the legs and resolves from the
  shared wheel identically on both legs (benign 5-symbol warning; no CK solver in the
  kthvalue/batchnorm dispatch chains).
- The `HIPRTC v.9.0` version string is non-discriminating across stacks (Reviewer B
  probed both); runtime isolation rests on dladdr provenance, which every gate carries.
- HIPRTC "v9.0" appears in logs with HIP 7.14.60850 — the string is the internal
  hiprtc major version, not the ROCm release.
