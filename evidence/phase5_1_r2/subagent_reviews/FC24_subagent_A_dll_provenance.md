# F-C2-4 Subagent A — Windows DLL loader / dependency provenance audit

Reviewer: fresh-context general-purpose subagent (agent_26ecbcd6), read-only,
own commands incl. PowerShell/powershell Start-Process captures and psutil 7.2.2.

## VERDICT: PASS (no BLOCKER/MAJOR/MINOR; 1 NIT)

Confirmed from its own runs:
- Direct imports of test exe: hiprtc0714.dll + MSVCP140/VCRUNTIME140/KERNEL32 +
  UCRT apisets only; hiprtc0714.dll itself imports ONLY KERNEL32 (no transitive
  ROCm deps → single prepended dir sufficient).
- DLL uniqueness: exactly two copies on machine (yolo_amd env wheel + conda-base
  wheel), byte-identical sha256 c6159dd1…fd86e; absent from System32/Windows/
  SysWOW64/VS trees/WinSDK/llvm\bin/buildtools/ctest CWDs. Version resource
  "AMD Accelerated Parallel Processing hiprtc 7.14 Runtime" — correct 7.14 stack.
- Repro: clean PATH → direct exe exit -1073741515 signed = 0xC0000135; with
  _rocm_sdk_core\bin prepended → exit 0, "PASS: kernel compiled without host STL
  (5784-byte code object)". ctest clean env → Passed 0.13s rc 0.
- CMake derivation traced step-by-step against the shim config; generated
  CTestTestfile carries ENVIRONMENT PATH prepend + SKIP_RETURN_CODE 4.
- Loaded-module provenance independently reproduced via psutil:
  ...\envs\yolo_amd\..._rocm_sdk_core\bin\hiprtc0714.dll, sha c6159dd1… (match).
- Falsification: no wrong-version load path — loader order (app dir/System32/
  Windows/CWD) all clean; prepended dir FIRST in PATH; both wheel copies
  identical; relocation yields loud 0xC0000135, never silent wrong version.
- RCA doc cross-checked: all technical claims match (NITs: ctest-form failure
  not re-run — requires reverting source, prohibited; review files §7 were
  pending at review time — now written).

Note: review was performed against interim HEAD 61410b68 (pre MINOR-1
hardening); the hardening changes only the escaping of the inherited PATH tail
(comment + string(REPLACE)) — none of the audited provenance facts change; the
final-HEAD clean-env ctest PASS (d758aed7, evidence/phase5_1_r2/ci/
fc24_fix_ctest_clean_env.json) re-exercises the loader path end-to-end.
