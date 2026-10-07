# Subagent A — Falsification Review (independent, challenge mode)

Reviewer: SUBAGENT A. Date: 2026-10-07. Mandate: try to PROVE the RCA
conclusion wrong. All file paths relative to repo root
`C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA\`
unless absolute. Live experiments were run read-only with
`C:\Users\rocm\miniconda3\python.exe`; temp scripts were written only to the
OS temp dir; nothing was installed or modified.

---

## Attacks attempted

### A1. "The pure repro doesn't really match the Ultralytics signature" (attack on LEVEL 1)

**Checked:** compared `evidence/raw/batchnorm/minimal.txt` (lines 9–19, 48)
field-by-field against `evidence/raw/ultralytics/train_gpu.txt`
(lines 50–60, 132).

| Signature field | minimal.txt | train_gpu.txt | Match |
|---|---|---|---|
| Kernel | `MIOpenBatchNormFwdTrainSpatial.cpp` | same (line 50) | exact |
| HIPRTC error | `HIPRTC_ERROR_COMPILATION (6)` | same (lines 9–10 vs 50–51) | exact |
| Missing header | `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` | same (line 15 vs 56) | exact |
| Target | `1 error generated when compiling for gfx1151.` | same (line 18 vs 59) | exact |
| Terminal exception | `RuntimeError: miopenStatusUnknownError` | same (line 48 vs 132) | exact |
| Build failure | `hipoc_program.cpp:299: Code object build failed` | same | exact |

The full include chain (`MIOpenBatchNormFwdTrainSpatial.cpp:8 →
batchnorm_functions.hpp:30 → configuration.hpp:34 → vector_types.hpp:8 →
miopen_type_traits.hpp:151`) is identical. Even the torch-level frames are
identical (`batchnorm.py:210`, `functional.py:2850`). Only differences: the
random comgr temp-dir names and timestamps — expected and irrelevant. Also
cross-checked `minimal_issue3956.txt` and `minimal_yololike.txt` (both
EXIT=1, same 5 fields, lines 9–19/48–49 of each).
**Result: attack FAILED — the signatures are identical.**

### A2. "AMP could still explain it" (H4)

**Checked:** `evidence/raw/ultralytics/train_gpu_amp_off.txt` —
- Line 2 command includes `amp=False`; line 4 args dump shows `amp=False`
  (and `device=0`), i.e. the override was actually in effect.
- The `AMP: running/checks passed` lines present in `train_gpu.txt:34–35`
  are ABSENT in the amp-off run — corroborates Ultralytics honored it.
- Failure at the identical code point (`conv.py:87` line 102,
  `batchnorm.py:210` line 110) with the identical 5-field signature
  (lines 48–58, 130) and `exit_code=1` (line 131).
**Result: attack FAILED — AMP falsified.**

### A3. "The dataset could explain it" (H3)

**Checked:** `scripts/02_batchnorm_minimal.py` uses only
`torch.randn(8,16,64,64, device="cuda")` — no dataset, no dataloader, no
checkpoint, no YOLO code (read the script; log confirms
`x shape = (8, 16, 64, 64) device = cuda:0`). Additionally, in the failing
Ultralytics run itself the COCO8 scans completed BEFORE the crash
(`train_gpu.txt:38,41` — "4 images, 0 backgrounds, 0 corrupt"), so data
loading was healthy even there.
**Result: attack FAILED.**

### A4. "Python 3.13 could explain it" (H8) — is the RCA honest about the limit?

**Checked:** `docs/HYPOTHESES.md` H8 status is "**Falsified (external
evidence), UNPROVEN locally**", Medium confidence, with the decisive
experiment column explicitly "none local (no second interpreter with ROCm
wheels available without installing)". `docs/RCA.md` §Falsified Hypotheses
lists only H1–H5/H12/H13 (all locally falsified) and separately warns
"Python-3.13 and gfx1151 specificity are falsified only by *external*
evidence from MIOpen #3956, not by local experiment". Verified the external
artifact: `evidence/raw/external/miopen_3956_issue.json` body contains
`Python version: 3.12.7`, `1 error generated when compiling for gfx1200.`,
`miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found`,
`ROCm version: 7.2.1`.
**Result: attack FAILED — the limit is disclosed everywhere the claim is
made (RCA, HYPOTHESES, phase1_conclusion.json).**

### A5. "Correlation vs causation in the Evidence Chain"

**Checked:** `docs/RCA.md` §Evidence Chain arrow by arrow.
- The compile emits exactly **one** error ("1 error generated"), and it is
  the unresolvable `#include <type_traits>` — a direct diagnostic-causal
  link, not an incidental co-occurring message.
