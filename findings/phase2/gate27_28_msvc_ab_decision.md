# Gates 27–28 — MSVC A/B experiment and H10 vs H11/H12-P2 decision

Date: 2026-10-07. Raw evidence: `evidence/phase2/raw/msvc/`.

## What was installed (and only what)

Per Gate-27 authorization ("minimum supported Microsoft C++ Build Tools",
no IDE), installed via winget (log: `gate27_winget_install.txt`, exit 0):

```text
winget install --id Microsoft.VisualStudio.2022.BuildTools --silent \
  --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools \
  --includeRecommended --installPath C:\BuildTools"
```

- MSVC toolset `14.44.35207` (cl.exe FileVersion 19.44.35229.0)
- Windows SDK `10.0.26100.0` (ucrt/shared/um/winrt/cppwinrt includes)
- `vswhere.exe` at the standard `%ProgramFiles(x86)%\Microsoft Visual
  Studio\Installer\` location
- `type_traits` now physically at
  `C:\BuildTools\VC\Tools\MSVC\14.44.35207\include\type_traits` (108,106 B)
- No IDE; `cl` is NOT on plain-shell PATH (unchanged resolution)
- ROCm stack untouched — post-install SHA256 re-verify:
  MIOpen.dll `74b4ee038803606e…`, hiprtc0714.dll `c6159dd12714eed4…`
  (identical to pre-install) — `gate27_post_install_record.txt`
- This is a TEST PREREQUISIAL experiment, not "the fix" (ownership decided
  in Gate 28 below).

## The A/B result (all with the SAME clean env, same wheel stack)

| Arm | Environment | Standalone HIPRTC `<type_traits>` | Minimal MIOpen BN repro | Raw evidence |
|---|---|---|---|---|
| baseline (Gate 24, MSVC absent) | plain shell | **FAIL** `HIPRTC_ERROR_COMPILATION (6)` `'type_traits' file not found` | **FAIL** same chain | `hiprtc/header_matrix.json`, `clean_env/C_bn_minimal_train.txt` |
| **A** | MSVC installed, **plain shell** (INCLUDE/LIB unset, no dev shell) | **PASS** (all 6 probes: none/type_traits/utility/limits/cstdint/initializer_list) | **PASS** (`y mean=-0.000000`, exit 0) | `gate27_armA_plain_shell.txt`, `gate27_armA_bn_repro.txt` |
| **B** | VS dev shell (`vcvars64.bat`: INCLUDE/LIB/VCToolsInstallDir set) | **PASS** | **PASS** | `gate27_armB_devshell.txt` |
| **C** | child process with ONLY `INCLUDE` injected (no dev shell) | **PASS** | **PASS** | `gate27_armC_include_only.txt` |

Mechanism confirmation for arm A: the wheel's bundled clang, re-probed
with `-v -E` in the same plain shell, now constructs
`-internal-isystem C:\BuildTools\VC\Tools\MSVC\14.44.35207\include` +
Windows SDK dirs (vs. resource-dir + VS8/9/10-era fallbacks before
install) — `miopen_type_traits.hpp` preprocessing succeeds.
HIPRTC inherits this MSVC auto-discovery (clang MSVC toolchain detection
via vswhere/registry — no environment variable involved).

## Additional mechanism facts (this gate)

1. **`-I` option support**: hiprtcCompileProgram honors `-I<dir>` /
   `-isystem<dir>` (fake-header probe: `hiprtc/include_option_probe.json`);
   nvrtc-style `--include-path=` is rejected.
2. **Wheel MIOpen DOES pass `-I$ROCM_PATH/include`** when `ROCM_PATH` is
   set — proven by the cache-isolated poisoned-header A/B
   (`gate32_poison_header_test_v2.txt`): with
   `ROCM_PATH=C:\hiprtc_poison` whose `include\type_traits` is
   `#error POISONED_TYPE_TRAITS_SHIM_EXPERIMENT`, the BN compile FAILS on
   exactly that poisoned file (the `-I` dir SHADOWS the auto-discovered
   MSVC STL). First run (`gate32_poison_header_test.txt`) was
   cache-confounded (kernel DB warm) and is retained as the
   cache-confounder demonstration; v2 redirects HOME/USERPROFILE/LOCALAPPDATA
   to force recompilation (positive control: recompile actually happened).
   NOTE: `MIOPEN_USER_DB_PATH` was NOT honored by this MIOpen build in the
   v1 run — evidence: fresh BN entries appeared in the default
   `~/.miopen/cache/3.5.2.cd957402/gfx1151_20.ukdb` instead.
