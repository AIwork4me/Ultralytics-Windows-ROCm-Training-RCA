# Gate R23 — Upstream Maintainer Design Review (two independent reviewers)

## REVIEWER A — MIOpen CMake maintainer (agent_21e750f8): VERDICT PASS

No BLOCKER/MAJOR. MINORs (both disclosure-quality, no code change required):
1. Link-policy divergence from src/CMakeLists.txt (:1093-1098 still WIN32-split) is
   justified but the comment omitted the load-bearing clause: the impl target survives
   the plain name only via transitive hip::host/hip::device; the test deliberately
   links nothing else. → RESOLVED: comment clause added to the block before freezing
   ("(The MIOpen implementation target survives the plain name only because it also
   links hip::host/hip::device, which carry the search paths; this test deliberately
   links nothing else.)").
2. Duplicated skip-guard may drift if the helper's policy evolves. Duplication judged
   correct given the helper-modification ban (local MIOPEN_TEST_GDB=Off needs
   save/restore + still cannot set SKIP_RETURN_CODE; helper parameterization touches
   ~200 registrations). → Documented in PR draft (Gate R34).

Verified by A: TARGET probe correct (find_package(hiprtc) :600 before test :968);
Linux/Windows parity (deltas = GDB-wrapper removal + WORKING_DIRECTORY drop, both
disclosed); no construct newer than CMake 3.15 (CMP0057 NEW set); skip-list behavior
correct incl. MIOPEN_NO_GPU/INT8/BF16; BUILD_TESTING gating untouched; zero new
platform sniffing (only pre-existing NOMINMAX WIN32 remains); top maintainer
objections pre-emptable.

## REVIEWER B — false-PASS / test-coverage auditor (agent_b306cd62): VERDICT PASS

No BLOCKER/MAJOR. MINORs:
1. M-1: theoretical probe-failure ambiguity in stdlib_is_reachable (false both when
   genuinely unreachable and when probe fails for unrelated reason without marker) —
   practically self-contradictory (probe uses identical option set with strictly
   simpler source); future-hardening option noted, no registration-side fix possible.
   → Documented; no change.
2. M-2: always-exit-4 tamper renders green where R1 rendered red — designed F-C2-1
   tradeoff; skip visible in ctest summary/did-not-run list; requires tracked source
   edit to exploit. Mitigation noted: RCA legs assert the test actually ran.
   → Documented; Windows validation (Gates R25/R26) proves the test RUNS and PASSES
   here, closing the practical hole for this platform.

Exit-code contract fully re-traced in the cpp: 0 only after probe-proven isolation +
successful compile + non-empty materialized code object (+ identity markers); 1 on any
verdict shortfall; 2 setup errors (renders Failed, no skip mapping); 4 only from the
two honesty probes (positive-mode reachable: line 474 only). Signature discrimination
direction confirmed: positive mode fails on ANY compile error (exit 1); negative mode
counts only the exact missing-STL signature as control success, anything else exit 4.

## Resolution summary
- Reviewer A MINOR 1: comment clause applied (diff re-verified clean, +44/-16).
- Reviewer A MINOR 2 + Reviewer B NIT-1 (MIOPEN_USER_DB_PATH env parity): PR-draft text.
- Reviewer B MINOR 1/2: documented limitations, no code change (outside registration scope).
No BLOCKER or MAJOR unresolved.
