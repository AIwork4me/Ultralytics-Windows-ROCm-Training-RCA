# PHASE 5.3B SUMMARY — Linux Radeon 8060S (gfx1151) Final R2 Cross-OS Validation

Mission ID: **LINUX-GFX1151-P53B-R2-CROSSOS**
Candidate: **P5.1-CANDIDATE-R2** (frozen evidence commit `c8417161125dc33275b7ac615298b449a81e7cf8`)
Host: AMD RYZEN AI MAX+ PRO 395 w/ Radeon 8060S (**gfx1151**), Ubuntu 24.04.4,
kernel 6.17.0-1032-oem. ROCm **7.14.0** isolated wheel SDK (HIP 7.14.60850,
torch 2.12.0+rocm7.14.0, AMD clang 23.0.0git). System ROCm 7.2.1 coexists and
was held out of every configure and runtime path (zero contamination
evidenced; a stray distro `libamdhip64.so.5` was also on the checklist).

## FINAL VERDICT

**P53B_GFX1151_R2_CROSSOS_PASS_WITH_CTEST_SKIP**

All required build, runtime, and numerical gates PASS. The single test
limitation is the genuine Linux no-STL isolation unavailability (same class
as the W7900/ROCm 7.14.1 finding): the R2 regression test's own stdlib probe
reports INCONCLUSIVE (exit 4) and CTest renders Skipped with process exit 0 —
never counted as a no-STL PASS. The Windows no-STL FAIL→PASS claim remains
the Windows RCA's evidence.

## Gate results (each with an independent fresh-subagent review; see reviews/)

| Gate | Scope | Result |
|---|---|---|
| H00 | Machine reconciliation | PASS — 8060S/gfx1151 verified, dual-stack inventory, Phase-3 assets untouched |
| H01 | R2 evidence integrity | PASS — all hashes recomputed from bytes; strict consumer check-only PASS; adversarial matrix 19/20 (16b: authorized-apply positive blocked by the intentionally partial local object store; tree reconstruction proven 3 independent ways in H02) |
| H02 | Exact source reconstruction | PASS — git am AND git apply --index + write-tree = tree `b983cadd…`; 10/10 changed-file blobs match the manifest; reviewer's third scratch-repo derivation agrees |
| H03 | Targeted CTest validation | PASS_WITH_CTEST_SKIP — target builds with NO include/lib injection (R2 CMake fix carries it); ordinary + with-stl PASS; no-STL exit 4 INCONCLUSIVE (stdlib reachable under -nostdinc via comgr staging; auditor reproduced with an independent driver) |
| H04 | Two source-built legs | PASS — legA `7f282a6f…` (pristine base) / legB `b14e907a…` (exact R2 tree); CMake-semantic identity; zero /opt/rocm in either build tree |
| H05 | Real kthvalue A/B | PASS — 3/3 cases both legs vs CPU reference (0 value/index mismatches); 15/15 byte-identical A/B dumps; KthvalueFwd + MIOpenKthvalue.cpp RTC from fresh per-leg caches; auditor re-ran both legs independently |
| H06 | Direct BatchNorm A/B | PASS — 6/6 checks both legs, identical errors, all six below predeclared tolerances with 26x–3.8e7x headroom; fwd+bwd spatial kernels dispatched (`-mcpu=gfx1151`, `MIO_BN_GFX115X=1`); auditor rebuilt the harness from source |
| H07 | Targeted coverage | PASS — partial-STL failure class reproduced on legA + designed guard on legB (real comgr RTC); tensor_view/radix/initlist closures; **BF16 kthvalue RUNTIME PASS on both legs** (closes the W7900-recorded BF16 gap) |
| H08 | Optional YOLO26n smoke | EXECUTED/PASS — in-process legB binding asserted before training; 1 epoch amp=False + val; last.pt `40ae9450…` |
| H09 | Cross-OS matrix | PASS — three-platform matrix (Windows gfx1151 / Linux gfx1100 / Linux gfx1151) |
| H10 | Adversarial panel | see reviews/ (maintainer / GPU runtime / supply-chain) |

## Key identities

- Upstream base: `7c5866144ac4b879be442563e2b49fa1c142ea36` (tree `8b0bf035…`)
- R2 tree: `b983caddf9f9f561e7d1b590deadb16267c2de15` (two-method reconstruction + reviewer third)
- Patches: `816946b4…`, `46044d8c…`, `df7c3c3a…`; series concat: `48308f6d…`
- legA libMIOpen: `7f282a6f569e31d05708a1b40f298dd60ad39dcbd197794ff24ec478e7f2533b`
- legB libMIOpen: `b14e907a8f259b27e9fc2ebc5fa58120ae90ff179f63a84676ab1a60619e90eb`
- Kthvalue harness (unchanged Phase-3 binary): `4d77a96f…`; BatchNorm harness (recompiled from W7900 source): `bcd242eb…`; BF16 probe: `942fd38f…`

## What Platform C adds beyond W7900 (Platform B)

1. Same-GPU/different-OS replication of the exact R2 A/B (gfx1151 on Linux).
2. First runtime BF16 kthvalue validation within this three-platform R2 program (W7900 had recorded it untested; both legs PASS here).
3. Partial-STL Windows-failure-class reproduction through real comgr RTC on
   gfx1151 Linux (legA fails with `utility not found`; legB guard fires).
4. An ROCm 7.14.0 (vs 7.14.1) data point for the no-STL isolation behavior.

## Honest limitations

- The no-STL positive control could not execute its isolation prerequisite
  (CTest Skipped / exit 4) — same fixture-documented class as W7900.
- Radix int32/int64 KEY-encode arms are covered statically/compile-level;
  runtime coverage exists for FP32/FP16/BF16 encode arms and 64-bit indices.
- H01 adversarial test 16b (consumer --apply full-checkout positive) was
  blocked by the intentionally partial local object store (documented; the
  equivalent identity was proven by three independent reconstructions).
- Network to github was intermittently throttled; blob acquisition used the
  Phase-3 raw-backfill method (SHA-1-verified per blob). All hashes verified.
- Upstream governance items (DCO author identity, submission authorization)
  remain human actions, unchanged by this mission.
