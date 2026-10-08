# Reviewer C — DCO / Submission-Policy Audit — P5.1-CANDIDATE-R1

- **Reviewer:** C (adversarial DCO / submission policy / copyright-authorization)
- **Date:** 2026-10-08
- **Verdict:** **CONDITIONAL PASS**
- **Counts:** BLOCKER 0 / MAJOR 1 / MINOR 1 / NIT 3
- **Inputs of record:** P5.1 worktree `C:/Users/rocm/Desktop/YOLO_AMD/rocm-libraries-phase5.1-candidate` (branch `prepare/miopen-hiprtc-phase5.1`, HEAD `e7ff6d75fac3e7b683e81e671555ada99af13b74`, base `7c5866144ac4b879be442563e2b49fa1c142ea36`); RCA repo `docs/phase5_1`, `findings/phase5_1`, `docs/phase5`, `findings/phase5`, `patches/phase5_1/canonical`, git histories of both repos; the user's Phase-5.1 authorization (copyright OR-authorization only; DCO certification NOT authorized).

## Per-check results

| ID | Check | Result |
|----|-------|--------|
| CHK-C1 | Approved author on all 3 commits, correct base | **PASS** — author AND committer = `AIwork4me <AIwork4me@users.noreply.github.com>` on `d4003de1`/`3b18a065`/`e7ff6d75`; oldest parent = stated base `7c58661`; worktree git config matches; consistent with `docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md` §1 and `docs/phase5/AUTHORSHIP_DCO_AUDIT.md` §1 (user confirmed identity ownership in Phase 5) |
| CHK-C2 | Email↔identity record sound and honestly derived | **PASS** — §2 rests on observed API linkage (pushed `7294c66` for the noreply address; web-merge `033e6f4` for qq.com; account id 261514469), both commits present in RCA git log; GitHub linking rules stated correctly; conclusion not inferred from string similarity; P5.1 cites rather than re-asserts (see NIT-3) |
| CHK-C3 | Copyright assertions authorized & correctly scoped | **PASS** — the 4 files with `Copyright (c) 2026 AIwork4me` are exactly the 4 files ADDED by this series (2 in commit 1, 1 in commit 2, 1 in commit 3, via `git diff-tree --diff-filter=A`); `git diff base..HEAD` shows copyright-line changes ONLY as 4 `+` lines inside those new files; modified pre-existing files retain their AMD notices untouched; P5→P5.1 delta re-verified as 4 files, +4/−4, placeholder→AIwork4me comment lines only, MIT text verbatim; code inspection found no third-party/AMD/LLVM markers and only standard-mandated minimal implementations, so "no third-party code" is defensible; no legal-entity status claimed |
| CHK-C4 | DCO correctly NOT performed | **PASS** — 0 `Signed-off-by:` trailer lines in the 3 commit bodies and in `patches/phase5_1/canonical/*.patch` (only marker-text mentions); exactly one `DCO: PENDING HUMAN CONFIRMATION …` marker per commit, not parseable as a sign-off; manifest `dco_status = DCO_ATTESTATION_PENDING (…)`; independently grepped both CONTRIBUTING.md files at the frozen base — no DCO/Signed-off/developer-certificate text (root's sole regex hit is the `amdclang` false positive on "cla"; miopen's has zero), and last 30 develop commits carry no sign-offs — so `DCO_REQUIRED_BY_UPSTREAM = NOT DOCUMENTED AS REQUIRED` is accurate and DCO is nowhere described as an upstream requirement; §3 gives exact reword instructions (rebase, delete marker, add `Signed-off-by: AIwork4me <AIwork4me@users.noreply.github.com>`, format-patch, re-hash, update manifest) |
| CHK-C5 | Every current doc says FOUR | **PASS WITH FINDING (C-MAJ-1)** — `phase5_conclusion.json` `copyright_status` explicitly says FOUR with a transparent `count corrected 3->4` note; `AUTHORSHIP_DCO_AUDIT.md` §4 and `P3_TO_P5_DELTA.md` corrected (verified via git diff, no evidence rewritten); remaining "three" hits audited as correct usages (3 patches; "3 kernel headers" as decomposition of FOUR; "Three small MIT-licensed headers" in PR draft = headers only) — except **SOURCE_CHANGE_JUSTIFICATION.md Fix 5** (C-MAJ-1). `findings/phase5/reviews/` treated as immutable per policy |
| CHK-C6 | Provisional labeling, no readiness exaggeration | **PASS WITH FINDING (C-MIN-1)** — `candidate_status = TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE`; `FINAL_SUBMITTABLE` appears nowhere; `authorization_to_submit_upstream=false`; `linux_validation_status="PENDING"`; PR_DRAFT_FINAL.md is honestly gated ("DO NOT SUBMIT WITHOUT HUMAN APPROVAL", Linux row PENDING, no DCO claim) but references the superseded P5 series (C-MIN-1) |
| CHK-C7 | No forbidden upstream actions | **PASS** — manifest flags all false; worktree `branch -r` = `origin/develop` only (candidate branches local-only; sole remote is ROCm/rocm-libraries); RCA remote is the user's own evidence repo; RCA git log shows internal phase activity only plus an explicit historical "UPSTREAM PR/ISSUE/COMMENT: NONE" record |
| CHK-C8 | RIGHT_TO_CONTRIBUTE not inflated | **PASS** — recorded as `CONFIRMED_BY_USER (2026-10-08)` with the user's verbatim OR-wording; DCO attestation kept separate and PENDING; "no external copyright holder exists" is grounded in the verified new-file/no-third-party facts, not presented as a legal ownership certification |

