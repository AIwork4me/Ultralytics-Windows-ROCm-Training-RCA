# Gate P56 — Reviewer B (CI engineer): independent verification of the `hiprtc_selfcontained` regression test

- **Reviewer:** B (CI engineer), independent re-verification, no reliance on executor-run evidence.
- **Date:** 2026-10-08.
- **Objects:**
  - Test source (FINAL hardened): `patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`
    (signatures anchored to `fatal error: '<name>' file not found`; single-error rule via
    diagnostic-count AND clang footer count; mandatory STL-unreachable probe; `--keep-isolated`
    removed from code and usage).
  - Binary: `C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\ci-test\hiprtc_selfcontained.exe`
    — **rebuilt by me** from the FINAL source with `scripts\phase4\build_ci_test.py`
    (exit 0, idempotent) before any test run below.
  - Trees: unpatched `rocm-libraries-phase4-baseline` (HEAD `b68f8944300f`, `git status` clean);
    patched `rocm-libraries-phase4-canonical` (HEAD `4084759f`, 2 commits, clean).
  - Prior adversarial reports: `P49_adversarial_review.md`, `P49_adversarial_reverify.md`.
- **Environment:** Git Bash; `PATH` prepended with
  `C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin` (hiprtc0714.dll);
  `CPATH` unset except in the F2 attack; arch `gfx1151`; `--hip-flat` derived (7.1.4 →
  7001000000 ≥ 7·10⁹, affected HIP≥7 arm exercised — confirmed: no `< 7` note in any run).
