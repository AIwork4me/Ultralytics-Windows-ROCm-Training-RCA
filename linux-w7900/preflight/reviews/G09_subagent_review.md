# G09 Independent Subagent Review — System State & Reproducibility

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC) — run retroactively before packaging (Reviewer C
  found the gate lacked its own review artifact)

## VERDICT: CONDITIONAL PASS -> PASS after fixes

## Verified live
- kernel 6.8.0-79-generic + amdgpu 6.16.13 unchanged
- /opt/rocm -> rocm-7.2.1; system libMIOpen sha256 bd03b864…d8d77eb4 match
- No global LD_PRELOAD / HSA_OVERRIDE_GFX_VERSION (env, /etc/environment,
  profile.d, bashrc)
- A/B caches separated; credential scan 0 hits
- All scripts executable; invocation table present
- pip check clean both venvs
- upstream-pristine radix.hpp UNPATCHED (line 30 unconditional
  #include <limits>; MIOPEN_HIP_RUNTIME_COMPILE guards only hip includes)
- STL probe rerun reproduced the exact matrix (default all 1s; isolation
  modes utility=0 others=1)
- repos/rocm-libraries: 54,688 porcelain entries ALL "D" (known worktree
  backfill transient; zero M/A/?? => no hidden local modifications)

## Findings
- MINOR — dpkg count figure in evidence/log wrong (17 vs reviewer's 50;
  pattern-dependent). RESOLVED: evidence now records all three counts with
  patterns + dpkg.log provenance (nothing installed/removed during mission).
- MINOR — logs/G05_stl_probe.log was stale (older 3-line include-test
  format; no archived matrix). RESOLVED: matrix rerun appended with fresh
  timestamp, byte-consistent with expectation.
- NIT — cache listing snapshot missed reviewerB-rerun (post-snapshot).
- NIT — g02_gpu_baseline.py exec bit recorded NOT-EXEC in log, fixed
  between log and JSON.

Gate G09 final: PASS.
