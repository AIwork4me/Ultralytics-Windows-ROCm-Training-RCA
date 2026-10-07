# Phase 19 — Final RCA Gate (20 questions)

Answered against raw evidence; each answer cites its source. Any answer not
fully determinable is marked UNRESOLVED rather than guessed.

| # | Question | Answer | Evidence |
|---|---|---|---|
| 1 | Does ROCm PyTorch detect the GPU? | Yes — `torch.cuda.is_available()==True`, name = AMD Radeon 8060S, count=1 | `environment/torch_probe.txt` |
| 2 | Does real GPU compute work? | Yes — 4096² GEMM PASS on cuda:0 | `gpu-control/gemm.txt` |
| 3 | Does Ultralytics inference work? | Yes — predict exit 0, 4 persons + 1 bus | `ultralytics/predict.txt` |
| 4 | Is the YOLO training failure reproducible? | Yes — epochs=1 repro, exit 1, full signature | `ultralytics/train_gpu.txt` |
| 5 | Reproducible without Ultralytics? | Yes — 5-line pure-PyTorch BatchNorm2d, identical 5-field signature | `batchnorm/minimal.txt` |
| 6 | BatchNorm training specifically implicated? | Yes — failure at first BN module; TrainSpatial kernel | `ultralytics/train_gpu.txt` lines 50–132 |
| 7 | Does CPU BatchNorm work? | Yes — matrix case B PASS | `batchnorm/matrix.txt` |
| 8 | Does eval/inference BN behave differently? | No — eval also FAILS, via InferSpatial kernel (Ultralytics predict only works because BN is fused into convs) | `batchnorm/matrix_results.json` case C; `ultralytics/predict.txt` ("fused") |
| 9 | AMP causal or falsified? | Falsified — `amp=False` fails identically | `ultralytics/train_gpu_amp_off.txt` |
| 10 | Does `torch.backends.cudnn.enabled=False` alter the outcome? | Yes — BN then passes via native path (diagnostic only, not a fix/proposal) | `batchnorm/matrix.txt` case E |
| 11 | MIOpen definitively in the failing call path? | Yes — API trace `miopenBatchNormForwardTrainingActivation_V2` (bn_mode=1) precedes failure; MIOpen.dll loaded live | `miopen/minimal_bn_miopen_logging.txt`; `environment/dll_provenance.json` |
| 12 | HIPRTC definitively the failing compilation layer? | Yes — `hiprtcCompileProgram` → `HIPRTC_ERROR_COMPILATION (6)`; hiprtc0714.dll loaded live | all failure logs; `dll_provenance.json` |
| 13 | `<type_traits>` absent, present-but-undiscoverable, or unresolved? | **Physically absent** from every searched location (no MSVC/LLVM/gcc STL on machine; none in wheel trees; independent full-C: drive scan by ROCm reviewer found 0 `type_traits`). Whether HIPRTC *would* use one if present is UNRESOLVED (cannot test without installing) | `toolchain/toolchain_probe.txt`, `toolchain/wheel_stl_sweep.txt`, `findings/subagent_rocm_review.md` |
| 14 | Root cause LEVEL 2 or LEVEL 3? | **LEVEL 2** (mechanism). LEVEL 3 (owning layer: MSVC prerequisite vs wheel packaging vs HIPRTC search) not claimed | `docs/RCA.md` |
| 15 | Which hypotheses actually falsified? | H1 Ultralytics, H2 model, H3 dataset, H4 AMP, H5 general GPU, H12 pip conflicts, H13 virtual adapter — all locally. H8 (Py3.13) / H9 (gfx1151) falsified by external evidence only | `docs/HYPOTHESES.md` |
| 16 | All claims backed by raw evidence? | Yes — 30-row ledger with file citations (spot-audited by 3 subagent reviews) | `docs/CLAIMS_AND_EVIDENCE.md`, `findings/subagent_*_review.md` |
| 17 | Raw files checksummed? | Yes — 39 files, SHA256SUMS + manifest.json (verified by evidence reviewer) | `evidence/SHA256SUMS.txt` |
| 18 | Secrets absent? | Yes — pattern scan clean (only benign filename mention of `aau_token`, no values) | `findings/subagent_evidence_review.md` |
| 19 | Can another engineer rerun the minimal repro from README? | Yes — `python scripts\02_batchnorm_minimal.py minimal`, plus full suite `run_all_rca.ps1` | `README.md`, `scripts/` |
| 20 | Conclusion conservative enough for upstream review? | Yes — explicit non-claims section; "same signature, not proven same root cause" wording vs upstream | `docs/RCA.md` §What Phase 1 Does NOT Claim; `docs/EXTERNAL_EVIDENCE.md` |

**Gate result: PASS** — all 20 answered; #13 carries an explicit UNRESOLVED
sub-item by design.
