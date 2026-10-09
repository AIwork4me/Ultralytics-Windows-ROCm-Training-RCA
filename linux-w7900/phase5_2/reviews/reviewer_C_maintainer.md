# Reviewer C — MIOpen Upstream Maintainer (Gate B11)

Fresh-context subagent; scratch /tmp/opencode/rC/.

VERDICT: **PASS**

BLOCKERS: none. MAJORS: none.

Verified independently (all reproduced):
1. Candidate identity via the strict consumer (PASS exit 0; pins
   P5.1-CANDIDATE-R1 / 7c5866144ac4 / 797a69b5ae86 / 605d0d214acd).
2. Same-base A/B discipline: frozen-base-checkout HEAD == 7c586614...;
   CMAKE_HOME_DIRECTORY proves the leg-A build used the frozen source;
   leg-b path enforces write-tree == head_tree_sha1 (exit 3 on mismatch).
3. Two distinct baselines (6af347af... vs 7e045dc0...) with correct
   provenance docs; MIOpenDriver 3.6.2 bound through the frozen prefix.
4. Harness on the frozen leg (UNPATCHED, allowed): PASS 3/3; dladdr
   provenance; KthvalueFwd dispatch; RTC LoadBinary(miss)->compile->
   SaveBinary; 0 mismatches.
5. Cache isolation per label; patched-cache EMPTY; stale-cache refusal
   fires on label reuse.
6. Patch scope: exactly 10 changed files, set-identical to manifest, blob
   SHAs match.
7. No premature Linux PASS claims; linux_validation_status PENDING;
   patched dirs all empty.
8. Runbook review: defensible as written.

MINORs M-1/M-2/M-3 (doc-only) — ALL RESOLVED post-panel (runbook
re-materialization block + historical-prefix warning; mandatory STOP
protocol; CMakeCache identity diff recording). NITs N-1..N-4 folded in.

Maintainer's note: the write-tree identity gate, dladdr in-stream
provenance, zero-init outputs vs stale-memory false passes, and the honest
Linux negative-mode expectation with explicit anti-spoofing prohibition
are exactly the disciplines demanded of an upstream submission.

REQUIRED FIXES: none blocking Gate B11.
