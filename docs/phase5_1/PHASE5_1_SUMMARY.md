# Phase 5.1 Summary — Final Candidate Freeze

**Date:** 2026-10-08 · **Branch:** `phase5.1/windows-final-candidate-freeze`
**Verdict:** `TECHNICAL_CANDIDATE_FROZEN — HUMAN_AUTHORIZATION_PENDING`

Phase 5.1 finalized the upstream submission candidate for the MIOpen
HIPRTC no-host-STL fix: handoff-consistency repair, copyright
attribution under confirmed right-to-contribute, honest DCO handling,
full targeted Windows revalidation, an authoritative Linux handoff,
independent freeze verification, and three adversarial reviews. **No
upstream action was taken** (no PR, no issue, no comment; nothing pushed
to any ROCm repository).

## What changed vs Phase 5

1. **P5.1-CANDIDATE-R1** rebuilt from the frozen base
   `7c586614` (develop, 2026-10-08) with the SAME three logical commits
   and byte-identical commit messages; the only source delta vs
   P5-CANDIDATE-R1 is FOUR copyright placeholder comment lines replaced
   with `Copyright (c) 2026 AIwork4me` (+4/−4 lines, 4 files), under the
   user's explicit right-to-contribute confirmation (2026-10-08).
   New identities: commits `d4003de1` / `3b18a065` / `e7ff6d75`;
   patch SHA256 `14719b8b…` / `7d40c314…` / `3eb20ec0…`; series
   `797a69b5…`; head tree `605d0d21…`.
2. **Handoff inconsistencies repaired** (Gate 02): stale intermediate
   commit IDs and pre-amendment patch/series hashes removed from
   `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md` (now superseded-banner
   + corrected values); `phase5_conclusion.json` `commit_subjects` order
   fixed to match the SHA array; every current doc corrected to say FOUR
   copyright files. Consistency validator
   `scripts/phase5_1/verify_handoff_consistency.py`: **pre-fix 6/10 →
   post-fix 10/10** (evidence under `evidence/phase5_1/consistency/`).
3. **Kthvalue method corrected** (Gate 03): the Linux handoff's primary
   Kthvalue regression method is now the DIRECT
   `miopenKthvalueForward` runtime harness (Phase-3 validated; solver →
   `MIOpenKthvalue.cpp` → patched `radix.hpp`, dladdr provenance, fresh
   isolated caches, exact known cases, A/B byte-comparison);
   `torch.topk/kthvalue` demoted to supplemental-only.
4. **DCO handled honestly** (Gate 04): upstream CONTRIBUTING.md files
   (root + projects/miopen) state no DCO requirement; the user did not
   authorize certification → `DCO_ATTESTATION_PENDING` retained, explicit
   markers kept, exact reword instructions prepared
   (`docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md`).

## Windows revalidation (GATE 07, full scope because source bytes changed)

| Gate | Result |
|---|---|
| CMake configure / test build / ctest discovery / ctest run | PASS 4/4 at `e7ff6d75` |
| HIPRTC A/B regression matrix (incl. adversarial controls) | PASS 13/13 |
| MIOpen.dll rebuild | PASS — SHA256 `9a7744029ccd…` (built from the exact final commit) |
| DLL load provenance (in-process path + SHA) | PASS |
| No-STL fresh-cache BatchNorm train/backward (MSVC include isolated) | PASS |
| BatchNorm numerics vs CPU fp64 (pre-fixed tolerances) | PASS — bit-identical to P5 values (comment-only change) |
| YOLO26n coco8 1-epoch GPU train | PASS `amp=False` (required minimum) and `amp_default` as training; AMP-check environment attribution control recorded (fails for P5 DLL and pristine wheel too ⇒ environment, not the candidate) |
| Environment restoration (wheel DLL 74b4ee03, MSVC tree) | PASS, hash-verified |

## Independent verification

- **Freeze integrity (GATE 09, fresh verifier subagent):** FREEZE VERDICT
  PASS — six verdict tokens true; source reconstructed three independent
  ways to the exact tree; `evidence/phase5_1/freeze_integrity.json`,
  `findings/phase5_1/freeze_review.md`.
- **Reviewer A (git/patch integrity):** PASS — 0 BLOCKER/MAJOR.
- **Reviewer B (MIOpen/Linux regression):** PASS — 0 BLOCKER/MAJOR.
- **Reviewer C (DCO/submission):** CONDITIONAL PASS — 1 MAJOR
  (stale "three files" text) **resolved pre-publication** with all
  MINORs; see `findings/phase5_1/reviews/resolutions.json` (all
  findings resolved or accepted-with-rationale; 0 open).

## What remains for a human

1. **DCO decision** — certify (exact commands in
   `docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md` §3) or proceed unsigned
   if maintainers accept that; the candidate is NOT labeled
   submission-ready until decided.
2. **Linux validation** — execute
   `findings/phase5_1/FINAL_HANDOFF.json` /
   `docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md` (direct
   `miopenKthvalueForward` harness included); status PENDING.
3. **Submission day** — re-check develop applicability (Gate P5-02
   method); regenerate the PR draft from the P5.1 manifest.

## Authoritative artifacts

```text
findings/phase5_1/FINAL_HANDOFF.json      ← single identity authority
docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md  (generated from it)
patches/phase5_1/canonical/*.patch        ← P5.1 series (byte-exact)
docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md
findings/phase5_1/phase5_1_conclusion.json
evidence/phase5_1/**                      ← raw validation evidence
```

Historical Phase-3/4/5 evidence and the P5-CANDIDATE-R1 series are
immutable and untouched.
