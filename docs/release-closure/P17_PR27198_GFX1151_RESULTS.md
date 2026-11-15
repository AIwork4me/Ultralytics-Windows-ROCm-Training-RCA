# P17 — PR #27198 Real-Hardware Validation on Windows Radeon 8060S (gfx1151)

Mission: P17 | Date: 2026-11-15 | Operator: ZCode agent session (user-directed)
Machine: Windows 11 build 26200, AMD Radeon(TM) 8060S Graphics (gfx1151, gfx115128), driver 32.0.22032.6002
Stack: Python 3.13.16, torch 2.12.0+rocm7.14.1 (HIP 7.14.60850), MIOpen.dll 3.6.2 from official wheel companions (`_rocm_sdk_libraries`), SHA256 ed7c67a909307b211bbda260eeda7f6bce17cc7d097b6b1f74f8270456e6179a
Environment provenance: `P17_ENVIRONMENT_PROVENANCE.json` (frozen at mission start)

## Frozen sources

| PR | Branch tip validated | Full SHA |
|---|---|---|
| #27198 | checkamp-guard-probe-exceptions @ GitHub head (API-confirmed 2026-11-15) | `e5ac8593db60880b92b3e3cbd2e11ee3a7344034` |

Worktree: `C:\Users\rocm\Desktop\YOLO_AMD\p17_pr27198` (detached HEAD, clean `git status --porcelain`).
Import path verified per process: `ultralytics.__file__` resolves into the worktree (PYTHONPATH-prepended; pip 26 editable finder is appended after PathFinder and is shadowed by the base-env 8.4.182 install — documented in provenance).

Branch-ancestry audit vs P16 head fc72b4e: fast-forward only (`git merge-base --is-ancestor fc72b4e e5ac8593` = yes). New commits reviewed before running (required by mission §0):

- `9fafbd2` "Align AMP probe diagnostics and test scope with upstream policy" — deletes `tests/test_check_amp_probe_exception.py` (78 lines, 2 mock-heavy tests) per AGENTS.md anti-mock policy.
- `467754f` "Auto-format by https://ultralytics.com/actions"
- `e5ac859` "Limit AMP probe recovery to runtime failures" — **`except Exception` → `except RuntimeError`**, docstring extended ("Numerical mismatches disable AMP; probe exceptions also disable AMP as a precaution, without establishing that the GPU backend can execute FP32 training successfully."), log message retains the "not necessarily AMP-specific" disclaimer and adds "if FP32 training also fails with the same error, the problem is your GPU backend/runtime rather than AMP."

## A1 — Real healthy-path check_amp (PHYSICAL_GPU)

Script `a1_check_amp_healthy.py`, log `a1_log.txt`, machine result `a1_result.json`.

```
model = YOLO("yolo26n.yaml").model.to("cuda:0")
result = check_amp(model)
```

- device = `cuda:0`, HIP runtime identity: torch 2.12.0+rocm7.14.1 / HIP 7.14.60850
- **result = True** (bool), per-layer Conv2d+Attention AMP↔FP32 agreement all close
- elapsed 12.37 s (includes model build), log line `AMP: checks passed ✅`
- **A1 = PASS** (real GPU evidence, taken while the HIP runtime was still healthy)

## A2 — Real AMP training through the official interface

Command (yolo CLI from the worktree, 8.4.213):

```
yolo detect train model=C:/Users/rocm/Desktop/YOLO_AMD/yolo26n.pt data=coco8.yaml epochs=1 imgsz=64 device=0 amp=True workers=0
```

Three runs were executed; together they cover both sides of the PR's behavioral contract:

| Run | MIOpen cache state | AMP precheck | Training outcome | Params changed vs yolo26n.pt | Exit |
|---|---|---|---|---|---|
| try1 (`a2_train_log.txt`) | stale user cache (later found to be **held locked by 6 unkillable HIP zombie processes**; `taskkill /F` ineffective; `mv` of `~/.miopen` → Permission denied) | True ("checks passed ✅") | **CRASHED** at first train batch: `torch.AcceleratorError: CUDA error: invalid kernel file` (hipErrorInvalidKernelFile) inside MIOpen conv path | n/a | non-zero (exception) |
| try2 (`a2_train_log_try2.txt`, fresh cache dirs via `MIOPEN_USER_DB_PATH`/`MIOPEN_CUSTOM_CACHE_DIR`) | fresh | **AcceleratorError raised in probe → caught by the PR's `except RuntimeError` handler → AMP disabled with truthful log** | **FP32 fallback training completed** 1 epoch, results saved, checkpoint written | **241/366** | 0 |
| try3 (`a2_train_log_try2.txt`-pattern, warm cache) | warm | same as try2 (probe AcceleratorError caught, FP32 fallback) | FP32 fallback training completed, `runs/detect/train-3` saved | 241/366 | 0 |

