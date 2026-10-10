# CI Status — ROCm/rocm-libraries PR #13437

Head SHA: `1cc73f1c1e7c3831a1eb334a483732178948fc66` · Base: `develop` @ `54b079ca`

## Snapshot 1 (minutes after creation)

| Check | Status | Elapsed |
|---|---|---|
| Base freshness | pending | 0 |
| labeler | pending | 0 |
| therock-pr-bot | pending | 0 |

Classification: 0 pass / 3 pending / 0 fail. Full matrix not yet dispatched.

## Snapshot 2

| Check | Status | Elapsed | Note |
|---|---|---|---|
| Base freshness | pass | 12s | base within 3 days of develop |
| base-freshness | pass | 0 | (same check, workflow-level row) |
| labeler | pass | 7s | |
| Math CI Summary | pass | 0 | external math-ci.amd.com webhook — "SKIPPED BY MATH-CI" is its normal dispatch semantics |
| therock-pr-bot | pending | — | dispatching |

Classification: 4 pass / 1 pending / 0 fail / 0 unexpected skip.

## Snapshot 3 (classification complete)

| Check / workflow | State | Classification |
|---|---|---|
| Base freshness / base-freshness | pass | PASS |
| labeler (Auto Label PR) | pass | PASS |
| Math CI Summary | pass | EXPECTED SKIP (external math-ci.amd.com webhook dispatch semantics) |
| therock-pr-bot (Libraries PR Bot) | in_progress | PENDING — bot handles PR intake; approval workflow below |
| TheRock CI · Component CI · TheRock Multi-Arch CI · Multi-Arch CI ASAN · clang-tidy · pre-commit | completed `action_required`, **zero jobs ran** | **EXPECTED SKIP (awaiting maintainer workflow approval)** — first-PR gating for a first-time external contributor; triggering_actor AIwork4me; GitHub requires an org maintainer to approve workflow execution. Not a source failure; the matrix dispatches after approval. |

Classification totals: 4 pass / 1 pending / 0 fail / 7 expected-skip (1 external-webhook + 6 approval-gated) / 0 unexpected skip / 0 blocking failures.

## Snapshot 4 — PR bot policy check (issue comment)

`therock-pr-bot` posted: **"✅ All Policy Checks Passed"** with:
- PR Description ✅ · Forbidden Files ✅ · Draft PR / Feature Flag / Code Coverage 🔜 To Be Enabled
- **⚠️ Unit Test warning**: the bot's filename heuristic expects `test_<name>.cpp` / `<name>_test.*` and did not match `test/hiprtc_selfcontained.cpp`. The regression test IS present and CTest-registered as target/test `test_hiprtc_selfcontained` (`projects/miopen/test/hiprtc_selfcontained.cpp` + `test/CMakeLists.txt`). Renaming the file would alter the frozen, triple-reviewed patch payload and invalidate the validated series — not done. Disclosed here and in the maintainer handoff.

Overall: policy gate green (warning-level only); no override requested.

## Expectations (pre-registered, see PR body "Regression Test Design")

- Linux CI legs: `test_hiprtc_selfcontained` expected **Skipped** (isolation probe exit 4) — this is the designed capability-skip, NOT a failure and NOT a no-STL pass.
- Any CI leg with ambient `CPATH`/`CPLUS_INCLUDE_PATH` (conda/LLVM images) also reports Skipped — expected.
- Genuine Windows no-STL coverage is supplied by this RCA's validation (upstream Windows CI may enable it separately).
- No claim of persistent background monitoring; this file records in-session snapshots.
