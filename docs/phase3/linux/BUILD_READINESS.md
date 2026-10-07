# Linux MIOpen Source-Build Readiness — pre-handoff assessment

Date: 2026-10-07
Purpose: Gate L25–L28 preparation, performed under the §4 re-entrant rule
("complete unpatched rocm-libraries build readiness where feasible") while
BLOCKED_ON_PATCH_HANDOFF. No source build was attempted because SOURCE_SHA
does not exist yet; this document inventories what the post-handoff build
will need and what is already in place.

## Evidence sources

- projects/miopen/{README.md, CMakeLists.txt, install_deps.cmake,
  requirements.txt} fetched from ROCm/rocm-libraries develop via
  raw.githubusercontent.com (saved under ~/Desktop/YOLO_AMD/tmp/, network to
  github git-protocol was stalled; raw fetches worked)
- .gitmodules fetched the same way
- wheel inventory: _rocm_sdk_devel/lib/cmake (54 packages)
- system inventory: dpkg, /usr/include

NOTE: develop-branch files are for READINESS PLANNING ONLY. The actual build
gates (L22+) must re-read these files at the exact SOURCE_SHA.

## Chosen configuration (for Gate L25/L28, semantics per plan)

```text
MIOPEN_BACKEND=HIP
MIOPEN_USE_HIPRTC=ON   (must equal MIOPEN_USE_COMGR=ON per CMakeLists L313-315;
                         both default ON for HIP backend with hip >= 6.1.40091)
CMAKE_BUILD_TYPE=RelWithDebInfo
CMAKE_INSTALL_PREFIX=<installs/miopen-{unpatched,patched}>
CMAKE_PREFIX_PATH=<wheel _rocm_sdk_devel;_rocm_sdk_core;_rocm_sdk_libraries;
                   _rocm_sdk_libraries/lib; .deps/miopen>
CMAKE_CXX_COMPILER=<wheel>/lib/llvm/bin/amdclang++ (AMD clang 23.0.0)
AMDGPU_TARGETS/GPU_TARGETS=gfx1151
```

## Contamination risk: /opt/rocm-7.2.1

1. System ROCm 7.2.1 exists and is on ldconfig.
2. MIOpen's CMakeLists (develop L206) APPENDS /opt/rocm, /opt/rocm/llvm,
   /opt/rocm/hip to CMAKE_PREFIX_PATH unconditionally, and several
   find_package calls pass `PATHS /opt/rocm`.
3. Mitigation (mandatory at L26/L28): wheel prefixes FIRST in
   CMAKE_PREFIX_PATH (CMake searches CMAKE_PREFIX_PATH before find_package
   PATHS hints), PLUS explicit cache pins:
   `-Dhip_DIR=<wheel>/lib/cmake/hip -Dhiprtc_DIR=… -Drocblas_DIR=…
    -Dhipblaslt_DIR=… -Dhipblas-common_DIR=… -Damd_comgr_DIR=…`
   and verify CMakeCache.txt afterward that every ROCm dependency resolved
   under .venv/site-packages and NONE under /opt/rocm-7.2.1.

## Dependency inventory

### Provided by the wheel stack (CMAKE_PREFIX_PATH-able)

hip, hiprtc, hip-lang, comgr (amd_comgr), rocblas, hipblaslt, hipblas-common,
hipblas, rocm-core, clang/lld/llvm (compiler + offload bundler), rocprim,
rocthrust, rocrand, etc. (54 cmake packages under _rocm_sdk_devel/lib/cmake)

### Present on system

- libbz2-dev 1.0.8 ✓ (BZip2 REQUIRED by CMakeLists L141)
- cmake 3.28.3 ✓ (>= 3.15 required), gcc/g++ 13.3.0 ✓, ninja 1.13.2 via uv ✓
- rocm-cmake 0.14.0 (system apt; provides ROCmCMakeBuildTools). Version-mix
  risk with 7.14 noted; if it causes issues, cget-install rocm-cmake into
  .deps instead. Not in wheel cmake list.

### Missing (must be provided before configure) — plan per GATE L27

Via the source tree's own installer into a LOCAL prefix
(~/Desktop/YOLO_AMD/.deps/miopen):

```bash
uv pip install cget   # install_deps.cmake drives cget; pip/uv-installable, no sudo
cmake -P projects/miopen/install_deps.cmake --minimum \
      --prefix "$HOME/Desktop/YOLO_AMD/.deps/miopen"
```

requirements.txt (develop) pins: bzip2@1.0.8, sqlite3@3.50.4, zstd v1.4.5,
rocMLIR@rocm-5.5.0 (only if MLIR backend enabled), nlohmann/json v3.11.2,
FunctionalPlus, eigen, frugally-deep, ../composablekernel (CK),
googletest@v1.14.0. SQLite3 and nlohmann_json are hard find_package REQUIRED.

### Risks / open questions for the build gates

1. **composable_kernel for gfx1151**: CK is required by the super-repo build
   (plain directory projects/composablekernel, not a submodule; only
   projects/miopen/fin → ROCm/MIFin.git is a submodule). CK gfx1151 support
   is unverified; long build time. If CK lacks gfx1151, MIOpen should still
   build (CK unbundling is per-arch); verify at configure time and record.
2. **rocMLIR**: `find_package(rocMLIR … REQUIRED)` appears conditional
   (MLIR path); confirm it is not required for the HIPRTC configuration.
3. **Network**: github git-protocol stalls observed today (clone hung twice;
   raw + pip indexes worked). The post-handoff clone of the exact SOURCE_SHA
   must use retries; consider `--filter=blob:none` + resumable fetch.
4. **Disk**: 114 GB free at time of writing (94% used) — MIOpen+CK build
   trees and two install prefixes fit, but large; keep builds/ out of git.

## Verdict

```text
BUILD READINESS: FEASIBLE — wheel stack covers all ROCm-side dependencies;
system has compiler/cmake/bzip2; remaining deps (sqlite3, nlohmann_json, CK,
test deps) installable via the tree's own cget-based installer into a local
prefix without sudo. /opt/rocm-7.2.1 contamination neutralizable with
explicit cache pins (mandatory verification step added to L26/L28 plan).
```
