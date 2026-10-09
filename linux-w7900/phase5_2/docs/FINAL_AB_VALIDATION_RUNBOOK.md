# FINAL A/B Validation Runbook — next mission (Phase 5.3)

Mission boundary reminder: Phase 5.2 prepared everything but did NOT build
or run the operational patched leg, and did NOT execute the final A/B.

## Preconditions

1. `python3 scripts/check_final_handoff.py --check-only
   repos/rca-evidence/findings/phase5_1/FINAL_HANDOFF.json
   --rca-root repos/rca-evidence
   --rca-evidence-sha 494907699f3b57095663f0a70b42278001a8efb7`
   → PASS, exit 0 (fail closed on ANY mismatch).
2. Frozen upstream objects complete in `repos/rocm-libraries`
   (`refs/phase52/frozen-base` → `7c5866144...`; blob inventory 0 missing).
3. Leg A (frozen unpatched) ALREADY BUILT in Phase 5.2:
   `install/legA-frozen-baseline/lib/libMIOpen.so.1.0`
   sha256 `7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d`
   (config-identical to the historical baseline; CMakeCache 0 opt/rocm).

## Leg A re-materialization (ONLY if the artifact is lost)

    source scripts/env_rocm7141.sh
    MIOPEN_SOURCE=$PWD/build/recon/frozen-base-checkout/projects/miopen \
    MIOPEN_BUILD=$PWD/build/legA-frozen-miopen \
    MIOPEN_INSTALL=$PWD/install/legA-frozen-baseline \
      bash scripts/build_leg_miopen.sh
    sha256sum install/legA-frozen-baseline/lib/libMIOpen.so.1.0
    # MUST equal 7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d
    # — otherwise STOP and investigate before any A/B run.

DO NOT use `prepare_validation_legs.sh leg-a <sha>` for the final mission:
that path builds into `install/baseline` — the HISTORICAL b68f894 preflight
leg — and would silently overwrite the preflight evidence artifact. The
`leg-a` script mode is retained for preflight/history purposes only.

## Abort protocol (mandatory)

On ANY failure anywhere in the final mission (consumer check, leg build,
harness run, ctest, dump comparison): STOP immediately. Preserve logs,
cache dirs, build and install directories VERBATIM. Report FAIL with the
raw evidence. NO retries with changed flags, NO reuse of failed labels,
NO environment edits to make a step pass.

## Leg B construction (authorized ONLY in the final-validation mission)

    source scripts/env_rocm7141.sh
    # reconstruct + build in one step (tree-identity enforced by the consumer):
    ENABLE_APPLY=1 bash scripts/prepare_validation_legs.sh leg-b \
        repos/rca-evidence/findings/phase5_1/FINAL_HANDOFF.json

The `--apply` path re-verifies every hash, applies the ordered series into
a clean worktree, `git add -A` + `git write-tree`, and REFUSES unless the
tree equals `605d0d214acdbc06086fdb27c61fec970c0f2798`. Then it builds with
the IDENTICAL script/flags as Leg A (`build_leg_miopen.sh`) into
`build/patched-miopen` + `install/patched`.

Build-flag identity must be RECORDED, not trusted — save with the phase-5.3
evidence:

    for k in MIOPEN_BACKEND MIOPEN_USE_HIPRTC MIOPEN_USE_COMGR \
             MIOPEN_USE_COMPOSABLEKERNEL CMAKE_BUILD_TYPE GPU_TARGETS \
             AMDGPU_TARGETS CMAKE_CXX_COMPILER; do
      echo "== $k"; grep -h "^$k:" build/legA-frozen-miopen/CMakeCache.txt \
                                  build/patched-miopen/CMakeCache.txt
    done | tee legAB_cmakecache_identity.txt   # every pair must be identical

