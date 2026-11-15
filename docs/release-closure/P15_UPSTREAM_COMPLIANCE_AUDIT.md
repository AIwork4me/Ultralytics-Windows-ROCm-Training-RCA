# P15.2 — Upstream Compliance Audit (2026-11-15)

Scope: rules actually read **today** from upstream `main` (SHA `d0cfceaf`, 8.4.213) before any P15 code/doc change, and their application to the two P15 upstream actions (PR #27198 update; new PR #27203).

## 1. Sources read (current versions, fetched 2026-11-15)

| Source | Key binding content confirmed |
|---|---|
| `AGENTS.md` (root) | Delete > Replace > Add; solve at owner; no try/except masking; no monkeypatched device-state tests; >50 net non-doc lines = high barrier; NEVER push main; NEVER force-push; worktree workflow; fix on existing PR; review the live diff |
| `CONTRIBUTING.md` | PR process, CLA requirement, AGPL-3.0, Google docstrings |
| `docs/AGENTS.md` | docs ownership, macros owners, `build_reference.py`/`build_docs.py` flow, `git diff --cached` warning, pinned prettier |
| `pyproject.toml` `[tool.ruff]` | line 120, py38 target, google pydocstyle convention |
| `.github/workflows/docs.yml` | exact Ruff selector/ignore list (F,I,D,UP,RUF,FA minus BLE001,D100,D104,D203,D205,D212,D213,D401,D406,D407,D413,RUF001,RUF002,RUF012,S110) — reproduced locally |
| `tests/` layout + `tests/test_python.py` | existing coverage ownership (no `tests/AGENTS.md` exists) |
| `LICENSE` | AGPL-3.0 (unchanged; headers on files) |

Raw copies archived: `p15_upstream_audit/` on the workstation (outside repo history), latest blobs verified via `gh api`.

## 2. Mission §2 rule matrix → P15 application

| # | Rule | Application in P15 | Verdict |
|---|---|---|---|
| A | Delete > Replace > Add | PR #27198 test file **shrunk** −79/+13 instead of extended; #27203 adds fallbacks only where deletion impossible (nvidia-smi/NVML genuinely absent on AMD) | PASS |
| B | Fix at actual owner | probe guard → `check_amp` (owner of probe contract); nvidia-smi count → `checks.cuda_device_count`; NVML-less selection → `GPUInfo.select_idle_gpu`; no workaround placed in Ultralytics for MIOpen/HIPRTC (that defect stays with ROCm) | PASS |
| C | No speculative guards/shims | #27198 guard restores a *pre-existing* (pre-8.4.197) failure contract, not new masking; **removed** the `torch>=1.13` OutOfMemoryError compat shim in fc72b4e | PASS |
| D | Search & reuse first | checked `tests/` ownership before adding test file (no CPU-runnable owner exists; `test_rocm.py` is MIGraphX-specific); reused `test_cuda.py::test_amp` as healthy control | PASS |
| E | Prefer changing existing code | both PRs modify existing files only; zero new files in #27203 | PASS |
| F | New deps/args need justification | none added in either PR | PASS |
| G | Tests only where high-risk gap | minimized #27198 tests to the 2 distinct contracts; #27203 relies on existing `test_select_device` + before/after real-hardware evidence | PASS |
| H | No mock/monkeypatch device-state tests | #27198 test count reduced 6→2; remaining 2 are the minimum needed because the fault path is unreachable on healthy CI hardware (documented in-file); no new mock tests added in #27203 | PASS-with-justification |
| I | >50 net non-doc lines barrier | #27198 after shrink: checks.py +18/−7 (net +11) + 65-line test file — justified by the #26967 demonstrated-regression precedent (this exact contract already regressed silently once); #27203 net +5 code | PASS |
| J | Never push upstream main | pushes went to fork branches only | PASS |
| K | Never force-push | verified remote tip before every push (`ls-remote`); fast-forward only | PASS |
| L | Worktree workflow | `C:\wp15` (PR-branch work), `C:\wp15b` (#27203 from upstream main); primary checkouts untouched | PASS |
| M | Fix on existing PR, no replacement PRs | #27198 got `fc72b4e` on its existing branch; the *new* defect (GPU gates) got its own PR #27203 — new defect ≠ review repair of #27198 | PASS |
| N | Preserve bot/maintainer commits | `124de39` (auto-format) intact in #27198 history; remote tip verified before push | PASS |
| O | Review the live diff | full diffs read from API/local worktree before every decision (not from summaries) | PASS |
| P | docs/AGENTS.md when public API changes | no public API/docs changes in either PR; not applicable | N/A |
| Q | Current repo test/format commands | used repo pyproject + docs.yml exact selectors; focused pytest per AGENTS.md commands | PASS |
| R | No upstream merge | neither PR merged by us; merge remains maintainer action | PASS |

## 3. Non-Ultralytics repositories touched in P15

- **ROCm/rocm-libraries**: read-only today. #15862 not re-commented (no new material finding — anti-spam rule from mission §5 honored; last state = P14 comment 6887740468). No duplicate fix of merged #13437 submitted.
- No PyTorch/AMD-docs submissions in P15 (no new defect owned there).

## 4. License / CLA / disclosure

- AGPL-3.0 respected; files carry upstream headers; no new files added.
- CLA: signed by owner (PR #27198 CLA check green in P13/P14).
- AI-assistance disclosure present in both PR bodies.

## 5. Verdict

**COMPLIANT** — 17 PASS + 1 PASS-with-justification (H: two remaining CPU fault-injection tests are the minimal, documented way to protect a contract that already silently regressed once; both state their rationale in-file) + 1 N/A (P).