- The chain contains a true **intervention**, not just covariation: matrix
  case E (`evidence/raw/batchnorm/matrix_results.json`, PASS exit 0)
  disables only the MIOpen/cuDNN-compat BN path and the failure disappears;
  case F (Conv2d through MIOpen) PASSES while every MIOpen BN kernel fails.
  Flip the suspected component → flip the outcome.
- The remaining causal gap (would supplying an STL make it compile?) is
  exactly the unclaimed LEVEL 3 / H10-vs-H11 boundary, explicitly open in
  RCA ("A HIPRTC-side default-include-path defect cannot yet be excluded").
**Result: attack FAILED — no unevidenced causal leap found.**

### A6. "CPU-training PASS doesn't really exonerate model/data/Ultralytics"

**Checked:** `evidence/raw/ultralytics/train_cpu.txt` — command line and
args dump show `device=cpu`; epoch completed
(`1/1 ... 100% ━━━ 1/1 1.2s/it`), validation ran
(`all 4 17 0.551 0.962 0.943 0.669`), `1 epochs completed`,
weights saved, `EXIT=0`. CPU training exercises the same Ultralytics
trainer logic, same model, same COCO8 data, same loss/validation. It cannot
exonerate GPU-specific host code — but that residual is closed by A1 (the
identical failure without any Ultralytics in the process at all).
**Result: attack FAILED — control is valid, and its residual is covered by
the pure repro.**

### A7. Claim-ledger spot check (≥8 claims; I did 17)

All against the cited files; SHA256 integrity of the four pivotal logs
(`minimal.txt`, `train_gpu.txt`, `train_cpu.txt`, `matrix_results.json`)
matches `evidence/SHA256SUMS.txt` exactly (recomputed live).

| ID | Verdict | Notes |
|---|---|---|
| C005 | supported | `gemm.txt`: PASS, mean=0.015937, EXIT=0 |
| C006 | supported | `predict.txt`: "4 persons, 1 bus", exit_code=0, "(fused)" summary present |
| C007 | supported | `train_gpu.txt`: FAIL, signature at cited lines 50–132, exit_code=1 |
| C008 | supported | `train_cpu.txt`: EXIT=0, epoch+val complete |
| C009 | supported | `minimal.txt`: identical 5-field signature, EXIT=1 |
| C010 | supported | both variant logs same signature, EXIT=1 |
| C011 | supported | `matrix_results.json` case C = InferSpatial, case D = TrainSpatial, same type_traits chain |
| C012 | supported | case E PASS exit 0 |
| C013 | supported | cases F, H PASS (F first-call compile 16.76 s — consistent with MIOpen conv JIT working) |
| C014 | supported | see A2 |
| C015 | supported | `minimal_bn_miopen_logging.txt:29–31`: `miopenBatchNormForwardTrainingActivation_V2`, `bn_mode = 1`, NCHW strides |
| C018 | claim TRUE, citation weak | no raw grep artifact archived; I re-ran the grep myself (see S1) |
| C019 | claim TRUE, wording broader than cited file | see S2 |
| C020 | supported | probe file matches; clang triple lives in ENVIRONMENT.md (see S3) |
| C021 | supported | `dll_provenance.json/.txt`: MIOpen.dll (`_rocm_sdk_libraries\bin`), hiprtc0714.dll / amd_comgr.dll / amdhip64_7.dll (`_rocm_sdk_core\bin`), SHA256s recorded |
| C022/C024 | supported | 3956 JSON verified field-for-field (gfx1200, 3.12.7, 7.2.1, same header/line) |

