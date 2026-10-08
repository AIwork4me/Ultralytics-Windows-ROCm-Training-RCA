# P517 — Reviewer D: Upstream-Submission Compliance Audit (FINAL)

Date: 2026-10-08. Scope: the prepared (NOT submitted) MIOpen contribution
`P5-CANDIDATE-R1`: 3 commits `135f775e` / `b1adc77a` / `39319c4d` on branch
`prepare/miopen-hiprtc-phase5` (worktree `rocm-libraries-phase5-candidate`),
base `7c5866144ac4b879be442563e2b49fa1c142ea36` (ROCm/rocm-libraries develop,
frozen). Everything verified independently from local state plus read-only
GitHub REST API lookups.

## VERDICT: CONDITIONAL PASS

The package is compliant on all seven audit dimensions and submission-accurate;
no BLOCKER or MAJOR defect found. Three documentation/packaging conditions
must be discharged before handoff (none changes patch bytes or any VALIDATED
claim). The submission itself remains — correctly and by design — gated on
human DCO certification and copyright attribution, both explicitly marked
PENDING in the artifacts.

---

## Dimension 1 — Author identity: PASS

- `git log -3 --format=fuller` in the candidate: Author and Committer are
  `AIwork4me <AIwork4me@users.noreply.github.com>` on all three commits.
- AUTHORSHIP_DCO_AUDIT.md §2 claims both `AIwork4me@users.noreply.github.com`
  and `AIwork4me@qq.com` are linked to GitHub account `AIwork4me`
  (id `261514469`). Re-verified live against the REST API:
  - `GET .../commits/7294c66` — commit email `AIwork4me@users.noreply.github.com`,
    API `author.login = "AIwork4me"`, `id = 261514469`. Confirmed.
  - `GET .../commits/033e6f4` — commit email `AIwork4me@qq.com` (GitHub
    web-flow merge), API `author.login = "AIwork4me"`, `id = 261514469`.
    Confirmed.
- Account `AIwork4me` exists, id `261514469`, created `2026-02-13` — matches
  the audit doc's claim verbatim.
- The two linkage paths (verified email push; signed-in web-UI commit) are
  both demonstrated; the inference "the noreply address belongs to the
  confirmed account" is sound.

## Dimension 2 — DCO legitimacy: PASS

- All three commits are UNSIGNED: `%G?` = `N`, no `gpgsig` header in
  `git cat-file commit`.
- Each commit message carries exactly one
  `DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream submission; ...`
  line (lines 22/20/26 of the respective messages).
- The string "Signed-off-by" occurs once per message — ONLY inside that
  marker's instruction text ("replace this line with a real Signed-off-by"),
  never as a trailer. `git log --format="%(trailers)"` parses only the DCO:
  marker. No commit is represented as signed.
- `git show 7c58661:projects/miopen/CONTRIBUTING.md` (131 lines, read in
  full): MIT-licensed contributions, branch+PR flow, two reviewers, CI pass,
  issue association, regression test. **No DCO / Signed-off-by requirement is
  stated** — matching AUTHORSHIP_DCO_AUDIT.md §3 and MAINTAINER_REPORT §
  "Outstanding" item 1 ("does not mandate DCO, but the monorepo PR bot may").
- Spot-checked 21 commits ending at base `7c58661`: zero `Signed-off-by:`
  trailers — the audit doc's claim about develop history is accurate.
- The conservative stance (refuse to self-certify DCO for a human) is the
  correct one and is consistently documented with an exact finalize command.

## Dimension 3 — Copyright attribution: PASS

- Series adds 4 files: 3 new kernel headers + 1 test source. All four carry
  the placeholder line
  `Copyright (c) 2026 [contributor name and notice to be set by the submitter]`.
- No invented copyright holder: no "Advanced Micro Devices" or any other
  attribution appears in the new files (grep-verified); status correctly
  recorded as `COPYRIGHT_ATTRIBUTION_PENDING` in PATCH_IDENTITY.json,
  PATCH_HANDOFF.json, and the docs.