## Findings

### MAJOR

**C-MAJ-1 — Stale three-count in `docs/phase5/SOURCE_CHANGE_JUSTIFICATION.md` Fix 5 contradicts the frozen completeness claim.**
`docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md` §2 asserts "Phase 5.1 corrected every current checklist, conclusion and summary to say FOUR" and lists three files — accurate for those three (verified, including the uncommitted diffs). But `SOURCE_CHANGE_JUSTIFICATION.md` "Fix 5 — Copyright attribution — PENDING (human decision)" (lines 66–85) still says "**The three new MIT headers** still carry [the placeholder]" and "**those three comment lines** change", i.e. an attribution scope of THREE files when FOUR files carried placeholders and FOUR comment lines changed. Its status is also still "PENDING" although P5.1 resolved it, and the file is neither corrected nor marked superseded (git status confirms it is not among the Phase-5 files Phase 5.1 touched; `FINAL_HANDOFF.json` supersedes only `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md`). It is not an immutable reviewer transcript, so the stale count survives into the frozen record next to a claim that none remain. No code/manifest impact (candidate is 4/4 correct; delta re-verified +4/−4 comment-only).
**Fix before final freeze:** correct Fix 5 to the FOUR-file scope and add a resolved/superseded pointer to `findings/phase5_1/FINAL_HANDOFF.json` (or tighten the "corrected every…" sentence to name exactly which documents were corrected), then re-run the count sweep.

### MINOR

**C-MIN-1 — `docs/phase5/PR_DRAFT_FINAL.md` references the superseded P5 series and predates the copyright/DCO resolution; nothing in phase5_1 supersedes it.**
The draft is internally honest for its P5 framing (submission-gated, Linux row "PENDING NEW VALIDATION", no DCO claim, no readiness overstatement; "Three small MIT-licensed headers" is literally accurate). But reused verbatim it cites the wrong series identity (`patches/phase5/canonical/`, P5-CANDIDATE-R1), wrong evidence paths (`evidence/phase5/`), and is silent on the now-applied AIwork4me copyright notices. `FINAL_HANDOFF.json`'s supersedes list does not mention it and no P5.1 PR draft exists.
**Fix:** add a superseded/needs-re-pointing banner (as done for the phase5 Linux handoff) or regenerate the draft from `FINAL_HANDOFF.json` before any human submission action.

### NIT

1. **C-NIT-1 — Phase 5.1 corrections are uncommitted working-tree changes in the RCA repo** (4 modified files + 5 untracked dirs). Edits verified scoped and disclosed (count corrections, supersession banner, human_actions updates, plus a `commit_subjects` order fix visible only in git diff). Commit the set after reviews land, with a message enumerating the corrections (explicitly including the subject reorder) so the 3→4 change is versioned.
2. **C-NIT-2 — Copyright holder named by GitHub handle.** `Copyright (c) 2026 AIwork4me` identifies an account handle, not a legal name — permissible, and exactly the user's own wording; no legal-entity status is claimed anywhere. Informational: maintainers may ask for a real name; a later change would be another COPYRIGHT_TEXT-only delta needing the documented re-hash steps.
3. **C-NIT-3 — Legacy noreply format footnote.** `AIwork4me@users.noreply.github.com` is the legacy bare-username form (modern accounts default to `261514469+AIwork4me@…`). The Phase-5 evidence does not depend on the format (observed API linkage for the pushed commit; web-merge path for qq.com), and the recorded sign-off instructions use the same email for author and sign-off, so DCO-bot email-match checks would pass. Informational only.

## Independent verifications performed (not deferred to the freeze reviewer)

- `git log -3 --format=fuller`, `diff-tree` per commit, full-body sign-off grep, worktree `config user.*`, `branch -r`, `remote -v` (candidate worktree).
- `git diff base..HEAD` copyright-line grep (only 4 `+` lines, new files only); AMD notices confirmed intact on all 4 modified pre-existing headers.
- `git diff 29846fc4..e7ff6d75` = 4 files, +4/−4, placeholder→AIwork4me only (re-verified the manifest's P5→P5.1 claim).
- Own greps of root and `projects/miopen` CONTRIBUTING.md at the frozen base for DCO/CLA/sign-off terms; 30-commit develop-history sign-off scan.
- Read all four new files end-to-end for third-party provenance; grepped for AMD/LLVM/libc++ markers.
- Count sweep (`3 MIT`/`three`) across `docs/phase5/*.md` + `findings/phase5/*.json` with per-hit context adjudication; `FINAL_SUBMITTABLE` / readiness sweep across `docs/` + `findings/`; patch-file sign-off grep.
- RCA git log sweep for upstream contact; RCA remote check; git diff review of every Phase-5 file Phase 5.1 modified.

**Bottom line:** the candidate, commits, patches and manifest are procedurally clean on every DCO/submission-policy dimension audited; one documentation-consistency defect (C-MAJ-1) must be corrected before the provisional freeze is treated as final, and one staleness risk (C-MIN-1) should be annotated. Neither touches code, patch bytes, or the manifest's correctness.
