# Gate 23 — Independent Subagent Audit (Clean-Env Reproduction)

Date: 2026-10-07. Reviewer: independent adversarial auditor (challenge
mode). Target: `findings/phase2/clean_env_result.md` (Gate 23) and its
supporting construction record `docs/PHASE2_CLEAN_ENVIRONMENT.md`
(Gates 21–22). Mandate: try to FALSIFY the Gate-23 conclusion that the
clean `yolo_amd` env reproduces the Phase-1 failure field-for-field and
that P2-H1 (dirty base environment causes the failure) is falsified.

Method: read all 8 raw logs in `evidence/phase2/raw/clean_env/` and
diffed them against their Phase-1 counterparts
(`evidence/raw/batchnorm/minimal*.txt`, `matrix.txt`,
`evidence/raw/ultralytics/train_gpu.txt`, `gpu-control/gemm.txt`,
`conv/conv_control.txt`) with a normalization script substituting only
the random comgr temp-dir name and the site-packages root; verified the
native-stack SHA256 identity from the two provenance JSONs (all 10 DLLs,
not just the 4 the doc claims); audited the Gate-21/22 environment
evidence; inspected the MIOpen user kernel DB evidence
(`evidence/raw/miopen/user_kernel_db_listing.txt`, the captured
`batchnorm…3_5_2_cd957402.udb.txt.lock`); and checked git state
(`git ls-files --eol`, commit `dc18b65`, `.gitattributes`,
`evidence/manifest.json` / `SHA256SUMS.txt` coverage).

---

## 1. Raw-log verification — do the logs show what the result matrix claims?

| Log | Claimed | Actually in log | Verdict |
|---|---|---|---|
| `A_gemm.txt` | GEMM control PASS | 4096² fp32 `cuda:0`, `PHASE1_GEMM: PASS`, isfinite=True, 0.167 s | **VERIFIED** |
| `B_conv.txt` | Conv control PASS | `(8,32,64,64)`, mean=0.008730, `CONV_CONTROL: PASS`, 0.03 s | **VERIFIED** (warm-cache caveat, §4.4) |
| `C_bn_minimal_train.txt` | FAIL, identical to Phase-1 minimal | Full chain present: `MIOpenBatchNormFwdTrainSpatial.cpp` → `miopen_type_traits.hpp:151:10 fatal error: 'type_traits' file not found` → `HIPRTC_ERROR_COMPILATION (6)` → `miopenStatusUnknownError`; torch frames at module.py:1778/1789, batchnorm.py:210, functional.py:2850 | **VERIFIED** |
| `C_bn_issue3956.txt` | FAIL, identical | Same chain, shape (20,100,35,45) | **VERIFIED** |
| `C_bn_yololike.txt` | FAIL, identical | Same chain, shape (16,16,320,320) | **VERIFIED** |
| `D_bn_eval.txt` | FAIL, FwdInferSpatial variant | `MIOpenBatchNormFwdInferSpatial.cpp` via `bnorm_spatial_activation_functions.hpp:32` → configuration.hpp:34 → vector_types.hpp:8 → miopen_type_traits.hpp:151 — matches Phase-1 matrix case C | **VERIFIED** |
| `E_bn_cudnn_off.txt` | PASS, native BN | `gpu bn train cudnn.disabled ok mean=-0.000000` (Phase-1 matrix E: `mean=0.000000` — sign formatting only) | **VERIFIED** |
| `F_yolo_train.txt` | FAIL, identical full chain, exit 1 | Header `### captured 2026-10-07T13:18:26+08:00`; `Ultralytics 8.4.174 Python-3.13.16 torch-2.12.0+rocm7.14.0 CUDA:0 (AMD Radeon(TM) 8060S Graphics, 80065MiB)`; `device=0` in args dump; failure after "Closing dataloader mosaic" at first BN (`conv.py:87 self.bn`); `RuntimeError: miopenStatusUnknownError`; `exit_code=1` | **VERIFIED** |

**Quantified signature identity.** After substituting only the random
comgr temp-dir token and the site-packages root, the normalized diff of
clean-env vs Phase-1 is **0 lines for all three C cases** (46 vs 46
lines each). `F_yolo_train.txt` matches the canonical
`evidence/normalized/training_failure_signature.txt` on **12/12 key
fields**: kernel name + HIPRTC (6), `<type_traits>` fatal at
miopen_type_traits.hpp:151:10, include chain .cpp:8 →
batchnorm_functions.hpp:30 → configuration.hpp:34 → vector_types.hpp:8,
`gfx1151` target line, `hipoc_program.cpp:299` build provenance,
`RuntimeError: miopenStatusUnknownError`, torch/ultralytics traceback
line numbers (trainer.py:546, conv.py:87, batchnorm.py:210,
functional.py:2850), lifecycle point, and `device=0`. "Field-for-field"
is literally true, not rhetorical.

