# Phase-2 Clean Controlled Environment (Gate 22)

Date: 2026-10-07. All commands and outputs archived under
`evidence/phase2/raw/environment/`.

## Goal

Reproduce Phase-1's failure with the SAME relevant versions in an
environment isolated from conda base's unrelated packages
(paddlex/paddleocr/omnidocbench/anaconda-cli/…), without upgrading any
component (ROCm 7.14.0 pinned by the brief).

## Why a curated clone rather than a fresh download

The exact wheels (`torch-2.12.0+rocm7.14.0`,
`amd-torch-device-gfx1151-2.12.0+rocm7.14.0`, `rocm-sdk-*-7.14.0`, …)
are **not retrievable** from AMD's public indexes today:

| Index checked | Result |
|---|---|
| `https://stable.repo.amd.com/rocm/pytorch/whl-next/amd-torch-device-gfx1151/` | reachable (HTTP 200); newest = `2.14.0+rocm10.1.0`; `2.12.0` exists only as `+rocm10.0.0` — **no `+rocm7.14.0`** |
| `https://rocm.nightlies.amd.com/v2/gfx1151/` | reachable; torch nightlies top out at `2.9.1+rocm7.13.0a…` (Apr 2026) — **no `7.14.0`** |
| PyPI `amd-torch-device-gfx1151` / `rocm` | placeholders only (`0.1.0`) |
| Local pip cache (`pip cache list`) | only the 28 kB `rocm-7.14.0-py3-none-any.whl` meta-wheel; multi-GB payload wheels absent |
| Local disk sweep for `*rocm7.14*.whl` | none |

Downloading different versions is forbidden (Gate-22 brief: no silent
upgrade). Therefore the clean env is built as a **curated byte-identical
clone**: real Python interpreter (fresh conda install), plus a RECORD-exact
copy of the transitive dependency closure of the experiment roots from
base's site-packages. This preserves the native stack bit-for-bit
(verified by SHA256 below) while removing every unrelated Python package.

## Construction (every mutating command, in order)

```text
1. conda create -n yolo_amd python=3.13 --yes
   (previous "yolo_amd" contained ONLY conda-meta/ + etc/ — no Python,
   no packages; verified Gate 21. Nothing was deleted: conda create
   populated the existing empty env dir.)
   → evidence/phase2/raw/environment/gate22_conda_create.txt  (exit 0)

2. python gate22_copy_closure.py \
     --src  C:\Users\rocm\miniconda3\Lib\site-packages \
     --dst  C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages \
     --roots torch torchvision ultralytics ultralytics-thop ultralytics-platform \
             rocm rocm-bootstrap rocm-sdk-core rocm-sdk-libraries \
             rocm-sdk-device-gfx1151 amd-torch-device-gfx11 \
             amd-torch-device-gfx1151 amd-torchvision-device-gfx1151 \
     --exclude torchaudio
   (run with base python; copies per-distribution RECORD file lists)
   → gate22_closure_manifest.json  (45 dists, 27,180 files, 4.89 GB)
```

### Closure contents (45 distributions)

amd-torch-device-gfx11, amd-torch-device-gfx1151,
amd-torchvision-device-gfx1151, anyio, certifi, charset-normalizer,
contourpy, cycler, filelock, fonttools, fsspec, h11, httpcore, httpx,
idna, jinja2, kiwisolver, markupsafe, matplotlib, mpmath, networkx,
numpy, nvidia-ml-py, opencv-python, packaging, pillow, polars,
polars-runtime-32, psutil, pyyaml, requests, rocm, rocm-bootstrap,
rocm-sdk-core, rocm-sdk-device-gfx1151, rocm-sdk-libraries, setuptools,
sympy, torch, torchvision, typing-extensions, ultralytics,
ultralytics-platform, ultralytics-thop, urllib3.

`torchaudio` excluded (not needed by any experiment). Known gaps copied
verbatim from base (pre-existing, behavior-preserving): matplotlib's
`pyparsing` + `python-dateutil` are missing in base too
(`missing_in_source` in the manifest) — Phase-1 runs shared the same gap.