3. The wheel MIOpen contains the log string
   `"HIPRTC compile ROCm include path argument"` (develop-branch
   `comgr.cpp` `BuildHip` logic present in the 3.5.2 rockrel binary).

## Gate 28 — decision table mapping

Observed pattern (brief's "Result pattern 1"):

> Standalone HIPRTC `<type_traits>`: FAIL before MSVC; PASS after
> installing MSVC **even in plain shell**.

→ **Strong support for H10: host MSVC C++ STL presence is the operative
prerequisite on this machine.** Not pattern 2 (dev-shell-only), not
pattern 3 (MSVC present but still fails), not pattern 4
(standalone-pass/MIOpen-fail): standalone and MIOpen flipped together.

### Ownership analysis (H10 vs H11 vs H12-P2)

The A/B separates the *machine-level* cause (STL absence — now proven
sufficient and necessary) from the *product-level* question (who should
supply/discover/document the STL):

- **H10 (undeclared prerequisite)** — SUPPORTED as the operative mechanism:
  with MSVC present, everything works, including via pure auto-discovery.
  But Phase-1 C028 (AMD Windows install docs declare no MSVC
  prerequisite) means AMD has NOT declared this prerequisite — the docs
  gap is real.
- **H11 (wheel packaging/include-path defect)** — SUPPORTED as the
  *design* gap, mechanically corroborated three ways:
  (a) hiprtc source hardcodes `-target x86_64-pc-windows-msvc` +
  `-fms-extensions/-fms-compatibility` on `_WIN32` and injects NO
  C++-stdlib include path (`hipamd/src/hiprtc/hiprtcInternal.cpp`,
  develop); (b) the wheel ships no STL (Phase-1 C019 + Gate 25); the
  wheel's clang search list before MSVC install was resource-dir +
  nonexistent VS8/9/10 fallbacks; (c) the `-I$ROCM_PATH/include` hook
  exists and is honored — a wheel-side or docs-side remedy is available
  without any MIOpen change.
- **H12-P2 (HIP ≥ 7.0 MIOpen header-gating design)** — SUPPORTED as the
  *trigger* of the regression window: MIOpen commits `ce14dab3` (PR #3803 "All 7.0
  hipRTC fixes", 2025-06-16, `miopen_type_traits.hpp`) and `b514736610`
  (PR #3147, 2025-12-18, `miopen_utility.hpp`, independently) added the
  outer `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` gate so that for
  HIP ≥ 7.0 the no-STL compatibility shim is disabled and real std headers
  are required **even in runtime-compile mode**. Upstream
  context (ROCm/clr `hipamd/src/hiprtc/hiprtc.cpp`): hiprtc's builtin
  header previously *defined* `std` type traits; in 7.0 they moved to
  `__hip_internal`, so consumers must include the real STL — safe on
  Linux (system libstdc++ always present), NOT safe on Windows wheels
  without MSVC.

### Verdict

**LEVEL 3 (exact defect + ownership): PROVEN as a two-layer defect with
exact upstream anchors.**

1. *Proximate, machine-level*: no C++ standard library is discoverable by
   the wheel's msvc-triple clang/HIPRTC on this machine — installing MSVC
   Build Tools (or providing an STL via `-I`) removes the failure with no
   other change.
2. *Root, design-level*: MIOpen commit `ce14dab3` (PR #3803) made
   runtime-compiled kernels unconditionally require real C++ std headers
   for HIP ≥ 7.0, while AMD's Windows wheel distribution neither ships an
   STL for the bundled clang, nor sets/discoverers an include path, nor
   documents MSVC as a runtime prerequisite. The defect therefore lives
   jointly in **MIOpen's HIP≥7.0 RTC header gating** (assumption: real STL
   available to RTC on all platforms) and **AMD Windows wheel
   packaging/documentation** (no STL provision, no discovery, no declared
   prerequisite). Single-layer blame is NOT supported: either side closing
   its gap removes the user-visible failure.

Confidence: High (each link locally evidenced: A/B arms, poisoned-header
shadowing, upstream source + commit diff, docs evidence from Phase 1).
