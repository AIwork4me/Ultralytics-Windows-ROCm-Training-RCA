# Gate C1 — Independent Subagent Review (Phase 5.2.1)

Reviewer: fresh-context adversarial subagent (general agent), no prior session state.
Scope: falsify the Gate-1 reproducibility claims; read-only + disposable clone.

## Sub-check verdicts

1. Branch base & ancestry — **PASS**
   merge-base(linux-w7900/phase5.2.1-ci-closure, origin/main) = 4754622fdad…;
   5883db9 and c4f9da2 both ancestors of HEAD.
2. No rebase/rewrite — **PASS**
   Merge commit 90c3d38 has parents 4754622 + c4f9da2 (true merge);
   published phase-5.2 commits are byte-identical objects (same SHAs,
   authors, dates); origin/linux-w7900/phase5.2-handoff-bridge tip unchanged.
3. Wrapper spot-check — **PASS (strengthened: all 21 checked)**
   HEAD blob == operative local file == manifest sha256 for 21/21.
   SUPERSEDES pair verified adversarially: prepare_validation_legs.sh
   (2f750c26… vs published 2ea9395a…, +15/−6) and run_validation_leg.sh
   (856d1322… vs published 8c9d8ddc…, +16/−4); published preflight copies
   remain byte-identical to origin/main in the branch.
4. Windows phase-5/5.1 preservation — **PASS**
   Full diff vs origin/main = 75 files, all additions, all under
   linux-w7900/; zero modifications/deletions. Freeze tip still
   494907699f3b…; the three canonical patches re-hash to the frozen
   values 14719b8b… / 7d40c314… / 3eb20ec0….
5. Fresh-clone re-run — **PASS**
   Reviewer's own clone + fetch + verify_clean_checkout.py →
   C1 PASS (21 wrappers), C2 PASS (34 refs), C3 PASS (8 entry points),
   C4 PASS, C5 PASS → VERIFY RESULT: PASS. Clone deleted afterwards.
6. Reproducibility-gap hunt — **PASS**
   No unmanifested drift (local 21 == manifest 21 == HEAD 21);
   the two git-retry.sh variants correctly distinct entries;
   15 unresolved doc basenames found are upstream MIOpen source
   references, not local wrapper claims.

## Notes (non-blocking)

- verify_clean_checkout.py C4 freeze-tip check silently skips when the
  freeze branch is not fetched; the documented procedure includes the
  fetch and the reviewer's run confirmed the tip.
- The committed C1 log records the pre-log commit HEAD (stale by
  construction); reviewer re-ran verification at the log commit and
  reproduced PASS.

## Overall verdict: **APPROVED**

The branch is correctly based on current origin/main, integrates the
published phase-5.2 history as a true merge with byte-identical commits,
preserves all Windows phase-5/5.1 artifacts and the freeze tip, and
reproduces PASS from a clean checkout.
