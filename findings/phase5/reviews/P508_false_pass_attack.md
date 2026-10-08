# P508 — Adversarial false-PASS attack review of `test_hiprtc_selfcontained`

- Date: 2026-10-08
- Reviewer: CI security review (independent re-execution, no prior verdicts trusted)
- Target: `projects/miopen/test/hiprtc_selfcontained.cpp` @ candidate tree `39319c4d2f51998529dc0f2144841ba4cbe82ff3`
- Binary attacked: `C:\Users\rocm\Desktop\YOLO_AMD\phase5_build\ci_test\bin\test_hiprtc_selfcontained.exe`
- Claimed matrix: `evidence/phase5/ci/ci_matrix_phase5.json` (13/13 PASS)

## VERDICT: CONDITIONAL PASS

No BLOCKER and no MAJOR false-PASS vector found. Every in-scope attack on the
CI-wired configuration (positive mode, default `--isolate=-nostdinc`, arch from
CMake) failed to produce exit 0 on a broken tree. Two MINOR unresolved vectors
and several NITs keep this from an unconditional PASS; conditions are listed at
the end.

## 0. Provenance verification (before attacking)

```
$ sha256sum phase5_build/ci_test/bin/test_hiprtc_selfcontained.exe
6bc922596fdff45e473e1d781483d00228785443ee3aaf6f0a800a3bb1ac15db   (matches matrix test_binary_sha256)
$ sha256sum rocm-libraries-phase5-candidate/projects/miopen/test/hiprtc_selfcontained.cpp
c97e748eebdd2b47a5efb97dce876f73b80a6e88615609075734422464313c80   (matches matrix test_source_sha256)
```

Patch surface (diff pristine vs candidate `src/kernels`): modified
`miopen_type_traits.hpp`, `miopen_utility.hpp`, `radix.hpp`, `tensor_view.hpp`;
added `miopen_freestanding_{type_traits,utility,initializer_list}.hpp`.
Include chain of the tested kernel reaches **only** `miopen_type_traits.hpp`
( via `batchnorm_functions.hpp`/`configuration.hpp`/`vector_types.hpp` ) — it
does **not** reach `tensor_view.hpp`, `miopen_utility.hpp`, or `radix.hpp`.

## 1. Baseline reproduction (all four core cells)

```
$ export PATH="/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin:$PATH"
$ test_hiprtc_selfcontained.exe <candidate-kernels>  --mode=positive --arch=gfx1151   -> exit 0  "PASS: kernel compiled without host STL (5784-byte code object)"
$ test_hiprtc_selfcontained.exe <pristine-kernels>   --mode=positive --arch=gfx1151   -> exit 1  "FAIL: positive compile did not produce a code object"
$ test_hiprtc_selfcontained.exe <pristine-kernels>   --mode=negative --arch=gfx1151   -> exit 0  "PASS: unpatched kernel fails with the field signature ..."
$ test_hiprtc_selfcontained.exe <candidate-kernels>  --mode=negative --arch=gfx1151   -> exit 1  "FAIL: no-STL compile unexpectedly succeeded"
```

Matrix reproduced exactly. `with-stl` on pristine also re-verified exit 0
(ambient STL reachable via `C:\BuildTools\VC\Tools\MSVC\14.44.35207`, the path
the harness itself uses for its CPATH control).

## 2. Vector 1 — kernel-source substitution (all defended)