Legitimate non-matching fields (all expected, none diagnostic): comgr
temp dir (random per compile), site-packages root (the variable under
test), `Python-3.13.16` vs `3.13.13` (§4.1), entry frames (`<string>`
vs `yolo.exe`/runpy — python -c vs CLI), `name=train-7` vs `train-3`
(run-dir increment).

**Native-stack identity is stronger than claimed.** The doc's table
compares 4 DLLs; I diffed all 10 records in
`gate22_dll_provenance.json` vs Phase-1's
`evidence/raw/environment/dll_provenance.json`: **10/10 SHA256-identical**
(MIOpen, MIOpenCKGroupedConv_gfx1151, amd_comgr, amdhip64_7,
hiprtc0714, hiprtc-builtins0714, miopen_plugin, rocm-openblas,
rocm-openblas64, rocm_kpack), same sizes. The gate22 live-process list
also confirms all 46 loaded ROCm DLLs resolve inside
`envs\yolo_amd\...` — no base leakage into the failing path.

## 2. F run provenance (question 4)

- **GPU**: `F_yolo_train.txt:4` `CUDA:0 (AMD Radeon(TM) 8060S Graphics,
  80065MiB)`; `:5` `device=0`; and the failure itself is a MIOpen GPU
  kernel compilation, reachable only on the GPU path (CPU path is
  Phase-1-proven PASS).
- **Clean env**: every ultralytics/torch frame in the traceback
  (`:65`–`:115`) resolves under
  `C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\...`;
  `:4` `Python-3.13.16` matches the interpreter installed by
  `gate22_conda_create.txt` (python-3.13.16 h2e1fde4_102). The
  standalone `gate22_env_verify.txt` (13:13) independently confirms
  `sys.executable`/`sys.prefix` = envs\yolo_amd and torch/ultralytics
  import origins from the env, five minutes before F was captured
  (13:18). Chain is consistent.
- **Weakness**: F's `### command:` header (`yolo_amd python -c "..."`)
  is a paraphrase, not a literal reproducible command line, and no A–E
  log has any header at all (§5.1).

## 3. MIOpen kernel-DB confounder analysis (question 3)

