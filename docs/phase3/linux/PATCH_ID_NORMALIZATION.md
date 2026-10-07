# PATCH_ID Normalization — P3-FINAL → P3-FINAL-R3

Date: 2026-10-08
Gate: F02 (final integration closure)
Actor: Linux validator (this branch)

## What changed

Current Phase-3 Linux/final summary and structured-conclusion documents
previously identified the final patch series as `P3-FINAL`, an earlier
shorthand used while the Linux branch consumed the handoff. The
authoritative immutable handoff published at
`findings/phase3/PATCH_HANDOFF.json` (origin/main, commit `e43321f`)
defines the identity as:

```text
PATCH_ID    P3-FINAL-R3
SOURCE_SHA  b68f8944300f104875d953fc8e4510908c9aaf0b
0001 SHA256 f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20
0002 SHA256 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532
series      b1150afcf2170a9d396f9a25669547c0ed4021c221f7feaa59e073d4b9706685
```

`P3-FINAL` and `P3-FINAL-R3` refer to the **same patch bytes**: the Linux
branch consumed the handoff (recorded at execution time as `P3-FINAL`)
with byte-identical SHA256 values for 0001, 0002, and the ordered series
at the same SOURCE_SHA. The later handoff publication on origin/main
assigned the final revision label `P3-FINAL-R3`. This is a metadata label
normalization only.

**Patch bytes were not changed.** No patch file, patch content, line
endings, or SOURCE_SHA were modified by this normalization.

## Documents normalized (current summaries / structured conclusions)

| Document | Change |
|---|---|
| `findings/phase3/linux/linux_conclusion.json` | `patch_id`: `P3-FINAL` → `P3-FINAL-R3` |
| `docs/phase3/linux/LINUX_VALIDATION_SUMMARY.md` | `PATCH_ID` line → `P3-FINAL-R3` |
| `docs/phase3/linux/LINUX_REGRESSION_MATRIX.md` | prose reference → `P3-FINAL-R3` |
| `docs/phase3/CROSS_PLATFORM_VALIDATION.md` | `PATCH_ID` line → `P3-FINAL-R3` |
| `findings/phase3/linux/final_gate.md` | prose reference → `P3-FINAL-R3` |

## Documents intentionally left unchanged (historical evidence)

These recorded the shorthand as it existed at execution time and are
kept immutable so historical evidence chronology is preserved:

| Document | Reason |
|---|---|
| `evidence/phase3/raw/linux/patch_handoff/identity.json` | raw capture of the handoff identity as consumed |
| `evidence/phase3/raw/linux/patch_handoff/identity_audit.txt` | raw capture of the handoff identity audit |
| `evidence/phase3/raw/linux/build_patched/provenance.txt` | raw build provenance recorded at execution time |
| `findings/phase3/linux/BLOCKED_ON_PATCH_HANDOFF.resolved.md` | historical blocked→resolved event record |
| `findings/phase3/linux/subagent_maintainer_review.md` | historical independent review, performed under the then-current label |

## Verification

The handoff verifier (`git cat-file blob` recomputation of both patch
SHA256s and the ordered series SHA256) was re-run against origin/main
immediately before and after this normalization and the subsequent
merge; all values MATCH at every checkpoint. See
`evidence/phase3/raw/linux/final_integration/handoff_premerge_verification.txt`
and `handoff_postmerge_verification.txt`.
