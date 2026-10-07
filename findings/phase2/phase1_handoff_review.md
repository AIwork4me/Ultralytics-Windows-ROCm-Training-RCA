# Gate 20 — Phase-1 Handoff Review (Phase 2)

Date: 2026-10-07. Reviewer: primary Phase-2 agent. Method: read all Phase-1
docs and findings listed in the Phase-2 brief; verify that Phase 2 continues
from established facts rather than rediscovering them.

## Documents read

- `README.md`
- `docs/RCA.md`, `docs/HYPOTHESES.md`, `docs/CLAIMS_AND_EVIDENCE.md` (33 claim rows),
  `docs/EXPERIMENT_MATRIX.md`, `docs/NEXT_STEPS.md`, `docs/ENVIRONMENT.md`,
  `docs/EXTERNAL_EVIDENCE.md`
- `findings/phase1_conclusion.json`, `findings/final_gate.md`,
  `findings/subagent_evidence_review.md`,
  `findings/subagent_falsification_review.md`,
  `findings/subagent_rocm_review.md`

## Already proven (Phase-1, with local evidence; Phase 2 takes these as input facts)

| # | Fact | Phase-1 evidence anchor |
|---|---|---|
| 1 | GPU compute works (4096² GEMM PASS) | C005 / `gpu-control/gemm.txt` |
| 2 | Ultralytics GPU inference works (fused BN bypasses MIOpen BN) | C006 / `ultralytics/predict.txt` |
| 3 | YOLO GPU training fails at first BN | C007 / `ultralytics/train_gpu.txt` |
| 4 | Pure PyTorch BatchNorm2d reproduces identically (no Ultralytics) | C009 / `batchnorm/minimal.txt` (C011 = Ultralytics-side repro) |
| 5 | GPU Conv/autograd work (case-F conv-JIT-via-HIPRTC graded **INFERRED** by Phase-1 ROCm review; direct cache evidence for the conv path is P10d) | C013 / `batchnorm/matrix.txt` F,H |
| 6 | CPU BatchNorm works; CPU YOLO training completes | matrix B; `train_cpu.txt` |
| 7 | AMP off does not resolve failure | P3b `train_gpu_amp_off.txt` |
| 8 | cudnn/MIOpen-disabled BN passes (diagnostic toggle) | matrix E |
| 9 | Failure is inside MIOpen HIPRTC runtime compile of BN kernels | C016–C020, `miopen/minimal_bn_miopen_logging.txt` |
| 10 | Missing header is `<type_traits>` (fatal, HIPRTC_ERROR_COMPILATION (6)) | every failure log |
| 11 | `type_traits` physically absent machine-wide at Phase-1 time; wheels ship no C++ STL; wheel clang triple `x86_64-pc-windows-msvc` | C019/C020 / `toolchain/*.txt` |
| 12 | Embedded `miopen_type_traits.hpp` contains `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` ×2 (raw artifact = preprocessor strings only; the ≥7.0→real-STL branch mapping is the ROCm reviewer's narrated extraction, not an archived artifact — Phase 2 Gate 29 must re-derive it from upstream source) | `miopen/miopen_dll_shim_gate.txt` + C032 caveat |
| 13 | BN1d(2D input) and GroupNorm pass; BN1d(3D)/BN2d/BN3d fail — failure is the MIOpen *spatial* BN kernel path | `batchnorm/bn_variants.txt` |
| 14 | MIOpen 3.5.1-era cache compiled BN via OpenCL `.cl` path on this same machine; 3.5.2 rockrel cache has only conv `.cpp.obj` (ledger C033 caveats: cache lineage is corroborating, not proof of a BN OpenCL→HIPRTC switch) | `miopen/user_kernel_db_listing.txt` |

## Still unresolved (Phase-2 mandate)

- **H10**: a host MSVC C++ STL is an intended-but-undocumented prerequisite.
- **H11**: the ROCm Windows wheel / MIOpen / HIPRTC runtime-compile path
  incorrectly depends on an unavailable host STL or fails to
  provide/discover required headers.
- **H12-P2**: the HIP >= 7.0 MIOpen runtime-compile header gating itself is
  the defective design/implementation.

H11 and H12-P2 are kept separate per the brief: H11 is about *STL
availability/discovery*, H12-P2 is about *MIOpen's own source-level decision
to include real std headers in runtime-compiled kernels when HIP >= 7.0*.

## Environment note feeding Gate 21

Phase-1 `docs/ENVIRONMENT.md` records that the validated stack ran from
conda **base** (`C:\Users\rocm\miniconda3\python.exe`) while `yolo_amd`
existed as an *empty* conda env (no Python, no packages). The Phase-2 brief
reports the user now sees `(yolo_amd)` active. Neither observation is
trusted; Gate 21 must independently determine the live state (ENV-A/B/C/D).

## Contradiction check between Phase-1 evidence and Phase-2 brief

The brief's version matrix (torch 2.12.0+rocm7.14.0, torchvision
0.27.0+rocm7.14.0, ROCm 7.14.0, Ultralytics 8.4.174, gfx1151) matches the
Phase-1 baseline exactly. No contradictions found. The only environmental
delta to resolve is the interpreter/env question (Gate 21).

## External-evidence Phase-2 leads (carried per Gate-20 audit; local vs external kept separate)

- **C022**: MIOpen #3956 (open, unanswered since 2026-04-22) shows the
  identical compiler-diagnostic signature on gfx1200 / ROCm 7.2.1 /
  Python 3.12 — external corroboration only; identical signature ≠ proven
  identical root cause until Phase 2 proves the mechanism.
- **C025**: rocm-libraries #2169's Windows log (TheRock build, Oct 2025)
  compiled **past the entire include chain** before failing at gfx1151
  inline asm — a decisive H11 lead: an AMD Windows build that did NOT hit
  this defect. Phase 2 should diff TheRock-vs-rockrel wheel composition.
- **C028**: AMD's Windows PyTorch install docs declare no MSVC
  prerequisite — the documented basis for H10's "undeclared" framing.

## LEVEL-3 methodology constraints (from Phase-1 ROCm review — binding on Phase 2)

A bare "install VS and re-run" A/B is **confounded** (changes STL presence,
driver detection, and environment propagation at once). The cheaper
decisive discriminators, in order:
1. Standalone HIPRTC reproducer (`hiprtcCreateProgram` /
   `hiprtcCompileProgram` on a `<type_traits>` source) — Gate 24.
2. `INCLUDE`-redirect A/B in a child process — Gate 27 arm C.
3. `AMD_COMGR_SAVE_TEMPS` capture of MIOpen's actual compile inputs —
   during Gate 23/24 if available.
4. TheRock-vs-rockrel wheel diff — Gate 29/38.
5. Gate-commit archaeology (`ce14dab…` "All 7.0 hipRTC fixes") — Gate 29.

## Gate-20 conclusion

Phase 2 proceeds on the Phase-1 established chain (facts 1–14 above) without
re-running Phase-1 discovery experiments. New evidence goes to
`evidence/phase2/`, scripts to `scripts/phase2/`, findings to
`findings/phase2/`, patches to `patches/`. Phase-1 artifacts remain
untouched (read-only).

**Status: CONDITIONAL PASS → amendments applied** (see
`subagent_gate_20_review.md`; the four required amendments — C009/C011
fix, external-lead carry-over, methodology constraints, row 5/12/14
caveats — are incorporated in this revision).
