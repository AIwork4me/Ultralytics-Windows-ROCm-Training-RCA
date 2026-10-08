# MIOpen Build Readiness — W7900 Linux Prep (G04 summary doc)

Date: 2026-10-08

## Status: BASELINE BUILD SUCCESSFUL (pristine upstream)

```text
source   rocm-libraries @ b68f8944300f104875d953fc8e4510908c9aaf0b
         (codeload tarball; 8032/8032 files blob-hash-verified vs commit
          by independent G04 subagent; fin/ = submodule gitlink, empty dir)
project  MIOpen 3.6.2 (projects/miopen standalone cmake entry point)
toolchain isolated ROCm 7.14.1 wheel SDK (venv) — HIP 7.14.60850
         amdclang++ from _rocm_sdk_devel/llvm; ninja 1.13; cmake 3.31.10
config   MIOPEN_BACKEND=HIP  MIOPEN_USE_HIPRTC=ON  MIOPEN_USE_COMGR=ON
         MIOPEN_USE_COMPOSABLEKERNEL=OFF (mirrors Phase-3 Linux; CK not
         needed for the kthvalue/radix path)  RelWithDebInfo  GPU_TARGETS=gfx1100
result   841/841 targets; MIOpenDriver + libMIOpen.so.1.0
         install/baseline/lib/libMIOpen.so.1.0
         sha256 6af347af760bb5145a6d8f2c50871bcd2d11c7aa71075a59cd67de7e49990697
         MIOpenDriver --version -> 3.6.2 (correctly bound; see G04 fixes)
```

## Dependency resolution summary

| Dependency | Source | Note |
|---|---|---|
| hip / hiprtc / comgr / rocblas / hipblaslt / rocrand | wheel 7.14.1 SDK | explicit `-D<pkg>_DIR` cache pins |
| SQLite3 3.45.1 / BZip2 1.0.8 / boost 1.83 | system (pre-existing or apt during prep) | apt added only: libbz2-dev, nlohmann-json3-dev, libeigen3-dev |
| Eigen3 3.4.0 | system libeigen3-dev, `-DEigen3_DIR=/usr/share/eigen3/cmake` | Debian hides it from default search |
| FunctionalPlus / frugally-deep / googletest | pre-seeded tarballs (SHA256-verified) under build/thirdparty-preseed | gitlab/github FetchContent black-holed by proxy |
| rocMLIR | not required (HIPRTC config) | confirmed |
| CK | OFF | Phase-3 parity |

## Contamination controls (mandatory for every build)

1. `source scripts/env_rocm7141.sh` (never build from ambient shell).
2. CMake cache pins for every ROCm package + offload-bundler + assembler
   (two /opt/rocm leaks were caught by the mandatory post-configure grep and
   pinned away — keep the grep).
3. Post-configure assertion: `grep -c "opt/rocm" CMakeCache.txt` == 0.
4. Post-build assertion: driver `--version` bound through the leg prefix.

## Known transient

`repos/rocm-libraries` blobless clone: commits+trees complete; worktree
materialization at the pinned SHA still backfilling through the unstable
egress proxy (scripts/repo_backfill_loop.sh). Non-blocking (source of
record = verified tarball). The FINAL validation must materialize the
frozen SHA in the repo (leg-a/leg-b reconstruction) using the same retry
tooling or the tarball+verification fallback.
