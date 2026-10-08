# Linux Evidence Preservation (Gate P53)

Date: 2026-10-08. Linux Phase-3 was executed by an independent validator on
the branch `rca/linux-gfx1151-phase3-regression` and merged to `origin/main`
(`f553c49` → final readiness audit `cb5e8ca`). Per mission rules, Linux is
NOT rerun from Windows; this gate verifies the canonical source content
matches what Linux validated.

## Source identity chain (all verified 2026-10-08 from origin/main)

| Link | Value | Status |
|---|---|---|
| Linux `SOURCE_SHA` (`evidence/phase3/raw/linux/patch_handoff/identity.json`) | `b68f8944300f104875d953fc8e4510908c9aaf0b` | matches handoff and canonical base |
| Linux `PATCH_SHA256_0001` | `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20` | identical blob (P41 re-hash) |
| Linux `PATCH_SHA256_0002` | `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532` | identical blob (P41 re-hash) |
| Linux `patch_modified_by_linux` | `false` + tracked-diff audit | no mutation |
| Linux baseline tree | clean at `b68f894`, every file blob-byte-verified (`source_identity.txt`) | provenance complete |
| Windows canonical commits (P45) | 8/8 files byte-identical to `b68f894` + same two patches | **canonical == Linux-validated content** |

## Linux regression results preserved (from `findings/phase3/linux/linux_conclusion.json`)

- BatchNorm: unpatched 8/8 → patched 8/8 (fresh isolated caches per leg).
- Numerical regression: **bit-identical, overall max_abs_error 0.0 across
  37 tensors** (y/xgrad/wgrad/bgrad/running stats; 6 cases incl. the
  MIOpen#3956 repro and YOLO-like shapes; CPU-referenced).
- Non-BN RTC workload matrix: 11/11 → 11/11.
- Kthvalue runtime A/B: **unpatched PASS → patched PASS** (correct values
  and indices; adversarial falsification review PASS).
- YOLO predict + train (AMP-default self-disabled → FP32, and amp=False):
  PASS both, with in-stream binding match and fresh cache rerun.
- Source-built MIOpen A/B: unpatched 690/690, patched 800/800.

## Conclusion

The canonical two-commit reconstruction validated on Windows in Phase 4 is
byte-equal to the source Linux validated (same base SHA, same patch blobs,
proven 8/8 equivalence). The Linux PASS→PASS regression conclusion
therefore carries over to the canonical commits without rerunning Linux.
No Linux claims are being re-made beyond what the independent validator's
evidence shows; nothing in Phase 4 modifies it.