Key evidence obtained from try2/try3: **the PR's core repair fired on a real, uninjected physical GPU fault** — `AcceleratorError` (a `RuntimeError` subclass on this torch build, measured, see A3) was caught, logged truthfully, training proceeded in FP32 and completed with real optimizer updates (241/366 parameter tensors differ from the pretrained checkpoint; `epoch=-1` and absent optimizer state in `last.pt` are the normal `strip_optimizer` final-save behavior). No silent CPU fallback: `GPU_mem 0.221G` column present, device=cuda:0 throughout.

**A2 verdict = PASS_WITH_ENVIRONMENT_NOTES**: the official-interface training completed with real optimizer updates and checkpoint (twice). A run with AMP precheck True *and* completion in the same run was blocked mid-mission by a HIP runtime state degradation (see RCA below); this closure item is listed in the final report as re-openable after a machine reboot.

Root-cause chain established during A2 (evidence in `evidence/p17/`):

1. Six zombie python processes (P13/P15-era `inner.py` / `p132_checkamp_real.py`) have been running 1 CPU core each for ~16 h; they hold locks on `C:\Users\rocm\.miopen` (SQLite ukdb WAL) — proven by `mv` Permission denied while every other file in the home dir is movable.
2. try1's training triggered a MIOpen kernel find against that locked/degraded cache → bad kernel selection/compilation → `hipErrorInvalidKernelFile` at conv kernel load. `MIOpen: Error [EvaluateInvokers] ... failed condition: elapsed <= 0` also observed (solver timing corrupted under the CPU burn load).
3. Redirecting MIOpen user DB + kernel cache to fresh directories (`MIOPEN_USER_DB_PATH`, `MIOPEN_CUSTOM_CACHE_DIR` — both verified as supported by scanning env-var strings out of the loaded MIOpen.dll) removed the lock interaction; try2/try3 then completed FP32.
4. After repeated kernel-load crashes the HIP runtime state degraded further: SDPA flash/efficient backends (aotriton) then fail launch with `AcceleratorError: invalid argument` in **every new process** (driver-layer state, not process state), while MATH backend and MIOpen conv paths work. This makes the AMP probe itself hit the new `except RuntimeError` handler in try2/try3 — again exactly the behavior this PR is designed for.

## A3 — RuntimeError capture boundary

### A3.1 Actual exception inheritance measured on this stack (PHYSICAL fact)

```
torch.AcceleratorError MRO:  AcceleratorError → RuntimeError → Exception → BaseException
torch.cuda.OutOfMemoryError MRO: OutOfMemoryError → RuntimeError → Exception → BaseException
OutOfMemoryError is subclass of RuntimeError: True
AcceleratorError is subclass of RuntimeError: True
OOME is subclass of AcceleratorError: False
KeyboardInterrupt is subclass of Exception: False
SystemExit is subclass of Exception: False
```

### A3.2 Controlled injection at the probe boundary (CONTROL_FLOW_INJECTION, not physical)

