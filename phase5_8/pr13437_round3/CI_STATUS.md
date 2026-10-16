# Upstream CI status — Agent D

Read-only GitHub API snapshot on 2026-10-17 Asia/Shanghai; exact HEAD `d4b574ac8a039f39976c5f9f4e18adcb074dc237`. Raw responses: `provenance/closure/live/upstream_runs.json` and `provenance/closure/live/upstream_pr.json`. No current-head code-test failure is recorded; seven workflows have not received execution approval. This does not certify a green test suite.

| Workflow | Run ID / link | Status | Conclusion / classification | Required next action |
|---|---|---|---|---|
| pre-commit | [38927815775](https://github.com/ROCm/rocm-libraries/actions/runs/38927815775) | completed | action_required / ACTION_REQUIRED | Upstream maintainer approve run; then read actual hook results |
| clang-tidy | [38927815624](https://github.com/ROCm/rocm-libraries/actions/runs/38927815624) | completed | action_required / ACTION_REQUIRED | Maintainer approve run |
| Component CI | [38927815554](https://github.com/ROCm/rocm-libraries/actions/runs/38927815554) | completed | action_required / ACTION_REQUIRED | Maintainer approve run; inspect actual target results |
| TheRock CI | [38927815732](https://github.com/ROCm/rocm-libraries/actions/runs/38927815732) | completed | action_required / ACTION_REQUIRED | Maintainer approve run |
| TheRock Multi-Arch CI | [38927818117](https://github.com/ROCm/rocm-libraries/actions/runs/38927818117) | completed | action_required / ACTION_REQUIRED | Maintainer approve run; watch gfx942 results without presuming cause |
| TheRock Multi-Arch CI ASAN | [38927818341](https://github.com/ROCm/rocm-libraries/actions/runs/38927818341) | completed | action_required / ACTION_REQUIRED | Maintainer approve run |
| gfx1250 HW hipBLASLt + TensileLite Tests | [38927816071](https://github.com/ROCm/rocm-libraries/actions/runs/38927816071) | completed | action_required / ACTION_REQUIRED | Maintainer approve run |
| Libraries PR Bot (latest) | [38927872837](https://github.com/ROCm/rocm-libraries/actions/runs/38927872837) | completed | success / SUCCESS | Policy bot result only; does not prove tests executed |
| Libraries PR Bot (earlier) | [38927811864](https://github.com/ROCm/rocm-libraries/actions/runs/38927811864) | completed | cancelled / CANCELLED | Superseded by later policy bot run |
| Auto Label PR | [38927811882](https://github.com/ROCm/rocm-libraries/actions/runs/38927811882) | completed | success / SUCCESS | Metadata only |
| PR Base Freshness | [38927811472](https://github.com/ROCm/rocm-libraries/actions/runs/38927811472) | completed | success / SUCCESS | Freshness only |

Math CI Summary reports a SUCCESS status context linking to [archived GitHub external-status metadata](provenance/closure/live/upstream_pr.json); no actual Math test execution is established by this status. A freshness success and policy-bot success cannot stand in for Component CI or TheRock tests. Local pre-commit evidence cannot be called GitHub Actions pre-commit success.

No current-head CI approval request has yet been posted. One combined evidence/review update can include the approval request; see GITHUB_PREFLIGHT_AUDIT.md. Account AIwork4me lacks upstream push/maintain permission. Do not attempt approval, reruns, empty commits, workflow changes, or upstream merge.

Evidence PR #12 has zero current-head workflow runs and an empty statusCheckRollup at initial b0a52dd; its branch policy requires no checks. Re-query these facts after the evidence-only push.

Executive upstream state: **WAITING_FOR_CI_APPROVAL**. Formal review state: **REVIEW_REQUIRED**, no APPROVED review. Review threads: **19 total / 11 resolved / 8 unresolved**.
