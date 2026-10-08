# Reviewer D — Upstream Submission Readiness Review

Date: 2026-10-08. Repo state reviewed: `main` @ `f553c49e4168c1f8c1...` ==
`origin/main` (verified: `git rev-parse HEAD origin/main` both
`f553c49e4168c1f208a3e01202a713a3ddcfb09a`; tracked working tree clean —
one untracked evidence file, see N-6). Question answered: if this exact
patch and evidence were submitted to ROCm/rocm-libraries TODAY.

## 1. Commit decomposition — PASS (2 nits)

Two logical commits as format-patch artifacts (404 + 156 = 560 lines, 8
unique files — verified by wc and by applying both to a pristine tree):

- `0001` "MIOpen: keep RTC type traits self-contained when no host STL is
  reachable" — the defect fix: availability-probed `<type_traits>` /
  `<utility>` in the HIP>=7 RTC arms, two new freestanding headers,
  partial-STL `#error` guards, CMake embed-list registration. Subject
  accurate and conventional; body states root cause (#3803 / #3147 shim
  disabling), observed impact (MIOpen#3956, TheRock#8292), design
  (prefer real headers via `__has_include`; freestanding only where
  nothing resolves; loud rejection of partial STL), and what is left
  unchanged (HIP<7 arms). Good upstream commit-message quality.
- `0002` "MIOpen: make remaining RTC kernel std includes self-contained"
  — residual coverage from the 104-entry audit: radix.hpp builtin limits
  (`__INT32_MAX__`/`__INT64_MAX__` + `miopen_cstdint` routing) and
  tensor_view.hpp `initializer_list` probe + clang-lowered freestanding
  fallback. Clean scope separation from 0001.

Hunk minimality: no EOL churn, no CRLF, no whole-file rewrites, no
trailing whitespace in added lines (space-prefixed lines are standard
unified-diff blank context). Nits: (N-1) cosmetic blank-line additions
around the unchanged `#include <type_traits>`/`<utility>` in the
non-RTC arms of 0001; (N-2) `#define MIOPEN_FREESTANDING_TRAITS_ACTIVE`
is defined and never referenced (dead marker macro). Neither warrants
mutating the validated patch.

## 2. Test strategy — PASS (stronger than typical upstream PRs)

- Windows live single-variable A/B with MSVC include tree renamed away:
  wheel DLL fails with the exact field signature
  (`miopen_type_traits.hpp:151 'type_traits' file not found`, exit 1) →
  patched DLL passes (exit 0), re-proven on the final V3 build; per-run
  `GetModuleFileNameW` + SHA256 provenance of the loaded DLL.
- Windows matrices: BN (minimal/#3956/yolo-like/BN1d-3D/BN2d/BN3d,
  train+eval) numerics <= 9.5e-7 vs CPU; 11-op non-BN RTC matrix in both
  STL states; YOLO26n coco8 1-epoch train in both amp modes.
- Linux independent PASS→PASS on real gfx1151 (separate validator
  branch/machine): exact SOURCE_SHA + exact patch bytes (Git-blob SHA
  verification pre/post merge), source-built unpatched/patched bound via
  LD_PRELOAD + dladdr, fresh caches, BN 8/8, numerics BIT-IDENTICAL
  (max_abs 0.0), non-BN RTC 11/11, YOLO predict+train, no-STL and
  partial-STL canaries (partial-STL reproduced the Windows failure class
  on the unpatched tree; patched tree fires its `#error` guard cleanly),
  canary facility set GPU-executed through the real RTC path.
- Kthvalue runtime closure (Gates F07–F15): `miopenKthvalueForward` →
  solver `KthvalueFwd` → `MIOpenKthvalue.cpp` RTC-compiled from fresh
  cache and launched on BOTH source builds (FP32 x2, FP16 x1); values
  and indices exact vs CPU and byte-identical A/B; adversarial
  falsification review PASS. This is the right closure for the 0002
  radix risk (MIOpenKthvalue.cpp is the sole runtime consumer of the
  changed `encode`/Radix machinery).
- Proposed CI test (`patches/phase3/proposed_ci_test/hiprtc_selfcontained.cpp`):
  compile-only via hipRTC with `-nostdinc` and the runtime-compile
  define, mirroring comgr's option set; no GPU required;
  negative-control capable. Sensible upstream ask.

Independent re-verification performed by this review (not just document
trust): both patches apply cleanly (`git apply --check` then apply) to a
pristine `b68f8944` checkout (`/home/amd/Desktop/YOLO_AMD/rocm-libraries-linux-baseline`),
and ALL 8 resulting files are BYTE-IDENTICAL to the validated patched
tree (`rocm-libraries-linux-patched`, diffstat 5 files, 48+/5-, plus 3
new headers). The "round-trip validated, 8 files byte-identical" claim
is reproduced. (`git am` commit creation could not complete in the local
evidence clone because that clone has a damaged/shallow object store —
`git fsck` shows missing blobs — an environmental artifact of the
validator's network-adverse cloning, not a patch defect; `git apply`
and content equivalence fully cover the substantive claim.)

## 3. DCO placeholders — CONFIRMED (HUMAN_SUBMISSION_STEP)

Both patches carry `From:` / `Signed-off-by:` =
`<AUTHOR NAME> <author@example.com>` with a trailing
`# DCO: fill in before submission` reminder. Rationale is documented and
sound: filling identity now would change the validated patch identity;
`docs/phase3/FINAL_SUBMISSION_CHECKLIST.md` EXISTS (the plan's
pre-submission requirement is met) and explicitly defers author/DCO fill
to the human submitter (steps 1–5), forbidding agent submission. The
reminder comment must be stripped when the real sign-off is filled — the
checklist's regenerate-and-reverify flow (steps 3–5) covers this.

## 4. Copyright headers — contributor placeholder (HUMAN_SUBMISSION_STEP)

New files carry `Copyright (c) 2026 [contributor name and notice to be
set by the submitter]` over MIT license text matching the existing
MIOpen kernel-header style (the touched files use the same MIT block).
This is a deliberate post-review change from V2's "Advanced Micro
Devices, Inc." attribution (V2 is marked SUPERSEDED in
`patches/phase3/README.md`); checklist item 6 defers to maintainer
preference (AMD line if requested). Acceptable for upstream as a
fill-at-submission placeholder; license type (MIT) already matches the
component.

