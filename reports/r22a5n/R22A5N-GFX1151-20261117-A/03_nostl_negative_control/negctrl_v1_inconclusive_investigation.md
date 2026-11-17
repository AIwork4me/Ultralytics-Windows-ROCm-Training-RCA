# R22A.5N — negative-control v1 INCONCLUSIVE: investigation & resolution

- v1 attempt (`nostl_prefit_control.json`, run-id R22A5N-G1-NEGCTRL): ran the
  official leg with `--expect FAIL` from `p16_testenv`
  (torch 2.12.0+rocm7.14.1). It UNEXPECTEDLY PASSED (exit 0) →
  classified INCONCLUSIVE by the verifier, per the mission contract
  ("never manufacture the expected failure; investigate").
- Investigation (loaded-DLL identity in that environment):
  the child loaded
  `C:\Users\rocm\miniconda3\envs\pm13437_merged\...\_rocm_sdk_libraries\bin\MIOpen.dll`
  (sha256 ed7c67a9…, build 3.6.2.f0a5d266, PR#13437 marker=2) — the
  P13/P14 MERGED-SOURCE-built (post-fix) DLL. `p16_testenv` contains NO
  MIOpen.dll of its own (7.14.1-era venv without an own `_rocm_sdk_libraries`
  tree), so the Windows loader satisfied the dependency from another
  environment on this development host via the DLL search path.
  The bytes exercised were therefore post-fix, and the PASS is fully
  explained — hidden-STL reachability is NOT implicated (the same leg under
  the same isolation FAILS on genuinely pre-fix bytes, see v2).
- Host-environment lesson recorded: on this shared dev host, a venv without
  its own `_rocm_sdk_libraries\MIOpen.dll` silently inherits a foreign
  MIOpen.dll through the loader search path. The candidate environment
  (C:\r22a5n\venv) is NOT exposed to this (own DLL present; G0 child evidence
  proves the loaded path+SHA equal the frozen wheel).
- Resolution: v2 (`nostl_prefit_control_v2.json`, run-id R22A5N-G1-NEGCTRL-V2)
  from `pm13437_official` — the independently verified official pre-fix
  environment (P13/P14 post-merge validation) whose OWN
  `_rocm_sdk_libraries\bin\MIOpen.dll` is the genuine pre-fix build
  (sha256 e97891df…, version 3.5.2.cd957402, PR#13437 marker=0) and is the
  DLL actually loaded in-process (recorded in the receipt). Result:
  OFFICIAL_PRE_FIX_EXPECTED_FAIL / MIOPEN_HIPRTC_COMPILATION with the exact
  #3956 signature (`miopen_type_traits.hpp:151: fatal error: 'type_traits'
  file not found` in MIOpenBatchNormFwdTrainSpatial.cpp) under equivalent
  no-STL isolation. v1 evidence retained unmodified.
