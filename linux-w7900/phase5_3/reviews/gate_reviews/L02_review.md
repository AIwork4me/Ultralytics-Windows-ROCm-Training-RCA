# Gate L02 Independent Subagent Review — Security / False-Acceptance Audit
Reviewer: fresh general subagent (ses_ee05fec3cffeZxBG17o61L7XnW)
## VERDICT: CONDITIONAL PASS -> resolved to PASS
No false-acceptance path found under default or attacker-controlled invocation.
Auditor ran 5 additional novel attacks (missing sha256, absolute path, schema_version 2,
exec bit, dirty checkout) - all rejected fail-closed. Deep defenses caught attacks even
when a primary pin was bypassed.
### Findings & resolutions
- M1 (--expect-* overrides weak without secondary auth; empty manifest pin disables check)
  -> RESOLVED: ALLOW_EXPECT_OVERRIDE=1 now required for any non-default expectation;
  empty --expect-manifest-sha256 hard-errors. Verified: unauthorized override exit 1.
- M2 (KeyError crash on missing per-patch sha256) -> RESOLVED: clean JSON failure
  (matrix check 17). Fail-closed behavior was already the case.
- NIT-1 (apply TOCTOU window sha256_file->git apply) -> accepted residual, documented.
- NIT-2 (README.md allowlisted without content pin) -> accepted; not series-hashed.
- NIT-3 (docstring count 19 vs 16 statuses) -> RESOLVED: corrected to 16.
- NIT-4 (MIOPEN_WS_ROOT influences base-commit presence check only) -> accepted.
### Final state
Matrix 20/20 (incl. M2 regression test 17); positive control PASS exit 0.