## 5. PR draft quality — PASS with one staleness issue (M-1)

`docs/phase3/PR_DRAFT.md` claim wording is conservative and
evidence-matched; the Risk section honestly discloses probe
machine-state dependence, kernel-cache provenance differences, and the
`__has_include` availability assumption. No overclaim found. Upstream
references spot-verified against the live trackers today:
- MIOpen#3956 — exists, OPEN, no official reply; exact signature
  (type_traits not found / HIPRTC_ERROR_COMPILATION / Windows /
  MIOpenBatchNormFwdTrainSpatial) — matches how it is cited.
- rocm-libraries#7718 — exists (closed); `std::forward` REDEFINITION when
  freestanding and real STL coexist — the patch's `#error` guards and
  TU-global probe are correctly motivated by it.
- TheRock#8292 — exists (closed, no visible fix); AMD Windows release CI
  `miopenStatusUnknownError` — "also seen in AMD's own Windows release
  CI" is a fair characterization.
- rocm-libraries PR #8247 — exists, MERGED 2026-07-11 (rocRAND
  `__HIPCC_RTC__` guard) — accurate precedent (N-4: the PR_DRAFT label
  "rocRAND PR #8247" is imprecise; it lives in the rocm-libraries
  monorepo, where a bare `#8247` auto-links correctly — fine when
  submitted there, slightly 404-ish as prose).