- **Scratch:** all manipulated copies under `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\rB\`
  (logs in `rB\logs\`). Real trees verified clean (`git status --porcelain` empty) after every phase.

## VERDICT: **APPROVE WITH CHANGES**

The gate-relevant behavior of the FINAL hardened test is independently confirmed end to end:
the 6/6 expectation matrix passes on the real trees, both control-integrity cells hold
(negative×patched = 1, positive×unpatched = 1), the prior BLOCKER/MAJOR attack set
(F1, F1d, F2, F3, F4, V1 in both prepend and append forms) is fully defended (all exit 4),
the probe is mandatory and fires with evidence, and `--keep-isolated` is gone (exit 2).
One deviation from the review brief was observed and analyzed (B1: N2-class re-added include
→ negative mode exits 0 on a sabotaged patched copy); it is a genuine, not forged,
field-signature failure of a tree that again carries the defect — inherent to any
log-matching negative control, already acknowledged in round 2 (N2), and caught by the
CI-wired direction (positive mode exits 1 on the same sabotage — verified). It is a
documentation gap, not a test defect. Required changes are documentation/evidence-hygiene
class; none block the gate.

## 1. Binary provenance

- Recorded evidence binary SHA256 (`ci_matrix.json`): `3bb22cae907ad44c…f3a64c`.
- My rebuild from the FINAL source (same pinned script, exit 0):
  SHA256 `8f84b21a1ccc28be…e64b7fa` — differs, as expected for a non-reproducible PE build
  (embedded link timestamp). Identity is carried by the source path pinned in the build
  script; all results below were produced with my fresh rebuild, i.e. they verify the FINAL
  source, not just the executor's binary.
- (E4, NIT) Recommend the evidence json record the test SOURCE file SHA256 alongside the
  binary SHA, since the binary SHA cannot be reproduced across rebuilds.

## 2. Full matrix on REAL trees (brief item 1) — 6/6 PASS, controls 1/1

Common prelude (Git Bash):

```bash
export PATH="/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin:$PATH"
unset CPATH
EXE=/c/Users/rocm/Desktop/YOLO_AMD/phase4_build/ci-test/hiprtc_selfcontained.exe   # my rebuild
"$EXE" <kernels-dir> --mode=<M> --arch=gfx1151
```

| Cell (mode × tree) | Expected | Actual exit | Semantic verdict (stdout/stderr) |
|---|---|---|---|
| ordinary × unpatched | 0 | **0** | `PASS: ordinary hiprtc control (code object generated)` |
| ordinary × patched | 0 | **0** | same |
| negative × unpatched | 0 (expected-fail-with-signature = PASS) | **0** | log: `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` + `1 error generated` → `PASS: … as the sole error` |
| positive × patched | 0 | **0** | `PASS: kernel compiled without host STL (5792-byte code object)` |
| with-stl × unpatched | 0 | **0** | `PASS: kernel compiled with host STL (5792-byte code object)` |
| with-stl × patched | 0 | **0** | same |

## 3. Negative-control integrity on REAL trees (brief item 3) — HOLDS

| Cell | Expected | Actual exit | Reason printed |
|---|---|---|---|
| negative × **patched** | 1 | **1** | `FAIL: no-STL compile unexpectedly succeeded (self-containment regression?)` |
| positive × **unpatched** | 1 | **1** | `FAIL: positive compile did not produce a code object` |

Both controls are discriminating: the test verdicts flip exactly on the fix, not on
environment or chance.

## 4. Adversarial re-runs on scratch copies (brief item 2)

Scratch: hardlink copies of each kernels dir under `phase4_attack\rB\scen\<name>`; all edits
via `sed -i` / `mv` / `cp` (link-breaking). Real trees checked clean before and after.

| Attack (all `--mode=negative` unless noted) | Exit | Want | Assessment |
|---|---|---|---|
| **V1 residual, append form**: `#error 'type_traits' file not found` appended to `batchnorm_functions.hpp`, PATCHED copy | **4** | 4 | `INCONCLUSIVE … (signature=0, diagnostics=1, footer=1)` — diagnostic is `error:` (line 354:2), not `fatal error:`; the prefix anchor rejects the forgery. **Executor's fix claim confirmed.** |
| **V1 original N1 form**: same `#error` as line 1 (single line), PATCHED copy | **4** | 4 | `signature=0, diagnostics=1, footer=1` — pure single-`#error` forgery no longer passes. |
| **N2**: `#include <type_traits>` prepended to `batchnorm_functions.hpp`, PATCHED copy | **0** | brief said 4 or 1 | See B1 below — genuine (not forged) `fatal error: 'type_traits' file not found`, single error. |
| N2b: same include prepended to the kernel `.cpp` itself | **0** | — | same class (`MIOpenBatchNormFwdTrainSpatial.cpp:1:10: fatal error`). |
| N2c: same include appended to `batchnorm_functions.hpp` | **0** | — | same class. |
| **Gate-direction check on N2 sabotage**: positive mode on N2/N2c copies | **1** | 1 | `FAIL: positive compile did not produce a code object` — the CI-wired leg catches the re-added STL dependency. |
| **F1**: `miopen_type_traits.hpp` renamed `.bak`, unpatched copy | **4** | 4 | `'miopen_type_traits.hpp' file not found` → quoted-token anchor rejects. |
| **F1d**: same rename, PATCHED copy (round-1 BLOCKER) | **4** | 4 | defended. |
| **F2**: `CPATH=C:\BuildTools\VC\Tools\MSVC\14.44.35207\include`, unpatched copy | **4** | 4 | probe fired: `stl_probe.cu:2:2: error: STL_PROBE_REACHABLE` → `INCONCLUSIVE: host C++ stdlib still reachable under -nostdinc`. |
| **F3**: `#error boom` as line 1 of `batchnorm_functions.hpp`, unpatched copy | **4** | 4 | two diagnostics → single-error rule rejects. |
| **F4**: rogue file named `type_traits` (freestanding content) in kernels dir, unpatched copy, `--mode=positive` | **4** | 4 | probe fired (`STL_PROBE_REACHABLE`) — no bypass flag exists. |
| `--keep-isolated` (removed flag) | **2** | 2 | usage error; flag absent from usage string. |
| `--hip-flat=abc` | **2** | 2 | `SETUP ERROR: bad --hip-flat value` (F7 fix confirmed). |
| no args | **2** | 2 | usage. |

### B1 — the N2 exit-0 deviation, analyzed (MINOR)

