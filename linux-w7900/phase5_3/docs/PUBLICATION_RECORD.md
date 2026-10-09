# PUBLICATION RECORD — Phase 5.3

Branch: `linux-w7900/phase5.3-r2-final-ab`
Base: RCA `origin/main` @ `73e51c440c53c1fb12594fe959934f494ab86235`
Evidence commit (Phase 5.3 package): `86c4ea13d1e25f9ec0b865b5b1a5461b6d8f1636`
Publication-record commit: this commit (see git log).

## Push

First attempt: proxy CONNECT tunnel 503 (transient egress-proxy failure; recorded in
mission workspace log). Second retry window: first attempt 503 again, second attempt
succeeded. No force-push used at any point.

## Post-push remote verification (all performed against the remote ref)

- `git ls-remote origin refs/heads/linux-w7900/phase5.3-r2-final-ab`
  → `86c4ea13d1e25f9ec0b865b5b1a5461b6d8f1636` (equals local branch tip).
- Remote vs local `git ls-tree -r` blob-hash comparison over all 134 files: MATCH.
- Clean-checkout verification (`git worktree add` at the remote tip):
  - `evidence/evidence_manifest.json` byte-check over 133 files: ALL MATCH.
  - `findings/FINAL_LINUX_VALIDATION.json` verdict consistent:
    `PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP`.
  - Required evidence files L00–L11 + manifest: ALL present.
  - Published L08 logs re-checked (dispatch lines + exit files): OK for both legs.
- Windows frozen branches unchanged on the remote:
  - `phase5.1/windows-r2-ci-portability-freeze` → `c8417161125dc33275b7ac615298b449a81e7cf8`
  - `phase5.1/windows-final-candidate-freeze` → `494907699f3b57095663f0a70b42278001a8efb7`

## Boundaries honored

No merge into main. No internal or upstream PR. No upstream issue/comment. No DCO
sign-off. No modification of frozen Windows R2 artifacts or the frozen manifest (its
`linux_validation_status` remains PENDING at the evidence pin; this branch is the Linux
reporting authority per the R2 handoff §6).
