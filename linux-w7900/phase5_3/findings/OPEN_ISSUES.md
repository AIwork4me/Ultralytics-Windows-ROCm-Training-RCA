# OPEN ISSUES — Phase 5.3 (post-mission state)

None block the final verdict (PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP). Tracked items,
by owner:

## Human/governance (before any upstream action)

1. DCO sign-off absent by design; `authorization_to_submit_upstream=false` in the frozen
   manifest. A new Windows-side candidate revision/manifest update is required before any
   upstream PR (do NOT mutate the frozen R2 manifest on Linux).
2. Execute the no-STL positive control once on an isolation-capable host and attach to
   the future PR (Linux permanently SKIPs: libhiprtc-builtins embeds C++ headers).

## Erratum (documentation of record; historical artifacts intentionally untouched)

3. Published Phase-5.2 artifacts (B08/B09/runbook) carry a 65-char harness-hash typo;
   corrected in Phase-5.3 docs (true 64-char digest pinned everywhere here).

## Upstream-improvement requests (future candidate revisions; not Linux blockers)

4. Extend the compile-only test to more kernel closures (PReLU/ReduceSum) so the
   freestanding initializer_list arm is guarded in the default suite.
5. Refactor skip-policy duplication into `add_test_command` or a shared helper.
6. Align/comment the test's define set vs production RTC defines.
7. Copyright header attribution review for the 4 new files (AMD convention).

## Environment notes for future validators

8. `env_rocm7141.sh` sets errexit when sourced; wrap adversarial harnesses accordingly.
9. The failing no-STL test binary can kill its invoking process tree in some shells;
   run under ctest isolation (as L07 does) for CI stability.
10. `/tmp` is a small tmpfs here — full rocm-libraries worktrees must live on /workspace.
11. GitHub release assets are unreachable through this host's egress proxy; HuggingFace
    official Ultralytics repos were used for the optional YOLO smoke provisioning.
