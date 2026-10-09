# FINAL R2 A/B VALIDATION — Linux W7900 (gfx1100)

## Design

Single-variable A/B: Leg A = frozen unpatched upstream `7c586614` (reused frozen binary,
sha `7e045dc0…`); Leg B = exact R2 tree `b983cadd…` (built this mission, sha `bf21a5fa…`).
Identical semantic CMake configuration (HIP backend, HIPRTC ON, COMGR ON, CK OFF,
RelWithDebInfo, GPU_TARGETS=gfx1100, BUILD_TESTING=OFF), identical ROCm 7.14.1 venv
toolchain, same GPU, same harness binaries, same deterministic inputs, per-leg fresh
runtime caches. The ONLY difference is the R2 three-patch series.

## Execution facts

- Build: both legs via the published `build_leg_miopen.sh` wrapper (byte-identical to the
  Phase-5.2.1 manifest). Leg B configure/build/install exit 0; `CACHE_CLEAN` (zero
  `/opt/rocm` in cache); 10 changed files exactly.
- Runtime: every execution through `run_validation_leg.sh` (LD_PRELOAD leg libMIOpen +
  leg-lib LD_LIBRARY_PATH prepend + per-label fresh cache dirs; wrapper refuses non-empty
  cache dirs). The wheel's MIOpen (`941a92da…`, present in 3 wheel locations) provably
  shadows bare-soname dlopen under the ambient env — the wrapper is mandatory and its
  effect was attack-verified (L11 A3).
- Provenance: in-stream `dladdr` on the exact function pointers used, every gate
  (L06 probes, L08/L09 harnesses, L10 python process).

## Results

- Kthvalue (direct `miopenKthvalueForward`): 3/3 cases PASS on both legs;
  value/index mismatches 0; max_abs_err 0; 15/15 dump files byte-identical A/B
  (inputs, outputs, indices, CPU-expected); dispatch chain proven
  (FindSolutionImpl KthvalueFwd → MIOpenKthvalue.cpp.o kern_db miss → HIPRTC compile →
  INSERT → run kernel_name=KthvalueFwd, `-mcpu=gfx1100`).
- BatchNorm (direct public API fwd training + backward, N=8 C=16 H=64 W=64 FP32 spatial,
  CPU float64 full-gradient reference): all 6 checks PASS both legs — y 3.75e-7 (tol 1e-5),
  dx 2.30e-7 (1e-5), dw 6.47e-7 (1e-4), db 2.67e-7 (1e-5), running mean 2.6e-12 (1e-4),
  running var rel 5.4e-8 (1e-3); identical values both legs; finite; nontrivial running
  stats; GPU sync after every phase.
- Optional YOLO26n coco8 1-epoch amp=False smoke on Leg B: in-process proof the training
  process used the source-built R2 MIOpen (`YOLO_MIOPEN_PROVENANCE … bf21a5fa…`);
  507 find-db entries for the actual conv shapes + 653 comgr JIT objects in the leg's
  fresh cache (physical kernel-execution evidence found by the L10 reviewer).

## Interpretation

Both legs passing means the R2 fix does not regress the covered Linux workloads. It does
NOT mean the Windows no-STL failure was reproduced on Linux, and no such claim is made.

## Fresh-cache proof

Per-label `MIOPEN_CUSTOM_CACHE_DIR`/`MIOPEN_USER_DB_PATH`/`XDG_CACHE_HOME` under
`runtime/<leg>-cache/<label>`; wrapper aborts on non-empty dirs (L11 A4); each L08/L09/L10
log contains the kern_db-miss / Prefetch-unreadable / Database-created lines and the
per-leg ukdb files were independently queried by the L08 reviewer (2 kthvalue rows per leg).
