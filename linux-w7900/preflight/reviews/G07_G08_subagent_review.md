# G07 + G08 Independent Subagent Review — A/B Isolation & Adversarial Handoff-Consumer Audit

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## PART 1 — G07 A/B isolation: PASS (scripts)

- Identical cmake flags for both legs confirmed (single literal in
  build_leg_miopen.sh; only SOURCE/BUILD/INSTALL env vars differ).
- Cache roots per leg; live stale-label refusal test: exit 2, nothing exec'd.
- B directories verified EMPTY at audit time.
- leg-b gating verified: requires manifest, runs strict check-only first;
  --apply additionally interlocked behind ENABLE_APPLY=1.

Findings (Part 1):
- PENDING deliverables VALIDATION_LEG_DESIGN.md / G07_readiness.json at
  audit time — DELIVERED after the audit.
- NIT stale-cache refusal exempted a lone `xdg` entry — FIXED (refusal now
  scans the whole cache dir incl. xdg subtree).
- INFO leg-b hard-codes a radix.hpp existence assertion — acceptable.

## PART 2 — G08 adversarial consumer audit: CONDITIONAL PASS (pre-fix)

Attack results on the ORIGINAL implementation:

| Attack | Result | Real vulnerability |
|---|---|---|
| valid manifest | ACCEPTED | no (sanity) |
| self-consistent reorder | ACCEPTED | no (manifest defines order; check+apply iterate identically) |
| tampered twins via rca_repo_root vs manifest-dir divergence | ACCEPTED | YES — HIGH |
| unlisted EXTRA.patch sibling | ACCEPTED | YES — MEDIUM-LOW |
| duplicate path | REJECTED | no |
| 39/41-char + uppercase sha | REJECTED x3 | no |
| mode typo/missing | REJECTED x2 | no |
| ../ traversal, absolute /etc/passwd | ACCEPTED | YES — MEDIUM |
| stale anchors (base + evidence commit) | REJECTED x2 | no |
| hash_chain swapped order | REJECTED | no (order-sensitive) |
| hash_chain per documented definition | REJECTED | YES — MEDIUM (doc/impl mismatch) |

## REQUIRED ACTIONS — ALL RESOLVED same-session

1. Check/apply root divergence — FIXED: one resolution routine; root must be
   explicit (--rca-root or rca_repo_root); silent manifest-dir default
   removed; apply re-verifies sha256 immediately before each git apply.
2. hash_chain — FIXED: implemented exactly as documented
   (h0=sha256(seed); h_i=sha256(h_{i-1}||sha256(patch_i).digest())).
3. Path containment — FIXED: relative-only, no ~, no absolute, containment
   via commonpath, symlinks/non-regular rejected.
4. Unlisted files — FIXED: any unlisted regular file in a patch dir fails
   verification; producer rule documented.

Post-fix regression matrix re-verified by primary agent (valid PASS;
hash_chain PASS; swapped-order chain FAIL; ambiguous root FAIL; EXTRA.patch
FAIL; traversal FAIL; absolute FAIL; apply interlock intact).

Gates G07/G08 final: PASS.
