# Upstream PR Readiness — Final (Gates F24–F27)

Date: 2026-10-08. Reviewed object: integrated `origin/main` at
`f553c49` (Windows handoff + Linux evidence + final integration).

## Bottom line

```text
readiness = READY_FOR_HUMAN_SUBMISSION_PREP
```

Not "MERGE READY" — only upstream maintainers decide merge readiness.
No upstream PR, issue, or comment has been created.

## Evidence state

| Claim | Status | Evidence |
|---|---|---|
| Windows UNPATCHED→FAIL / PATCHED→PASS (live no-MSVC A/B) | PROVEN | Windows Phase-3 gates (final_gate.md, phase3_conclusion.json) |
| Linux UNPATCHED→PASS / PATCHED→PASS (source-built A/B) | PROVEN | linux_conclusion.json, LINUX_VALIDATION_SUMMARY.md |
| Linux numerics bit-identical (max_abs 0.0) | PROVEN | numerics evidence, evidence/phase3/raw/linux/ |
| Kthvalue runtime UNPATCHED PASS → PATCHED PASS | PROVEN | KTHVALUE_RUNTIME_CLOSURE.md, evidence/phase3/raw/linux/kthvalue/ |
| Kthvalue adversarial falsification review | PASS | findings/phase3/linux/subagent_kthvalue_review.md |
| Patch bytes unmodified since validation | VERIFIED | blob SHA256 recomputation pre-merge, post-merge, post-push (F01/F04/F23) |
| Cross-platform closure | PASS | CROSS_PLATFORM_VALIDATION.md |
| No upstream/PR/issue/comment created | TRUE | all status fields false; nothing submitted |

## Final review panel (four fresh independent subagents on origin/main)

| Reviewer | Verdict | Key independent acts |
|---|---|---|
| A — MIOpen maintainer sim | **APPROVE** | git-am round-trip byte-identical; audit script re-run reproduces 104-entry census; gate truth-table re-derived |
| B — regression attacker | **NO REGRESSION FOUND** | 10 adversarial untested RTC TUs token-identical; real-hipRTC compiles of fp8/Getitem/RNN; BFP16 kthvalue runtime A/B PASS/PASS; MSVC-triple IR-level lowering proof |
| C — CI / portability | **NO LOCAL BLOCKER** | cross-HIP gate analysis (only HIP≥7+RTC arm changes); concrete J1–J7 CI matrix proposal |
| D — upstream submission | **APPROVE** | live upstream-reference verification (MIOpen#3956 open w/ exact signature); claim-discipline sweep |

Consolidated classification: `findings/phase3/final_readiness/FINDINGS.md`.
Zero BLOCKERs. Both MAJORs were outside the validated patch bytes
(proposal artifact + stale draft text) and are resolved. Technical
blockers: **none**.

## What remains (deliberately human / CI)

1. Human submission steps (DCO/author identity incl. removing the
   placeholder comment, commit regeneration + re-verification,
   copyright attribution, final PR text) —
   `docs/phase3/FINAL_SUBMISSION_CHECKLIST.md`.
2. Upstream CI follow-ups (cross-arch gfx94x/110x/120x legs, HIP 10.x
   leg, CI-test wiring fixes, audit ratchet) — these are appropriate
   upstream-CI validation, not local blockers; a single contributor
   machine cannot and should not own AMD's architecture matrix.

## Machine-readable verdict

`findings/phase3/final_readiness/PR_READINESS.json`.
