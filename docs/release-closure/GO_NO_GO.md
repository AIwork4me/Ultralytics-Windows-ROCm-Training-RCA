# GO / NO-GO — Final verdicts (2026-11-14)

## GO-A: Experimental Windows FP32 Training — **PASS (CONDITIONAL on ENV-B labeling)**

| Condition | Status |
|---|---|
| Native Windows AMD HIP (torch.version.hip=7.14.60850, real device, fwd/bwd/optimizer proven) | ✅ |
| Verified MIOpen (in-process loaded-DLL sha256 per leg) | ✅ |
| FP32 training lifecycle PASS | ✅ 7 tasks × T01–T15 (14/14 each) + 30-epoch long run |
| Reproducible installation/environment | ✅ pinned wheel command + lock records + probe tools |
| Explicit limitations | ✅ ENV B = **source-built patched MIOpen** (G0 BLOCKED_RELEASE — no official wheel with the fix exists yet); official wheel works for FP32 with host STL visible |

**Conditional nature**: the PASS describes the validated environment; on the *official wheel today*, spatial-BN training works only because host MSVC STL is present — the no-STL robustness comes exclusively from the fix, which ships in no official package yet.

## GO-B: Complete Windows Training — **CONDITIONAL PASS**

| Condition | Status |
|---|---|
| GO-A | ✅ |
| AMP verified | ✅ on official wheel (precheck PASS + real updates in 10-epoch probe); on ENV B the precheck can silently fall back (root-caused, cache-state dependent) — falls under known-limitations |
| Task matrix covered | ✅ all 7 tasks the current version supports |
| Checkpoint/resume works | ✅ T12 7/7 + integrity audits |
| Quality/stability evidence | ✅ 30-epoch public-dataset run, A/B with disclosed limits; **quality-vs-reference INCONCLUSIVE** (no Linux reference machine — BLOCKED_HARDWARE) |
| GPU families tested or claims narrowed | ✅ claims narrowed to gfx1151 only |

**Conditional nature**: AMP PASS is wheel-scoped (official); quality claims remain functional-level (no benchmark claim); non-tested families explicitly excluded.

## GO-C: Upstream Official-Ready — **NO-GO today / CONDITIONAL on external events**

| Condition | Status |
|---|---|
| G0 official release package confirmed | ❌ **BLOCKED_RELEASE** — no obtainable official package contains PR #13437 (2026-11-14) |
| G1/G2/G3/G4 gates satisfied | ✅ (on the two available environments, as scoped above) |
| Maintainer-friendly tests | ✅ drafts + executed supersets (PR-A/B/C/D + MIOpen issue draft) |
| CI strategy + execution evidence | ⚠️ strategy documented; GPU-CI execution requires self-hosted runner (Owner Action Required) |
| Documentation matches supported scope | ✅ conditional wording enforced (verifier pattern-scan) |
| No unsupported claims | ✅ enforced (184-check verifier) |

**Path to GO-C**: (1) an official Windows wheel built from a post-merge MIOpen lands (re-run G0 §4 checklist + G1/G2 against it) → (2) owner approves upstream submissions → (3) GPU CI runner provisioned. GO-C is *blocked on external events + human approvals*, not on unknowns.

## One-line summary

**The engineering is done and evidenced; the release channel and the human approvals are the remaining gates.** A Windows developer still cannot get the fixed MIOpen from any official wheel today — that is the single decisive blocker (BLOCKED_RELEASE), and until it clears, "official support" language is forbidden everywhere in this repo (machine-checked).
