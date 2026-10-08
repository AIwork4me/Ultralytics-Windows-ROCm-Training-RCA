# Gate P56 — Reviewer D (submission review)

- **Role**: submission reviewer — authorship, DCO, licensing, patch format, PR-draft
  and evidence honesty, status fields, human-steps checklist.
- **Date**: 2026-10-08. Machine: Windows (Git Bash).
- **Objects**: canonical worktree `rocm-libraries-phase4-canonical`
  (`prepare/miopen-hiprtc-selfcontained` = `b68f894` + `c86d1b9` + `4084759`),
  `patches/phase4/canonical/{README.md,0001-*.patch,0002-*.patch}`,
  `patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`,
  `docs/phase4/{AUTHORSHIP_DCO_AUDIT,PR_DRAFT_FINAL,MAINTAINER_REPORT_FINAL,
  UPSTREAM_SUBMISSION_CHECKLIST,UPSTREAM_BASE_COMPATIBILITY}.md`,
  all prior reviews under `findings/phase4/reviews/`, all of `evidence/phase4/`.

## VERDICT: **APPROVE WITH CHANGES**

All hard requirements pass: DCO discipline, licensing placeholders, patch
authenticity (independently re-proven), status fields, and the human-steps
checklist. No claim in the final docs is fabricated or unbacked. Four
documentation-level defects (2 MINOR, 2 NIT) must be fixed before this package
is handed to the human submitter; none touch the validated bytes, the commits,
or the evidence.

---

## 1. DCO discipline — PASS

`git log --format=fuller b68f894..HEAD`:

| Commit | Author | Committer | DCO marker count |
|---|---|---|---|
| `c86d1b95aacc35eed6b25e69ba659e1f6a133197` | AIwork4me \<AIwork4me@users.noreply.github.com\> | same | exactly 1 |
| `4084759f3804748b7935d882db2d0445a3e0c380` | AIwork4me \<AIwork4me@users.noreply.github.com\> | same | exactly 1 |

- **No real `Signed-off-by` trailer anywhere.** Grep for
  `^\s*Signed-off-by` over both full commit bodies: zero hits. The string
  "Signed-off-by" occurs exactly twice per archive — once inside each
  DCO-pending marker's instruction text ("replace this line with a real
  Signed-off-by per DCO…"), which is not a trailer, plus prose in the patches
  README explicitly stating no sign-off is present. Verified in commits AND in
  `patches/phase4/canonical/*.patch`.
- **Marker discipline**: `DCO: PENDING HUMAN CONFIRMATION - provisional local
  commit, not for upstream submission; …` present exactly once per commit
  message and exactly once per archived patch (per-hash grep count = 1 each).
- **README classification**: `patches/phase4/canonical/README.md` is titled
  "… PROVISIONAL, NOT DCO-READY", states author/committer identity is not DCO
  authorization, and ends with "Do NOT `git send-email` / `git am` these files
  into any upstream branch."
- `docs/phase4/AUTHORSHIP_DCO_AUDIT.md` (P54) classifies the package as
  `PROVISIONAL LOCAL PACKAGE` with `DCO-APPROVED … NOT achieved`, and confirms
  the Phase-3 envelope placeholder (`Signed-off-by: <AUTHOR NAME>
  <author@example.com>`) was NOT copied into the commits.

## 2. Licensing — PASS

- All three new files carry full MIT headers with the intentional placeholder:
  - `projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp`
  - `projects/miopen/src/kernels/miopen_freestanding_utility.hpp`
  - `projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp`

  Each: `Copyright (c) 2026 [contributor name and notice to be set by the
  submitter]`. The proposed CI test
  (`patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`) carries the same
  header + placeholder.
- **No fabricated attribution.** Added-line grep across the whole 8-file diff
  (`git diff b68f894..HEAD | grep '^+' | grep -iE 'copyright|author|ltd|llc|inc\.|gmbh|corp'`)
  returns only the three placeholder MIT headers and standard MIT boilerplate;
  no invented person/company name anywhere in the 8 files. No `-Copyright`
  lines (nothing stripped from the 5 modified files). Added lines mentioning
  AMD/ROCm are technical (issue references, environment descriptions), not
  attributions.