| Attack | Command sketch | Result |
|---|---|---|
| E1a revert ONLY `miopen_type_traits.hpp` to pristine (copy of candidate otherwise intact) | `--mode=positive` | **exit 1**, `fatal error: 'type_traits' file not found` at `miopen_type_traits.hpp:151` — the historic failure reappears from a single-file revert. Same tree `--mode=negative` → exit 0 (genuine signature). DEFENDED |
| E1b delete `miopen_freestanding_type_traits.hpp` | `--mode=positive` | **exit 1**, `fatal error: 'miopen_freestanding_type_traits.hpp' file not found`. DEFENDED |
| E1c partial revert: flip the arm to always-STL (`sed -i '151s/#if __has_include(<type_traits>)/#if 1/'`) | `--mode=positive` | **exit 1**, `'type_traits' file not found` at line 152. DEFENDED |
| E1d CRLF-mangle every kernel source (`unix2dos`) | `--mode=positive` | exit 0 on the healthy tree (5792-byte object) — no over-strictness; and since the tree is genuinely fixed this is not a false pass |
| E1e fake extensionless `type_traits` planted INSIDE the kernels dir (angle includes search `-I`) | `--mode=positive` | **exit 4 INCONCLUSIVE**, probe fired `error: STL_PROBE_REACHABLE`. The probe's option list contains the same `-I<kernels_dir>` as the kernel compile, so a planted header cannot be visible to one and not the other. DEFENDED |

## 3. Vector 2 — probe bypass (all defended; one coverage note)

Token-by-token comparison (source, `hiprtc_selfcontained.cpp`): the probe calls
`compile("stl_probe.cu", src, kernel_options(a, /*isolate_stl=*/true), false)`
and positive/negative kernel compiles call
`compile(kKernelName, kernel_src, kernel_options(args, isolate), true)` with
`isolate==true`. Both option vectors are produced by the **same**
`kernel_options(a, true)` — token-identical, including `-I<kernels_dir>`,
`--gpu-architecture`, `-DHIP_PACKAGE_VERSION_FLAT`, and the isolate option. The
only differences are the TU name/content and `require_code` (post-compile
only). No include-search asymmetry exists; environment variables apply to both
compiles identically.

| Attack | Result |
|---|---|
| `CPATH=<dir containing fake empty type_traits>`, positive | **exit 4**, probe fired. Matches matrix adversarial cell. DEFENDED |
| `CPATH=<dir containing fake empty utility>` (only `<utility>` reachable), positive, patched tree | **exit 1** — the patch's own tripwire fires: `error: "inconsistent C++ standard library availability: <type_traits> is not reachable but <utility> is ..."`. So a partial-STL leak cannot silently flip the arm. DEFENDED |
| `CPATH=<dir containing fake empty initializer_list>`, positive, patched | exit 0 — but the BN kernel's include chain never reaches `tensor_view.hpp` (verified by include-graph walk), so the `<initializer_list>` gate is not in this compile at all; the `<type_traits>` no-STL path **was** genuinely exercised and the PASS is truthful. Coverage note → finding F4 |
| `--isolate=-nostdinc++` / `--isolate=-banana` / `--isolate=` on **pristine** tree | **exit 4** all three (probe fires: STL reachable because these options do not isolate on this msvc-triple toolchain). The test refuses to issue a verdict. DEFENDED — and it proves a would-be false pass on the unpatched tree is impossible under these flags |
| `--isolate=-nostdinc++` etc. on **patched** tree | deterministic **exit 4** in 12/12 runs (loop of 4 x 2 path styles + verbatim replays). One exception window → finding F2 |

## 4. Vector 3 — signature forgery in negative mode (defended by construction)

| Attack | Result |
|---|---|
| E3a planted unconditional `#include <type_traits>` into `vector_types.hpp` of a patched copy | `--mode=negative` **exit 0** — but the failure is a *genuine* missing-STL failure (the tree truly is non-self-contained); `--mode=positive` on the same tree → exit 1. Assessment: not a false pass. The negative control proves the detector fires on the field signature; it cannot distinguish *which* header pulled the STL, but any tree that fails this way is broken, so the verdict's claim is true. Acceptable for its purpose |
| E3b `static_assert(sizeof(int)==999, "fatal error: 'type_traits' file not found")` | **exit 4** `signature=1, diagnostics=4` — refused. Key mechanism: the signature string itself contains `error:`, so any forged occurrence inflates `count_error_diagnostics` past 1. DEFENDED |
| E3c `#error fatal error: 'type_traits' file not found` | **exit 4** `signature=1, diagnostics=3` (diagnostic line + echoed `#error` line both contribute). DEFENDED |

