# Resolutions — review findings across Phase 5.2 (W7900-PHASE52-BRIDGE-R1)

| Gate | Finding | Severity | Resolution |
|---|---|---|---|
| B00 | placeholder timestamp in evidence JSON | NIT | fixed (real timestamp) |
| B00 | GPU reported as "W7900D" | MINOR | documented; PCI 1002:744b/gfx1100 is the authoritative identity; folded into final conclusion environment record |
| B01 | head_tree_sha1 declaration-only at B01; manifest/doc hashes unpinned | MINOR/NIT | tree reproduced in B05 (two methods + auditor); all artifact hashes pinned in B01 evidence and in the consumer |
| B02/B03 | F1 manifest sha not pinned | MINOR | FIXED: EXPECTED.manifest_sha256 pin + blob-match when manifest is inside the pinned checkout |
| B02/B03 | F2 harness not re-runnable | MINOR | FIXED: exist_ok + rmtree; two consecutive clean runs verified |
| B02/B03 | F3 exit codes null in matrix | MINOR | FIXED: consumer_exit_code recorded for every attack |
| B02/B03 | F4 frozen-untouched asserted | NIT | FIXED: real git status + rev-parse verification recorded |
| B02/B03 | F5 effective pins invisible | NIT | FIXED: effective_expect_pins embedded in check-only reports |
| B02/B03 | F6 symlinked .git + double cat-file | NIT | FIXED: islink rejection; single cat-file call |
| B04/B05 | recon worktrees left registered | MINOR | CLEANED after evidence capture (frozen-base-checkout retained for leg A) |
| B04/B05 | method-A commit SHAs committer-dependent | NIT | expected git behavior; tree SHA is the identity (matches Windows note) |
| B06 | __has_include spoofable via -D | MINOR | recorded in evidence; runbook forbids -D__has_include overrides; not exploitable in planned A/B (MIOpen builds its own options) |
| B06 | axpy host over-read | MINOR | documented cosmetic; no evidential impact |
| B07 | ldconfig maps ROCm sonames to /opt/rocm-7.2.1 | MINOR | mitigated by LD_LIBRARY_PATH precedence (LD_DEBUG proof); runbook forbids launching without env_rocm7141.sh |
| B07 | wheel-shadowing guard load-bearing | MINOR | runbook mandates run_validation_leg.sh for every leg |
| B08 | leg-b RCA pins env-overridable | MINOR | accepted (defaults pinned; overrides restricted to authorized final mission, commented) |
| B08 | predisk log bare | NIT | accepted (value recorded in evidence JSON) |
| B09 | FRESH_CACHE_FORCE silent | NIT | FIXED: explicit OVERRIDE warning (downgrades evidence grade, printed) |
| B09 | harness sha not printed by wrapper | NIT | FIXED: wrapper prints first executable argument's sha256 |
| B09 | frozen leg unreachable by wrapper | NIT | FIXED: new leg name 'legA-frozen' |
| B10 | symlinked --rca-root aliasing | NIT (informational) | content-neutral (git HEAD pin + hashes bind everything); accepted |
| B10 | --expect-manifest-sha256 '' relaxation | NIT (informational) | by design for adversarial tests; never used in frozen operation; accepted |
| B11-A | space-pruned develop checkout | NIT | pre-existing; integrity unaffected (index-only methods) |
| B11-A | HEX40/HEX64 duplication | NIT | cosmetic; accepted |
| B11-B | W7900D marketing name | NIT | folded into conclusion environment record |
| B11-B | B07 log leg annotation | NIT | sha printed in-stream (recoverable); accepted |
| B11-C | M-1 leg-a script mode targets historical prefix | MINOR | FIXED: runbook re-materialization block + in-script warning |
| B11-C | M-2 no abort protocol | MINOR | FIXED: mandatory STOP protocol in runbook |
| B11-C | M-3 flag identity not recorded | MINOR | FIXED: CMakeCache identity diff step in runbook |
| B11-C | N-1..N-4 (ctest cache, patched driver bind, env refresh, tensor_view smoke) | NIT | folded into runbook |

No unresolved BLOCKER or MAJOR findings exist.