- The placeholder is correctly flagged as a human submission step in
  AUTHORSHIP_DCO_AUDIT.md (action 3) and UPSTREAM_SUBMISSION_CHECKLIST.md §2.

## 3. Patch format — PASS (independently re-proven)

- `From` lines carry the real full commit hashes (`c86d1b95…`, `4084759…`),
  matching `git log`; correct `[PATCH 1/2]`/`[PATCH 2/2]` ordering; real dates.
- No `From 000000000000…`, no literal `2.x.y`, no `<AUTHOR NAME>`,
  no `author@example.com`/`example.com` (grep over `*.patch` + README: clean).
- The patches end with the authentic local git version signature
  `2.55.0.windows.5` (once each) — genuine `git format-patch` output, not a
  forged placeholder.
- **Decisive re-verification by this reviewer**:
  1. `git format-patch b68f894..HEAD` regenerated into a scratch dir is
     **byte-identical** to both archived `.patch` files (`diff` empty).
  2. **`git am` round-trip** onto a pristine detached worktree at `b68f894`
     applies both patches cleanly and reproduces **all 8 file blob OIDs
     identical** to canonical HEAD (independently reproduces the P46 claim
     cited in the README and MAINTAINER_REPORT).
- Canonical worktree `git status --porcelain`: clean; base commit is
  `b68f8944300f104875d953fc8e4510908c9aaf0b` as claimed.

## 4. PR-draft / maintainer-report honesty sweep — PASS with 2 MINOR wording defects

Every load-bearing claim was traced to evidence:

| Claim in final docs | Backing | Status |
|---|---|---|
| Applies cleanly on develop `18e1985` (+37 commits, zero drift) | `UPSTREAM_BASE_COMPATIBILITY.md` (P42: `git apply --check` in pristine worktree, empty affected-file diff, no equivalent fix); P42 review PASS | BACKED |
| 8/8 byte-equivalence (P45) | `evidence/phase4/equivalence/file_hash_matrix.json`: 8/8 MATCH (blob OID + SHA-256), overall PASS; P45 review PASS | BACKED |
| Windows unpatched FAIL (field signature) | phase-3 `g63_A_wheel_nomsvc*.json`, `g78_A_wheel_nomsvc_FINAL.json` (contain the `'type_traits' file not found` chain); phase-4 CI `negative/unpatched` cell reproduces the exact signature at compile level | BACKED |
| Windows phase-4 rebuilt+loaded+rerun (P50–P52) | `build_provenance.json` (fresh build at `4084759`, DLL SHA `b32d6310…`), `runtime_binding.json` + `binding_probe.txt` (SHA-proven PyTorch load), `nostl_validation.json` (P52C: MSVC include renamed, env scrubbed, restored, PASS), `batchnorm_minimal.txt` (train/eval/backward, max_abs vs CPU 6.8e-7), `yolo_train.json` (P52E: both AMP modes, TRAIN_DONE) — same DLL SHA across P50→P52E | BACKED |
| Linux PASS→PASS bit-identical, 37 tensors max_abs 0.0, BN 8/8→8/8, non-BN 11/11→11/11 | `evidence/phase4/linux_preservation.md` (P53) + P53 review PASS; identity chain `evidence/phase4/identity/verification.json` (P41: patch SHA-256 `f06d7ae5…`/`77f9fc16…` match `origin/main` handoff); preserved `findings/phase3/linux/linux_conclusion.json` | BACKED (phase-3 evidence, correctly carried over via proven byte-equivalence, not re-claimed as rerun) |
| kthvalue runtime unpatched→patched PASS (values+indices) | `linux_conclusion.json` per P53 preservation doc + phase-3 subagent review | BACKED |
| CI test 6/6 matrix | `evidence/phase4/hiprtc_ci/ci_matrix.json`: 6 cells PASS with full compiler logs, real trees (`b68f894` / `4084759`), hashed binary + hiprtc DLL | BACKED |
| Adversarial hardening (Gate P49) | Round-1 review FAIL (F1–F4 false-verdict vectors) → hardened → round-2 reverify re-ran all four (all exit 4 INCONCLUSIVE) + 19 new attacks; final source contains the round-2 required fixes: `fatal error: '<hdr>' file not found` anchors, plural-safe error counting excluding source-echo, marker+compile_status-gated probe, `--keep-isolated` removed from usage; final 6/6 matrix re-run on the final binary | BACKED |
| 104-entry RTC audit script committed | `scripts/phase3/audit_rtc_std_dependencies.py` exists; `rtc_entry_count: 104` in `evidence/phase3/raw/source/rtc_std_dependency_matrix.json` | BACKED |
| Environment identity (gfx1151, ROCm 7.14 wheels, torch 2.12.0+rocm7.14.0) | `evidence/phase4/environment/environment.json` + YOLO run logs | BACKED |