Machine-global state: `C:\Users\rocm\.miopen\cache\` is keyed by MIOpen
version + gfx arch — **not** by Python environment — so the
Phase-1-compiled user kernel DB
(`3.5.2.cd957402/gfx1151_20.ukdb`, 356,352 B, mtime Oct 7 11:36, during
Phase 1) was live, shared state for every Phase-2 run. Could it have
manufactured the Gate-23 result?

- **It cannot explain the failures.** (a) Each clean-env failure log
  shows a *fresh* comgr temp dir with a *fresh* compile attempt and the
  same fatal diagnostic — the kernel was actually recompiled and failed
  again; a DB hit would have skipped compilation entirely. (b) The 3.5.2
  ukdb contains only conv kernels (`25 × MIOpenIm2d2Col.cpp.obj`) and
  **zero BatchNorm entries** — BN compiles failed in Phase 1, so nothing
  BN was ever cached (the 6 `MIOpenBatchNormFwdInferSpatial.cl.obj`
  entries live in the *3.5.1*-era DB of a previous, OpenCL-path stack
  and are not consulted by 3.5.2). The captured
  `batchnorm_gfx1151_20.HIP.3_5_2_cd957402.udb.txt.lock` confirms the
  DB was actively used on the BN family. (c) Direction of bias: had the
  cache contained BN kernels, Phase-2 BN would have *passed* — the
  shared cache biases toward masking the failure, and the failure
  occurred anyway. The falsification of P2-H1 is therefore **robust to
  the kernel-DB confounder**.
- **It does touch one control.** `B_conv.txt` first-call = 0.03 s vs
  Phase-1 *cold* conv (matrix case F, 16.76 s, which compiled im2col via
  HIPRTC) and Phase-1 *warm* `conv_control.txt` (0.05 s, captured
  12:10 after the 11:55 matrix). The clean-env conv pass is
  cache-warm: it demonstrates conv *executes* in the clean env, not
  that the clean env can cold-compile conv kernels. Immaterial to P2-H1
  (conv is not the failing op) but the doc's "every previously-passing
  control still passes" carries this asymmetry unstated. GEMM (rocBLAS
  path, not MIOpen) and E (torch's native precompiled BN kernel,
  cudnn/MIOpen disabled) are cache-independent genuine controls.
- **Symmetry**: neither phase set `MIOPEN_FIND_MODE` / user-DB env vars
  (Phase-1 matrix records `env: ""`); both used default TEMP (the
  redirected-TEMP run was a separate Phase-1 logging experiment). No
  cache clearing occurred between phases — correctly so, since the
  shared cache is the conservative direction for this gate.

Other shared state: F reused the same `datasets\coco8\labels\*.cache`
and `runs\detect\` tree (train-7), and the same `yolo26n.pt`. Benign for
a compile-time failure (dataset is scanned, not trained on, before the
crash), but formally uncontrolled.

## 4. Uncontrolled variables between Phase-1 and Phase-2 runs

1. **Interpreter build — real, disclosed, immaterial.** base 3.13.13
   (Anaconda, MSC v.1942, per `torch_probe.txt:5`) vs env 3.13.16
   (`gate22_conda_create.txt:57`). The doc's "base 3.13.13 → env 3.13.x"
   understates this as an instance change when it is a patch-version
   change. Immaterial to the conclusion: the failing computation lives
   entirely in SHA256-identical native DLLs, and the *same* failure
   exists externally on Python 3.12 (MIOpen #3956). Keep it precise,
   though.
2. **`PYTHONNOUSERSITE=1` — asserted, never captured.** The invocation
   contract is stated in two docs but **no archived artifact shows the
   flag set on any experiment run**: the clean_env logs record no env
   dump, and the only env-verification capture
   (`gate22_env_verify.txt`) itself ran WITHOUT the flag — its pip list
   includes user-site packages and its isolation section prints
   `onnxruntime present`. The doc's verification-table row "onnxruntime
   … absent with it" cites a file that shows the opposite half. The
   tracebacks prove the *torch/ultralytics* origin (env), but user-site
   never shadowed those anyway, so the logs cannot confirm the flag.
   Impact is likely nil — but for a gate whose entire value is
   invocation discipline, the contract itself is the one unarchived
   variable.
3. **User-site is dirtier than documented.** The doc says user-site
   contains "(at least) onnxruntime". In reality it carries a ~25-package
   stack (kokoro-onnx, soundfile, espeakng-loader, phonemizer-fork,
   rdflib, csvw, ruamel.yaml, jsonschema, protobuf, … — visible in
   `gate22_env_verify.txt` pip list and in Phase-1 base `pip_freeze.txt`
   lines 89/116-117: kokoro-onnx, onnxruntime, onnxruntime-directml).
   Phase-1 runs therefore executed with this stack importable
   (user-site on by default); Phase-2 claims to remove it. Note this
   *strengthens* the falsification (yet more machine dirt removed with
   the failure persisting) but the doc's description minimizes it.
4. **Warm vs cold controls** (§3): B_conv is a warm pass; only E and A
   are cache-independent controls in the clean env.
5. **Env-local CRT**: `conda create` brought `vc14_runtime-14.44.35208`/
   `vs2015_runtime` into the env root (`gate22_conda_create.txt:65-66`),
   so the process loads env-local `msvcp140.dll`/`vcruntime140.dll`
   (see `gate22_dll_provenance.json` live list) whose versions may
   differ from base's. These are *runtime* DLLs with no headers; they
   cannot affect HIPRTC include resolution, and the identical failure
   settles it empirically — recorded here for completeness because
   "machine toolchain state" is exactly what this gate does not hold
   fixed.
6. **Not re-run from Phase 1** (see §5.3): matrix G (BN+activation),
   amp-off train, BN1d(3D)/BN3d variants (all Phase-1 FAIL cases);
   matrix H (linear+backward), CPU BN, GPU predict (Phase-1 PASS cases).

## 5. Defects found (adversarial yield)

1. **Provenance regression on A–E logs.** All Phase-1 raw logs carry
   `### captured <timestamp>` / `### command: …` headers and EXIT
   footers via committed `.ps1` harnesses. The seven clean-env A–E logs
   have **no timestamp, no command line, no env capture, and no recorded
   exit code** (C/D logs end at the traceback; exit=1 is inferred).
   There is **no committed Gate-23 runner script**
   (`scripts/phase2/` contains only gate21/gate22 tooling), so the exact
   Gate-23 invocation — including the `PYTHONNOUSERSITE=1` contract — is
   not reproducible from the repo. This is the biggest legitimate
   attack surface on Gate 23: an adversary can ask "were A–E really run
   under the documented contract, and when?"
2. **`gate22_env_verify.txt` does not substantiate the doc's
   verification table as written.** (a) The onnxruntime row's "absent
   with `PYTHONNOUSERSITE=1`" half is not archived anywhere; (b) the
   pip-check row claims "only 2 complaints inside the clone (missing
   pyparsing, python-dateutil)" but the archived verify — post-dating
   the pyparsing install — shows a *different*, single complaint
   (`soundfile 0.14.0 requires cffi`, a user-site leak into the check).
   The claims are plausible but their cited evidence does not contain
   them.
