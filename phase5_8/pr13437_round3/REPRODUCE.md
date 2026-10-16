# Reproduction and independent inspection

## Verify the frozen evidence without a GPU

Clone this repository and select the PR #12 evidence commit or merged main commit. From
the repository root, Python 3 standard library and Git are sufficient for integrity:

```powershell
python phase5_8/pr13437_round3/scripts/verify_manifest.py
```

The tool compares exact coverage, path ordering, digests and LF bytes against `git ls-files`.
It excludes only `SHA256SUMS.txt`, rejects untracked payload, duplicate/unexpected entries
and missing files. To intentionally regenerate after an evidence edit, stage new payload
files first, run with `--write`, then run without `--write`. A second `--write` must leave
the manifest byte-identical. The package `.gitattributes` disables normalization even with
`core.autocrlf=true`. Final verification must also use committed blobs/a separate checkout.

Reproduce retained device-code comparisons without ROCm or a GPU:

```powershell
python phase5_8/pr13437_round3/scripts/verify_isa_pairs.py
```

This verifies ten ELF `.text` pairs, seven archived BN instruction dumps, and the three
kthvalue cache rows per label against retained ELF bytes. SQLite is read from disposable
copies so archived sidecars are unchanged. BN cache option/source mapping is not archived.

The claim audit links every major conclusion to actual logs. The retained `.elf`, compressed
`.co`, disassemblies and SQLite caches allow code-object inspection without rebuilding
MIOpen. Empty `.body` outputs are historical failed-extraction artifacts and are never used
as equality evidence. See the retention audit for exact dispositions and independent ISA checks.

## Pin sources and reconstruct the Windows build

- Round-3 source: `d4b574ac8a039f39976c5f9f4e18adcb074dc237` in
  [ROCm/rocm-libraries](https://github.com/ROCm/rocm-libraries/tree/d4b574ac8a039f39976c5f9f4e18adcb074dc237).
- Round-2 performance comparator: `f0f330c4837a3c4ca9736a8059410cca1a7c2b85`.
- Negative control: `b8cf0e7b526f4a25c0623f5b2a4fe41e03ede179`, plus the unchanged
  `projects/miopen/test/gtest/hiprtc_selfcontained.cpp` from Round 3 as an untracked test.
  It must still use the unpatched headers. That test injection is intentional, not a clean
  production baseline checkout claim.

Use separate detached source worktrees/build directories; do not alter the implementation
branch. The original runner used `C:\w58` / `C:\b58` (B), `C:\w56` / `C:\bfin` (A),
`C:\wp` / `C:\bwp` (negative). Build settings are in [build driver](scripts/build_b58.sh),
[configure log](build/configure_b58.log), [build log](build/build_b58.log), and
[toolchain versions](build/toolchain.txt). Dependency versions, shims and environment are
described in the unchanged [Phase 5.7 environment](../../phase5_7/pr13437_final_head_f0f330c4/ENVIRONMENT.md),
[Phase 5.7 build provenance](../../phase5_7/pr13437_final_head_f0f330c4/BUILD_PROVENANCE.json),
and the [repository guide](../../README.md).

These are historical, machine-specific drivers, not a portable environment installer.
They require Git Bash, the ROCm 7.14.0 wheel stack and torch 2.12.0+rocm7.14.0, Windows SDK
tools, CMake/Ninja, and the dependency directories listed by the build driver. Adapt the
absolute paths in copies for another machine, preserving compiler options/source SHAs.
The build targets are `MIOpen`, `bin/test_hiprtc_selfcontained.exe`, `bin/test_kthvalue.exe`.
Successful host compilation does not prove every embedded GPU kernel compiled offline.

## Re-execute the measured workloads

| Leg | Original driver / interpretation |
|---|---|
| No-STL positive | [run_r3_tests.sh](scripts/run_r3_tests.sh), B block; unique fresh cache home; exactly one PASSED gtest, no SKIP; nonce logs distinguish 3 isolated and 2 ambient compiles |
| Negative | [run_r3_negative.sh](scripts/run_r3_negative.sh); must fail with missing `type_traits`, not merely any nonzero status |
| kthvalue | Same positive driver, E block; historical `/usr/bin/time` invocation failed, so the file named `warm` is the first successful fresh-home run; require 27/27 |
| BatchNorm | [d_batchnorm.py](scripts/d_batchnorm.py) via [swap driver](scripts/swap_run.sh); inspect finiteness and CPU output/gradient errors. Running-var uses biased reference, so do not interpret its residual as exact unbiased agreement |
| YOLO FP32 smoke | [f_yolo26n_coco8.py](scripts/f_yolo26n_coco8.py) via swap driver; requires COCO8 and model downloads. Inspect actual epoch completion/finite losses; printed PASS alone is insufficient |
| AMP controls | [amp_check_ab.py](scripts/amp_check_ab.py) with R2/R3/shipping wheel separately; precheck failure is not successful AMP training |
| Warm timing | [run_r3_perf2.sh](scripts/run_r3_perf2.sh) + [perf_bn2.py](scripts/perf_bn2.py), A-B-B-A; verify per-process loaded library proof |
| Cold timing | [run_r3_cold_ab.sh](scripts/run_r3_cold_ab.sh); retain drift/order information, classify original small sample INCONCLUSIVE |

The old test driver removes fixed cache-home paths; substitute fresh dedicated directories
when adapting it. DLL-swap drivers operate on the installed wheel and use trap-based restore;
the archived transcripts, rather than the trap alone, prove the recorded restores. Record
source status, binary hashes, loaded module path, wheel restore hash and every exit status
for a new run. No historical script was changed to pretend that it produced stronger results.

## Linux and gfx942

No local current-head Linux/GPU run was available. The [gfx942 analysis](GFX942_CI_RCA.md)
contains the upstream job link and maintainer reproduction command. Current-head Actions
must first be approved by a ROCm maintainer; if the hang recurs, compare the same shard/test
on develop and PR on matched gfx942 hardware. This package does not establish a final cause.
