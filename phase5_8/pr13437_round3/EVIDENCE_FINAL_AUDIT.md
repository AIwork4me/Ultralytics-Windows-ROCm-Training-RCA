# Final evidence-package audit — prepublication record

Date: 2026-10-17 (Asia/Shanghai). Implementation frozen at
`d4b574ac8a039f39976c5f9f4e18adcb074dc237`; initial evidence PR #12 HEAD
`b0a52dd14e58af39aecd5c67bd080aeeba43de45`.

## Repairs and retained findings

- The old manifest had 134 entries, including an invalid self-entry, for 135 tracked
  files. It covered 133 payload files and omitted `.gitattributes`. The corrected
  deterministic tool covers every tracked payload except the manifest itself.
- All original 135 paths are retained. No binary/cache/log pruning occurred. The sole
  changed original raw log is the disclosed same-length hostname redaction in YOLO.
- Source/binary records and original positive/negative/BN/kthvalue/FP32 smoke logs remain.
  The current compiler is recorded as AMD Clang 23.0.0git; five RTC compiles means three
  isolated and two ambient controls. Build rc=0 does not mean every GPU TU compiled offline.
- BatchNorm comparisons establish tolerance results and identical printed error summaries,
  with the biased running-variance reference explicitly limited; tensorwise identity is
  unproven. AMP precheck fails on all three libraries; AMP training PASS is not claimed.
- Ten retained A/B ELF `.text` pairs are equal. Three kthvalue variants can be re-extracted
  from committed cache snapshots. BN originating cache rows/options are absent; original
  A/B naming supplies weaker source association. No whole-program performance proof exists.
- Warm/cold timing is INCONCLUSIVE: negative event minima include a GPU-bound case and
  individual samples were not archived. Reported medians show no confirmed material
  regression, without certifying timing non-regression. No YOLO paired A/B exists.
- gfx942 has one established hang with duplicate ctest failure-output replay, not a
  demonstrated retry. Actual CI compile mode is unproven. LIKELY_INFRASTRUCTURE remains
  a hypothesis; matched develop-versus-PR testing is outstanding.
- Historical initial auditor mistakes are preserved with explicit superseding supplements.
  No dissent is hidden and no new GPU run is claimed.

## Verification and publication protocol

The standard-library manifest and ISA tools are included under `scripts/`. Reproduction
commands, required dependencies and machine-specific paths are documented in REPRODUCE.md.
API/audit records are normalized to LF; original run logs and source diff snapshots retain
their exact bytes. The package-local `raw/** -whitespace` rule only changes Git whitespace
diagnostics for preserved records; authored docs/tools remain checked. Agent D accepted
this policy and independently verified redaction scope and absence of credential patterns.

Before publication the final candidate must pass all of:

1. Two manifest generations with byte-identical output; exact tracked-file coverage,
   zero mismatches/missing/unexpected paths and no self-entry.
2. Independent Git blob and fresh-clone verification with core.autocrlf=true.
3. Independent retained-ELF/cache validation without mutating archived SQLite sidecars.
4. All local Markdown/script/raw paths present, all required external documentation links
   accessible. The external Math CI endpoint was not accessible directly; the report links
   the archived GitHub metadata and makes no executed-Math-test claim.
5. `git diff --check`, correct branch/remote, package-only delta, unchanged Phase 5.7.
6. Independent B/C/D final acceptance, refreshed evidence PR HEAD/checks/policies,
   normal push and ordinary merge with exact expected-head guard; no bypass.

This record states the review protocol rather than predicting a future GitHub merge.
Final exact commit, fresh-clone results, independent acceptances, published comment and
merge SHA are recorded in the separate `PR13437_MERGE_CLOSURE_HANDOFF.md` after execution,
avoiding a manifest/commit self-reference. Source audit A and semantic audit B recommend
freezing code. Retention audit C and security audit D recommend preserving artifacts.

## Upstream conditions remain separate

At the recorded snapshot seven workflows are ACTION_REQUIRED, not failed code tests and
not PASS; no formal APPROVED review exists. Nineteen review threads include eleven resolved
and eight addressed-but-unresolved threads. No thread was mass-resolved and no upstream
code/branch/workflow was modified. Maintainer approval, subsequent actual CI results and
final reviewer confirmation remain required. See CI_STATUS.md and REVIEW_THREAD_MATRIX.md.
