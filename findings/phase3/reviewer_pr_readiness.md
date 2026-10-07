# Phase-3 Gate 83 — Reviewer D (upstream PR reviewer simulation)

Date: 2026-10-07. Mandate: "Would you approve this PR as-is?"

## Verdict: REQUEST CHANGES (path to APPROVE-AS-DRAFT is short)

## Blockers

1. **No commit, no commit message, no DCO sign-off** — bare `git diff`
   output; DCO bot fails on first push.
2. **Three of five modified files are full-file rewrites from EOL churn**
   (radix 6 real lines / tensor_view 8 / CMakeLists 3) — bakes CRLF into
   an LF repo; destroys blame; gets closed unread.
3. **Linux regression runs do not exist** (self-declared merge
   precondition — held to the PR's own standard).

## Majors

4. **Copyright attribution wrong for an external contributor** (new files
   claim AMD copyright; the footer says independent RCA).
5. **Nothing CI-wireable ships in the patch** — canary harness is
   RCA-repo-only, Windows-path-defaulted, JSONL without expected-fail
   semantics; the negative control is precisely specified in prose but
   must land as a test in the MIOpen tree (compile-only, no GPU needed).
6. **radix.hpp comment overclaims** (numeric_limits references parse-time
   checked; only uninstantiated in practice).

## Minors

7. RCA jargon leaks into upstream artifacts (G57-7, "Gate 82", "Gate-54").
8. "Round-trip validated" has no archived artifact; "see Gate 71 record"
   dangles (no file).
9. Probe idioms inconsistent between wrappers and tensor_view.
10. Cosmetic churn inside "untouched" arms (blank lines/comments).
11. Scope-split opportunity: defect fix vs residual coverage as two
    commits (cherry-pickable).

## Nits

12. `canary_non_trivial` vocabulary in an upstream header.
13. "GPU-executing canaries verify every trait at runtime" slightly
    overstated (kernel verifies composite; static_asserts verify per-trait).

## What Linux CI must show (exactly)

(a) standard MIOpen suites (batchnorm/conv/pooling min) green on HIP>=7
with COLD kernel cache, A/B vs unpatched develop; (b) confirmation the
probe took the real-STL branch (successful RTC compile in logs); (c) the
no-STL compile-only test: patched exit 0 / unpatched 'type_traits' not
found; (d) if any HIP<7 lane exists, a legacy-shim-arm compile check
(reordering is truth-table-preserving but CI should prove it); (e) no
perf lane needed (host-preprocessor-only).

## Noted strengths

Availability-probe design correct (#7718 analysis right); wrapper
restructure preserves the truth table exactly; Windows A/B single-variable
with SHA-proven provenance; 104-entry audit committed/reusable/parameterized;
negative controls reproduce the field signature exactly.
