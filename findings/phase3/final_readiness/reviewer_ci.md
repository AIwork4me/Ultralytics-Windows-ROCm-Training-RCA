# Reviewer C — Upstream CI and Portability Review (final readiness)

Scope: what must block submission FROM THIS MACHINE vs what UPSTREAM CI
(rocm-libraries PR CI / AMD Jenkins / TheRock) should enforce across
gfx94x / gfx110x / gfx120x and HIP/ROCm 10.x. Reviewed 2026-10-08.

Inputs reviewed (working tree, HEAD f553c49 == origin/main, verified):

- `patches/phase3/0001-miopen-hiprtc-selfcontained.patch` — SHA256
  re-verified `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20`
- `patches/phase3/0002-miopen-hiprtc-selfcontained.patch` — SHA256
  re-verified `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53f3cdd31f761532`
  (both match the P3-FINAL-R3 identity declared in
  `docs/phase3/CROSS_PLATFORM_VALIDATION.md`; round-trip claim stands)
- `docs/phase3/`: GATE70_LATEST_ROCM_LINE.md, PR_DRAFT.md,
  MAINTAINER_REPORT_DRAFT.md, CROSS_PLATFORM_VALIDATION.md,
  PHASE3_SUMMARY.md (+2026-10-08 addendum), FINAL_SUBMISSION_CHECKLIST.md,
  GATE79_DISTINCTION.md, linux/KTHVALUE_RUNTIME_CLOSURE.md
- `findings/phase3/phase3_conclusion.json` (`second_windows_version`,
  `latest_rocm_line_checked` read as instructed)
- `scripts/phase3/audit_rtc_std_dependencies.py`,
  `scripts/phase3/hiprtc_canary.py`
- `patches/phase3/proposed_ci_test/hiprtc_selfcontained.cpp`
- `evidence/phase3/raw/linux/kthvalue/comparison.json`,
  `evidence/phase3/raw/linux/rtc_kernels/{no_stl_canary,extended_canary}.json`

---

## 1. The cross-HIP-version risk (the reason CI legs exist): gate analysis

The patch's only cross-version surface is the reordering of the gates in
`miopen_type_traits.hpp` / `miopen_utility.hpp` (0001). Verified hunk by
hunk against the develop context lines:

| State | develop b68f8944 | patched | delta |
|---|---|---|---|
| HIP < 7, RTC (`MIOPEN_HIP_RUNTIME_COMPILE`) | legacy shim | same legacy shim | none — shim body lines untouched (both hunks touch only the two gate lines and the HIP>=7 else-arm; the shim body is outside every hunk) |
| HIP < 7, offline | real `<type_traits>`/`<utility>` | same (outer `#else`) | none |
| HIP >= 7, offline | real headers | same (outer `#else`) | none |
| `HIP_PACKAGE_VERSION_FLAT` undefined (evaluates 0) | shim arm (RTC) / real header (offline) | identical resolution | none — undefined-macro edge behaves the same in both orderings |
| HIP >= 7, RTC | real headers, hard | `__has_include` probe: real / freestanding / loud `#error` on partial STL | **the only changed arm — exactly the arm that fails on Windows wheels** |

Consequences for CI design:

- The pre-HIP7 arms are preserved byte-identically; the residual risk
  there is gate-ordering mistakes, which a cheap compile-only leg with
  `-DHIP_PACKAGE_VERSION_FLAT=<6.x value>` pins down (job J2 below). Not
  worth a separate toolchain matrix.
- HIP 10.x: GATE70 verified the identical outer gate is still present on
  develop (= the 10.x source line), so 10.x takes the new probe arm. The
  probe needs only C++17 `__has_include`, which every clang hiprtc of the
  7.x/10.x lines has. The right enforcement is one 10.x CI leg (J1/J6),
  not local work.