The brief expected "4 or 1, NOT 0" for the re-added-include attack. Actual: exit 0, with the
log showing the **genuine** clang diagnostic `fatal error: 'type_traits' file not found` and
`1 error generated` — i.e., the sabotaged patched tree *genuinely depends on the host STL
again* and fails exactly as the field does. Assessment:

1. **Not a false verdict about the tree under test.** The negative mode's claim — "this
   kernel tree fails with the field signature under no-STL isolation" — is true of that
   tree. The one-line edit re-created the actual defect; the test correctly classifies the
   tree as carrying the defect. No log-matching negative control can distinguish an
   unpatched tree from a patched tree with the include re-added: both fail identically.
2. **The gate-relevant direction is not defeated.** The control cell "negative × patched
   must exit 1" is defined on the pristine patched tree, where it holds (section 3). The
   leg an upstream CI would actually wire — positive mode on the patched tree — exits 1
   (FAIL) on the sabotage: verified. An accidental re-introduction (bad merge) is therefore
   caught loudly by the wired leg.
3. **Precedent.** Round 2 (N2) reached the same conclusion ("inherent to any log-matching
   negative control and is semantically defensible; document it") and folded it into V1's
   required actions. The V1 forgery itself is now fixed (verified above); what remains is
   the *documentation* half of that action, which is **not present** in the FINAL artifacts
   (no mention in the test header comment or the design doc — checked by grep).

Counting-logic note: I additionally probed the forgery surface of the single-error rule.
A `#error` whose text embeds `fatal error: '…'` (e.g. `#error fatal error: 'type_traits'
file not found`) yields `diagnostics≥2` (both `error:` tokens counted) → exit 4; an echo-line
carried signature requires an `error:`-bearing diagnostic line and hence inflates the count
→ exit 4. Within the `diagnostics==1` envelope, the signature can only be matched by a line
containing `fatal error: 'type_traits' file not found` exactly once and `error:` exactly
once — i.e., a genuine clang fatal-error diagnostic line. I found no text-only route to a
forged PASS; the residual is confined to genuine-defect re-creation (B1).

## 5. CMake wiring proposal review (brief item 4)

Sound, upstream-maintainable choices:

- `BUILD_TESTING AND MIOPEN_USE_HIPRTC` gating: correct — test only builds where RTC is in
  play, compile-only (no GPU, no MIOpen runtime linkage). 
- **Negative control NOT wired into upstream CTest** — correct and important: after the fix
  merges, the upstream tree is "patched", on which negative mode must exit 1; wiring it
  would permanently fail upstream CI. Its home (PR-story/validation harness) is right.
- Keeping the wiring as a separate optional third commit, source commits clean — good
  upstream practice. Arch explicitly passed by CI (no implicit machine default in-tree).
- Positive-mode-only `add_test` matches the upstream convention stated in the doc.

Issues (all pre-upstream-PR fixes, none gate-blocking):

- **C1 (MINOR).** `--arch=$<IF:$<BOOL:${AMDGPU_TARGETS}>,<first-of>,gfx1030>` is not valid
  CMake: there is no `<first-of>` generator expression, and a list value inside `$<BOOL:…>`
  is comma/semicolon-fragile. Compute at configure time instead, e.g.
  `if(AMDGPU_TARGETS) list(GET AMDGPU_TARGETS 0 _arch) else() set(_arch gfx1030) endif()`.
  The doc flags the snippet as "to be adapted at wiring time", but it is the artifact a
  maintainer reads — it should be syntactically real before the PR.
- **C2 (MINOR).** `${MIOPEN_SOURCE_DIR}` — the auto variable from `project(MIOpen)` is
  `MIOpen_SOURCE_DIR`; depending on where the snippet lands, `${PROJECT_SOURCE_DIR}/src/kernels`
  or `${CMAKE_CURRENT_SOURCE_DIR}/../src/kernels` is the robust spelling.
- **C3 (NIT).** Default-arch inconsistency: the test defaults to `gfx1151` (validation
  machine), the CMake sketch falls back to `gfx1030`. Pick one convention and document that
  CI legs must pass `--arch` explicitly.
- **C4 (NIT).** `hiprtc::hiprtc` target name must be verified against the monorepo's
  exported hip targets at wiring time (doc already acknowledges).
- **C5 (NIT).** The hardcoded production define set (`MIOPEN_USE_FP32=1`, `MIO_BN_VARIANT=0`,
  …) mirrors today's `comgr.cpp`/BN runtime set; a comment tying it to `src/comgr.cpp`
  (or deriving from the same CMake vars) would prevent silent drift.

## 6. Evidence json assessment (brief item 5) — `evidence/phase4/hiprtc_ci/ci_matrix.json`

Present and correct: schema/gate/timestamp; test binary path+SHA256; hiprtc DLL path+SHA256
(`hiprtc0714.dll`); both tree SHAs (top-level and per-cell `tree_git`); per-cell mode, exit
code, stdout tail (2 kB) and stderr tail (12 kB, includes the full compiler log for the
negative cell and code-object sizes); per-cell + overall verdicts; `patch_id`; `arch`.

Gaps:

- **E1 (MINOR).** Per-run **options are not recorded**: the actually-used `--hip-flat`
  (derived 7001000000 — determines that the affected HIP≥7 arm ran) and `--isolate`
  (`-nostdinc`). The design doc's harness section promises "architecture, options, include
  paths" per run; the json records only `arch` globally. One-line addition in
  `run_ci_matrix.py` (pass `--hip-flat` explicitly from `hiprtcVersion` and echo both).
- **E2 (MINOR).** The two control-integrity cells (negative×patched, positive×unpatched)
  are not part of the recorded matrix — they are the cells that prove the controls
  discriminate. I verified them independently (both exit 1); add them to the harness so the
  discriminance evidence is first-party, not only in review reports.
- **E3 (NIT).** Logs are tails; the key diagnostic lines are present, but full logs on disk
  would strengthen audits.
- **E4 (NIT).** The recorded binary SHA is not reproducible across rebuilds (section 1);
  record the test source SHA as the stable identity.

## 7. Reviewer incident disclosure (resolved, no executor fault)

My first scratch-copy attempt used `cp -ral` (hardlinks) and an in-place `printf >>` append;
the append wrote through the shared inode and added the sabotage line to the REAL canonical
tree's `batchnorm_functions.hpp` (detected immediately via `git status`: 1 file, 1 insertion).
I restored it with `git checkout -- projects/miopen/src/kernels/batchnorm_functions.hpp`,
verified both real trees clean (`0` porcelain lines), then recreated ALL scenarios from
scratch using only link-breaking edits (`sed -i`, `mv`, `cp`) and re-ran the entire attack
battery on the clean copies. Every result reported in section 4 is from the clean re-run.
The real-tree matrix and integrity runs (sections 2–3) all executed before any scratch work
began and are unaffected. Lesson recorded: never in-place-edit hardlinked scratch copies of
trees under review.

## Findings summary

| ID | Severity | Finding |
|----|----------|---------|
| B1 | MINOR | N2-class genuine re-added `#include <type_traits>` on a patched copy → negative mode exit 0 (matrix-cell violation only under deliberate content sabotage that re-creates the real defect). Inherent to log-matching negative controls; the CI-wired positive leg catches it (exit 1, verified). **The round-2 requirement to document this residual was not carried out** — test header comment and design doc are silent. |
| C1 | MINOR | CMake sketch contains invalid generator expression (`<first-of>`); must be configure-time `list(GET)`. |
| C2 | MINOR | `${MIOPEN_SOURCE_DIR}` variable-name error in the wiring sketch (`MIOpen_SOURCE_DIR` / `PROJECT_SOURCE_DIR`). |
| D1 | MINOR | Design doc desynced from the FINAL test: isolation section and controls table still describe `-nostdinc++` (test now defaults to `-nostdinc`, with msvc-triple rationale only in the source comment); table's negative-mode wording under-specifies the `fatal error:` anchor. |
| E1 | MINOR | Evidence json omits per-run options (`--hip-flat` used, `--isolate`), which the design doc's harness section promises. |
| E2 | MINOR | Control-integrity cells (negative×patched=1, positive×unpatched=1) not recorded in the matrix evidence; verified here independently. |
| E3 | NIT | Matrix evidence stores log tails, not full logs. |
| E4 | NIT | Binary SHA non-reproducible across rebuilds; record test-source SHA alongside. |
| C3 | NIT | Default-arch inconsistency (test `gfx1151` vs sketch `gfx1030`). |
| C4 | NIT | `hiprtc::hiprtc` target to be confirmed against monorepo exports at wiring time. |
| C5 | NIT | Hardcoded BN define set can drift from `comgr.cpp`; add a cross-reference comment. |

No BLOCKER or MAJOR findings. All prior adversarial findings that were claimed fixed
(F1–F4, F7, F9 usage/echo, V1, V2 plural-footer) are confirmed fixed on independent re-run;
V3/V4/V5/V6 were round-2 NIT/MINOR residuals not required for this gate (probe-broken-vs-
isolated distinction, `--hip-flat` junk tolerance, ordinary-mode dir validation, 4-header
probe) and remain open as low-priority hardening.

## Required actions

1. **(B1, before gate close-out)** Document the residual in the FINAL artifacts: one
   sentence in the test's header comment (negative mode: "a tree in which the STL include
   has been re-introduced genuinely exhibits the field failure and will legitimately pass
   negative mode; the CI-wired positive leg is the control that catches it") and a matching
   note in `CI_REGRESSION_TEST_DESIGN.md`.
2. **(C1/C2, before any upstream PR)** Correct the CMake sketch: configure-time
   `list(GET AMDGPU_TARGETS 0 …)` arch selection; fix the source-dir variable.
3. **(E1/E2, evidence hygiene)** Extend `run_ci_matrix.py`: pass/record `--hip-flat` and
   `--isolate` per run; add the two integrity cells to the recorded matrix.
4. **(D1)** Sync the design doc's isolation description and controls table to the FINAL
   test (`-nostdinc` default + msvc-triple rationale; `fatal error:`-anchored signatures).
5. **(E4/C3, optional)** Record the test-source SHA; reconcile the default-arch values.

## Evidence: raw commands and exit codes (all with the PATH/CPATH prelude of section 2)

```text
# matrix (real trees)          exit
ordinary  U / P                 0 / 0
negative  U                     0   (PASS w/ field signature, sole error)
positive  P                     0   (5792-byte code object)
with-stl  U / P                 0 / 0
negative  P  (integrity)        1   (FAIL: unexpectedly succeeded)
positive  U  (integrity)        1   (FAIL: no code object)

# attacks (scratch copies under phase4_attack/rB/scen)
v1_append_patched   negative    4   (signature=0, diagnostics=1, footer=1)
v1_prepend_patched  negative    4   (signature=0, diagnostics=1, footer=1)  [pure N1]
n2_inc_prepend_hdr  negative    0   (genuine fatal error, 1 error generated)  -> B1
n2b_.._kernel       negative    0   (genuine fatal error at .cpp:1:10)        -> B1
n2c_inc_append_hdr  negative    0                                                 -> B1
n2_hdr / n2c        positive    1 / 1  (gate direction catches the re-added dep)
f1_unp_rename_tt    negative    4
f1d_pat_rename_tt   negative    4
f2_cpath_unp        negative    4   (probe: STL_PROBE_REACHABLE)
f3_boom_prepend_unp negative    4
f4_rogue_unp        positive    4   (probe: STL_PROBE_REACHABLE)
--keep-isolated                 2   (usage; flag removed)
--hip-flat=abc                  2
no args                         2
```

Logs retained: `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\rB\logs\` (matrix_*, atk_*).
Real trees left pristine (verified by `git status --porcelain` = empty on both, twice).
