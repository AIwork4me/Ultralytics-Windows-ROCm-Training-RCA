# FINAL SUBMISSION CHECKLIST — P5.1-CANDIDATE-R2

State: LOCAL CANDIDATE ONLY. Nothing below authorizes upstream action.

## Done (machine-verified)
- [x] R1 immutable (branch @ 4949076; patches re-hash to frozen values).
- [x] Linux 5.2.1 findings incorporated (F-C2-1/2/3) + F-C2-4 loader fix.
- [x] Windows no-STL regression test remains hard PASS (ctest Passed, not skipped).
- [x] Linux INCONCLUSIVE → SKIP semantics proven (fixture + matrix cell);
      no genuine failure converted into SKIP (exit 1 → Failed everywhere).
- [x] MIOpen test-selection policy preserved (guard replicated; BF16 leg proof).
- [x] Production MIOpen source bytes unchanged vs R1 (per-blob identity).
- [x] Windows 13/13 adversarial matrix (independently re-executed).
- [x] Windows CMake/CTest fresh-build validation (incl. clean-env ctest).
- [x] DLL rebuilt + provenance-verified (loaded path + SHA in-process).
- [x] BatchNorm + numerics regression PASS; YOLO26n training PASS.
- [x] AMP behavior truthfully disclosed (this run: genuine amp=True; R1
      environment-fallback history recorded).
- [x] Three-commit series independently verified (git am + git apply both
      reproduce tree b983cadd; patch/series SHA256 re-hash from bytes).
- [x] R2 manifest contains ONLY R2 identities (39/39 consistency checks);
      R1 manifest intact on its branch.
- [x] Linux handoff unambiguous (R2-only identities, consumer pin update
      requirement stated).
- [x] Copyright/DCO accurately recorded; no Signed-off-by, no markers.
- [x] Every gate independently audited; no unresolved BLOCKER/MAJOR.
- [x] Evidence published to the R2 branch (see publication record).
- [x] No upstream PR / issue / comment created.

## Pending — human decisions (in order)
1. **DCO certification decision** — if the user chooses to sign off, the
   three commits must be regenerated with the trailer (ALL identities
   change: commits, patch SHA256s, series hash, tree stays, manifest,
   handoff doc). See docs/phase5_1_r2/COPYRIGHT_DCO_STATUS.md.
2. **Linux W7900 R2 validation** — independent validator executes
   docs/phase5_1_r2/LINUX_FINAL_VALIDATION_HANDOFF.md; results recorded on
   the Linux evidence branch; R2 manifest linux_validation_status updated
   by that mission (not from Windows).
3. **Submission-day develop re-check** — verify 7c586614 is still a sane
   base (or rebase decision); re-run the quick Windows validation battery
   on the final tree if anything moved.
4. **Explicit submission authorization** — only then create the upstream
   PR from docs/phase5_1_r2/UPSTREAM_PR_DRAFT.md (update Linux status +
   re-check identities first).

## Never
- Never force-push or rewrite the published R1/R2 evidence branches.
- Never describe unsigned commits as DCO-certified.
- Never claim Linux PASS from Windows-side evidence.
- Never bypass integrity checks (verify_*.py must pass on real bytes).