- `radix.hpp` note (0002): the `std::numeric_limits` → `__INT32_MAX__` /
  `__INT64_MAX__` change is value-identical (same integer constants) but
  applies to ALL compilations of radix.hpp, not only no-STL ones — this
  is the one change that can in principle alter a kernel that runs on
  full-ROCm Linux machines. It is exactly what the Linux kthvalue
  runtime A/B closed on gfx1151 (values+indices byte-identical,
  `evidence/phase3/raw/linux/kthvalue/comparison.json`: 3 cases,
  `regression: NONE`), and per-arch runtime kthvalue in CI (J6) is the
  correct ongoing enforcement. No local action remains.
- `tensor_view.hpp` probe nuance: `#if defined(X) && !__has_include(<h>)`
  is technically ill-formed-NDR when the right operand is skipped,
  pre-C++23 (C++23 made it well-defined). Universally accepted by
  clang/GCC/MSVC and the left operand is checked first, so the practical
  risk is nil. NIT only; no change requested.

## 2. Proposed upstream CI matrix

Principle: no-STL / partial-STL / HIP-gate coverage is compile-only and
arch-independent (pure C++ templates and preprocessor) — enforce it
everywhere cheaply with no GPU. The per-arch value of GPU legs is for
the runtime kernels whose sources changed (radix → kthvalue; BN spatial
→ the defect class itself), not for the freestanding headers themselves.

### Tier 1 — required PR checks, no GPU, minutes each (ctest-able)