Vector 7 (log-parser shapes): for negative mode to pass we need
`n_diag==1 && footer<=1 && signature-present && compile_status!=SUCCESS`. Every
error diagnostic contributes >= 1 `error:`; the signature contributes >= 1
wherever it appears; if they are on different lines the total is >= 2, and if
the signature is inside the error's own message the total is >= 2 as well. The
only theoretical bypass is a log truncated at an embedded NUL between the first
error and a second one (`get_log()` truncates at the first NUL) — but kernel
source is NUL-truncated by `src.c_str()` before reaching the compiler, so NULs
cannot enter echoed source through the tested file, and planting one in a
header requires the same attacker-controlled-tree position as E3a. NIT.

## 5. Vector 4 — code-object lies (defended, with one vacuous-pass finding)

| Attack | Result |
|---|---|
| **E4a 0-byte `MIOpenBatchNormFwdTrainSpatial.cpp`** | **exit 2** — `hiprtcCreateProgram` rejects the empty source (`create=3`); positive mode maps create-failure to SETUP. Not PASS. A truncated kernel cannot yield a code object. DEFENDED (see F5: exit 2 vs 1 semantics) |
| E4b file beginning with `\x00` then garbage | **exit 2** — `c_str()` truncates at the NUL, reducing to the empty-source case. DEFENDED |
| **E4c file replaced with `extern "C" __global__ void trivial_kernel() {}`** | **exit 0**, `PASS: kernel compiled without host STL (3840-byte code object)` — **finding F1**: the test performs no validation that the kernel source is the real BN kernel. A vacuous pass with a one-line kernel |
| Code-retrieval path review | `require_code=true`: `hiprtcGetCodeSize` must return SUCCESS with size>0 AND `hiprtcGetCode` must succeed or `code_size` is reset to 0 → FAIL. Empty code with SUCCESS status cannot pass (`code_size > 0` gate). No hole found |

## 6. Vector 5 — argument confusion (defended except duplicate-arg downgrade)

| Attack | Result |
|---|---|
| trailing `\`, trailing `/`, all-forward-slashes, dir with spaces, relative `kernels` (cwd=src/), UNC `//localhost/c$/...` | all exit 0 on the healthy patched tree (correct behavior; read_file and `-I` tolerate mixed separators) |
| kernels arg is a FILE | exit 2 `SETUP ERROR: cannot read .../MIOpenBatchNormFwdTrainSpatial.cpp/MIOpenBatchNormFwdTrainSpatial.cpp` |
| `--arch=gfx1151x` / `--arch=` / `--arch="gfx1151 "` / `--arch=gfx9999` (matrix) / `--arch=gfx1151:junk` on pristine | **exit 1** in every case — bad arches fail closed, never PASS |
| `--hip-flat=99999999999999999999` | exit 2 `bad --hip-flat value` (stoull range check) |
| `--mode=no-such-mode` | exit 2 usage (matrix reproduced) |
| `--mode=positive --mode=ordinary` | **exit 0 running ORDINARY** (last-wins) — finding F3: silent downgrade of the gate to a toolchain sanity check if a wrapper ever appends a second `--mode` |
| `--mode=ordinary --mode=positive` | exit 0 running positive (last-wins, benign order) |

## 7. Vector 6 — CMake wiring (no false-PASS path found)

- Registration in `phase5_build/ci_test/test/CTestTestfile.cmake:25` is the
  **real command**: the exe, `${CMAKE_CURRENT_SOURCE_DIR}/../src/kernels`
  (absolute, source tree), `--arch=gfx1151`. The `add_test_command` skip path
  (`COMMAND echo skipped` + `DISABLED On`, test/CMakeLists.txt:332-333) did
  **not** apply: `test_hiprtc_selfcontained` is not in any `SKIP_TESTS`
  contribution (sqlite/db_sync/ctc/conv2d/immed_conv2d) and
  `SKIP_ALL_EXCEPT_TESTS` is empty in this configure. Even if it had applied,
  `DISABLED` makes ctest report *Not Run*, not *Passed*; only a CI that
  ignores ctest's per-test status could mistake that for a pass.
- `WORKING_DIRECTORY=KERNELS_BINARY_DIR` and
  `ENVIRONMENT=MIOPEN_USER_DB_PATH=...` are irrelevant to this test (all paths
  absolute; no DB use).
