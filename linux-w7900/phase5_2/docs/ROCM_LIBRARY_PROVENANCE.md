# ROCm Library Provenance — Phase 5.2 (Gate B07)

Validation environment: isolated ROCm 7.14.1 wheel SDK venv
(`tools/rocm7141-venv`), entered ONLY via `scripts/env_rocm7141.sh`
(strips every `/opt/rocm` entry from PATH/LD_LIBRARY_PATH).
System ROCm 7.2.1 (`/opt/rocm`) exists independently and is never loaded.

## Static state (re-verified this phase)

| Check | Result |
|---|---|
| PATH `/opt/rocm` entries | 0 |
| LD_LIBRARY_PATH `/opt/rocm` entries | 0 |
| ROCM_PATH / HIP_PATH | venv `_rocm_sdk_devel` |
| `grep -c "opt/rocm"` on leg CMakeCaches | 0 (both baseline + frozen legA) |
| `ldd` resolutions of source-built libMIOpen into `/opt/rocm` | 0 |

## Dynamic state (live process, real GPU API activity)

`phase5_2/scripts/b07_library_isolation_audit.cpp` run through the same
launcher discipline as the final legs (`run_validation_leg.sh`):
dlopen(libMIOpen.so.1) → `miopenCreate`=0 → tensor descriptor ops →
explicit dlopen of the lazy set → full `/proc/self/maps` scan.

dladdr provenance (all inside venv or source-built install):

| Object | Resolved path |
|---|---|
| `miopenCreate` / `miopenKthvalueForward` | `install/<leg>/lib/libMIOpen.so.1` (source-built; LD_PRELOAD first-in-scope) |
| `libhiprtc.so.7` | `_rocm_sdk_core/lib` |
| `libamdhip64.so.7` | `_rocm_sdk_core/lib` |
| `libamd_comgr.so.3` | `_rocm_sdk_core/lib` |
| `librocblas.so.5` | `_rocm_sdk_libraries/lib` |
| `libhipblaslt.so.1` | `_rocm_sdk_libraries/lib` |
| `libhsa-runtime64.so.1` | `_rocm_sdk_core/lib` |

Maps scan: 22 ROCm-related objects loaded (including lazy ones: CK grouped
conv plugin, rocroller, rocm_kpack, aqlprofile, hermetic
`rocm_sysdeps_*` sqlite3/zstd/bz2/lzma/numa/drm/elf/z wrappers) —
**zero** under `/opt/rocm`.

## Known attack surfaces and their guards (auditor-verified)

1. **ldconfig cache** maps `libhiprtc.so.7`/`libamdhip64.so.7`/
   `librocblas.so.5` to `/opt/rocm-7.2.1`. Guard: glibc resolution order
   puts LD_LIBRARY_PATH (venv first) ahead of the cache — proven with
   `LD_DEBUG=libs` and the live maps scan. Launching validation processes
   WITHOUT `env_rocm7141.sh` is forbidden by the runbook.
2. **Wheel `libMIOpen.so.1` shadowing**: the venv `_rocm_sdk_libraries`
   contains a wheel libMIOpen. Guard: `run_validation_leg.sh` LD_PRELOADs
   the leg's source-built absolute-path library and prepends the leg lib
   dir. The auditor demonstrated a bare soname dlopen picks the wheel —
   therefore every leg MUST go through the wrapper (runbook rule).

## Logs

* `phase5_2/logs/B07_isolation_audit.log` (dynamic audit, full provenance)
* `phase5_2/logs/B07_static_checks.log`
