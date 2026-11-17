# P15 FINAL GO / NO-GO (2026-11-15)

## Six gates — final verdicts

| Gate | Verdict | Exact evidence |
|---|---|---|
| G1 Engineering correctness (two Windows Radeon classes, full workflow) | **NOT_MET** — one class complete, second class blocked | gfx1151: full P15 leg set PASS on official released stack (amp-probe / smokes w0-w4 / 30-epoch 0.4927→0.5980 / hard-kill @ epoch≥20 → new-process resume to 30 / best.pt val 0.5949 / reload+inference) — `P15_WINDOWS_RELIABILITY_REPORT.md`, `P15_AMP_NUMERICAL_ACCEPTANCE.md`. Class B (gfx1100/RDNA3): **BLOCKED_HARDWARE** — `P15_TWO_ARCH_WINDOWS_GPU_MATRIX.md` |
| G2 Upstream maintained | **IN_PROGRESS** | #13437 merged (ROCm side, `f0a5d266`). Ultralytics: #27198 open @ `fc72b4e` (CI 15 pass/6 skip/0 fail; bot MEDIUM answered; **no human review**), #27203 open @ `a1be048` (new P15 defect fix; bot MEDIUM answered). Neither merged; no PyPI release contains either change |
| G3 Official distribution | **BLOCKED_RELEASE** (re-confirmed live) | both channels unchanged; `rocm_sdk_libraries-10.1.0` byte-identical to pre-fix build (Last-Modified 2026-10-05 < merge 2026-10-19) — `P15_OFFICIAL_RELEASE_CLOSURE.md` |
| G4 First-time developer success | **NOT_MET** | issue #14 zero comments (live-verified); kit + manifest ready; **BLOCKED_INDEPENDENT_USER_TEST** |
| G5 NVIDIA UX parity | **NOT_RUN** — comparator hardware missing | contract frozen pre-registration + `nvidia_reference.py` prepared; all NVIDIA legs `NOT_RUN`; **NVIDIA_COMPARISON_BLOCKED_HARDWARE**; no parity claimed anywhere |
| G6 Regression readiness | **IN_PROGRESS / BLOCKED_RUNNER** | Layer A: minimal regression protection submitted upstream (both PRs carry it); Layer B: physical GPU CI **BLOCKED_RUNNER** with a complete local-runner contract producing identical artifacts (`P15_GPU_CI_AND_RELEASE_REGRESSION.md`) |

## Overall P15 verdict

**PROJECT SUCCESS = NOT_MET** (unchanged external state), with all unblocked work completed and two new validated upstream contributions opened:

1. **PR #27198** (`fc72b4e`): check_amp probe-exception guard, test suite minimized to current AGENTS.md (6 mock-heavy tests → 2 focused contracts).
2. **PR #27203** (`a1be048`): NVIDIA-only GPU detection gates fixed (nvidia-smi count fallback + NVML-less selection fallback) — proven SKIP→PASS on real gfx1151 hardware; prerequisite for any AMD GPU CI ever running upstream.

## Carried owner actions (unchanged or new)

| Owner | Action |
|---|---|
| AMD release chain | publish post-#13437 Windows wheel → GATE 3 re-verdict (full §5 checklist ready) |
| ultralytics maintainers | human review of #27198 / #27203 → GATE 2 |
| RCA owner | rotate ZHIPU_API_KEY (history still contains blobs); restart machine to clear ENV B ghosts; optional history rewrite |
| project owner | provide second GPU class + NVIDIA Windows comparator |
| independent developer | accept invitation (#14 open) or respond to future public call |