- rocm-libraries#2169 / TheRock#842 / PR#1288 — correctly characterized
  everywhere as a DIFFERENT compile-stage defect (gfx1151 DPP inline
  asm); no conflation with this patch's failure class.
- #3803 / #3147 — used in commit message and PR summary as the
  shim-disabling history; consistent with the RCA record.

(M-1) MAJOR, submission-package: PR_DRAFT.md ("Remaining before merge:
Linux HIP>=7 regression runs (author lacks a Linux ROCm GPU
environment...)") and MAINTAINER_REPORT_DRAFT.md ("Not yet run",
"pending (blocking for merge)") are pre-Linux-leg (Gate 82) and were not
refreshed after the 2026-10-08 Linux PASS. Direction of error is
UNDER-claiming (safe), but submitting them verbatim would misstate the
validation performed and omit the strongest evidence (bit-identical
Linux numerics, kthvalue runtime closure). The final claim set is
already correctly stated in FINAL_SUBMISSION_CHECKLIST item 8 — the
human submitter must refresh these two docs in the same mandatory pass
that fills DCO identity (HUMAN_SUBMISSION_STEP; do NOT let this leak
into any temptation to touch the patch bytes).

## 6. Claim wording across final docs — PASS

Grepped README.md, docs/, findings/ for MERGED UPSTREAM / OFFICIALLY
FIXED / PR ACCEPTED / accepted upstream: no prohibited claim anywhere.
The only "accepted upstream" phrasing refers to rocRAND's #8247
precedent (a fact about OTHER work). Explicit disclaimers present in all
final-state docs: README ("No upstream fix has landed and none is
claimed"; "UPSTREAM PR NOT CREATED"), PHASE3_SUMMARY (dated addendum;
"Still NOT claimed: MERGED UPSTREAM / OFFICIALLY FIXED / PR ACCEPTED"),
phase3_conclusion.json / linux_conclusion.json / final_gate.md
(pr/issue/comment all false). Windows kthvalue: NO manufactured
coverage — CROSS_PLATFORM_VALIDATION.md row reads exactly "NOT TESTED
(runtime; radix compile+value-equivalence covered)" / "NOT TESTED
(runtime; see note 4)" with note 4 stating "Windows never executed a
kthvalue at runtime ... no Windows runtime kthvalue is claimed";
README/conclusion kthvalue mentions are Linux-scoped;
linux_conclusion.json records Windows coverage as compile-level only.
README's "proven FIXED by the source change alone" is explicitly the
local live A/B, next to the no-upstream-fix disclaimer — acceptable.

## 7. Cross-platform evidence — PASS

`docs/phase3/CROSS_PLATFORM_VALIDATION.md`: Windows columns FAIL→PASS
(live no-MSVC A/B; YOLO train FAIL→PASS), Linux columns PASS→PASS,
numerics row exact (Windows <= 9.5e-7 vs CPU; Linux bit-identical,
max_abs 0.0), kthvalue row exact as quoted above. Coordination identity
block matches the handoff. (N-5: the "Linux-leg notes" are numbered
1, 2, 4, 3 — the kthvalue note was inserted before note 3.)

## 8. Patch minimality — PASS

560 lines / 8 files confirmed. No drive-by edits beyond N-1's two
cosmetic blank-line pairs; no debug prints / iostream includes; no
TODO/FIXME/XXX/HACK; no commented-out code; no binaries. Self-tests in
the new headers are static_assert-only (zero runtime cost) and
namespaced (`miopen_freestanding_selftest`) to avoid polluting the
kernel namespace.

## 9. Submission discipline — PASS

- `upstream_state` / `upstream_*_created` = false in PATCH_HANDOFF.json,
  phase3_conclusion.json, linux_conclusion.json, final_gate.md (also
  `internal_pr_created: false`). No evidence of any upstream
  PR/issue/comment anywhere in the tree.
