# Gate P56 — Reviewer C (regression attacker): cross-platform / artifact-regression attack on the canonical reconstruction

- **Reviewer:** C (regression attacker). Independent; verify-by-direct-observation only.
- **Date:** 2026-10-08.
- **Objects:**
  - Canonical worktree `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical` (HEAD
    `4084759f3804748b7935d882db2d0445a3e0c380`, 2 commits over `b68f8944300f`, `git status` clean).
  - Baseline worktree `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-baseline`
    (pristine `b68f8944300f`, clean).
  - Phase-4 evidence `evidence\phase4\{windows_runtime\runtime_binding.json,
    windows_runtime\nostl_validation.json, windows_runtime\yolo_train.json,
    hiprtc_ci\ci_matrix.json}`; Phase-3 comparison `evidence\phase3\raw\regression\*.json`,
    `docs\phase3\CROSS_PLATFORM_VALIDATION.md`.
- **Scratch:** everything manipulated lives under `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\rC\`
  (stub include dirs, run logs, rebuilt binaries). The real trees were only ever read; both verified
  `git status --porcelain` empty after every phase. CI test reruns pointed at the real kernel
  directories (read-only by design of the test).

## VERDICT: **NO REGRESSION FOUND**

Every attack angle was executed by direct observation. The canonical reconstruction introduces no
regression on Windows/Linux/HIPRTC that I could find: the 8-file diff contains only intended
edits (no reformat / line-ending / whitespace drift), the HIP<7 arms are byte-identical, all four
machine states (STL-present / no-STL / both partial-STL directions) behave identically to baseline
or fail loudly by design, the CI matrix reproduces 6/6 from the *current* artifacts, the runtime
evidence claims all check out against raw text, and no run modified anything outside its declared
temp dirs. Three MINOR provenance-hygiene findings (C1–C3) and three NITs (C4–C6) are listed;
none is a functional regression, none blocking.

---

## Attack 1 — Byte-equivalence of the 8 changed files

`git diff b68f894..HEAD` touches exactly 8 files (3 added, 5 modified, +384/−5):

| File | Delta | Intent check |
|---|---|---|
| `src/CMakeLists.txt` | +3 | registers the 3 new freestanding headers in the header list — intended |
| `kernels/miopen_freestanding_initializer_list.hpp` | +64 (new) | intended |
| `kernels/miopen_freestanding_type_traits.hpp` | +216 (new) | intended |
| `kernels/miopen_freestanding_utility.hpp` | +56 (new) | intended |
| `kernels/miopen_type_traits.hpp` | +15/−2 | guard reorder + `__has_include` selection + partial-STL `#error` — intended |
| `kernels/miopen_utility.hpp` | +14/−1 | same pattern — intended |
| `kernels/radix.hpp` | +9/−2 | RTC-only include switch (`miopen_cstdint.hpp` vs `<limits>`) + `std::numeric_limits::<int32/int64>::max()` → `__INT32_MAX__`/`__INT64_MAX__` — intended; values identical (2147483647 / 9223372036854775807), compile-time constants, no numeric change |
| `kernels/tensor_view.hpp` | +7 | `__has_include(<initializer_list>)` fallback — intended |

Checks performed:

- `git diff --check b68f894..HEAD` → exit 0: no trailing whitespace, no conflict markers introduced.
- Line endings: every blob in **both** trees is 100% CRLF (CR-line count == total line count for
  all 8 files, e.g. `miopen_type_traits.hpp` 152/152 → 165/165); the 3 new files are also 100%
  CRLF — consistent with the repo's existing convention, no mixed endings, no LF drift.
- Full hunk review (all hunks reproduced in scratch logs `rC\*.txt`): every changed line belongs
  to the intended edits; no untouched region was reformatted. The only cosmetic touches are blank
  lines/comment annotations *inside* the intended hunks (e.g. `#include <type_traits> // std::remove_reference…`).