3. **Overgeneralization in the headline sentence.** "every
   previously-failing case still fails identically and every
   previously-passing control still passes" — the clean env re-ran a
   *subset*: 4 of ~8 Phase-1 failing configurations (minimal ×3 +
   eval) plus the YOLO train, and 3 of ~8 passing controls (GEMM, conv,
   E). The re-run selection covers the load-bearing cases, but "every"
   is falsifiable as written.
4. **Chain-of-custody gap for phase2 evidence.** `.gitattributes`
   protects only `evidence/raw/**` (`-text`); `evidence/phase2/**`
   falls under `* text=auto`, so the clean-env logs were committed
   EOL-normalized (`git ls-files --eol`: index `lf` vs worktree
   `crlf`/`mixed`; F stored as `-text` in index). Phase-2 files are
   also absent from `evidence/manifest.json` / `SHA256SUMS.txt`
   (grep: 0 hits), despite Phase-1's NEXT_STEPS instruction to
   regenerate them for new raw logs. The committed bytes are not the
   captured bytes, and cannot be checksum-verified as committed.
5. Minor: `gate22_dll_provenance_stdout.txt:116` prints the Phase-1
   script's hardcoded "written to evidence/raw/..." line — cosmetic
   reuse artifact. Untracked work for later gates (24–27:
   `evidence/phase2/raw/hiprtc/`, `msvc/`, `scripts/phase2/hiprtc_probe/`)
   sits outside the commit — not Gate 23's problem, but commit it or
   note it.

## 6. Is "P2-H1 falsified" a valid inference?

**Valid, within its proper scope — and the doc mostly keeps that
scope.** The logical structure: P2-H1 says the failure is caused by
conda base's unrelated package set; the clean env removes that entire
set (paddlex/paddle/paddleocr/omnidocbench/anaconda-cli/conda ABSENT,
verified) *and* the user-site fallback, keeps the native stack
bit-identical (10/10 SHA256), and every re-run case behaves exactly as
in base. Dirt is demonstrably not *necessary* for the failure. The
shared kernel DB biases the experiment *toward* the failure
disappearing, and it did not. I could not construct a mechanism by
which any removed package was causal for a HIPRTC C++ header-resolution
error inside byte-identical DLLs.

Two scope guards, both already half-acknowledged in the docs, must stay
attached to the claim:

- The clone **cannot** falsify machine-level causes shared by both envs
  (missing MSVC STL headers, driver, wheel-bytes-inherited-from-base).
  The doc's "Classification honesty" section says this correctly; the
  headline "FALSIFIED" is fine only while P2-H1 is read as the
  package-set hypothesis. Any wider reading ("not the environment at
  all") would be overstated — the machine's toolchain state remains the
  live suspect (H10/H11), as the doc's own interpretation ("wheel stack
  + machine toolchain state") concedes.
- The evidence-hygiene gaps (§5.1, §5.2, §5.4) do not overturn the
  result — the logs' internal consistency (fresh comgr dirs, env
  site-packages in tracebacks, version strings) makes fabrication or
  mis-invocation unlikely — but they fall short of the repo's own
  Phase-1 provenance standard, which this project set for itself and
  was previously audited against (Gate-20 review: 45/45 checksums OK).

## 7. Required amendments (conditions of the verdict)

1. Re-capture or annotate the invocation provenance for A–F: one
   archived header per run (timestamp, literal command line,
   `PYTHONNOUSERSITE`/relevant env dump, `sys.executable`), and commit a
   Gate-23 runner script reproducing the contract; add exit codes for
   A–E.
2. Fix the verification-table rows in
   `docs/PHASE2_CLEAN_ENVIRONMENT.md` to match archived evidence (or
   archive the missing with-flag probe and pre-fix pip check); describe
   the user-site leak at its true size (~25 packages, incl.
   onnxruntime-directml).
3. Extend `.gitattributes` (`evidence/phase2/raw/** -text`) and add
   phase2 files to `SHA256SUMS.txt`/`manifest.json`; re-commit
   byte-exact.
4. Reword the Gate-23 headline claims: "every re-run case" not "every
   previously-failing/passing case"; add the warm-cache caveat to the
   B_conv row; state the interpreter delta precisely (3.13.13 →
   3.13.16) including the env-local CRT it brought.

## Verdict: **CONDITIONAL PASS**

The Gate-23 experimental result is genuine, the signature identity is
verified to the letter (normalized diff = 0 on all three BN repros;
12/12 canonical fields on F; 10/10 DLL SHA match; kernel-DB confounder
biases toward the opposite outcome), and "P2-H1 falsified" is a valid
inference for the package-set hypothesis. The conditions are provenance
and wording amendments (§7) — none of them threatens the conclusion,
but until archived, the gate does not meet the evidence standard the
repo itself established in Phase 1.
