# P15.4 — Ultralytics PR #27198 Closure (2026-11-15)

Status: **IN_PROGRESS** (GATE 2 not yet met — awaiting human maintainer review, merge, and release).
PR: https://github.com/ultralytics/ultralytics/pull/27198 — state **open**, not merged.

## Live state at P15 start (verified via API, not memory)

- head `090e378` (4 commits, 2 files, +162/−7), `mergeable_state: blocked` (review gate), no `reviewDecision`.
- Review threads: exactly 2 — **UltralyticsAssistant** bot MEDIUM (2026-11-14T17:07:24Z: guard started after probe-model construction/transfer) + author fix reply (root cause → `3f6076c`, all probe stages guarded). **No human maintainer review exists.**
- Bot auto-format commit `124de39` preserved untouched.

## STEP A — owner and minimal solution (cold verdict)

`check_amp` is the owner of the probe and its boolean contract; `_setup_train` is not (other callers exist; trainer should not know probe internals). Pre-8.4.197 `check_amp` already owned an `except Exception → warn + return False` contract; PR #26967's redesign dropped it accidentally, which is exactly the regression class this PR repairs. The guard is therefore a **restored failure contract at the owner**, not a speculative guard over broken logic — Core Principle 1 compliant. The handler message states the truth (error is not necessarily AMP-specific; points to backend/runtime if FP32 fails identically). `KeyboardInterrupt`/`SystemExit` propagate. Alternatives rejected: propagate (crashes `train()` — regression vs 8.4.182), narrow exception types (backend error taxonomy is heterogeneous across HIP/CUDA/MPS), relocate to trainer (wrong owner).

## STEP B — expected behavior demonstrated

Carried evidence (unchanged `checks.py` bytes since `090e378`): healthy real accelerator → `True` (`test_cuda.py::test_amp`, gfx1151); injected backend failure during real probe → `False` + new truthful message (gfx1151 HIP, archived in P13/P14); CPU fault-injection suite → degrade semantics. Today's re-validation: minimized CPU suite **2/2 PASS** (`p14_mode_a_dev` env, py3.13); healthy-path control re-run on gfx1151 logged to `p15_upstream_audit/test_amp_gfx1151_control.log`. Repeated-invocation and OOM-at-transfer behaviors follow from the single handler and were covered by (now removed) duplicate tests; `check_amp` is stateless.

## STEP C — test minimization (executed today, commit `fc72b4e`)

Current AGENTS.md mandates: mock/monkeypatched device-state tests are deleted by default; tests are out of scope by default; >50 net non-doc lines need strong justification. The previous 144-line six-test file monkeypatched `torch.cuda.get_device_name`, `DetectionModel.__init__/.to/.forward`, `torch.rand`, and carried a `torch>=1.13` `OutOfMemoryError` compatibility list (a compatibility shim). Transfer/forward/repeat variants all exercise the **same** handler lines, so they test one contract three extra times. Shrink to **two tests covering the two distinct contracts**:

1. `test_check_amp_probe_exception_degrades_to_fp32` — probe raises → `False` + logged, no crash.
2. `test_check_amp_user_interruption_propagates` — `KeyboardInterrupt` is not swallowed.

Net test-file change: −79/+13 (65 lines). Healthy path stays covered by existing `tests/test_cuda.py::test_amp` on real accelerator CI (NVIDIA + AMD GPU runners). No correctness gate weakened: the regression-protection pair (degrade + interrupt) is retained, and the shrink is *justified by the demonstrated regression history* — #26967 silently removed this exact contract and nothing caught it.

PR net size after shrink: checks.py +18/−7 (guard) + test file 65 lines ⇒ below the 50-net-line barrier for the code change; the focused test file is defended by the #26967 regression precedent.

## STEP D — validation (today)

- `ruff format --check` → clean (2 files).
- `ruff check --extend-select F,I,D,UP,RUF,FA --target-version py38 --ignore BLE001,D100,D104,D203,D205,D212,D213,D401,D406,D407,D413,RUF001,RUF002,RUF012,S110` — **the exact docs.yml Ruff step** → All checks passed.
- Focused pytest `tests/test_check_amp_probe_exception.py` → **2 passed** (0.71s).
- `ultralytics/utils/checks.py` blob on upstream `main` = `bfad3c58cdb…` = the PR diff base ⇒ main has not touched `checks.py` since branching; no rebase conflict.
- PR-branch CI re-runs on `fc72b4e` (tracked in §STEP F).

## STEP E — existing-PR hygiene

- Pushed `fc72b4e` to the **existing** branch `checkamp-guard-probe-exceptions` (fast-forward, no force-push, bot commit preserved).
- Posted a self-review comment documenting the minimization rationale: [#issuecomment-6888323588](https://github.com/ultralytics/ultralytics/pull/27198#issuecomment-6888323588).
- No replacement PR created. CLA signed (owner). AI-assistance disclosure present in PR body.

## STEP F — real acceptance tracker

| Requirement | Status |
|---|---|
| Actual maintainer (human) review | ❌ none yet |
| Terminal-green CI on final head | ⏳ running on `fc72b4e` |
| Zero unresolved review threads | ✅ bot MEDIUM answered/fixed; no new threads |
| Merged state | ❌ open |
| Released Ultralytics package containing fix | ❌ not released |

**GATE 2 = IN_PROGRESS.** No claim of maintainer acceptance is made; green CI and bot comments are not human approval.
