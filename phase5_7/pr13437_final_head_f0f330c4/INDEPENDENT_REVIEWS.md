# Independent Reviews — Gates A / B / C

Three independent subagent audits were run against the actual trees, logs,
and binaries (no self-attestation). Each auditor recomputed hashes and
grep-verified raw logs rather than trusting the package prose. Gate A/B ran
against the assembled package; every finding was then corrected in the same
round; A and B re-verified their findings' resolutions, and Gate C reviewed
the final package from a maintainer's perspective.

## Gate A — Evidence & Provenance Auditor

**First pass verdict: PASS** (chain sound; documentation gaps to fix).

| # | Severity | Finding | Resolution |
|---|---|---|---|
| A1 | MAJOR | Kthvalue l6 doc claimed fresh compiles/30 launches; the l6 log actually showed 3 cache hits + 27 launches (compiles happened in the unlogged plain run) | **Fixed**: kthvalue rerun with `USERPROFILE` redirected to an empty home → fresh kernel DB, 3 visible `Unable to load binary`→`SaveBinary` compiles + 27 launches (`raw/kthvalue/E_kthvalue_patched_l6_isolated.log`); docs corrected (KTHVALUE_VALIDATION.md, VALIDATION_MATRIX.md); cache-hit log retained and labeled as such |
| A2 | MINOR | D/F wheel-swap hash transcript printed to unarchived stdout | **Fixed for D**: v2 rerun with `tee`'d transcript archived (`raw/batchnorm/swap_transcript_v2.log`). F swap-window hashes remain console-only, compensated by archived v2 transcript protocol, in-process module-path lines, `__FILE__` `C:/w56/…` diagnostics in the F log, and the auditors' independent re-verification of current pristine wheel state |
| A3 | MINOR | D log byte-identical to the pre-squash R2 D log (deterministic script → no fresh-run discriminator) | **Fixed**: v2 run adds UTC banner lines (`D_RUN_STARTED/ENDED_UTC`); byte-identity disclosed in BATCHNORM_VALIDATION.md as expected seeded determinism |
| A4 | MINOR | README referenced then-missing SHA256SUMS.txt / INDEPENDENT_REVIEWS.md | **Fixed**: INDEPENDENT_REVIEWS.md created with the audit records; SHA256SUMS.txt generated as the final pre-commit step over the finished content |
| A5 | NIT | F-log redaction also normalized EOLs (76 CRs dropped by first attempt) | **Fixed**: redaction redone byte-preserving; final file verified `cmp`-identical to the reference substitution (8 bare-LF lines gained trailing CR from the tool I/O layer; disclosed in YOLO26N_VALIDATION.md) |
| A6 | NIT | Failed configure attempts' logs overwritten | **Disclosed**: accurate five-attempt failure sequence recorded in BUILD_PROVENANCE.json (`configure_attempts_note`); only the successful configure log is archived |
| A7 | NIT | C leg executed before the patched build | No action needed (C depends on the baseline tree, not `C:\bfin`); noted by auditor as non-issue |

Independent verifications by Gate A (all held): recomputed SHA256 of all
binaries + wheel; worktree cleanliness at both SHAs; blob-identity of the
control test file (raw git blob hash identical); cache labels
(`3.6.2.f0f330c4` / `3.6.2.b8cf0e7b`, zero `-dirty`/`e4b9174a` occurrences
in package raw/); nonce batches distinct from R2; timeline coherence
(configure → build → hashes → B → E → D → F → restore); prefetch tarball
hashes vs `ThirdParty.cmake` URL_HASH; configure flags vs CMakeCache.

## Gate B — HIPRTC Regression Auditor

**First pass verdict: FAIL** — solely because of finding B1 (same root as
A1); "the package becomes acceptable once finding 1 is corrected".

| # | Severity | Finding | Resolution |
|---|---|---|---|
| B1 | MAJOR | kthvalue l6 evidence: cache-served execution presented as fresh compilation; launch count 30 vs actual 27 | **Fixed** as A1 (isolated-DB rerun shows 3 genuine compiles; count corrected to 27; audit-trail note added to KTHVALUE_VALIDATION.md) |
| B2 | MINOR | Relink/swap/clean-tree attestations referenced unarchived transcripts | **Fixed**: relink command inlined in NEGATIVE_CONTROL.md; git-status captures archived (`raw/provenance/`); D v2 swap transcript archived; remaining console-only items explicitly marked in SOURCE_PROVENANCE.md with compensating controls |
| B3 | MINOR | Dangling README/doc references (SHA256SUMS, INDEPENDENT_REVIEWS) | **Fixed**: INDEPENDENT_REVIEWS.md exists with the audit records; SHA256SUMS.txt generated as the final pre-commit step |
| B4 | NIT | Garbled "57-iteration-second" phrasing in YOLO26N_VALIDATION.md | **Fixed** ("a single 1-iteration batch step at 22.8 s + 2.6 s validation") |
| B5 | NIT | Probe kernel name shorthand (program vs symbol) | **Fixed** (P1 row now names both) |