- MIT permission notice in all 4 new files matches
  `projects/miopen/LICENSE.md` (the project's MIT terms) word-for-word
  (normalized diff over the comment-prefixed lines: identical).
- (See MINOR-2: the fill-in instruction scope says "three files" but the
  placeholder also lives in the 4th new file, `test/hiprtc_selfcontained.cpp`.)

## Dimension 4 — Commit/patch formatting: PASS

- Regenerated `git format-patch 7c58661..39319c4d` into a temp dir:
  all 3 outputs **byte-identical** (`cmp`) to `patches/phase5/canonical/`.
- Subject lines match the series (From-line SHAs = the three commit SHAs;
  filenames and titles match the PR draft's commit list).
- Per-file SHA256 recomputed from the canonical directory:
  - `0001-...no-h.patch` = `76fd6623958fb58fc71a9fabbf662bc28a22cfd19aeacba76ca9eee841abc586` (matches PATCH_IDENTITY.json)
  - `0002-...self-c.patch` = `16046b5426f51e4711e8cc0c1af235ca067761bff70a49066220a83419345242` (matches)
  - `0003-...test.patch` = `91914ac1963c79fd34d19c793e4cdd03aa05f4333e0eb7281bc58cee353976af` (matches)
- Series hash recomputed per the documented algorithm
  (`sha256_file_concat_v1`, concat of the 3 files' LF bytes, no separator):
  `c5e039c48c4904d3151441a44e870de43aa9641b7ca6a6c38467a31634a581ed` —
  **exact match** with PATCH_IDENTITY.json and PATCH_HANDOFF.json.
- Apply test: created a detached temp worktree at `7c58661` (from
  `rocm-libraries-phase3`), applied the on-disk canonical series
  sequentially with `git am`: all 3 applied clean. Resulting tree
  `04bbb617da813ef8c96f64da1e4163197df8f85a` is **identical** to the
  candidate commit `39319c4d`'s tree. Worktree removed afterwards.
  - Note: the audit mission's prescribed `git cat-file blob
    HEAD:patches/phase5/canonical/<f>` fails in the RCA repo because the
    phase5 tree is untracked (see NIT-1); the on-disk bytes were used, and
    they are proven identical to fresh `format-patch` output, which is the
    stronger guarantee.

## Dimension 5 — PR accuracy: PASS

- **Version distinction correct**: PR says v8.4.171 (Oct 1, 2026) is the
  *announcement* and 8.4.174 is the *tested* version; it explicitly says the
  defect "predates that announcement". It does NOT claim the defect was
  introduced by v8.4.171. Verified externally: the v8.4.171 release page
  exists, dated Oct 1, headlined "Add AMD ROCm and MIGraphX support
  (#24137)" — the PR's announcement characterization is accurate. 8.4.174
  appears in the phase5 YOLO logs (`torch-2.12.0+rocm7.14.0`, Radeon 8060S).
- **No over-broad impact claim**: scope is "HIPRTC toolchains without a host
  C++ stdlib (AMD's Windows wheels)" and "any no-stdlib HIPRTC environment" —
  not "all Windows Radeon GPUs".
- **Issue references consistent** across commit messages, patch-embedded code
  comments, and docs: MIOpen#3956 (commit 1 + 3, PR, test source),
  TheRock#8292 (commit 1, PR), #3803 and #3147 (commit 1 history section and
  PR root-cause section — same framing: the two HIP-7 PRs disabled the no-STL
  shims), rocm-libraries#7718 (patch 0001 code comments "failure class" +
  PR context + problem statement). No contradictions found.
- **Every VALIDATED claim maps to existing evidence** (see D6); HISTORICAL
  (P3/P4) vs PENDING (Phase-5 Linux) labels are used correctly — the PR
  never presents historical validation as fresh, and
  LINUX_FINAL_VALIDATION_HANDOFF.md explicitly refuses to relabel P3 Linux
  PASS as Phase-5 validation. The historical Linux branch
  `rca/linux-gfx1151-phase3-regression` exists (remote branch).
- **Unpatched-FAIL claim substantiated**: `ci_matrix_phase5.json` cell
  `positive/unpatched` exits 1 with `fatal error: 'type_traits' file not
  found` at `miopen_type_traits.hpp:151` and "1 error generated" (sole
  error). The runtime `miopenStatusUnknownError` traceback is correctly
  attributed to MIOpen#3956 + phase-3 raw logs (found in
  `evidence/phase3/raw/runtime/g78_A_wheel_nomsvc_FINAL.json` et al.).
- **Technical claims spot-checked in the candidate source**: `__INT32_MAX__`/
  `__INT64_MAX__` present in radix.hpp (no `numeric_limits` uses remain);
  12 `static_assert` self-tests in `miopen_freestanding_type_traits.hpp`;
  test gated on `MIOPEN_USE_HIPRTC`, `MIOPEN_TEST_HIPRTC_ARCH` cache
  override, registered via the repo's `add_test_command`, excluded from the
  `add_test_executable` glob — all as the PR/CI_INTEGRATION.md describe.
- **Upstream-base claims re-verified in git**: `18e1985..7c58661` touches
  zero `projects/miopen/` files; `b68f894..7c58661` touches exactly the 9
  MIOpen files listed in UPSTREAM_BASE_ASSESSMENT.md; the
  `use_gfx9_dpp` rename is present in the BN kernels.
- **Cross-checks**: ci_matrix `test_source_sha256`
  (`c97e748e...313c80`) equals the SHA256 of the candidate's
  `test/hiprtc_selfcontained.cpp`; ci_ctest logs show "Test #10:
  test_hiprtc_selfcontained ... Passed" and "100% tests passed";
  yolo_amp_default.txt contains "AMP: checks passed" (ANSI-stripped) and
  "1 epochs completed" in both AMP modes; phase4 standalone matrix has 6
  cells, overall PASS (the PR's "6/6 in Phase 4").
- No VALIDATED claim in PR_DRAFT_FINAL.md or MAINTAINER_REPORT_FINAL.md was
  found unsubstantiated, with one caveat that is a packaging pointer, not a
  claim (MINOR-1 below).

## Dimension 6 — Evidence completeness: PASS (with MINOR-1)

- `evidence/phase5/` fully populated: `ci/` (7 files incl. the 13-cell
  matrix, configure/build/discovery/run logs, integration json), `build/`
  (configure.log, build.log ending in `MIOpen.dll` link, provenance json),
  `runtime/` (dll_provenance, nostl_validation with scrubbed-env PASS and
  wheel restore, runtime_validation with pre-fixed tolerances and finite
  numerics, binding probe, workload log), `yolo/` (amp_false, amp_default,
  train json with per-run DLL SHA256 provenance), plus `environment/` and
  `source_delta/`.
- Every maintainer-report table row maps to an existing file; no PASS is
  claimed where a file is missing or shows FAIL. Adversarial matrix cells
  with nonzero exits are expected-failure controls, labeled as such.
- `scripts/phase5/` contains 7 runnable generators
  (build_final_miopen.py, build_gtest_dep.py, ci_ctest_integration.py,
  run_ci_matrix.py, runtime_validation.py, yolo_train_validation.py,
  generate_conclusion.py).
- **Gap**: `generate_conclusion.py` was never run — its outputs
  `findings/phase5/phase5_conclusion.json` and
  `findings/phase5/evidence_manifest.json` do not exist, while
  PATCH_HANDOFF.json points to the former for the yolo_train summary
  (MINOR-1).

## Dimension 7 — Unsubmitted state: PASS

- `findings/phase5/PATCH_HANDOFF.json` `upstream_state`:
  `pr_created: false`, `issue_created: false`, `comment_posted: false`.
  No `internal_pr_created` key anywhere; nothing in `findings/phase5/*` is
  present-and-true.
- MAINTAINER_REPORT_FINAL.md: `UPSTREAM PR CREATED: NO / ISSUE: NO /
  COMMENT: NO / INTERNAL PR: NO`, plus "Nothing here has been submitted to
  any AMD repository."
- ROCm repos: only remote is `origin = ROCm/rocm-libraries` (fetch-only in
  practice); `origin/develop` still at `7c58661`; no phase5 branch exists on
  any remote. No evidence of any upstream action anywhere.

---

## Findings by severity

### BLOCKER — none.

### MAJOR — none.

### MINOR

1. **Dangling evidence pointer in PATCH_HANDOFF.json.** Line 94:
   `"yolo_train": "see findings/phase5/phase5_conclusion.json"` — that file
   does not exist (neither does the `evidence_manifest.json` the generator
   also writes). The underlying claim is independently evidenced
   (`evidence/phase5/yolo/yolo_train.json`, `overall: "PASS"`, both AMP
   modes), so nothing is claimed PASS without evidence — but the Linux
   validator consuming the handoff will hit a broken reference. Fix: run
   `scripts/phase5/generate_conclusion.py` (and verify its output), or
   repoint line 94 to the yolo evidence file.

2. **Copyright fill-in instruction under-scopes the placeholder set.**
   AUTHORSHIP_DCO_AUDIT.md §4 and SOURCE_CHANGE_JUSTIFICATION.md Fix 5
   instruct the human to fill the attribution "in the three files" (the 3 new
   MIT kernel headers), but the placeholder line also exists in the 4th new
   file `projects/miopen/test/hiprtc_selfcontained.cpp`. At submission time
   four files must change (or a rationale recorded for the test file), and
   the "comment-only byte change → rerun targeted validation" scope must
   include it. The docs' phrase "the three new MIT *headers*" is literally
   true, but the follow-up instruction is incomplete as written.

### NIT

1. **Phase-5 RCA package is entirely untracked.** `docs/phase5/`,
   `evidence/phase5/`, `findings/phase5/`, `patches/phase5/`,
   `scripts/phase5/` are uncommitted working-tree files (phase4 material, by
   contrast, was committed via PR #4). Consequences: no git-history
   integrity anchor for the canonical patches in this repo, and blob-exact
   extraction (`git cat-file blob HEAD:patches/...`) is impossible. Recommend
   committing the package (the identity/hashes in PATCH_IDENTITY.json then
   become verifiable from history).

2. **PATCH_IDENTITY.json `new_upstream_base_sha` embeds prose in the value**
   (`"<sha> (ROCm/rocm-libraries develop, frozen 2026-10-08)"`). Machine
   consumers comparing SHA fields verbatim will mismatch. Split annotation
   into a sibling field.

3. MAINTAINER_REPORT_FINAL.md line 47 quotes `"AMP: checks passed"` — the
   literal bytes in `yolo_amp_default.txt` are ANSI-interleaved
   (`AMP: \x1b[0mchecks passed`). Harmless (ANSI-stripped rendering), noted
   only for byte-exactness pedantry.

---

## Hash recompute results (summary)

| Item | Recomputed | Matches |
|---|---|---|
| Patch 0001 SHA256 | `76fd6623...41abc586` | PATCH_IDENTITY.json, PATCH_HANDOFF.json — YES |
| Patch 0002 SHA256 | `16046b54...9345242` | YES |
| Patch 0003 SHA256 | `91914ac1...353976af` | YES |
| Series SHA256 (concat v1) | `c5e039c48c4904d3151441a44e870de43aa9641b7ca6a6c38467a31634a581ed` | YES |
| format-patch regeneration vs canonical | 3/3 byte-identical | — |
| `git am` series on detached `7c58661` worktree | applies clean; tree `04bbb617da813ef8c96f64da1e4163197df8f85a` | identical to candidate `39319c4d` tree — YES |
| ci_matrix `test_source_sha256` vs candidate file | `c97e748e...313c80` | YES |
| GitHub API author linkage (7294c66 / 033e6f4) | `author.login=AIwork4me`, id `261514469` both | audit doc — YES |

## Claims in PR_DRAFT_FINAL.md that could NOT be substantiated locally

None. All locally checkable claims verified. The two external-facing claims
(v8.4.171 announcement content/date; ultralytics#24137 as the AMD-support PR)
were verified against the live Ultralytics release page and hold. Claims that
are future work are correctly labeled PENDING (Phase-5 Linux validation) or
UPSTREAM CI FOLLOW-UP (cross-arch legs), not asserted as done.

## Conditions for PASS (pre-handoff, none affect patch bytes)

1. Generate `findings/phase5/phase5_conclusion.json` (+ `evidence_manifest.json`)
   or repoint PATCH_HANDOFF.json line 94. [MINOR-1]
2. Extend the copyright fill-in instruction to cover all 4 placeholder files
   (or record why the test source is exempt). [MINOR-2]
3. Commit the phase5 RCA package so the canonical patches gain a history
   anchor. [NIT-1, recommended]

Submission-blocking items remain the deliberate human gates already flagged
in the package: DCO sign-off (replace the PENDING marker per
AUTHORSHIP_DCO_AUDIT.md §3, then regenerate + re-hash patches) and copyright
attribution (per MINOR-2's corrected scope), followed by the targeted
revalidation the package itself mandates.