**Result: 14/17 fully supported by their cited files; 3 have citation
hygiene problems (S1–S3 below) — none factually wrong.**

### A8. "LEVEL 2 is secretly LEVEL 3"

**Checked:** `docs/RCA.md` "What Phase 1 Does NOT Claim" (six explicit
non-claims), Root Cause Statement (evidence-qualified), Confidence section,
and `findings/phase1_conclusion.json` (`"rca_depth_reached": "LEVEL 2"`,
H10/H11 "plausible ... unproven"). The Root Cause Statement asserts only
physical facts (machine has no C++ STL — C019/C020; wheels ship none —
C019) plus the mechanism; it never asserts which layer owes the fix, never
proposes VS install as the fix, never claims gfx/Python specificity.
**Result: attack FAILED — no LEVEL 3 leak.**

### A9. Live reproducibility NOW

**Ran:** `C:/Users/rocm/miniconda3/python.exe scripts/02_batchnorm_minimal.py minimal`
(2026-10-07, this session). Result: **EXIT=1**, all five signature fields
present (TrainSpatial kernel; HIPRTC_ERROR_COMPILATION (6);
miopen_type_traits.hpp:151:10 'type_traits' not found; gfx1151;
RuntimeError: miopenStatusUnknownError; hipoc_program.cpp:299). The defect
is reproducible today, in a fresh process, unchanged.
**Result: attack FAILED — reproduces.**

### A10. Scope probe: is it really BatchNorm2d-only? (new experiment)

**Ran** (temp script in OS temp dir, GPU): `BatchNorm1d` with 2D input
(8,16) → **PASS**; `BatchNorm1d` with 3D input (8,16,64) → **FAIL** with
`MIOpenBatchNormFwdTrainSpatial.cpp` + full type_traits signature;
`BatchNorm3d` (2,8,16,16,16) → **FAIL** same TrainSpatial signature;
`GroupNorm` → **PASS**; `BatchNorm2d.eval()` → **FAIL** with
`MIOpenBatchNormFwdInferSpatial.cpp` (matches matrix case C).
**Result: mechanism claim STRENGTHENED (failure is specific to the MIOpen
spatial-BN code path, independent of module class; non-MIOpen norms pass),
but the docs' op scope is understated — see S4.**

---

## Attacks that SURVIVE (RCA conclusion still stands)

- **A1 signature identity** — pure repro and Ultralytics failures are the
  same failure, field for field. Ultralytics is not required.
- **A2 AMP** — `amp=False` verifiably in effect; identical failure.
- **A3 dataset** — no dataset involved in the minimal repro.
- **A4 Python 3.13 / gfx1151** — external-only status disclosed at every
  mention; #3956 artifact genuinely contains 3.12.7 / gfx1200.
- **A5 causality** — single-error compiler diagnostic + a real intervention
  (case E bypass flips the outcome; case F shows MIOpen conv JIT works);
  the untested sufficiency step is explicitly unclaimed.
- **A6 CPU control** — clean PASS (EXIT=0, epoch+val complete).
- **A8 LEVEL 2 boundary** — no ownership/fix claims leak in RCA, README, or
  `phase1_conclusion.json`.
- **A9 live repro** — fails identically right now.

## Attacks that SUCCEED (problems found — all minor / documentation-level)

- **S1 (C018 citation gap).** `docs/CLAIMS_AND_EVIDENCE.md` C018's evidence
  is "grep of `MIOpen.dll` (see `docs/RCA.md` §Evidence chain)" — **no raw
  grep output is archived anywhere in `evidence/raw/`**, unlike every other
  claim. The claim itself is TRUE: I independently ran
  `grep -ao` on `C:\Users\rocm\miniconda3\Lib\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll`
  and found `MIOpenBatchNormFwdTrainSpatial.cpp`,
  `MIOpenBatchNormFwdInferSpatial.cpp`, `MIOpenBatchNormFwdTrainPerAct.cpp`,
  `MIOpenBatchNormFwdInferPerAct.cpp`, `#include <type_traits>`,
  `#include <utility>`, `#include <limits>`. Fix: archive the grep output as
  a raw evidence file and cite it.
