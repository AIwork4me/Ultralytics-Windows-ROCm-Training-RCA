# Gate L05 Independent Subagent Review — Build Isolation / Same-Variable Audit
Reviewer: fresh general subagent (ses_ee040566cffejpC2wJLogKLjkN)
## VERDICT: PASS
All 6 claims independently reproduced (0 BLOCKER/MAJOR). Notable independent checks:
395/638 compile_commands entries reference final-patched, 0 reference legA/upstream-pristine;
0 rocm-7.2.1 in cache/compile_commands/binary; wrapper byte-identical to published manifest
(5146289a); 10-file delta exactly matches R2 series; test target absent from leg build.
### Findings & resolutions
- MINOR-1 (configure log is re-configure) -> RESOLVED: primordial configure preserved in
  L05_build_driver_preserved.log; cache equality + contamination independently re-verified.
- MINOR-2 (editorialized version_string) -> RESOLVED: literal "MIOpen version 3.6.2.cd117724af"
  recorded with git-derive explanation.
- MINOR-3 (cache-type annotation STRING vs UNINITIALIZED) -> documented; values identical.
- NITs: MIOPEN_USER_DB_SUFFIX per-leg divergence documented (aids cache isolation);
  MIOPEN_JOBS=64 not echoed in logs (immaterial); partial-clone object store note for auditors
  (use GIT_ALTERNATE_OBJECT_DIRECTORIES or frozen-base-checkout).
