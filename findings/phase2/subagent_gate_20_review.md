# Gate 20 — Independent Subagent Audit of the Phase-1 Handoff Review

Date: 2026-10-07. Reviewer: independent adversarial auditor (challenge mode).
Target: `findings/phase2/phase1_handoff_review.md` (the primary Phase-2 agent's
Gate-20 handoff review). Mandate: try to FALSIFY the handoff — verify every
"already proven" row against the claims ledger and raw evidence, verify
H10/H11/H12-P2 separation, hunt for omitted Phase-1 facts that materially
bear on the Phase-2 mandate, and confirm cited evidence files exist.

Method: read all six mandated Phase-1 documents plus the three Phase-1
subagent reviews, `findings/final_gate.md`, `docs/NEXT_STEPS.md`,
`docs/EXTERNAL_EVIDENCE.md`, `docs/CLAIMS_AND_EVIDENCE.md` (33 rows counted —
handoff's count is correct), and 13 raw evidence files directly
(`batchnorm/minimal.txt`, `matrix.txt`, `matrix_results.json`, `bn_variants.txt`,
`bn_variants_results.json`, `gpu-control/gemm.txt`, `ultralytics/predict.txt`,
`ultralytics/train_gpu.txt`, `ultralytics/train_gpu_amp_off.txt`,
`ultralytics/train_cpu.txt` (tail), `miopen/minimal_bn_miopen_logging.txt`,
`miopen/miopen_dll_shim_gate.txt`, `miopen/miopen_dll_embedded_sources.txt`,
`miopen/user_kernel_db_listing.txt`, `toolchain/toolchain_probe.txt`,
`toolchain/wheel_stl_sweep.txt`, `conv/conv_control.txt`). Integrity:
`sha256sum -c evidence/SHA256SUMS.txt` → **45/45 OK** (the Phase-1 evidence
review's BLOCKING-1 CRLF defect is confirmed fixed; `.gitattributes` pins LF).

---

## 1. Existence and integrity of cited evidence

Every raw evidence path cited in the handoff table exists:

`gpu-control/gemm.txt`, `ultralytics/predict.txt`, `ultralytics/train_gpu.txt`,
`batchnorm/minimal.txt`, `batchnorm/matrix.txt`, `ultralytics/train_cpu.txt`,
`ultralytics/train_gpu_amp_off.txt`, `miopen/minimal_bn_miopen_logging.txt`,
`toolchain/*.txt` (both files), `miopen/miopen_dll_shim_gate.txt`,
`batchnorm/bn_variants.txt`, `miopen/user_kernel_db_listing.txt` — all
present, all checksum-verified (45/45 OK). **Missing files: none.**

## 2. Row-by-row verification of the "already proven" table

| Row | Handoff claim | Audit verdict | Detail |
|---|---|---|---|
| 1 | GPU compute works (4096² GEMM PASS) — C005/gemm.txt | **VERIFIED** | `gemm.txt`: `PHASE1_GEMM: PASS`, mean=0.015937, EXIT=0 |
| 2 | Ultralytics GPU inference works (fused BN bypasses MIOpen BN) — C006/predict.txt | **VERIFIED with nuance** | `predict.txt`: 4 persons + 1 bus, exit 0, `YOLO26n summary (fused)` line present. The parenthetical mechanism ("bypasses MIOpen BN") is Phase 1's documented consistency reading (final_gate Q8; EXPERIMENT_MATRIX note) — inference, not direct observation; acceptable as carried |
| 3 | YOLO GPU training fails at first BN — C007/train_gpu.txt | **VERIFIED** | signature at lines 50–60; traceback through `conv.py:87 self.bn` → `batchnorm.py:210` → `miopenStatusUnknownError`, exit 1 |
| 4 | Pure PyTorch BN2d reproduces identically — **C011**/minimal.txt | **FACT VERIFIED; CITATION DEFECT** | `minimal.txt` shows the identical 5-field signature — but this claim is **C009** in the ledger. C011 is a different claim ("both TrainSpatial AND InferSpatial affected", evidence `matrix_results.json`). The handoff anchors the right file to the wrong claim ID, and C011's actual content is dropped from the table |
| 5 | GPU Conv/autograd work (incl. MIOpen conv JIT compile) — C013/matrix F,H | **OVERSTATED vs its anchor** | C013 and cases F/H (PASS, F 16.76 s first call) are verified. But "case F compiled via MIOpen JIT" is graded **INFERRED, not proven** by Phase 1's own ROCm reviewer (`subagent_rocm_review.md` claim 5: no conv MIOpen log exists; case F may have used the precompiled CK path; what ukdb proves is that *some* conv kernels runtime-compile). The parenthetical is stated as fact and anchored to evidence that does not contain it |
| 6 | CPU BN works; CPU YOLO training completes — matrix B / train_cpu.txt | **VERIFIED** | matrix B PASS; `train_cpu.txt` EXIT=0, epoch + validation complete |
| 7 | AMP off does not resolve — P3b/amp_off | **VERIFIED** | `amp=False` present in args dump; identical signature; exit 1 |
| 8 | cudnn/MIOpen-disabled BN passes (diagnostic toggle) — matrix E | **VERIFIED** | case E PASS; correctly labeled diagnostic-only (C012's exact framing) |
| 9 | Failure inside MIOpen HIPRTC runtime compile of BN kernels — C016–C020 / miopen logging | **VERIFIED** (minor) | API trace (`miopenBatchNormForwardTrainingActivation_V2`, bn_mode=1) + compile failure inside the same call confirmed in `minimal_bn_miopen_logging.txt:29–64`. Nit: the cited file is C015's evidence; the range should start at C015 |
| 10 | Missing header `<type_traits>`, fatal, HIPRTC_ERROR_COMPILATION (6) — every failure log | **VERIFIED** | present in all 8 failure logs I read (minimal, matrix C/D/G, train_gpu, amp_off, bn_variants ×3) |
| 11 | `type_traits` physically absent machine-wide at Phase-1 time; wheels ship no STL; clang triple `x86_64-pc-windows-msvc` — C019/C020 | **VERIFIED** | `wheel_stl_sweep.txt`: 0 hits, triple confirmed; `toolchain_probe.txt`: NOT FOUND everywhere; "machine-wide" is closed by the ROCm reviewer's full-C: scan (0 hits, only drive). The "at Phase-1 time" qualifier is correct and important — keep it |
| 12 | Embedded shim disabled when `HIP_PACKAGE_VERSION_FLAT >= 7000000000ULL` — shim_gate.txt | **VERIFIED with dropped caveat** | The raw file contains only six extracted preprocessor gate strings — no shim bodies, no branch mapping. The shim→branch semantics come from the ROCm reviewer's byte-offset source extraction (narrated in `subagent_rocm_review.md` claim 4, **not archived as a raw artifact**) plus empirical corroboration (the real `#include <type_traits>` is attempted at line 151 in every failure). C032's ledger caveat ("read from preprocessor strings, not compiled source") is dropped. The statement is defensible, but this is the single fact the NEW hypothesis H12-P2 rests on — the caveat matters there |
| 13 | BN1d(2D)/GroupNorm pass; BN1d(3D)/BN2d/BN3d fail — spatial path — bn_variants.txt | **VERIFIED** | 2 PASS / 3 FAIL with type_traits error confirmed. Note: bn_variants kernel strings are truncated at `…FwdTr`, so the "Spatial" attribution for BN1d(3D)/BN3d rests on falsification-review A10's live observation + BN2d's full name in matrix D — sound, but the raw file alone does not spell it |
| 14 | 3.5.1 cache compiled BN via OpenCL `.cl`; 3.5.2 cache only conv `.cpp.obj` — ukdb listing | **VERIFIED with dropped caveat** | Listing matches verbatim (6× `MIOpenBatchNormFwdInferSpatial.cl.obj` vs 25× `MIOpenIm2d2Col.cpp.obj`). C033's caveats are dropped: 3.5.1 has BN **Infer-only** records (unknown whether BN training ever ran on that stack), and absence of BN `.cpp.obj` in 3.5.2 is consistent-with, not proof of, the compile failure. RCA.md hedged with "indicates"; the handoff states it flat |

Score: 11/14 fully verified as stated; 1 citation defect (row 4); 2 rows
whose parentheticals state more than their cited anchors prove (rows 5, 12);
1 row with dropped ledger caveats (row 14). **No row states a fact that
Phase 1 did not establish.** No LEVEL-3 (fix-ownership) claim leaks into the
table.

## 3. H10 / H11 / H12-P2 separation

- The three hypotheses are listed as unresolved, matching
  `findings/phase1_conclusion.json` (H10/H11 "plausible") and `docs/RCA.md`'s
  LEVEL-3 boundary. **H12-P2 is not smuggled in as proven**: row 12 carries
  only the gate's *existence* (Phase-1 evidence), while the *judgment* that
  the gating is defective stays under "Still unresolved". Correct.
- The separation paragraph (H11 = STL availability/discovery; H12-P2 =
  MIOpen's source-level decision) matches the Phase-2 mandate. One nuance
  neither hidden nor flagged: **Phase-1 H11 was broader** —
  `docs/HYPOTHESES.md` H11 explicitly included "or MIOpen sources should not
  require it", i.e. the slice now called H12-P2. The re-scoping is per the
  brief and openly attributed ("kept separate per the brief"), but a Phase-2
  reader comparing the handoff's H11 against the ledger will find Phase-1
  H11's text overlapping H12-P2. A one-line note would prevent confusion.
- Minor wording leak: the handoff's H11 one-liner ("wheel / **MIOpen** /
  HIPRTC ... incorrectly depends on an unavailable host STL") touches MIOpen
  territory; the separation paragraph below it repairs this. Acceptable.

## 4. Contradiction check vs the Phase-2 brief

- Version matrix (torch 2.12.0+rocm714.0, torchvision 0.27.0+rocm714.0,
  ROCm 7.14.0, Ultralytics 8.4.174, gfx1151): verified equal to
  `docs/ENVIRONMENT.md`. "Matches exactly" is correct.
- The **one real contradiction** — brief says user sees `(yolo_amd)` active;
  Phase 1 (C004) proved `yolo_amd` was an empty shell and the stack lives in
  conda base — is handled exactly right: neither observation trusted,
  resolution deferred to Gate 21. Gate 21 has since concluded **ENV-B**
  (activation cosmetic; python resolves to base), validating the handoff's
  skeptical treatment. No other Phase-1 fact contradicts the brief.
- No Phase-1 fact material to the mandate was *contradicted and omitted*.
  However, material Phase-1 facts were omitted without contradiction — see §5.

## 5. Material omissions (the audit's main findings)

The handoff table carries only **local** facts. Three clusters of
Phase-1-established, High-confidence facts that directly feed the Phase-2
mandate are absent:

**(a) External-evidence leads (C022, C025, C028) — most important.**
- **C025 / `docs/EXTERNAL_EVIDENCE.md`**: rocm-libraries #2169's TheRock
  Oct-2025 Windows build compiled **past the entire C++ include chain**
  before failing at DPP inline asm — an AMD Windows build that did NOT hit
  this defect. Phase 1 explicitly labeled this "a Phase-2 lead toward a
  packaging difference between AMD Windows builds"; it is listed in H11's
  decisive-experiment column and as NEXT_STEPS discriminator 4 (TheRock-vs-
  rockrel wheel diff). This is arguably the single strongest H11/H12-P2
  discriminator Phase 1 found, and it is invisible in the handoff.
- **C022**: #3956 shows the identical compiler-diagnostic signature on
  gfx1200 / ROCm 7.2.1 / Python 3.12 — bounds the defect across versions and
  targets; still open/unanswered upstream (bears on the upstream-report
  deliverable).
- **C028**: AMD's Windows install docs declare **no** MSVC/VS prerequisite —
  the evidentiary basis for H10's "undocumented" qualifier. The handoff's
  H10 line asserts "intended-but-undocumented" without carrying this fact.
**(b) LEVEL-3 experiment-design constraints from `subagent_rocm_review.md`.**
The ROCm reviewer established that the VS-installed A/B **alone is
confounded** (three variables: STL presence vs driver-level MSVC detection
vs hiprtc's embedded invocation) and specified the cheaper decisive set:
standalone hiprtc reproducer via `hiprtc0714.dll`, child-process
INCLUDE/CPATH redirect, `AMD_COMGR_SAVE_TEMPS=1` option capture,
TheRock-vs-rockrel wheel diff, upstream archaeology of the commit that added
the `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` gate. `docs/NEXT_STEPS.md`
absorbed these; the handoff lists both files as "read" but carries none of
this content. If Phase 2 executes only a bare VS A/B, it will repeat a
design Phase 1 already learned is insufficient.
**(c) Smaller facts with Phase-2 utility**: the standalone `amdclang` repro
already reproduces `'type_traits' file not found` driver-level with search
path = clang resource dir + hard-coded legacy VS 8/9/10 fallbacks (shapes
H10-vs-H11); `MIOpenDriver.exe` is not shipped in the wheel (blocks
driver-level repro); precompiled GEMM objects mean the GEMM control says
nothing about the compile layer.

None of these omissions corrupts the carried facts, but the handoff's stated
purpose is that Phase 2 "takes these as input facts" and proceeds "without
re-running Phase-1 discovery" — as the sole interface, it under-delivers the
leads and constraints Phase 1 actually established.

## 6. What the handoff gets right (for the record)

- The 14-row core chain is faithful to Phase 1; no overstatement of RCA
  depth (LEVEL 2 stated, LEVEL 3 nowhere claimed as proven).
- The environment contradiction is handled with exactly the right epistemics,
  since vindicated by Gate 21 (ENV-B).
- Case E kept diagnostic-only; "no fix applied" stance preserved; Phase-1
  artifacts declared read-only with new work routed to `evidence/phase2/`,
  `scripts/phase2/`, `findings/phase2/`, `patches/` — consistent with the
  brief and with what Phase 2 has actually done so far (Gate 21 artifacts
  conform to this layout).
- The "(33 claim rows)" count and all cited paths are accurate.

---

## Verdict: **CONDITIONAL PASS**

The handoff is accurate in every load-bearing fact, does not overstate the
Phase-1 RCA depth, keeps H10/H11/H12-P2 separate as the mandate requires, and
correctly handles the one genuine brief-vs-evidence contradiction. It fails
to be a *complete* interface: one wrong claim ID, two rows whose
parentheticals outrun their cited anchors, dropped ledger caveats on the row
H12-P2 depends on, and — most materially — total omission of the
external-evidence leads (C022/C025/C028) and the LEVEL-3 experiment-design
constraints that Phase 1's own review established.

Required amendments (all to `phase1_handoff_review.md`; none require new
experiments):

1. Row 4: cite **C009** (not C011); optionally add C011's content (both
   TrainSpatial and InferSpatial kernels affected) as its own row.
2. Add rows (or a "Phase-2 leads" section) for C022 (#3956 signature match,
   still open), C025 (TheRock Windows build compiled past the include chain —
   the wheel-diff lead), C028 (AMD docs declare no MSVC prerequisite).
3. Carry the LEVEL-3 discriminator constraints: VS A/B alone is confounded;
   standalone hiprtc reproducer / INCLUDE-redirect / AMD_COMGR_SAVE_TEMPS /
   TheRock-vs-rockrel diff / gate-commit archaeology are the decisive set.
4. Restore caveats: row 5 (case-F-via-HIPRTC is inferred; ukdb is the
   proof of conv runtime-compile), row 12 (shim semantics from source-level
   extraction narrated in `subagent_rocm_review.md`, not archived raw —
   archive the extraction or cite the review), row 14 (3.5.1 BN = Infer-only
   records; absence ≠ proof).

With amendments 1–4 applied, the handoff is a faithful Phase-1 → Phase-2
interface and the conditional clears to PASS.