### Known isolation caveat — Windows per-user site-packages

`C:\Users\rocm\AppData\Roaming\Python\Python313\site-packages` appears on
`sys.path` of every CPython 3.13 on this machine and sits **before** the
env's own site-packages. It contains (at least) `onnxruntime`. All
Phase-2 experiment invocations therefore set **`PYTHONNOUSERSITE=1`** so
that ONLY the yolo_amd env can satisfy imports. Recorded in
`gate22_env_verify.txt`.

## Verification (evidence/phase2/raw/environment/gate22_env_verify.txt)

| Check | Result |
|---|---|
| Interpreter | `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe` ✓ |
| `assert "envs\yolo_amd" in sys.executable.lower()` | **OK** |
| torch import origin | `...\envs\yolo_amd\Lib\site-packages\torch` ✓ |
| torch / torchvision / ultralytics versions | 2.12.0+rocm7.14.0 / 0.27.0+rocm7.14.0 / 8.4.174 — identical to Phase-1 ✓ |
| `torch.version.hip` | 7.14.60850 ✓ |
| `torch.cuda.is_available()` / device | True / AMD Radeon 8060S ✓ |
| paddlex / paddle / paddleocr / omnidocbench / conda / anaconda_cli_base | **ABSENT** ✓ |
| onnxruntime (user-site leak) | present WITHOUT `PYTHONNOUSERSITE=1`; absent with it — all Phase-2 runs use the flag |
| `pip check` | exit 1 — in-clone complaints: `soundfile requires cffi` plus the two pre-existing matplotlib gaps (`pyparsing`, `python-dateutil`) noted above; the base-only pydantic/ruamel/paddlex conflicts do NOT exist here (row corrected per Gate-23 audit; that verify run itself was made without `PYTHONNOUSERSITE=1`) |

## Native-stack identity (gate22_dll_provenance.json)

| DLL | yolo_amd SHA256 (prefix) | Phase-1 base SHA256 (docs/ENVIRONMENT.md) | Match |
|---|---|---|---|
| MIOpen.dll | `74b4ee038803606e…` | `74b4ee038803606e…` | ✓ |
| hiprtc0714.dll | `c6159dd12714eed4…` | `c6159dd12714eed4…` | ✓ |
| amd_comgr.dll | `0a890dbdcd12e6a1…` | `0a890dbdcd12e6a1…` | ✓ |
| amdhip64_7.dll | `b4b4799f5deafb81…` | `b4b4799f5deafb81…` | ✓ |

A live torch process in yolo_amd loads 46 ROCm DLLs — all from the env's
own site-packages. The clean env's failing-path binaries are
**bit-identical** to the Phase-1 baseline.

## Standing invocation contract for Phase-2 experiments

```text
PYTHONNOUSERSITE=1  C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe  <script>
```

in a plain shell (no VS/MSVC environment injection) unless an experiment's
protocol explicitly states otherwise.

## Classification honesty

This is an isolated *clone*, not an independent fresh install. It
decisively tests P2-H1 (dirty-base causation) at the Python-package
level: every unrelated package absent. It cannot test "wheel-state
corruption" — that is covered instead by the SHA256 identity with the
Phase-1-validated binaries (which produced the failure) and Phase-1's
checksummed manifest.

## Post-construction completion (recorded)

First clean-env YOLO run surfaced that base satisfied `pyparsing` /
`python-dateutil` / `six` via the Windows **user-site** fallback (see
caveat above). Installed into yolo_amd from PyPI, pinned to base's
effective versions, recorded in
`evidence/phase2/raw/environment/gate22_pip_install_pyparsing.txt`:

```text
pip install pyparsing==3.3.2 python-dateutil==2.9.0.post0
→ Successfully installed six-1.17.0 pyparsing-3.3.2 python-dateutil-2.9.0.post0
```

These are pure-Python members of ultralytics' documented dependency
closure (via matplotlib); the install completes the clone rather than
altering the stack under test.
