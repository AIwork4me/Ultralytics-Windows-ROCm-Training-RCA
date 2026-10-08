# Gate B11 — Final Three-Reviewer Panel (W7900-PHASE52-BRIDGE-R1)

Three fresh-context subagents, each with an independent challenge list.

## REVIEWER A — Source and supply-chain integrity: **PASS**

0 BLOCKERS / 0 MAJORS / 0 MINORS. NITs: (1) main rocm-libraries checkout
is space-pruned (pre-existing blob:none state, index+HEAD intact; METHOD B
is index-only so unaffected); (2) HEX40/HEX64 alphabets duplicate
(cosmetic); positive corroboration: patch `From <sha>` headers match
`ordered_commits` exactly. Chain of custody (evidence commit → manifest →
patch bytes → reconstructed tree) independently reproduced end-to-end,
including METHOD B write-tree == 605d0d21... in the reviewer's own
worktree.

## REVIEWER B — ROCm/HIPRTC toolchain: **PASS**

0 BLOCKERS / 0 MAJORS / 0 MINORS. gfx1100 provenance, two-stack
contamination discipline, B07 dynamic re-run (22 objects, zero
/opt/rocm), B06 matrices reproduced line-identically in both
environments, classification honesty confirmed (zero Linux full-no-STL
claims repo-wide; embedded-builtins mechanism verified via strings),
spoof guard + patch-0003 isolation probe confirmed, harness link-time
independence + both libMIOpen sha256s verified. NITs: W7900D marketing
name (folded into the conclusion's environment record); B07 log leg
annotation (sha printed in-stream); b06 axpy cosmetic (documented).

## REVIEWER C — MIOpen upstream maintainer: **PASS**

0 BLOCKERS / 0 MAJORS. All 7 hard challenges reproduced (manifest identity
via consumer; same-base discipline incl. CMAKE_HOME_DIRECTORY proof; two
distinct baselines + driver bind; harness run on the frozen leg with full
dispatch/RTC evidence; cache isolation + stale refusal; patch scope
exactly 10 files with matching blob SHAs; no premature PASS anywhere).
MINORs (all doc-only, ALL RESOLVED post-panel):
- M-1 leg-a script mode targets the historical prefix → runbook now has a
  Leg A re-materialization block + explicit warning in
  prepare_validation_legs.sh leg_a();
- M-2 no failure/abort protocol → runbook now has a mandatory STOP
  protocol (preserve verbatim, no flag-changing retries);
- M-3 build-flag identity asserted not recorded → runbook now requires a
  saved CMakeCache identity diff between legs.
NITs N-1..N-4 (cache isolation for ctest, patched-leg driver bind,
environment refresh before the final run, optional tensor_view smoke)
also folded into the runbook.
Maintainer's note: the write-tree identity gate, in-stream dladdr
provenance, zero-init outputs, and the honest Linux negative-mode
expectation with anti-spoofing prohibition are exactly the disciplines
demanded of an upstream submission.

## Gate B10 second-pass audit: **PASS**

Independent false-PASS/bypass auditor (10 attacks + source audit + matrix
re-run): no false-PASS achievable; PASS-with-failures structurally
impossible (verdict derives from the same failures list that is rendered
to stdout AND json-out); TOCTOU swap after a PASS run fails on re-check
(dirty checkout + blob equality); frozen evidence untouched. Two
informational notes (symlinked --rca-root aliasing is content-neutral;
explicit --expect-manifest-sha256 '' relaxation exists by design for
adversarial tests and never applies to frozen operation).

## Resolution status

No BLOCKER or MAJOR findings existed. All justified MINOR/NIT items were
resolved (runbook updates, script warning, environment naming). No gate
re-runs were required by any finding (doc-only changes plus script
comment; the consumer and matrix were re-validated after the last
consumer change in B10).