- `radix.hpp` keeps `std::is_same` in `encode()` but never included `<type_traits>` in baseline
  either (dependency on the including TU is pre-existing); `<limits>` is no longer reachable in
  RTC mode and nothing in the RTC path uses it anymore (grep: only the two replaced
  `std::numeric_limits` uses existed).

**Result: PASS** — byte-level delta is exactly the intended probe/freestanding edits.

## Attack 2 — HIP<7 arm preservation

Extracted the `namespace std { … } // namespace std` blocks (the HIP<7 RTC arms) from
`miopen_type_traits.hpp` and `miopen_utility.hpp` in both trees (`git show` blobs, awk-extracted,
`cmp`):

- `miopen_type_traits.hpp` HIP<7 arm: **byte-identical**, 114 lines, md5 `3c672c05aacf289cb1fc5140306a5346`.
- `miopen_utility.hpp` HIP<7 arm: **byte-identical**, 15 lines, md5 `bf26893bebbd94e9fa04732daaa4c8e9`.

Preprocessing-state equivalence of the guard reorder (`#if HIP_PACKAGE_VERSION_FLAT < 7G` moved
inside `#ifdef MIOPEN_HIP_RUNTIME_COMPILE`), enumerated over the 4 states:

| State | Baseline b68f894 | Canonical 4084759 |
|---|---|---|
| RTC + HIP<7 | inline `namespace std` (byte-identical body) | same |
| RTC + HIP≥7 | `#include <type_traits>` | NEW: `__has_include` select (real → freestanding → `#error` on partial) |
| non-RTC + HIP<7 | `#include <type_traits>` | same |
| non-RTC + HIP≥7 | `#include <type_traits>` | same |

(The only semantic delta is the RTC+HIP≥7 row — the intended change. Undefined
`HIP_PACKAGE_VERSION_FLAT` also resolves identically in both trees: it reaches `<type_traits>`
either way.)

**Result: PASS.**

## Attack 3 — Machine-state coupling (STL-present / no-STL / partial-STL)

*State analysis (no numerics risk anywhere):* all patch changes are preprocessor include
selection + compile-time constants (`__INT32_MAX__` etc.). The freestanding headers define only
compile-time machinery (`remove_reference`/`remove_cv`/`is_pointer`/`forward`/`move`/
`initializer_list`). There is no machine state in which the patched tree produces *different
numerics* — only different include resolution, and it prefers the real STL whenever reachable,
so patched ⊇ develop:

| Host state | develop/baseline | patched (canonical) |
|---|---|---|
| (a) full STL present | real STL | real STL (**identical** — verified: with-stl cells produce byte-class-identical 5792-byte code objects on both trees) |
| (b) no STL | compile FAIL `'type_traits' file not found` (field signature, reproduced in negative cell) | compiles via freestanding arm (5792-byte code object) |
| (c) partial: only `<utility>` reachable | confusing missing-include failure | **loud `#error` guard** (verified below) |
| (c) partial: only `<type_traits>` reachable | confusing failure | **loud `#error` guard** (verified below) |

No state exists where develop works and patched breaks, and none where patched silently changes
behavior.