Script `a3_a4_injection.py`, result `a3_a4_result.json`. Fault injected via `DetectionModel.__init__` replacement (same technique the PR's own (now deleted) tests used); **no MIOpen DLL, no driver state, no install was damaged**.

| Injected exception | Caught | check_amp returns | Log truthfulness |
|---|---|---|---|
| RuntimeError("simulated backend failure...") | yes | False | includes exception type + original message, "not necessarily AMP-specific" disclaimer, no FP32-health guarantee; does **not** claim numerical anomaly |
| torch.cuda.OutOfMemoryError("simulated OOM") | yes | False | same |
| torch.AcceleratorError("simulated accelerator fault") | yes | False | same |

**A3 = PASS.** All three lines in the table are marked CONTROL_FLOW_INJECTION in the result JSON. A2's try2/try3 additionally prove the same handler on **PHYSICAL_GPU_RUNTIME_FAILURE** (uninjected).

## A4 — Non-RuntimeError must propagate

Same injection harness (`a3_a4_result.json`, CONTROL_FLOW_INJECTION):

| Injected | Propagated out of check_amp |
|---|---|
| ValueError | yes (`ValueError`) |
| TypeError | yes (`TypeError`) |
| KeyboardInterrupt | yes (`KeyboardInterrupt`) — user interruption never swallowed |
| SystemExit | yes (`SystemExit`) |

**A4 = PASS.**

## A5 — Real AMP-specific error vs FP32-continues

- A real AMP-*numerical* anomaly cannot be safely reproduced on this healthy-AMP GPU (A1 shows agreement on every checked layer): **NOT_REPRODUCED_SAFE_TO_INJECT**.
- However the *intent* of A5 — "a real fault must disable AMP while FP32 continues" — was demonstrated physically and uninjected: try2/try3 probe failures (real AcceleratorError) → AMP disabled → FP32 training completed with finite losses and real updates (241/366 params changed).

## A6 — Existing upstream tests on the #27198 tree

`pytest tests/test_cuda.py::test_checks tests/test_cuda.py::test_amp -v -s` (pytest 9.2.0, isolated install):

- `test_checks` **FAILED**: `assert torch.cuda.is_available() == CUDA_IS_AVAILABLE` → `True == False`. Root cause measured directly: on the #27198 tree, `checks.cuda_device_count()` is the NVIDIA-only implementation (`nvidia-smi` query; returns 0 when nvidia-smi is absent), so `checks.cuda_is_available()` = False on this AMD host while torch reports a live HIP device. This is precisely the defect PR #27203 repairs; it pre-exists on the #27198 branch base and is **not** introduced by #27198.
- `test_amp` **SKIPPED** (`No CUDA devices available` — DEVICES computed from the same NVIDIA-only gate). Per mission §3-A6, the SKIP is expected on the #27198 tree and does not count against it; the direct real-GPU `check_amp` evidence is retained in A1/A2.
- Note: the branch's own dedicated probe tests were removed upstream in `9fafbd2` (AGENTS.md alignment); no other check_amp-specific test exists on this tree.

## Quality gates (P17.4 cross-reference)

- `ruff format --check ultralytics/utils/checks.py` → clean.
- `ruff check` / `ruff check --extend-select F,I,D,UP,RUF,FA` (repo pyproject config): PR-branch errors ≤ main-baseline errors (10/11 vs 12/13 measured with identical config); **zero new errors introduced**.
- AGENTS.md cold review: single-purpose try/except at the actual owner (checks.py), no compatibility shims, no new dependencies, mock-heavy test file **deleted** rather than maintained, diff minimal (1 source file + 1 test deletion for the merged state of the branch).

## Verdict

```
SOURCE_QUALITY_PASS              (ruff + AGENTS cold audit; no new lint issues; no owner violations)
GFX1151_PHYSICAL_VALIDATION_PASS (A1 real check_amp=True; A2 real training completed twice with
                                  real optimizer updates; A3/A4 boundary correct on CONTROL_FLOW_
                                  INJECTION and on uninjected PHYSICAL_GPU_RUNTIME_FAILURE)
AMP_TRUE_RUN_BLOCKED_ENV         (one run with AMP precheck True + completion in the same run is
                                  pending machine reboot; HIP driver-layer degradation after
                                  repeated kernel-load crashes + 6 unkillable zombie processes)
MULTI_GPU_NOT_RUN / NVIDIA_NOT_RUN (single GPU host; no NVIDIA hardware — outside PR scope anyway)
```

Raw evidence: `evidence/p17/a1_check_amp_healthy.py`, `a1_log.txt`, `a1_result.json`, `a2_train_log.txt`, `a2_train_log_try2.txt`, `a2_train_log_try3.txt`, `a3_a4_injection.py`, `a3_a4_result.json`, `modules_toolhelp.txt` (loaded-module enumeration proving MIOpen.dll provenance), `P17_ENVIRONMENT_PROVENANCE.json`.
