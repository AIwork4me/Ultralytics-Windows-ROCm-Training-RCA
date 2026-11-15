# P16 CONTRIBUTION RULES AUDIT (2026-11-15)

Per mission §3: the actual current upstream rules were read before touching any upstream repository. Sources fetched live (not from memory).

## 1. ultralytics/ultralytics

Fetched from `main` via API on 2026-11-15:

- `CONTRIBUTING.md` — fork→branch→PR workflow; first-time contributors ≤~50 lines; feature PRs require a pre-approved issue; **CLA signing required** (comment "I have read the CLA Document and I sign the CLA"); Google-style docstrings with types in parentheses; AGPL-3.0.
- `AGENTS.md` (CLAUDE.md is a symlink to it) — the operative review contract:
  - **Core principles**: "Less is more"; action hierarchy **Delete > Replace > Add**; solve at the owner; search/reuse first; no new dependencies without justification; **tests are out of scope by default** — "only an uncovered, high-risk regression path justifies minimal new test code"; delete mock tests including monkeypatched platform/device state.
  - **Review gate**: reviewer decides whether deleting/changing existing code would have fixed it — blocking finding if so. >50 net added non-doc lines (counting tests, net of deletions) = high-barrier exception requiring strong justification.
  - **Git discipline**: NEVER push to `main`; NEVER force-push; work in worktrees; fix accepted contributions **on their existing PR branches** — no replacement/follow-up PRs; preserve Ultralytics Actions bot commits; `git pull --rebase` before pushing.
  - **PR workflow**: wait for automated review + auto-format commit, pull, address every finding, batch fixes into one commit; merge only the cold-reviewed live head with terminal-green checks and zero unresolved threads.
  - **Commands**: `ruff format . && ruff check --fix .`; tests run with `--export-env base`; docstring rules only enforced with `--extend-select F,I,D,UP,RUF,FA` (docs.yml); prettier `npx prettier@3.9.9` for markdown; doctest-modules caveat; test assets hit the network — run from scratch cwd with dedicated weights dir.
- `docs/AGENTS.md` — required for any docs change (not touched in P16 code work; consulted before the eventual user-guide submission).
- License: AGPL-3.0 (header convention per-file; bot adds headers automatically).
- CI conventions verified empirically: check-runs on both PR heads show 15 success / 6 skipped (GPU, AMD_GPU, NVIDIA_Jetson, RaspberryPi, SlowTests, Conda) / 0 failed; Codecov patch coverage reported per PR; CLA check ✅.

### Application to P16 work

| Rule | P16 compliance mechanism |
|------|--------------------------|
| Fix on existing PR branch | Both PRs updated in place (`checkamp-guard-probe-exceptions`, `checkamp-gpu-gates-hip-fallback`); no replacement PRs |
| No force-push | #27203 correction pushed as a new commit; when git transport was down, pushed via Git Data API with `force=false` (server rejects non-fast-forward) |
| Worktrees | Separate worktrees `upstream_ultralytics` (27198) and `p16_pr27203` (27203) |
| Tests out of scope by default | #27203 adds exactly one focused no-mock test for the uncovered high-risk fallback path (the PR's core behavior); no test-percentage gaming |
| No mock-heavy tests | New test asserts path-invariant outcomes on the real host with and without NVML; only hardware-conditional legs, no monkeypatched device state |
| ≥50-line justification | #27203 net ≈ +53 including tests (≈10 docstrings/comments) — three owner files, each change minimal; justification stated in the PR description |
| Ruff/docstring conventions | `ruff format` clean; `ruff check --select E4,E7,E9,F` clean; Google docstrings kept |
| CLA | Already signed for both PRs (bot ✅) |
| AI disclosure | Retained in both PR descriptions |

## 2. ROCm/rocm-libraries

Not code-modified in P16 (issue #15862 is a tracker, not a code change). Its contribution rules were consulted in earlier phases for PR #13437 (merged). Any new P16 activity is limited to commenting on the existing tracker issue with release-handoff evidence — no new PRs opened there.

## 3. PR-description hygiene per mission §4.1

- #27198 description rewritten at P16 start: stale 6-test list replaced with the live 2-test suite; the FDB-warning ⇢ `hipErrorInvalidKernelFile` causal implication removed (P13 refuted the causal chain: probe passed 128/128 layers while the warning persisted — co-occurring symptoms, not cause and effect); raw error evidence retained.
- #27203 description rewritten after the P16 correction: stale "Net: +13/−8, no new tests" line replaced; truthful-criteria semantics documented.
