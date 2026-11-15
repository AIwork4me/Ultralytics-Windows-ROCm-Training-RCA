# P15.7 — Official Windows Documentation Readiness (2026-11-15)

Status: **PREPARED — submission deferred** until its compatibility claims have official-package evidence (mission §11 PR-timing rule).

## 1. Live upstream docs gap (verified 2026-11-15)

[docs.ultralytics.com/integrations/amd](https://docs.ultralytics.com/integrations/amd) today:

- Targets **Linux x86_64 only** ("This guide targets Linux x86_64 hosts with the AMD GPU kernel driver (amdgpu)…").
- MIGraphX EP: "published only as Linux x86_64 wheels… so **native Windows is not supported**" (scoped to the MIGraphX deployment path).
- **No documentation of native Windows PyTorch ROCm training** (no Windows wheel install, no MIOpen, no Windows driver compatibility, no Windows AMP/checkpoint/resume guidance). Windows DirectML is marked ❌ in its support table.
- Notably, the page's Linux install already uses the same `stable.repo.amd.com/rocm/whl-next/` index that also (undocumented) hosts Windows wheels — the ecosystem is converging, but no Windows statement exists.

## 2. Boundary honored

- The Linux/MIGraphX path and native Windows PyTorch training are **separate procedures**; no Windows MIGraphX claim is made anywhere.
- A public installation/compatibility statement must not overclaim an unreleased backend fix: today's official Windows wheels are **pre-#13437** (BLOCKED_RELEASE), so any docs saying "install and train on Windows Radeon" would be **false for no-STL robustness**. Submission therefore waits for GATE 3.

## 3. What is already prepared (content-complete, evidence-backed)

| Artifact | Role |
|---|---|
| `golden-path/WINDOWS_SETUP.md` | END-USER GOLDEN PATH: official drivers + official wheels + released ultralytics; GPU verification; standard train/val/predict; checkpoint reload; cross-process resume; common errors |
| `golden-path/requirements-lock.txt` + `acceptance_manifest.json` + schema | exact tested release versions, executable acceptance commands |
| `golden-path/verify_environment.py`, `train.py`, `validate.py`, `resume.py`, `verify_checkpoint.py` | the documented steps are literally executable scripts (P14 MODE B all-PASS on the official released stack) |
| `P13_GOLDEN_PATH_REPORT.md`, P15 results | verified behaviors + error-UX evidence |

DEVELOPMENT WORKFLOW (editable fork for upstream contributors) remains documented separately in the RCA repo and is never mixed into the end-user golden path.

## 4. Planned upstream docs PR (draft scope, NOT submitted)

Target owner: `docs/en/integrations/amd.md` (+ possibly a new `docs/en/guides/…windows-rocm` page — owner decision at submission time; macros/rules per `docs/AGENTS.md`):

1. Supported Windows versions / Radeon GPUs / driver compatibility (only what AMD's own release docs support at that time).
2. Python/PyTorch/ROCm wheel versions with **exact tested releases**.
3. GPU verification, standard CLI/API training, AMP behavior + limitations, validation, checkpoint save/reload, cross-process resume.
4. Common errors + verified recovery procedures; known unsupported configurations.
5. No private wheels, no source-built DLL replacement, no Linux-only commands, no accidental duplication of the Linux page's tables (macro owners).

Build validation at submission time: `uv pip install -e ".[dev]"`, `python docs/build_docs.py`, pinned prettier (`npx prettier@3.9.9 --tab-width 4 --print-width 120 --write` for `docs/**/*.md`), strict docstring selectors, and the `git diff --cached` check from `docs/AGENTS.md`.

## 5. What unblocks submission

GATE 3 (official Windows wheel containing MIOpen #13437) + re-run of the golden-path kit against that wheel. At that point the prepared content's claims become true for the ordinary installation path and the PR can be opened with evidence.
