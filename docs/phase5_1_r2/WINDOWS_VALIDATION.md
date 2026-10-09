# WINDOWS VALIDATION RECORD — P5.1-CANDIDATE-R2 (gfx1151)

Machine: Windows 11, AMD Ryzen AI MAX+ 395, Radeon 8060S (gfx1151),
PyTorch 2.12.0+rocm7.14.0 (wheel), MSVC 14.44.35207, CMake 4.4.4/Ninja.
All runs on final candidate HEAD `d758aed7dc8c3ff17d7c4672f1281f09ca3ef131`
(tree `06008706…`); every artifact under `evidence/phase5_1_r2/`.

## Toolchain + environment (R20)
environment/r20_environment_audit.txt — torch/GPU/DLL/MSVC/CMake identities;
wheel MIOpen.dll `74b4ee03…` pristine at start; hiprtc0714.dll `c6159dd1…`.

## CMake/CTest integration (R26)
- Fresh build dir `phase5_1_r2_build/ci_test` (R1's cache never reused),
  BUILD_TESTING=ON, MIOPEN_USE_HIPRTC=ON: configure/build/discover/run all
  exit 0 (ci/*.log, ci_integration.json).
- Test #10 executes: **Passed, 100% tests passed — NOT Skipped** (genuine
  Windows no-STL hard PASS).
- Linked hiprtc = namespaced imported-target arm (ninja LINK_LIBRARIES
  carries the full-path hiprtc.lib; no bare -lhiprtc fallback).
- Exit-code semantics proven by fixture (ci/exit_code_fixture.json):
  0→PASS rc0, 1→FAIL rc8, 2→FAIL rc8, 4→SKIP(Not Run) rc0.
- Restricted-test-list parity (R22 CHANGE 4): MIOPEN_TEST_BFLOAT16=ON
  fresh configure → test registers `echo skipped` + DISABLED On → ctest
  `***Not Run (Disabled)` rc 0 — identical to add_test_command's policy
  path. MIOPEN_NO_GPU itself is a computed variable (test/CMakeLists:112,
  TRUE only when GPU detection reports no devices) and cannot be
  legitimately produced on this GPU host; its guard arm is the same
  code path empirically exercised by the BF16 leg (documented in
  ci/r26_ctest_validation.json).

## F-C2-4 loader RCA (user-directed interjection)
- Repro: clean system PATH → direct exe exit 3221225781 = 0xC0000135;
  via ctest → `Exit code 0xc0000135`, rc 8 (ci/fc24_loader_failure_repro.json).
- Fix: test-scoped ENVIRONMENT PATH prepend (see CI_PORTABILITY_AMENDMENT.md).
- Post-fix: SAME clean env → ctest Passed rc 0
  (ci/fc24_fix_ctest_clean_env.json); in-process psutil module snapshot
  proves the loaded DLL is `_rocm_sdk_core/bin/hiprtc0714.dll`
  sha256 `c6159dd1…` (ci/fc24_dll_load_provenance.json). Both machine-wide
  hiprtc0714.dll copies are byte-identical (no version ambiguity).

## HIPRTC 13-cell adversarial matrix (R25)
ci/ci_matrix_phase5_1.json — 13/13 PASS on d758aed7, expectations identical
to R1: ordinary ×2 PASS; positive/unpatched exit 1 (exact missing-STL
signature); positive/patched exit 0 (5784-byte code object);
negative/unpatched exit 0 (signature control); negative/patched exit 1
(rejected); with-stl ×2 PASS; adversarial: missing dir/wrong dir/bad mode
→ 2, bad arch → 1, CPATH STL-reachable → 4 (INCONCLUSIVE, never a PASS).
Independent re-execution audit: R25 subagent PASS (re-ran 11/13 cells).

## MIOpen.dll rebuild + provenance (R27)
build/build_provenance.json — fresh `phase5_1_r2_build/miopen` from the
exact R2 tree: `bin/MIOpen.dll` SHA256
`eb0a1bf0d31cac5ae7597df423f3d6cb26f433df9c20110ae1d51fddd6ed0bfd`
(change is CMake-test-only; production kernels identical — DLL rebuilt and
revalidated anyway per mission).

## Runtime (reversible substitution; wheel restored after every cycle)
runtime/dll_provenance.json + runtime_validation.json — PASS:
- Loaded-path proof: GetModuleFileNameW in the target process → wheel path,
  in-process SHA256 == `eb0a1bf0…` (rebuilt R2 DLL); GPU = 8060S; active
  torch runtime 2.12.0+rocm7.14.0; no stale wheel copy in process.
- Fresh-cache no-STL BatchNorm (R28A): MSVC include renamed away, fresh
  profile, scrubbed env — fwd+bwd finite, running stats updated, exit 0.
- Numerics vs CPU fp64 (R28D): all within fixed tolerances
  (y/dx/dw/db/rm/rv — details in runtime_validation.json).
- Wheel DLL restored + SHA-verified after every cycle.

## Real workload (R28E/F)
yolo/yolo_train.json — PASS:
- YOLO26n coco8, 1 epoch, amp=False: exit 0, TRAIN_DONE, best.pt produced,
  in-process provenance `eb0a1bf0…`, device 8060S.
- Default AMP: exit 0, TRAIN_DONE, weights, provenance — and this run's
  AMP check PASSED → **genuine amp=True** (no FP32 fallback; R1's
  environment-dependent check failure is no longer present — R1 control
  evidence showed that failure affected the pristine wheel identically).
- Wheel DLL restored, SHA `74b4ee03…` verified.

## Known-honest limitations
- Linux results: NONE claimed (PENDING; see LINUX_FINAL_VALIDATION_HANDOFF).
- The STL-reachable (CPATH) cell legitimately renders exit 4; under CTest
  with SKIP_RETURN_CODE 4 it would show as Skipped — visible, never PASS.
- MIOPEN_NO_GPU arm verified by source-inspection equivalence + BF16
  empirical run (computed variable cannot fire on a GPU host).