- Patch identity recomputed from Git blobs on origin/main:
  0001 sha256 `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20`,
  0002 sha256 `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532`,
  series hash `b1150afcf2170a9d396f9a25669547c0ed4021c221f7feaa59e073d4b9706685`
  — ALL MATCH the handoff. PATCH_ID `P3-FINAL-R3`, SOURCE_SHA
  `b68f8944300f104875d953fc8e4510908c9aaf0b` consistent everywhere
  (handoff, conclusion, cross-platform doc, kthvalue doc, both local
  rocm-libraries checkouts verified at that SHA).
- Local baseline tree left pristine after this review's apply test
  (0 modified files, HEAD b68f8944).

## Issue register

| ID | Severity | Classification | Issue | Action |
|---|---|---|---|---|
| M-1 | MAJOR | HUMAN_SUBMISSION_STEP | PR_DRAFT.md + MAINTAINER_REPORT_DRAFT.md stale "Linux pending / author lacks Linux GPU" wording post-2026-10-08 | Refresh both docs with Linux PASS→PASS (bit-identical numerics, kthvalue runtime) during the mandatory DCO-fill submission pass; do not touch patch bytes |
| M-2 | MINOR | HUMAN_SUBMISSION_STEP | `findings/phase3/final_readiness/` (incl. `PR_READINESS.json`) referenced by checklist/README/conclusion but not yet present — package being assembled now (this file is part of it) | Complete the final_readiness package before submission |
| M-3 | MINOR | JUDGMENT (keep) | Internal RCA jargon in upstream header comment: "verified by Phase-3 canary G57-7 on gfx1151/hiprtc 7.14" (miopen_freestanding_initializer_list.hpp) — cryptic to upstream, but rewording changes validated patch identity | Recommend keep as-is (harmless provenance note); if reworded, follow checklist steps 3–5 re-verification |
| N-1 | NIT | — | Cosmetic blank lines added around unchanged includes in non-RTC arms (0001) | Keep (identity preservation outweighs) |
| N-2 | NIT | — | `MIOPEN_FREESTANDING_TRAITS_ACTIVE` defined, never used | Keep or drop in upstream review if maintainer asks |
| N-4 | NIT | — | "rocRAND PR #8247" label (lives in rocm-libraries monorepo) | Optional wording polish in PR description |
| N-5 | NIT | — | Cross-platform notes numbered 1,2,4,3 | Optional fix |
| N-6 | NIT | — | `evidence/phase3/raw/linux/final_integration/origin_main_final_verification.txt` untracked (Gate F23 record) | Commit with manifest refresh |
| N-7 | NIT | — | `hiprtc_selftrained` typo in proposed CI wiring comment; "2.x.y" sanitized version trailer | Optional; CI wiring is upstream-CI territory |
| CI-1 | — | UPSTREAM_CI_FOLLOWUP | Compile-only freestanding test on gfx94x/110x/120x | Upstream CI |
| CI-2 | — | UPSTREAM_CI_FOLLOWUP | `MIOpenDriver kthvalue` (or gtest) on >=1 non-gfx1151 target | Upstream CI |
| CI-3 | — | UPSTREAM_CI_FOLLOWUP | One HIP 10.x line leg (gate region is version-gated; develop == 10.x line already built+validated locally, CI confirmation is the right enforcement) | Upstream CI |
| CI-4 | — | UPSTREAM_CI_FOLLOWUP | ROCm 7.2.1 runtime not tested (wheels delisted) — source-verified gate presence; honestly disclosed | Upstream CI / future wheels |

None of the above is a technical defect in the validated patch. No
BLOCKER and no MAJOR technical issue exists: patch bytes, applicability,
identity chain, evidence linkage, reference accuracy, and claim
discipline all verified clean, including independent byte-level
re-verification of the patch→tree round trip against the validated
Linux build tree.

REVIEWER D VERDICT: APPROVE