Also bind the patched leg's driver: `LD_LIBRARY_PATH=install/patched/lib:$LD_LIBRARY_PATH
./install/patched/bin/MIOpenDriver --version` → 3.6.2.

## Harness execution (both legs, single-variable discipline)

    # Leg A:
    MIOPEN_LOG_LEVEL=6 bash scripts/run_validation_leg.sh legA-frozen final-ab-a \
        ./build/kthvalue-harness/kthvalue_runtime_harness_gfx1100
    # Leg B:
    MIOPEN_LOG_LEVEL=6 bash scripts/run_validation_leg.sh patched final-ab-b \
        ./build/kthvalue-harness/kthvalue_runtime_harness_gfx1100

Invariants enforced/checked per run:

* SAME harness binary both legs — wrapper prints its sha256; must equal
  `b830b37a5aa7aef37da8c79e3ceb30435fd631b99dda29516f2ed36c152e7ef8f`.
* Source-built lib provenance via dladdr lines for `miopenCreate` AND
  `miopenKthvalueForward` → `install/<leg>/lib/libMIOpen.so.1`
  (NEVER bypass `run_validation_leg.sh` — bare soname dlopen picks the
  wheel libMIOpen; auditor-proven).
* Fresh cache per label (`MIOPEN_CUSTOM_CACHE_DIR` + `XDG_CACHE_HOME`);
  the wrapper refuses a non-empty dir unless `FRESH_CACHE_FORCE=1` (which
  downgrades the run to non-fresh-cache-grade and says so).
* `MIOPEN_LOG_LEVEL=6` mandatory (Info2 dispatch evidence):
  `FindSolutionImpl KthvalueFwd`, `Invoker registered ... solver
  KthvalueFwd`, `kernel_name = KthvalueFwd`, RTC `LoadBinary(miss)` →
  HIPRTC compile → `SaveBinary` of `MIOpenKthvalue.cpp.o` (gfx1100).
* Deterministic cases (Phase-3 set): [100,500] FP32 k10; [10,20,300] FP32
  k137 keepDim; [8,3,10,2000] FP16 k2000 keepDim. PASS = values AND
  indices exact vs CPU reference (0 mismatches), dumps byte-identical
  between legs.

## HIPRTC self-contained regression test (patch 0003)

* Patched build: in-tree `ctest -R '^test_hiprtc_selfcontained$'` → PASS
  (run it with a fresh `MIOPEN_CUSTOM_CACHE_DIR`/`XDG_CACHE_HOME` exported
  to a dedicated dir so the build-tree test cannot reuse a warm cache);
  direct `test_hiprtc_selfcontained <kernels-dir>` `--mode=positive` and
  `--mode=ordinary` → PASS.
* EXPECTATION (set in Phase 5.2, Gate B06): `--mode=negative` on Linux
  ROCm 7.14.1 will report isolation-insufficient (embedded hiprtc builtins
  keep type_traits/limits/initializer_list reachable under every flag
  combination). That is an honest diagnostic, NOT a failure of the patch;
  the no-STL regression evidence remains the Windows run. Do NOT attempt
  to "fix" the environment with `-D__has_include` overrides (spoof vector,
  B06) or by touching system STL headers.
* BatchNorm spot-check + optional one-epoch YOLO26n coco8 amp=False per
  the Windows handoff doc §4–5.

## Recording

Before the first run, refresh and record the machine baseline (GPU/driver
identity, venv + lib sha256s) so the A/B is bound to a recorded
environment state. Per-leg raw logs, cache listings, libMIOpen sha256,
harness sha256, dump diffs (`cmp` legA vs legB for values and indices),
the CMakeCache identity record, and the PASS/FAIL statement go to the
phase-5.3 evidence branch. Only after both legs pass may
`linux_validation_status` be reported PASS to the RCA repo (manifest
update happens on the Windows side per its own process).

## Forbidden

* Reusing the historical b68f894 baseline as the A-side control.
* Mixing system ROCm 7.2.1 into any validation process (see
  ROCM_LIBRARY_PROVENANCE.md).
* Running any patched GPU workload outside the authorized mission.
* Upstream PRs/issues/comments; DCO sign-offs; pushing to ROCm repos.
