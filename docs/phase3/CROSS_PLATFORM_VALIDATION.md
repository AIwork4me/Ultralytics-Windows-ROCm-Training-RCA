# Cross-Platform Validation — Phase 3 final (Linux leg added)

Date: 2026-10-08 (Linux); Windows results 2026-10-07, consumed unmodified
from `rca/windows-gfx1151-rocm714-phase3` / origin/main.

Coordination identity (both platforms):

```text
SOURCE_SHA    b68f8944300f104875d953fc8e4510908c9aaf0b
PATCH_ID      P3-FINAL-R3
PATCH_SHA256  0001 f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20
              0002 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532
```

| Test | Windows unpatched | Windows patched | Linux unpatched | Linux patched |
|---|---|---|---|---|
| BN2d train (minimal 5-line) | FAIL (live A/B, no-MSVC) | PASS | PASS | PASS |
| BN2d eval / BN3d / BN1d-3D | FAIL (same gate) | PASS (all variants) | PASS | PASS |
| BN backward | — | PASS | PASS | PASS |
| numerics | — | PASS (≤9.5e-7 vs CPU) | bit-identical to patched | bit-identical to unpatched (max_abs 0.0) |
| no-STL freestanding canary | — | PASS | — | PASS (equivalence + fallback + GPU) |
| non-BN RTC kernels | — | PASS (11-op matrix) | PASS (11-op matrix) | PASS (11-op matrix) |
| YOLO predict | PASS (working case) | PASS | PASS | PASS |
| YOLO train | FAIL (original defect) | PASS (amp both) | PASS (wheel baseline) | PASS (amp both) |

The intended key story, now fully evidenced:

```text
             UNPATCHED       PATCHED
Windows        FAIL            PASS
Linux          PASS            PASS
```

## Linux-leg notes for the maintainer

1. Linux numerics between unpatched/patched source builds are bit-identical
   (overall max_abs_error = 0.0 across y, x/w/b grads, running stats, 6
   BN cases) — the patch is a provable no-op when an STL resolves.
2. Partial-STL environment (corrected after maintainer review): with
   `-nostdinc++`, comgr's bundled set exposes <type_traits> but NOT
   <utility>. The UNPATCHED tree fails there with 'utility' file not
   found — the Windows failure class reproduced on Linux through the real
   RTC path (extended-canary E1). The PATCHED tree in the same
   environment fires its designed partial-STL #error guard with a clean
   diagnostic (E2). A fully-no-STL environment is unreachable through
   comgr on this stack, so the freestanding fallback arms were exercised
   via the plain clang driver (`-x c++ -nostdinc++`): full wrapper chain,
   tensor_view + freestanding initializer_list chain, and facility
   static_asserts all PASS with zero STL (L33 arm C, extended E3), and
   the facility set executes on the GPU through the real RTC path
   (L33 arm D).
3. Build/contamination discipline: MIOpen's CMakeLists hardcodes
   `/opt/rocm*` in several find paths; this machine has a system ROCm
   7.2.1 there. The validation pinned every ROCm dependency to the 7.14
   wheel devel tree (`hip_DIR`, `hiprtc_DIR`, `rocblas_DIR`,
   `amd_comgr_DIR`, `MIOPEN_AMDGCN_ASSEMBLER`, `MIOPEN_OFFLOADBUNDLER_BIN`)
   and verified zero `/opt/rocm` references in both CMakeCaches and zero
   `/opt` resolutions at runtime (controlled LD_LIBRARY_PATH + ldd).

Windows-side evidence: see `docs/phase3/CROSS_PLATFORM_VALIDATION.md` on
`rca/windows-gfx1151-rocm714-phase3` (unchanged; this file ADDS the Linux
columns on the Linux evidence branch).
