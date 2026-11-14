# WINDOWS_GFX1151 — validated platform record

Machine: Ryzen AI MAX+ 395 w/ Radeon 8060S · Windows 11 Home build 26200 · driver 32.0.22032.6002 · 78 GB unified memory
Stacks: torch 2.12.0+rocm7.14.1 (+torchvision 0.27.0) from `repo.amd.com/rocm/whl-multi-arch/`, python 3.13.16, ultralytics 8.4.182

## Verified results (2026-11-14)

- **G1 primitives**: 16/16 PASS — 3× STL-visible + 3× hidden-host-STL cold homes (patched MIOpen) + official-wheel baseline + exact #3956 negative control (`../windows-training-validation/G1_VERDICT.md`)
- **G2 lifecycle**: 7 tasks × T01–T15 = 14/14 each (`G2_VERDICT.md`); workers 0/2/4; AMP track separate
- **G3 AMP**: root cause closed; real AMP training verified on official wheel (`../amp-rca/G3_VERDICT.md`)
- **G4 long run**: coco128 30-epoch FP32 (`../quality-stability/LONG_RUN_REPORT.md`)
- **Loaded-DLL provenance**: every leg probes in-process; MIOpen.dll sha256 recorded per run

## Environment quirks recorded

- 3 zombie python processes (uncleanable, HIP exit-cleanup hangs) — new GPU processes unaffected; MIOpen.dll file replacement blocked while zombies live (env-B restore deferred, hash-verified both directions otherwise)
- MIOpen `EvaluateInvokers` negative-elapsed errors (source-built 3.6.2 only)
- gfx1151 torch wheel MIOpen 3.5.2.cd957402: spatial-BN training **fails** with #3956 signature when MSVC STL hidden (pre-fix proof); works normally with STL visible