- Arch selection (`MIOPEN_TEST_HIPRTC_ARCH` > `GPU_TARGETS[0]` >
  `CMAKE_HIP_ARCHITECTURES[0]`, feature suffix stripped): this configure passed
  `-DCMAKE_HIP_ARCHITECTURES=gfx1151` → `--arch=gfx1151` registered. A
  wrong-but-valid arch still compiles headers identically (the STL question is
  front-end); a bogus arch fails closed (verified). No silent-degrade-to-default
  path exists because the binary's own default is also a valid arch and the
  failure mode of a bad arch is FAIL, not PASS.
- `EXCLUDE_FROM_ALL` + `add_dependencies(miopen-tests / miopen-check)`: plain
  `cmake --build --target all` will not build it — a suite run after source
  edits without rebuilding `miopen-tests` would exercise a stale binary.
  Standard CMake semantics; the harness builds the explicit target
  (`ci_ctest_integration.py`: `--target test_hiprtc_selfcontained`). NIT.
- `MIOPEN_USE_HIPRTC=OFF` would silently drop the test from the suite
  (coverage loss, not false pass). NIT.
- ctest wiring does not itself put the hiprtc DLL dir on PATH; the harness
  script prepends `CORE/bin`. Running the exe with a stripped PATH gives
  **exit 127** (DLL load failure) → ctest "Failed". Fail-closed. NIT.
- Harness verdict derivation (both `run_ci_matrix.py` and
  `ci_ctest_integration.py`): from **exit codes only** with per-cell expected
  values, CPATH popped, SHAs of source/binary/dll and tree git SHAs recorded.
  No stdout-grep verdicts. The ctest run log shows a genuine `Passed` for
  `^test_hiprtc_selfcontained$` and `ci_integration.json` ctest_run.exit=0;
  run time 0.16 s is consistent with a warm run (a manual timed run is 0.22 s
  even with a cold LOCALAPPDATA redirect, so this is a real compile, not a
  skipped one).
- `ci_integration.json` records `test_exe: null, test_exe_sha256: null` — the
  script hashes `BUILD/test_hiprtc_selfcontained.exe` but the binary lives in
  `BUILD/bin/`. Provenance is preserved via the matrix JSON (hash matches), so
  this is cosmetic. NIT.

## 8. Findings summary

| ID | Severity | False pass? | Finding |
|---|---|---|---|
| F1 | **MINOR** | **Yes, under attacker-controlled or wrong kernels dir** | No kernel-identity/content check: a `MIOpenBatchNormFwdTrainSpatial.cpp` replaced with a one-line trivial kernel yields exit 0 with a full "PASS: kernel compiled without host STL (3840-byte code object)". CI wiring pins the path to the source tree and the matrix records the tree SHA, which contains the exposure, but the test itself cannot detect a stale/foreign/neutered kernels dir. Recommend asserting a content marker (e.g. the file includes `batchnorm_functions.hpp` / defines the BN kernel / minimum size) before verdicts |
| F2 | **MINOR** | Unresolved direction; observed once | Transient window (single bash session) in which `--isolate=-nostdinc++`, `--isolate=-banana`, and `--isolate=` on the patched tree all returned **exit 0** (probe clean ⇒ STL apparently unreachable), while the same commands are deterministically **exit 4** in 12/12 subsequent runs including verbatim replays, with fresh-TMP and fresh-LOCALAPPDATA variants. Best explanation: a transient failure of comgr/clang MSVC autodetection (STL at `C:\BuildTools`), which would make the window's passes *truthful* (STL genuinely unreachable); the dangerous reading (STL reachable during the kernel compile but not the probe) is not excluded post-hoc because the probe is the only witness. The CI-wired configuration never passes `--isolate` (default `-nostdinc` was stable across 30+ runs all session). Recommend: CI must never use non-default `--isolate`; log the probe outcome line unconditionally for auditability |
| F3 | MINOR | Yes, vacuously | Duplicate `--mode` args are last-wins with no warning: `--mode=positive --mode=ordinary` silently runs the always-green ordinary control. Same class as the matrix's duplicate `--arch` cell (which fails closed). Recommend rejecting duplicate options |
| F4 | MINOR (coverage) | No | The STL-unreachable probe checks only `<type_traits>`, while the patch also gates `<utility>` (backstopped by the `#error` tripwires — verified E2b) and `<initializer_list>` (no tripwire, but unreachable from the tested kernel). The tested kernel exercises only the `miopen_type_traits.hpp` arm of the fix. Widening the kernel set or editing the include graph could silently open probe gaps. Recommend probing all four signature headers |
| F5 | NIT | No | 0-byte / NUL-prefixed kernel file yields SETUP(2), not FAIL(1). Both are non-zero so the gate blocks; semantically a corrupted tree is a test failure, not a usage error. Pairs with F1 (read_file accepts any content) |
| F6 | NIT | No | `ci_ctest_integration.py` records null exe hash (wrong path `BUILD/` vs `BUILD/bin/`); provenance recovered from matrix JSON |
| F7 | NIT | No | ctest registration relies on harness PATH for hiprtc.dll; missing DLL = exit 127 = ctest Failed (fail-closed) |
| F8 | NIT | No | Negative-mode PASS cannot distinguish the historic pristine failure from any other genuine missing-STL failure (E3a). Both trees are genuinely broken, and the paired positive control (exit 1) disambiguates in the A/B harness, so this does not weaken the claimed sensitivity evidence |