Gate B's substantive validations (all passed): B log's 5 fresh nonce'd
compiles with correct `-nostdinc` polarity on isolation legs and its absence
on ambient legs; both self-contained launches; probe-pair semantics with the
cross-check that leg C excludes fake-polarity worlds; negative control
failing at final-file line 147 with the exact original diagnostic while
probes and ambient leg prove harness soundness; nonce uniqueness across all
runs incl. R2; D numerics to the digit + script-verified CPU-reference
methodology; F epoch/AMP/absence checks; commit parentage, diffstat, and
radix.hpp premise re-verified from the actual diff.

## Gate C — Upstream Reviewer Simulation (averinevg perspective)

Ran on the corrected package, README-first, spot-checking every leg's raw
log against the prose. Six findings, none blocking:

| # | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | MINOR | README "Boundaries" pointed to `phase5_6` records — dead pointer on `main` (that phase lives on the unmerged `phase5.6/maintainer-review-r1` branch) | **Fixed**: pointer now names the branch explicitly and states it appears on `main` once merged |
| C2 | LOW | `SHA256SUMS.txt` referenced but not yet generated; repo-root README not yet linking the package | **By design**: manifest generated as the last step before the publication commit (covering final content incl. the redacted F log); root-README status section added in the same commit |
| C3 | NIT | INDEPENDENT_REVIEWS.md initially pre-recorded a Gate C verdict placeholder before the audit ran | **Fixed**: this file now records only the actual audit outcomes (auditor's note that a pre-written verdict "could have disagreed" is acknowledged; the published verdict below is the auditor's real one) |
| C4 | NIT | Leg F swap-window hashes console-only | Accepted as disclosed residual risk (compensating controls verified by the auditor) |
| C5 | NIT | B/E exit-code claims rest on gtest `[ PASSED ]` summaries rather than archived `exit=` echoes | Accepted (gtest PASSED deterministically implies exit 0; not load-bearing) |
| C6 | positive | "Disclosures are unusually honest" — R2 quarantine, build deviations, AMP attribution, bounded YOLO claim, CI status all verified | — |

Auditor's maintainer verdict (quoted): *"this package gives me exactly what I
need in the first screen — a pinned HEAD SHA, a one-line verdict per leg,
and a provenance chain I can spot-check, and every spot-check I ran …
matched the prose. The negative control is real and diagnostic, the
historical pre-squash logs are correctly excluded rather than recycled,
deviations and console-only gaps are disclosed rather than papered over …
I'd approve the CI workflows on this PR on the strength of this package
plus my own reading of the diff."*

**GATE C VERDICT: PASS**

---

### Re-verification (post-fix, same Gate A/B auditors)

- **Gate A re-check**: A1/A2/A3/A5/A6 **RESOLVED** (verified against the
  new raw artifacts, incl. md5 comparisons and the isolated-home DB on
  disk); A4 PARTIALLY — `INDEPENDENT_REVIEWS.md` delivered, `SHA256SUMS.txt`
  pending generation at commit time (known open item). Two new NITs, both
  fixed: the F-log redaction disclosure contained a false mechanical detail
  (no CRs were actually gained; the file is `cmp`-identical to the pure
  hostname substitution — the disclosure now states exactly that), and the
  stale "both runs" heading in KTHVALUE_VALIDATION.md. Chain remains intact;
  B/C/E-plain/build logs byte-unchanged across both audits.
- **Gate B re-check**: B1 **RESOLVED** ("The compile-freshness evidence that
  was missing now exists and says what the docs claim" — 3 compiles + 27
  launches verified line-by-line, D-v2 banner provably inside the swap
  window); B2/B4/B5 **RESOLVED**; B3 PARTIALLY for the same pending
  `SHA256SUMS.txt`. No regressions. **Final: PASS.**
- **Publication precondition**: `SHA256SUMS.txt` must exist in the
  publication commit covering the final content — done (generated
  immediately before commit, after all file edits above).