- **S2 (C019 wording vs probe coverage).** C019 claims "no `type_traits`
  anywhere under `_rocm_sdk_libraries` **or `_rocm_sdk_core`**", but the
  cited `evidence/raw/toolchain/toolchain_probe.txt` line 36 records a sweep
  of `_rocm_sdk_libraries` only. I re-searched both trees and the entire
  `site-packages`, all of `miniconda3` (incl. `Library\include`), and Git's
  `/usr/include` — zero hits; the claim is true, the cited artifact is
  narrower than the sentence. Fix: widen the probe or adjust wording.
- **S3 (C020 counter-evidence citation).** The `amdclang.exe` target triple
  `x86_64-pc-windows-msvc` appears in C020's counter-evidence column and in
  `docs/RCA.md:20,102`/`docs/EXPERIMENT_MATRIX.md:44`, but the cited
  `toolchain_probe.txt` never mentions amdclang; the triple is recorded only
  in `docs/ENVIRONMENT.md:138`. I verified it live
  (`amdclang.exe --version` → `Target: x86_64-pc-windows-msvc`). Fix: put
  the `--version` output into a raw probe file and cite that.
- **S4 (affected-op scope understated).** `docs/RCA.md:11` ("any
  `torch.nn.BatchNorm2d` executed through the MIOpen backend") and
  `README.md:36–38` ("every `nn.BatchNorm2d` on the GPU goes through
  MIOpen...") are too narrow: my A10 experiment shows `BatchNorm1d` with 3D
  input and `BatchNorm3d` ALSO route to the failing
  `MIOpenBatchNormFwdTrainSpatial.cpp` compile and fail identically
  (`BatchNorm1d` with 2D input and `GroupNorm` pass). The conclusion is
  unaffected — it further confirms MIOpen-spatial-BN-path specificity —
  but the docs should say "all spatial BatchNorm ops reaching MIOpen (BN1d
  with 3D input, BN2d, BN3d, train and eval modes)". This also matters for
  Phase 2: any workaround scoped to "replace BN2d" must cover BN1d/3D and
  BN3d too.
- **S5 (minor overstatement).** `findings/phase1_conclusion.json`
  `type_traits_status: "physically absent machine-wide"` is stronger than
  the probe's "no `type_traits` found anywhere **searched**" (C020's own,
  correct wording) — no whole-disk scan was performed. My independent
  searches found none either, so the substance holds; use C020's phrasing.

## Verdict

**The RCA conclusion SURVIVES falsification.** Every load-bearing element
was independently re-verified against the raw logs, hash-checked, and where
possible re-run live: the minimal pure-PyTorch reproduction fails right now
with the identical five-field signature (kernel name, HIPRTC_ERROR_COMPILATION,
'type_traits' at miopen_type_traits.hpp:151, gfx1151, miopenStatusUnknownError);
AMP-off, no-dataset, CPU-PASS, MIOpen-bypass-PASS and conv-PASS controls all
hold as documented; the Python-3.13/gfx1151 external-evidence limit is
honestly labeled; and no claim of fix-ownership (LEVEL 3) leaks anywhere.
LEVEL 2 (mechanism isolated) is justified.

**What must change (none conclusion-breaking):** archive a raw C018 grep
artifact (S1); align C019/C020 wording and citations with what the probe
files actually contain (S2, S3); widen the stated affected-op scope to
BN1d(3D-input)/BN3d per experiment A10 (S4); soften "machine-wide" in
`phase1_conclusion.json` (S5). My A10 results are also a free extra data
point for Phase 2 scoping.