Forbidden-claim sweep (grep over `docs/phase4`): **no occurrence of** merged
upstream / officially fixed / accepted upstream / validated on every AMD GPU /
tested on ROCm 10.x / any PR-issue-comment created. Cross-arch limits are
explicitly scoped ("Runtime: gfx1151 only"; PR draft "Cross-architecture
coverage (explicitly scoped limitation)"; ROCm 10.x framed as *remaining*
upstream-CI work, with only a source-inspection statement about gate logic).
The CI design doc explicitly says in-tree CTest integration is "proposed but
not claimed as run". PR draft footer: "No upstream PR, issue, or comment has
been created."

### Findings against the docs

| ID | Severity | Finding |
|----|----------|---------|
| D1 | **MINOR** | `PR_DRAFT_FINAL.md` Testing bullet 1 uses a compound subject — "the patched build (Phase 3) **and** the canonical two-commit reconstruction (Phase 4 …) pass BatchNorm train/eval/backward, **an 11-op non-BN RTC matrix**, numerical checks, and YOLO26n coco8 1-epoch training" — which attributes execution of the 11-op non-BN RTC matrix to the Phase-4 reconstruction. Phase-4 evidence contains BN + numerics + YOLO reruns only (`batchnorm_minimal.txt`, `nostl_validation.json`, `yolo_train.json`); the 11-op Windows matrix ran in Phase 3 (and on Linux), reaching Phase 4 via the P45 byte-equivalence bridge. `MAINTAINER_REPORT_FINAL.md` §9–12 scopes this correctly (11-op listed under the Phase-3 bullet). Not a fabrication — an over-attributing sentence. |
| D2 | **MINOR** | `CI_REGRESSION_TEST_DESIGN.md` points to "the optional third commit **on branch `prepare/miopen-hiprtc-selfcontained-ci`**" (PR draft: "kept on a separate branch"). No such branch exists in any of the four `rocm-libraries*` clones/worktrees on this machine (canonical, baseline, develop-check, phase3 — checked `git branch -a` and `git worktree list`); the CI test exists only as the uncommitted proposal artifact `patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`. A human submitter following the pointer finds nothing. |
| D3 | **NIT** | `hiprtc_selfcontained.cpp` header comment (lines 41–43): usage block still lists `[--keep-isolated]` (flag removed in hardening — actual usage string at line 333 is `[--arch=gfxNNNN] [--hip-flat=N] [--isolate=OPT]`) and omits `[--isolate=OPT]`. Comment drift only; runtime usage text is correct. |
| D4 | **NIT** | `AUTHORSHIP_DCO_AUDIT.md` states "no `2.x.y` signature (normalized)". The archived patches DO carry a version signature — the authentic local git version `2.55.0.windows.5`. The intended meaning (no placeholder version string) is clear from context, but as written it can be misread as "no signature at all". |

## 5. Status fields — PASS

Repo-wide grep for `upstream_pr_created` / `upstream_issue_created` /
`upstream_comment_posted` / `internal_pr_created` / `issue_created` /
`comment_posted`: every occurrence is either `false` (phase-3
`phase3_conclusion.json`, `linux_conclusion.json`, `PR_READINESS.json`,
`PATCH_HANDOFF.json`, `final_gate.md`) or the phase-4 checklist's list of
fields that "must remain false unless a human flips them"
(`UPSTREAM_SUBMISSION_CHECKLIST.md` §6). **No phase-4 file sets any of them to
true.** No phase-4 conclusion/status document flips them.

## 6. Human-steps checklist — PASS (complete and actionable)

`docs/phase4/UPSTREAM_SUBMISSION_CHECKLIST.md` covers all six required areas
with concrete, executable steps:

1. DCO/identity (BLOCKING): approve real identity, recreate commits (tree
   bytes unchanged), real `Signed-off-by:`, regenerate format-patch, re-run
   `scripts/phase4/semantic_equivalence.py`.
2. Copyright (BLOCKING): fill the MIT placeholder in the three new files; rerun
   CI matrix + build + P51/P52-style runtime spot-check.
3. Formatting (submitter decision): clang-format decision with the
   consequence spelled out (reformat = new candidate = rerun validation).
4. PR text: refresh PR draft with final hashes; associate #3956; mention
   #7718 / TheRock#8292.
5. Pre-submission verification: re-check applicability that day
   (`git apply --check`, Gate P42 method) + equivalent-fix landed-meanwhile
   grep (exact commands given).
6. Forbidden-until-approval: any `gh pr/issue/comment`, any push, any claim of
   acceptance; status fields enumerated.

Missing nothing material; each item is unambiguous and cross-referenced to the
audit doc and gates.

---

## Evidence examined

- Canonical worktree: `git log --format=fuller`, per-commit body greps,
  `git diff --name-only/--stat` (8 files, +384/−5), attribution-added-line
  grep, copyright-removed-line grep (none), branch/base verification, clean
  status.
- Independent reproductions: format-patch byte-diff (identical); `git am`
  round-trip into pristine `b68f894` worktree (8/8 blob OIDs MATCH); scratch
  worktree removed afterwards.
- Patches: full header/tail reads, placeholder greps, README read.
- Docs: PR_DRAFT_FINAL.md, MAINTAINER_REPORT_FINAL.md, AUTHORSHIP_DCO_AUDIT.md,
  UPSTREAM_SUBMISSION_CHECKLIST.md, UPSTREAM_BASE_COMPATIBILITY.md,
  CI_REGRESSION_TEST_DESIGN.md (full reads); forbidden-claim and status-field
  greps across `docs/`, `findings/`, `evidence/`, `patches/`.
- Evidence: `equivalence/file_hash_matrix.json`, `hiprtc_ci/ci_matrix.json`,
  `identity/verification.json`, `build/build_provenance.json`,
  `windows_runtime/{runtime_binding.json,binding_probe.txt, batchnorm_minimal.txt,
  gpu_control.txt,nostl_validation.json,yolo_train.json}`,
  `linux_preservation.md`, `environment/environment.json`; phase-3
  `raw/runtime/g63*/g78*` (unpatched FAIL), `raw/source/
  rtc_std_dependency_matrix.json` (`rtc_entry_count: 104`),
  `findings/phase3/linux/linux_conclusion.json`, phase-3 status-field JSONs.
- Prior reviews: P40, P41, P42, P44, P45, P49 (both rounds), P53 — verdict
  chain consistent with the docs' citations.

## REQUIRED ACTIONS

1. **(D1, MINOR)** Reword the PR_DRAFT_FINAL.md Windows testing bullet so the
   11-op non-BN RTC matrix is attributed to the Phase-3 patched build (and the
   Linux validator), with the Phase-4 rerun scope stated as BatchNorm +
   numerics + YOLO train — matching MAINTAINER_REPORT_FINAL.md §9–12.
2. **(D2, MINOR)** Resolve the phantom CI-test branch: either create
   `prepare/miopen-hiprtc-selfcontained-ci` actually containing the third
   commit, or amend CI_REGRESSION_TEST_DESIGN.md (and the PR-draft parenthetical)
   to state the CI test currently exists only as the proposal artifact at
   `patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp` (no branch yet).
3. **(D3, NIT)** Update the header usage comment in
   `hiprtc_selfcontained.cpp` (drop `[--keep-isolated]`, add `[--isolate=OPT]`)
   so the comment matches the actual usage string.
4. **(D4, NIT)** Reword the AUTHORSHIP_DCO_AUDIT.md signature bullet to e.g.
   "no placeholder `2.x.y` version signature; the patches carry the authentic
   local git version signature (`2.55.0.windows.5`)".

All four are documentation-only; none invalidate any gate evidence, the
commits, or the DCO posture. Once applied, the submission package is honest,
provisional-by-design, and ready for the human submitter workflow defined in
UPSTREAM_SUBMISSION_CHECKLIST.md.
