# Gate 21 — The real `yolo_amd` environment

Date: 2026-10-07. All facts below are backed by raw logs in
`evidence/phase2/raw/environment/`.

## Verdict: **ENV-B** — `yolo_amd` is activatable but Python resolves to conda base.

(The Phase-1 observation "interpreter is base python" is CONFIRMED still
true; the brief's caveat that `(yolo_amd)` prompt alone proves nothing is
also confirmed — the prompt is active yet cosmetic.)

## Evidence chain

| Probe | Result | Raw evidence |
|---|---|---|
| `conda env list` | `base`, `yolo_amd` both listed; neither active in probe shell | `gate21_shell_state.txt` |
| `envs\yolo_amd` directory contents | ONLY `conda-meta/` and `etc/` — **no `python.exe`, no `Lib/`, no packages**; `conda-meta/history` shows a single `conda create -n yolo_amd` transaction with zero installs | listing in `gate21_shell_state.txt` capture session; `ls` output recorded in session log |
| `envs\yolo_amd\python.exe` exists? | **NO** (`ls` → No such file or directory) | session log |
| Activated `(yolo_amd)` via `call conda activate yolo_amd` in cmd | `CONDA_DEFAULT_ENV=yolo_amd`, `CONDA_PREFIX=C:\Users\rocm\miniconda3\envs\yolo_amd` — activation succeeds | `gate21_activated_probe.txt` |
| `where python` inside activated shell | 1st hit `C:\Users\rocm\miniconda3\python.exe` (**base**), 2nd WindowsApps stub | `gate21_activated_probe.txt` |
| `where pip`, `where yolo` inside activated shell | `C:\Users\rocm\miniconda3\Scripts\{pip,yolo}.exe` (**base**) | `gate21_activated_probe.txt` |
| `sys.executable` under activated shell | `C:\Users\rocm\miniconda3\python.exe`; `sys.prefix` = base | `gate21_activated_probe.txt` |
| Package probe (torch/torchvision/ultralytics) | torch 2.12.0+rocm7.14.0, hip 7.14.60850, torchvision 0.27.0+rocm7.14.0, ultralytics 8.4.174, `cuda_available=True`, device AMD Radeon 8060S; all imported from `C:\Users\rocm\miniconda3\Lib\site-packages` (base) | `gate21_interpreter_probe.txt`, `gate21_activated_probe.txt` |
| pip freeze | identical relevant set to Phase 1 (`gate21_pip_freeze.txt`); same 3 pre-existing unrelated conflicts in `pip check` (pydantic/ruamel/paddlex) exit 1 | `gate21_pip_freeze.txt`, `gate21_pip_check.txt` |

## Classification (per Gate-21 taxonomy)

- ENV-A (real, populated, self-contained): **NO**
- ENV-B (active but Python resolves to base): **YES — this one**
- ENV-C (exists but empty/incomplete): the env *directory* itself is empty
  (no interpreter), but since activation succeeds and execution silently
  falls through to base, the operative classification is ENV-B.
- ENV-D (multiple installations leaking): no leakage *between conda envs*
  observed; there is exactly one populated Python environment (base).
  (A WindowsApps `python.exe` stub exists on PATH but never wins resolution
  while conda is on PATH.)

## Consequences for Phase 2

1. Every Phase-1 experiment necessarily ran in **base** — consistent with
   Phase-1 `docs/ENVIRONMENT.md`.
2. `(yolo_amd)` prompts in user transcripts are cosmetic; they do not
   indicate which interpreter executes.
3. Gate 22 must construct a genuinely isolated `yolo_amd` (real interpreter
   + isolated site-packages) before "clean-env reproduction" means anything.

**Gate status: PASS** (determination made with captured evidence; no
environment was modified during this gate).