| Job | What | Mode | Existing/proposed infra |
|---|---|---|---|
| J1 | `hiprtc_selfcontained` compile-only positive: compile one embedded RTC TU (e.g. `MIOpenBatchNormFwdTrainSpatial.cpp`, the defect's own kernel) through hiprtc with `-nostdinc`, `-DMIOPEN_HIP_RUNTIME_COMPILE`, `-DHIP_PACKAGE_VERSION_FLAT=7000000000` | expect success (freestanding arm); log must not contain `'type_traits' file not found` | the proposed test `patches/phase3/proposed_ci_test/hiprtc_selfcontained.cpp`, wired into `projects/miopen/test/CMakeLists.txt` behind `BUILD_TESTING` + hiprtc availability |
| J2 | Same TU with a 6.x `HIP_PACKAGE_VERSION_FLAT` define | expect success via the untouched legacy shim arm (pins the gate reorder) | same binary, second ctest invocation |
| J3 | Partial-STL negative control: `-nostdinc++` + include path exposing a `<type_traits>` but no `<utility>` (comgr's bundled set on this stack is exactly that state; a synthetic one-header stub dir also works) | expect the loud `#error "inconsistent C++ standard library availability"` — i.e. exit is a *compile* failure whose log matches the guard string, never a silent double-definition (the #7718 class) | same binary, third mode (needs the negative-control flag the proposal currently only describes) |
| J4 | kthvalue TU no-STL: compile `MIOpenKthvalue.cpp` via hiprtc `-nostdinc` (covers radix builtin-limits + freestanding initializer_list residuals; local precedent: extended-canary E3/E4 PASS) | expect success | same binary parameterized by TU name |
| J5 | Static ratchet: run `scripts/phase3/audit_rtc_std_dependencies.py` against `projects/miopen/src/kernels`; fail if any RTC closure gains a NEW unguarded std angle-include | prevents the next #3803-style regression from re-enterering | the audit script, upstreamed as a CI utility job |

The unpatched-tree negative control (develop fails J1 with the exact
field signature) needs no separate job: J1 lands in the same PR, so from
merge onward it is regression protection; the pre-patch failure is
already archived locally as the E1 record.

### Tier 2 — GPU runtime legs (the existing per-arch Jenkins legs a PR already triggers)

| Job | What | Arches | Infra hook |
|---|---|---|---|
| J6 | Kthvalue runtime with a FRESH kernel cache (`MIOPEN_CUSTOM_CACHE_DIR` empty per run, so `KthvalueFwd` is actually RTC-compiled): `MIOpenDriver kthvalue -D 100x500 -k 10 -V 1` (requires `MIOPEN_BUILD_DRIVER=ON`), and/or the existing kthvalue test entries (`test/kthvalue.cpp` → `test_kthvalue` perf test; `test_gtest` kthvalue suites) | gfx94x (MI300), gfx110x (RDNA3 dGPU), gfx120x (Strix); gfx1151 already closed locally | MIOpen's standard per-gfx test suites; the local harness `scripts/phase3/linux/kthvalue_runtime_harness.cpp` shows the byte-exact A/B discipline if CI wants it |
| J7 | BatchNorm spatial RTC smoke (the defect class): existing bnorm gtest/driver entries, fresh cache, on the same arches | same | existing suites; on full-ROCm Linux these exercise the real-STL probe arm (expected byte-identical to develop) |
| J7b (optional) | BFP16 kthvalue (`kthvaluebfp16` driver entry) — not runnable on gfx1151 scope here, native on gfx94x | gfx94x | existing driver |

### Tier 3 — version legs

- One HIP 10.x line leg and one latest-7.x leg for J1–J5 (J1 is already
  HIP-version-parameterized via the define; run it under the branch's
  real hiprtc of each line). Runtime tiers J6/J7 run on whatever lines
  the branch maintains — develop (10.x) plus the supported 7.x.
- HIP < 7: no dedicated toolchain leg requested; J2 is the cheap
  surrogate. Only if maintainers still ship a 6.x leg anyway.

### Tier 4 — correctly out of rocm-libraries CI scope (reference in the PR, do not gate)

- Windows no-STL end-to-end per arch (the true defect environment: wheel
  hiprtc, no MSVC): TheRock release-wheel CI, where TheRock#8292 already
  reproduces it. The PR should cite #8292 and state that this leg is the
  packaging-side validation point; it is not enforceable from
  rocm-libraries CI.
- ROCm 7.2.1 runtime: wheels delisted (only 7.13/7.14/10.1 remain;
  archive 403) — no CI leg exists or is practical. Source-verified on
  the `rocm-7.2.1` tag (identical outer gate; inner macro pre-rename,
  so a 7.2.1 backport would need trivial adaptation — one sentence in
  the PR, nothing more). The 7.x family is covered by the 7.14/latest-7.x
  legs.

## 3. Gap classification — every item, LOCAL BLOCKER vs UPSTREAM CI vs HUMAN STEP

No LOCAL BLOCKER was found. Full classification:

| # | Gap / finding | Class | Label |
|---|---|---|---|
| F1 | gfx94x / gfx110x / gfx120x runtime not locally validated | UPSTREAM CI (jobs J6/J7) — by design; a single contributor machine cannot own AMD's arch matrix | UPSTREAM_CI_FOLLOWUP |
| F2 | HIP/ROCm 10.x line not locally validated (source-state verified in GATE70: gate still present on develop) | UPSTREAM CI (J1–J5 on the 10.x leg; J6/J7) | UPSTREAM_CI_FOLLOWUP |
| F3 | ROCm 7.2.1 runtime untested (wheels delisted; source gate verified on the tag) | No local or CI action possible; PR note only (incl. one line that a 7.2.1 backport needs macro-name adaptation) | UPSTREAM_CI_FOLLOWUP (documentation note) |
| F4 | HIP < 7 arms: restructured gate ordering, byte-identical shim bodies (verified above) | UPSTREAM CI compile-only leg J2 pins it | UPSTREAM_CI_FOLLOWUP (low risk) |
| F5 | Proposed CI test defects: (a) no `-I<kernels-dir>` option — quoted includes (`"miopen_math.hpp"` etc.) will not resolve since the asserted source name carries no directory, so the test as written would fail even on a patched tree (the local canary that DID work, `scripts/phase3/hiprtc_canary.py`, always passes `--include-dir`); (b) wiring comment typo `target_link_libraries(hiprtc_selftrained ...)`; (c) the "negative-control mode" is described in the comment but not implemented; (d) in the rocm-libraries monorepo the kernels dir is `projects/miopen/src/kernels` — use MIOpen's project source dir, not `CMAKE_SOURCE_DIR` | Fix in the proposal before/while wiring with maintainers; does not affect the patch bytes or the validated trees | MAJOR (proposal artifact) + UPSTREAM_CI_FOLLOWUP |
| F6 | Stale handoff docs: `PR_DRAFT.md` "Remaining before merge: Linux HIP>=7 regression runs (author lacks a Linux ROCm GPU environment)" and `MAINTAINER_REPORT_DRAFT.md` "## Linux results — Not yet run … blocking for merge" contradict the completed 2026-10-08 Linux regression (PASS, bit-identical numerics, kthvalue runtime closed — CROSS_PLATFORM_VALIDATION.md, PHASE3_SUMMARY addendum, phase3_conclusion.json). Under-claims only (never over-claims), so not an integrity problem, but pasting as-is would misstate the current state and invite a needless "please run Linux" review round | Fix the two sections at submission time; five-minute text edit, already inside FINAL_SUBMISSION_CHECKLIST step 7 ("attach/refresh … as needed"); no machine time, no re-validation | MAJOR + HUMAN_SUBMISSION_STEP (mandatory pre-post edit; NOT a local blocker) |
| F7 | `FINAL_SUBMISSION_CHECKLIST.md` references `findings/phase3/final_readiness/PR_READINESS.json`, which did not exist at review time (this directory is being populated now with the reviewer files) | Ensure the final_readiness package (incl. PR_READINESS.json with the four false status fields) is created before handoff | NIT (packaging) |
| F8 | comgr-vs-hiprtc reachability nuance: on Linux, MIOpen's real RTC path (comgr `BuildHip`) exposes a PARTIAL-STL bundled set when host STL is hidden (`<type_traits>` but not `<utility>` on this stack) — the patched tree there fires the designed `#error` (E2), so the freestanding arm is reachable only through raw hiprtc (the Windows wheel path) | State in the PR/test docs so nobody "fixes" J3 as a bug; J1 must use hiprtc directly (it does) | MINOR (documentation) + UPSTREAM_CI_FOLLOWUP |
| F9 | BFP16 kthvalue and non-applicable solver shapes untested (out of gfx1151 scope; honestly scoped in KTHVALUE_RUNTIME_CLOSURE.md) | Optional gfx94x leg (J7b) | UPSTREAM_CI_FOLLOWUP (low) |
| F10 | Audit ratchet (J5) not yet part of any upstream job | Propose the script upstream with the PR | UPSTREAM_CI_FOLLOWUP |
| F11 | Patch identity: SHA256 of both patch files re-verified during this review; matches declared P3-FINAL-R3; pre-HIP7 shim bodies untouched | none — verification PASS | (informational) |
| F12 | DCO/author placeholders in both commits and in the three new MIT headers | Deferred by design to the human submitter (FINAL_SUBMISSION_CHECKLIST steps 1–6) | HUMAN_SUBMISSION_STEP |

Explicit statement per the review charter: F1/F2 (cross-arch,
cross-HIP-line coverage) are the load-bearing examples of work that
belongs to upstream CI, NOT to this machine. Requiring local gfx94x/
gfx110x/gfx120x/10.x validation before submission would be an improper
barrier; the patch's design (arch-independent C++ + preprocessor, with
the only hardware-relevant change value-identical and already A/B-closed
on gfx1151) makes the CI matrix above the proportionate enforcement.

## 4. Reviewer C verdict

The patch series is portable by construction where it claims to be
(byte-identical outside the failing arm), its cross-version surface is
pinned by cheap compile-only CI jobs, and every remaining gap maps to an
upstream CI job, a documentation edit inside the existing human
submission step, or a TheRock-scoped follow-up. Nothing on this machine
invalidates the validated patch bytes or requires re-validation before
submission.

REVIEWER C VERDICT: NO LOCAL BLOCKER
