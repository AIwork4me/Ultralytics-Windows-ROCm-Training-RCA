# H09 independent audit — cross-platform claims

VERDICT: CONDITIONAL PASS -> remediated to PASS. BLOCKERS: none. MAJORS: none.
Reviewer independently recomputed all patch/series hashes (two methods),
leg hashes, dump-pair byte equality (15/15 cmp), the six BN CHECK values
against run logs, CTest log contents, YOLO binding line, and the Windows
(manifest) + W7900 (L09/L07 JSONs) cells — every checkable claim verified
against primary evidence. Claim discipline (FAIL->PASS vs PASS->PASS not
mixed; no cross-arch equality claim; skip semantics) confirmed.

MINORS (all remediated):
1. "4-6 orders below tolerance" was inaccurate (true margins 1.4-7.6 orders,
   min 26x on y) — corrected in matrix and summary; the same phrase in the
   W7900 summary is flagged back to that branch as an erratum candidate.
2. "first-ever" BF16 scoped to this three-platform R2 program.
3. Row-16 forward reference relabeled "intended final verdict".