*Live tests (all logs under `rC\`):*

1. **Exact config from the brief:** patched tree + `--isolate=-nostdinc++` + `CPATH=C:\BuildTools\VC\Tools\MSVC\14.44.35207\include` + `--mode=positive` →
   **exit 4 INCONCLUSIVE**: the test's mandatory STL-unreachable probe fired first
   (`error: STL_PROBE_REACHABLE`), refusing to issue an isolated-mode verdict. This is correct
   and important: CPATH leaks through comgr into the RTC compile even under `-nostdinc++`, and
   the full MSVC dir makes the STL *fully* reachable (not partial), so this exact config can never
   reach the patch's guard — the test detects the compromised isolation instead of passing
   through it.
2. **True partial, only `<utility>` reachable** (default `-nostdinc` isolation — required on
   msvc-triple clang per the test's own docs — + `CPATH` → scratch dir containing only a `utility`
   stub): **exit 1 FAIL with the guard as the FIRST diagnostic**:
   `miopen_type_traits.hpp:155: error: "inconsistent C++ standard library availability: <type_traits> is not reachable but <utility> is; provide a complete standard library (or none)"`.
   Loud, actionable, exactly as designed. (See C5 for a comgr diagnostic-rendering oddity in this log.)
3. **True partial, only `<type_traits>` reachable** (`-nostdinc` + CPATH → `type_traits`-only
   stub): CI test → exit 4 INCONCLUSIVE via the probe (safe refusal; the probe only checks
   `<type_traits>`). The utility-side guard was therefore demonstrated by direct compile of
   `miopen_utility.hpp` with the production RTC define set (wheel clang, `-nostdinc`):
   `miopen_utility.hpp:59: error: "inconsistent C++ standard library availability: <utility> is not reachable but <type_traits> is (a partial freestanding override on the include path?); provide a complete standard library (or none)"`.
   **Both guard directions fire loudly.**
4. **Negative control under partial STL** (baseline tree, only-`<utility` stub CPATH):
   exit 0 PASS with exactly 1 diagnostic (`fatal error: 'type_traits' file not found`) — the
   exact-signature + single-error rule is not destabilized by the partial environment.

**Result: PASS** — (a) and (b) verified earlier via the matrix; (c) verified in both directions
with the guard firing; per the brief, FAIL(1)/INCONCLUSIVE(4) both observed and both constitute
acceptable evidence the guard fires.

## Attack 4 — Phase-4 runtime evidence vs Phase-3

- **BN numerics, same tolerance class: YES.** Phase-4 `max_abs_vs_cpu = 6.845486382189847e-07`
  (BN2d train 8×16×64×64, canonical DLL, GPU fp32 vs CPU fp64 — script verified to compute exactly
  that). Phase-3 same shape `bn2d_minimal_8x16x64x64: max_abs=7.153e-07`; phase-3 across-shape
  max was `9.537e-07` (= 2⁻²⁰, `9.5367431640625e-07` exactly, in `g65_66_results.json`) — the
  classic single-ulp fp32 reduction class. 6.8e-7 and 7.2e-7 on the same shape across independent
  runs/seeds are the same class; no drift, no regression.
- **no-STL validation proves what it claims.** `scripts\phase4\nostl_validation.py` reviewed
  line-by-line: refuses to start unless canonical DLL hash == pinned `b32d6310…` and wheel DLL ==
  pristine `74b4ee03…`; renames `C:\BuildTools\VC\Tools\MSVC\14.44.35207\include` away and
  `assert not MSVC_INC.exists()`; runs the workload under the redirected profile (below); the
  workload itself reports, in-process via `GetModuleHandleW/GetModuleFileNameW`, the loaded
  `MIOpen.dll` path + SHA == canonical; restore path hash-verifies the wheel
  (`wheel_restored_ok: true`, matches `74b4ee03…`). Evidence JSON carries every step
  (`msvc_include_renamed: true`, `fresh_profile: …phase4_iso_nostl_c27baac2`,
  `exit_code: 0`, y/grad/running-stats finite, `overall: PASS`). Note (C6): this run proves
  finiteness + provenance + no-STL-reachability, not max_abs numerics — numerics are covered
  separately under the STL-present BN run; the two together close the loop.
- **YOLO train evidence.** Both runs: `exit_code: 0`, `TRAIN_DONE` in stdout (also verified in
  the raw `yolo_amp_default.txt` / `yolo_amp_false.txt` with ANSI escapes stripped by grep),
  `weights/best.pt` exists, in-process provenance SHA == canonical `b32d6310…` on both.
  Default run: `amp=True` in the resolved config dump and `AMP: checks passed` present in raw
  text (ANSI `\u001b[34m\u001b[1mAMP: \u001b[0mchecks passed`) — genuine AMP;
  `amp_checks_passed: true`, `amp_default_genuine_amp: true`. amp=False run: `amp=False`,
  no AMP-checks line, `amp_checks_passed: false` — consistent. Wheel restored and hash-verified.
- **Pre-existing stderr noise is NOT a regression:** the `MIOpen: Error [EvaluateInvokers] …
  Invalid elapsed time` lines in the phase-4 YOLO stderr also appear verbatim in the phase-3
  evidence (`evidence\phase3\raw\yolo\g78_v3_yolo_default.json` contains them too) — machine /
  wheel-behavior constant across phases.

**Result: PASS.**

## Attack 5 — CI test binary side effects

Source review of `patches\phase4\ci_test_proposal\hiprtc_selfcontained.cpp` (480 lines, whole
file read): the test opens exactly one file read-only (`std::ifstream` on the kernel source),
compiles in memory (`hiprtcCreateProgram` from a string, `hiprtcGetCode` into a
`std::vector<char>`), and writes only to stdout/stderr. There is no filesystem write anywhere in
the test. The `%TEMP%\comgr-*` compile dirs are hiprtc/comgr internals (created and cleaned by
comgr; today's runs left zero leftovers — the six `comgr-108888-*` dirs still in Temp date from
Oct 7, an earlier crashed run, not from the CI test). After running the test repeatedly against
both real trees, `git status --porcelain` was empty on both. `run_ci_matrix.py` writes only its
evidence JSON.

**Result: PASS** — no writes outside hiprtc-managed temp compile dirs; trees untouched.

## Attack 6 — Kernel-cache semantics (stale-cache serving)

- **P52C no-STL run could not have been served by a stale cache.** Script + evidence agree:
  `USERPROFILE`, `LOCALAPPDATA`, `TEMP`, `TMP` all redirected to the fresh per-run dir
  `C:\Users\rocm\AppData\Local\Temp\phase4_iso_nostl_c27baac2` (so the default `.miopen` user
  cache/db and comgr cache locations resolve into an empty tree), and `MIOPEN_USER_CACHE_PATH`,
  `MIOPEN_USER_DB_PATH`, `AMD_COMGR_CACHE` were scrubbed from the environment. Consistent
  corroborating detail: this run's stderr contains none of the `ParseAndLoadDb`/perf-db noise the
  ambient-profile runs show — there was no user db to parse.
- **P52E YOLO runs** each built a fresh UUID profile (`phase4_yolo_<tag>_<uuid>` with the same
  redirections + scrubs) per run, so training exercised real RTC compiles against the swapped-in
  canonical DLL.
- Note (C6): the P51 + P52(A-D) cells (`binding_probe`, `gpu_control`, `batchnorm_minimal` in
  `runtime_binding.json`) run under the **ambient** profile (no redirect in
  `prove_dll_binding.py`). That is fine for their purpose (binding proof and numerics are
  cache-independent), but "fresh profile proves RTC recompiles" is carried by P52C/P52E, not by
  A-D.

**Result: PASS.**

## CI matrix reproduction (regression re-verification of current artifacts)

Reran the full 6-cell matrix three ways — with the on-disk binary (`8f84b21a…`, Reviewer B's
11:53 rebuild) and with a fresh build I made from the **current** (12:01) source into scratch:

```
mode=ordinary  unpatched exit=0 code_size=3824 PASS     mode=ordinary  patched exit=0 code_size=3824 PASS
mode=negative  unpatched exit=0 (signature, 1 error)    mode=positive  patched exit=0 code_size=5792 PASS
mode=with-stl  unpatched exit=0 code_size=5792 PASS     mode=with-stl  patched exit=0 code_size=5792 PASS
```

Identical exit codes, code sizes and verdict lines to `ci_matrix.json` in every cell, from both
binaries. hiprtc DLL SHA re-verified == evidence (`c6159dd1…`).

---

## Findings

| ID | Severity | Finding |
|---|---|---|
| C1 | MINOR (provenance, non-blocking) | `ci_matrix.json` records `test_binary_sha256 = 3bb22cae…`, but the binary at that path is now `8f84b21a…` (Reviewer B's 11:53 rebuild — documented in `P56_reviewer_B_ci.md` §1/E4). Root cause proven: I built the same source twice and got `dbd7ef2d…` / `200f69f4…` — the PE build is non-deterministic, so the recorded binary SHA is structurally unreproducible. Functional equivalence verified (6/6 cells identical from the current binary). |
| C2 | MINOR (provenance, non-blocking) | The CI test **source** was edited at 12:01:20 — *after* the evidence run (11:39) and after B's rebuild (11:53). I observed the delta live during this review: the usage comment line `[--hip-flat=N] [--keep-isolated]` became `[--hip-flat=N] [--isolate=OPT]` (applying B's finding). All phase-4 RCA content is untracked in git (last commit is phase-3), so the edit is undocumented except by mtime. Mitigated: I rebuilt from the current source (sha256 `06f9899993d5dad8e2c50c65c7195fd52df7406d89cd2368aadec4d864da0faf`) and reproduced 6/6 cells. |
| C3 | MINOR (provenance, non-blocking) | `scripts\phase4\yolo_train_validation.py` on disk (mtime 11:50:50 — *mid-run*; the YOLO evidence run started 11:44:22 and wrote its JSON at 11:51:10) does not emit several fields that `yolo_train.json` contains (`amp_checks_passed`, `amp_reported`, `val_completed`, `weights_best_exists`, per-run `ok`, `amp_default_genuine_amp`): the evidence was produced by a richer script version than the one now on disk. The underlying claims are independently supported by the raw `yolo_amp_*.txt` files (verified directly), so this is script/evidence divergence, not a substance problem. |
| C4 | NIT | `nostl_validation.json`'s `env_scrubbed` list omits `MIOPEN_FIND_MODE` and `MIOPEN_USER_DB_PATH`, both of which the script does scrub — evidence listing lags code. |
| C5 | NIT (observation) | In partial-STL failure states comgr emits a second, synthesized diagnostic (`batchnorm_functions.hpp:354:2: error: 'type_traits' file not found` echoing an `#error` directive whose text exists nowhere in any source; line 354 is one past EOF). Harmless: the state is already failing loudly with the guard message as the first diagnostic, and the CI test's negative mode would downgrade such multi-diagnostic failures to INCONCLUSIVE (the safe direction), which I confirmed stays exact (1 diagnostic) on the baseline tree. |
| C6 | NIT | Gate labeling: P51+P52(A-D) cells run under the ambient profile (no USERPROFILE redirect); the fresh-profile RTC-recompile proof rests on P52C (no-STL) and P52E (YOLO), and P52C proves finiteness+provenance rather than max_abs numerics. Worth one clarifying sentence in the phase-4 doc so nobody over-reads A-D. |

## REQUIRED ACTIONS

Non-blocking provenance hygiene (none affect the verdict):

1. **Commit all phase-4 artifacts** (docs/evidence/findings/patches/scripts) to the RCA repo —
   today's post-evidence edits (11:50:50 script, 12:01:20 CI source) are invisible to version
   control, which is what made C1–C3 necessary to reconstruct from mtimes.
2. **Record the CI test source hash** (sha256 `06f98999…` for the current file) in
   `ci_matrix.json` next to the binary SHA, and note in the evidence that the binary was rebuilt
   at 11:53 by Reviewer B (or pin a reproducible build); the binary SHA alone can never be
   re-verified.
3. **Restore/commit the exact `yolo_train_validation.py` version that produced
   `yolo_train.json`** (the on-disk version is a mid-run simplification missing the
   amp/val/ok field logic whose outputs the evidence contains).

## Evidence index (scratch, kept)

- `phase4_attack\rC\` — HIP<7 arm extractions (`*_hip7_*.txt`, md5-verified), matrix rerun logs
  (`rC_out/err.txt`), partial-STL runs (`rC_c*_*.txt`, `rC_c2b_*.txt`, `rC_neg_*.txt`),
  utility-guard demo (`util_tu.cpp` + output), stub dirs (`stub_only_type_traits/`,
  `stub_only_utility/`), rebuild script + binaries (`ci-rebuild\`, `rebuild1.exe` passes 6/6).