No BLOCKER or MAJOR findings. The two false-pass-capable vectors (F1, F3)
require an already-compromised or mis-wired invocation, not an environmental
trick; the environmental attack surface (CPATH, planted headers, partial STL,
forged signatures, truncated kernels, bad arches) fails closed in every tested
shape.

## 9. Strongest attack that failed

The **partial-STL leak family** was the strongest attempt at a semantic false
pass: make *some* host stdlib header reachable so the patched kernel compiles
through a real-STL arm while the `<type_traits>`-only probe still reports
"isolation verified". It failed twice over: a `<utility>` leak detonates the
patch's own `#error "inconsistent C++ standard library availability ..."`
tripwire (exit 1), and an `<initializer_list>` leak is unreachable from the
tested kernel's include graph. Combined with the token-identical option lists
of probe and kernel compile, no environment variable or `-I` trick can make
`<type_traits>` visible to the kernel but not the probe — the planted-header
(E1e) and CPATH (E2d) variants both correctly collapse to INCONCLUSIVE.

## 10. Conditions for unconditional PASS

1. Add a kernel-content marker check (closes F1's vacuous pass).
2. Commit to never passing non-default `--isolate` in CI wiring and document
   the F2 transient (or extend the probe to all four signature headers, which
   also closes F4 and would have flagged the F2 window's `utility`/`initializer_list`
   state).
3. Reject duplicate `--mode`/`--arch`/`--isolate` arguments (closes F3).

---

## Disposition log (primary agent, 2026-10-08)

Verdict requirement for Gate P5-08 is "zero unresolved false-PASS
findings". Disposition of the four MINORs:

- **F1 (kernel-identity), F3 (duplicate --mode last-wins), F4 (probe
  covers only <type_traits>) — TO BE HARDENED** in the test source
  (kernel-content marker, duplicate-argument rejection, probe extended to
  all four stdlib signature headers) after the P5-17 panel reviews
  complete (avoiding mutation of the tree under active review), followed
  by rebuild + full matrix + CTest re-run; the delta gets an independent
  re-check.
- **F2 (one-time transient under custom --isolate) — ACCEPTED WITH
  RATIONALE**: the CI wiring never passes `--isolate` (default
  `-nostdinc` stable across 30+ runs, 12/12 verbatim replays exit 4);
  the anomaly occurred only with operator-supplied non-default options
  and was not reproducible; the probe + option-identity design makes the
  dangerous reading unreachable in the CI configuration.

The CI-wired configuration (positive mode, default isolation,
CMake-supplied arch) had zero false-PASS vectors — every attack returned
exit 1/2/4, never 0.
