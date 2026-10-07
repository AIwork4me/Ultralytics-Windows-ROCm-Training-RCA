# Subagent Regression Attack Review — Gate L43

Date: 2026-10-08. Independent adversarial reviewer (fresh context), mission
"assume the patch causes a Linux regression — find it."

## Verdict (reviewer)

**NO_REGRESSION_CONFIRMED** (with 4 MAJOR evidence-integrity findings, all
validator-side record-keeping; none in the MIOpen behavior chain)

## Reviewer's independent reproductions

- Two libMIOpen.so differ only by the patch (+ honest `-dirty` version suffix)
- Kernel-cache footprints identical per leg (ukdb sizes equal pairwise;
  same kernel sets compiled both legs)
- Cross-build BN numerics genuinely bit-identical (recomputed max|unp−pat|=0.0
  from the saved tensors; both differ from CPU by ~1e-6 — real data)
- With-STL preprocessed kernels token-identical (reviewer EXTENDED arm A:
  type_traits.hpp and tensor_view.hpp also identical; radix differs by
  design, value-identical)
- Arm C no-STL environment independently validated with -H (only 4 kernel
  headers resolve, zero C++ stdlib); -D__global__= neutralization cannot
  create a false PASS
- Patch application round-trip re-done from scratch in a scratch dir:
  byte-identical to the patched worktree; tracked-diff sha reproduced
- 8/8 BN + 11/11 non-BN + YOLO predict/train×2 PASS under the patched lib

## Reviewer findings → validator remediation (GATE L46)

- MAJOR-1 stale conclusions layer → rewritten this commit
- MAJOR-2 unmanifested run-2 evidence → manifest regenerated this commit
- MAJOR-3 run_with_source_miopen.sh used LD_LIBRARY_PATH only (its own
  probe output proves the wheel binds under that mechanism) → script FIXED
  to LD_PRELOAD + dladdr echo + per-label fresh cache; YOLO train re-run
  under the fixed harness with in-stream binding proof
  (yolo_train_patched_amp_false_v2_bound.txt: bound → patched, MATCH, rc=0)
- MAJOR-4 parity claim wording → parity_note.txt + archive added earlier
  same remediation pass (Eigen find_package-vs-FetchContent residue
  documented; 690/800 incremental-vs-full explanation)
- MINOR-5 `-dirty` suffix disclosed in matrix note
- MINOR-6 YOLO train binding/cache → closed by the v2 rerun above
- MINOR-7 arm-B narrative/docstring rot → corrected (partial-STL reality);
  docstrings rewritten
- MINOR-8 arm-A scope → reviewer's own extension recorded in canary
  docstring; radix delta documented as designed
- MINOR-9 non-BN finiteness-only + unexercised families → documented as
  residuals in summary conditions (mirrors Windows-side decision)
- NIT-10 run_fresh_cache.sh env mismatch → superseded by the fixed
  run_with_source_miopen.sh (the actual harness used and now recorded)

(Full verbatim reviewer text preserved in the session record and reflected
above; the complete findings list is as returned.)
