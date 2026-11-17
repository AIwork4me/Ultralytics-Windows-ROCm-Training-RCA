# PR-D DRAFT — Ultralytics docs: Windows native ROCm PyTorch training support status

**Target repo**: `ultralytics/ultralytics` (`docs/en/integrations/amd.md`) · **Status: DRAFT — Owner approval required before any upstream submission**
**Basis**: `release-provenance/G0_VERDICT.md` (release lineage), G1/G2/G3 verdicts, and the evidence archive in this RCA repo.

## What must be distinguished (current doc conflates the two)

1. **Native PyTorch ROCm training/val/predict on Windows** — works today with the AMD wheel
   (`repo.amd.com/rocm/whl-multi-arch/`, torch 2.12.0+rocm7.14.1) **for FP32**, on supported GPUs.
   Since the MIOpen HIPRTC host-STL regression (MIOpen #3956 / rocm-libraries PR #13437,
   MERGED 2026-10-19, TheRock #9359), future releases restore spatial-BatchNorm training that
   currently crashes on wheels whose MIOpen predates the fix (all wheels published as of
   2026-11-14 predate it — verified `release-provenance/RELEASE_LINEAGE.md`).
2. **ONNX Runtime MIGraphX inference** — the existing doc's focus; Linux-only wheels; unrelated
   to (1) and not a blocker for it.

## Proposed doc additions (conditional wording, evidence-backed)

- **Windows support status**: "FP32 native training on Windows is verified experimentally on
  gfx1151 (Radeon 8060S) with torch 2.12.0+rocm7.14.1 wheels; spatial-BatchNorm training
  requires a MIOpen release that includes rocm-libraries#13437 (not yet in any published wheel
  as of 2026-11-14). AMP: works (verified end-to-end); the automatic AMP precheck may disable
  AMP on some stacks — see Known limitations."
- **Installation**: existing AMD wheel instructions; pin `torch[device-gfx1151]==2.12.0+rocm7.14.1`, then `ultralytics` after torch.
- **Minimal GPU verification**: the 5-line BatchNorm probe + `torch.version.hip` check.
- **Training example**: standard YOLO command with `device=0 amp=False` (FP32-verified) / `amp=True` (verified on official wheel, see limitations).
- **Known limitations**: AMP precheck sensitivity (check_amp design, G3); source-built MIOpen solver-timing anomaly (gfx1151, documented separately); per-family support limited to actually-tested GPUs (gfx1151 only).
- **Troubleshooting**: the exact #3956 error signature → "your MIOpen predates rocm-libraries#13437; wait for a wheel built from a post-merge release or use the linked workaround evidence".

## Reviewer checklist

- [ ] No official-support claims beyond verified scope (gfx1151, FP32 + verified AMP, listed wheels)
- [ ] MIGraphX section untouched
- [ ] Dated evidence links to the public RCA repo, not local paths
