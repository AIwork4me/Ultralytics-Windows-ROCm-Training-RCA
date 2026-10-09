# H01 independent audit — R2 evidence acquisition & integrity

Reviewer: independent subagent (fresh rerun; first attempt returned garbled
output and was discarded, not counted). Read-only, own commands.

VERDICT: **PASS**. BLOCKERS: none. MAJORS: none.

Independently verified: all three patch SHA256s + byte sizes + series hash
(48308f6d) recomputed; pinned clone at c841716, clean, manifest sha 55e88f4c
with candidate/base/tree pins; consumer check_final_handoff_r2.py
byte-identical (b82bb227) to the published W7900 version; consumer check-only
PASS on the reviewer's own invocation; matrix runner diff vs W7900 original
is path-constants only; matrix JSON: 18 negative/refusal controls + positive
control all PASS with intended reasons; 16b exit 128 cause independently
reproduced (docs/ blob 1fe5fd66 absent in the partial store) and accepted as
a documented environment limitation with H02's multi-method reconstruction
as the compensating control.

MINORS (remediated/noted):
1. 16b annotation now embedded in evidence/h01_adversarial_matrix.json.
2. Consumer self-labels "L02" — mandated by byte-identity; matrix runner
   emits H01.
3. legB-m2 M2 workspace is reset to base by design; M2 identity carried by
   logs/h02_reconstruct2.log + evidence/h02_m2_tree.txt + reviewer's own
   scratch re-derivation.
