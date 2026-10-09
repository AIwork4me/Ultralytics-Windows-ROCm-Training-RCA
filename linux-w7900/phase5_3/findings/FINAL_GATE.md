# FINAL GATE — L13/L14 checklist

## Package completeness

- [x] docs/ (8 documents: summary, final A/B, CTest portability, kthvalue, batchnorm,
      provenance, upstream readiness, reproduction guide)
- [x] findings/FINAL_LINUX_VALIDATION.json (machine-readable verdict)
- [x] findings/FINAL_GATE.md, findings/OPEN_ISSUES.md
- [x] evidence/L00..L11 JSONs + L01_verifier_run + L02_positive_control +
      as_used_patch_copies + kthvalue_dumps (15×2) + evidence_manifest.json (130 files pinned)
- [x] logs/ (all raw gate logs incl. exit files)
- [x] scripts/ (consumer, verifiers, harnesses, matrix runners, checker, reproduction guide refs)
- [x] reviews/ (12 gate reviews + 4 final reviewers + resolutions)

## Exclusions honored (mission L13)

- [x] No shared libraries, build dirs, object files, wheel packages, model weights,
      datasets, kernel caches, or credentials committed. Hashes + reproduction commands
      published instead. YOLO weights/runs/coco8 excluded; kthvalue dumps (2.8 MB test
      outputs) included deliberately as the byte-level A/B evidence.

## Verdict chain

L00–L11 PASS (independent reviews, all findings resolved) → L12 panel (A: CONDITIONAL
PASS scoped to out-of-mission governance conditions; B/C/D: PASS) →
**PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP**

## Publication (L14)

Branch `linux-w7900/phase5.3-r2-final-ab` from current RCA main (73e51c44). Single
forward commit adding `linux-w7900/phase5_3/` only. No force-push, no PR, no merge to
main. Remote verification recorded after push in the publication record.
