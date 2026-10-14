# PR #13437 — Final-HEAD Windows Evidence Package (`f0f330c4`)

Independent, evidence-first validation closure for the final Windows
implementation of **ROCm/rocm-libraries PR #13437**
("MIOpen: make HIPRTC kernel includes self-contained without host STL").

- Validated PR HEAD: `f0f330c4837a3c4ca9736a8059410cca1a7c2b85`
  (2-commit series on develop `b8cf0e7b`: `c6ed8131` + `f0f330c4`;
  7 files, +376/−61)
- Machine: Windows 11, Radeon 8060S (gfx1151), ROCm 7.14.0 wheels,
  PyTorch 2.12.0+rocm7.14.0 — see `ENVIRONMENT.md`
- This package is **evidence only**: no code changes, no pushes, no CI
  triggers against the upstream PR.

## Verdict (one line each)

| Leg | Result |
|---|---|
| HIPRTC no-STL regression gtest on final HEAD | **PASS** (5 fresh RTC compiles, `-nostdinc`, kernel launched + values verified) |
| Negative control (baseline + final test file) | **EXPECTED_FAIL** with the exact original signature `'type_traits' file not found` |
| BatchNorm fwd/bwd vs CPU | **PASS** (≤ 9.5e-07 output error, seeded) |
| kthvalue (radix.hpp consumer) | **PASS** 27/27 (FP32/FP16/BFP16) |
| YOLO26n COCO8 1-epoch real GPU training | **PASS** (AMP checks passed; no missing-STL failure) |

Full table with provenance columns: `VALIDATION_MATRIX.md`.

## The provenance chain (why this is final-HEAD evidence)

git commit `f0f330c4` → clean worktree → fresh isolated build (`C:\bfin`)
→ SHA256-recorded binaries → runtime logs that embed MIOpen's own
source-state label **`3.6.2.f0f330c4`** (and `3.6.2.b8cf0e7b` for the
unpatched control) → raw results. Details: `SOURCE_PROVENANCE.md`,
`BUILD_PROVENANCE.json`, `BINARY_SHA256.txt`.

The previous validation round ran against the pre-squash working tree
(cache label `e4b9174a-dirty`, 198-line pre-final test file); per the
rules above, those logs are **not** presented as final-HEAD evidence —
every leg here was re-executed from the pinned commit.

## Contents

- `VALIDATION_MATRIX.md` — every test, SHA, result, log, provenance
- `SOURCE_PROVENANCE.md` — commit→build→binary→runtime chain + disclosures
- `BUILD_PROVENANCE.json` — machine-readable build record
- `BINARY_SHA256.txt` / `SHA256SUMS.txt` — integrity manifests
- `ENVIRONMENT.md` — measured environment snapshot
- `HIPRTC_NO_STL_VALIDATION.md` (leg B), `NEGATIVE_CONTROL.md` (leg C),
  `BATCHNORM_VALIDATION.md` (leg D), `KTHVALUE_VALIDATION.md` (leg E),
  `YOLO26N_VALIDATION.md` (leg F)
- `INDEPENDENT_REVIEWS.md` — three independent subagent audits (A/B/C)
- `raw/` — unedited logs (one disclosed hostname redaction in the YOLO log)
- `scripts/` — the exact build/run scripts used this round

## Reproducing the essential validation

Prerequisites: the ROCm 7.14 wheel stack (PyTorch + `_rocm_sdk_*`), MSVC
Windows Kits on PATH for `mt.exe`, a clean checkout of `f0f330c4`, and the
dependency shims (`scripts/build_bfin.sh` shows the exact configure flags;
`README` of the repo root documents where the shims come from).

```bash
# 1. build (from a clean worktree at f0f330c4)
cmake -S <worktree>/projects/miopen -B /c/bfin -G Ninja <flags in scripts/build_bfin.sh>
ninja -C /c/bfin MIOpen bin/test_hiprtc_selfcontained.exe bin/test_kthvalue.exe

# 2. positive leg (expect: 1 test PASSED, cache label 3.6.2.f0f330c4)
MIOPEN_LOG_LEVEL=6 /c/bfin/bin/test_hiprtc_selfcontained.exe \
  --gtest_filter=CPU_HipRtcSelfContained_NONE.*

# 3. kthvalue (expect: 27 tests PASSED)
/c/bfin/bin/test_kthvalue.exe

# 4. negative control: baseline b8cf0e7b worktree + ONLY the test file from
#    f0f330c4 copied in, relink the test target, rerun step 2
#    (expect: FAILED, 'type_traits' file not found)

# 5. BatchNorm / YOLO: swap the built MIOpen.dll into the wheel dir (hash
#    both sides before/after), run scripts/d_batchnorm.py and
#    scripts/f_yolo26n_coco8.py, restore the wheel DLL and verify its hash.
```

Windows-specific: run test exes with their build `bin` dir first on PATH so
the freshly built `MIOpen.dll` wins DLL resolution (the `GetLibPath` log line
confirms it each time).

## Boundaries

- Linux: not revalidated locally this round (upstream CI covers it; the
  gtest is tri-state by design and reports GTEST_SKIP on comgr stacks that
  inject the STL — that behavior was validated in an earlier phase; the
  frozen record currently lives on the repository branch
  `phase5.6/maintainer-review-r1` under `phase5_6/maintainer_review_r1/`
  and appears on `main` once that branch is merged).
- Upstream CI remains approval-gated; this package does not claim any CI
  result beyond what the PR page shows.
- Historical phase evidence (frozen) lives in the earlier phase directories
  of this repository; this package does not modify them.
