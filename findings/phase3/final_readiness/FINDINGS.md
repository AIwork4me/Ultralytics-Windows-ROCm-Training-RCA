# Final Upstream PR-Readiness — Consolidated Findings (Gate F25)

Date: 2026-10-08. Source: four independent adversarial reviewers
(Reviewer A maintainer-sim `reviewer_miopen.md`; B regression attacker
`reviewer_regression.md`; C CI/portability `reviewer_ci.md`; D submission
`reviewer_submission.md`), each reviewing the integrated `origin/main`
at `f553c49` with independent recomputation (patch round-trips, SHA
re-verification, fresh GPU probes) — not document trust.

## Verdicts

| Reviewer | Verdict |
|---|---|
| A — MIOpen maintainer | **APPROVE** (no blocker; 1 MAJOR in a proposal artifact) |
| B — regression attacker | **NO REGRESSION FOUND** (0 BLOCKER, 0 MAJOR) |
| C — CI / portability | **NO LOCAL BLOCKER** |
| D — upstream submission | **APPROVE** |

## Classification and resolution

### BLOCKER — none (all four reviewers)

### MAJOR (2, both outside the validated patch bytes — both RESOLVED)

| ID | Finding (source) | Class | Resolution |
|---|---|---|---|
| X1 | Proposed CI test (`patches/phase3/proposed_ci_test/hiprtc_selfcontained.cpp`) as written would fail even on a patched tree: no `-I<kernels-dir>` passed to `hiprtcCreateProgram`; wiring typo `hiprtc_selftrained`; described negative-control mode not implemented; monorepo path mismatch (A-M1; C-F5) | MAJOR (proposal artifact) + UPSTREAM_CI_FOLLOWUP | **RESOLVED 2026-10-08**: the proposal file now carries a wiring-time fix block at the top enumerating all four defects; the fix belongs to CI wiring with maintainers, not to the validated patch series (both reviewers' explicit scoping) |
| X2 | Stale submission-package text: `PR_DRAFT.md` "Remaining before merge: Linux … not run" and `MAINTAINER_REPORT_DRAFT.md` "Linux results — not yet run … blocking for merge" contradict the completed 2026-10-08 Linux PASS (A-M3; C-F6; D M-1) | MAJOR + HUMAN_SUBMISSION_STEP (under-claim only, no integrity issue) | **RESOLVED 2026-10-08**: both documents refreshed with dated status corrections pointing at the Linux evidence (this closed it earlier than the reviewers' "fix at submission time" suggestion) |

### MINOR (5)

| ID | Finding (source) | Class | Resolution |
|---|---|---|---|
| m1 | Duplicated `new file mode 100644` lines in the three new-file diffs of the validated series (A-M2); `git am`/`git apply` accept and reproduce the exact validated tree | MINOR (patch-bytes formatting) | Not fixable without mutating the validated patch — DEFERRED BY DESIGN; self-heals at checklist step 3 regeneration; recorded in FINAL_SUBMISSION_CHECKLIST |
| m2 | Three consecutive blank lines in `miopen_freestanding_initializer_list.hpp` vs Google `.clang-format` (A-M4) | MINOR (patch-bytes formatting) | Same disposition as m1 — fix during regeneration if maintainers run clang-format |
| m3 | Untracked stray `miopen_freestanding_initializer_list.hpp` in the "pristine" baseline reference tree (A-M5, B-MINOR-1; introduced during the parallel review panel, postdates all recorded evidence, inert) | MINOR (evidence hygiene) | **RESOLVED 2026-10-08**: file removed; baseline tree re-verified clean at b68f8944 with empty `git status --porcelain` |
| m4 | comgr-vs-hiprtc partial-STL reachability nuance to state in PR/test docs so J3's `#error` is not "fixed" as a bug (C-F8) | MINOR (documentation) | Noted here and in reviewer_ci.md; PR draft references the design doc |
| m5 | `final_readiness/` package (incl. PR_READINESS.json) referenced before it existed (D M-2 / C-F7) | MINOR (packaging) | **RESOLVED**: package completed by this gate set |

### NIT (kept for identity preservation; optional at regeneration)

- `#if X && !__has_include(<h>)` short-circuit nuance (A-N1, C note) —
  universally accepted; no change requested.
- Partial-STL cross-check asymmetry in the initializer_list probe is
  sound (disjoint entity sets) but worth a comment line when
  regenerating (A-N2).
- Cosmetic blank-line/comment churn in non-RTC arms (A-N3 / D N-1).
- `MIOPEN_FREESTANDING_TRAITS_ACTIVE` defined-never-used (D N-2).
- "rocRAND PR #8247" label wording (D N-4); cross-platform note ordering
  1,2,4,3 (D N-5); "2.x.y" sanitized version trailer (D N-7).
- Internal jargon "Phase-3 canary G57-7" in one upstream header comment
  (D M-3) — kept: rewording changes validated patch identity.

### UPSTREAM_CI_FOLLOWUP

1. Cross-arch legs gfx94x / gfx110x / gfx120x for the compile-only
   no-STL test (J1–J5 tier) and kthvalue runtime fresh-cache run (J6/J7)
   — C-F1, A-U1.
2. HIP/ROCm 10.x line leg (gate still present on 10.x source per
   GATE70) — C-F2, A-U1.
3. ROCm 7.2.1: runtime untestable (wheels delisted); carry the one-line
   backport note (macro-name adaptation) in the PR — C-F3, A-U2.
4. HIP<7 arms pinned by compile-only leg J2 (byte-identical shim bodies
   re-verified by A and B) — C-F4 (low risk).
5. Audit ratchet: upstream `audit_rtc_std_dependencies.py` as a CI
   utility job (C-F10/J5, A-U4).
6. One static-CK wrapper TU in the compile-only CI set (A-U3).
7. initializer_list-lowering CI hardening for older wheel clangs
   (B F-UP-3); pre-existing BFP16-NaN `isnan(ushort)` semantics
   (B F-UP-1, not a regression of this patch); radix HIP<7 backport
   window note (B F-UP-2).

### HUMAN_SUBMISSION_STEP

1. DCO/author identity fill — including REMOVING the trailing
   `# DCO: fill in before submission` comment (a trailing comment fails
   DCO-bot matching) and the fabricated `2.x.y`/date trailers (A-H1,
   C-F12, D); governed by `docs/phase3/FINAL_SUBMISSION_CHECKLIST.md`.
2. Copyright attribution placeholder in the three new MIT headers —
   maintainer preference wins (A, D).
3. Final PR-text refresh pass (Linux results now included; X2 already
   applied, re-verify at submission).

## Notable additional evidence generated during review

Reviewer B extended runtime coverage beyond the F-gate set at no
additional risk: BFP16 kthvalue runtime A/B (3 cases / 198 slices,
fresh caches, cold HIPRTC compile proven per leg,
`-DMIOPEN_USE_BFP16=1 -DIN_OUT_TYPE=ushort`) — PASS/PASS, dumps
byte-identical A/B; adversarial TUs outside the tested matrices (10
kernels incl. fp8/Getitem/RNN/MarginLoss/BatchNormBwdSpatial/static-CK
wrapper) token-identical between trees; MSVC-triple freestanding
initializer_list lowering verified correct at the IR level. This
retroactively closes C-F9's BFP16 gap on gfx1151 (non-gfx archs remain
CI scope).
