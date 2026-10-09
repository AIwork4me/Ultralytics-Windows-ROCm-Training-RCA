# H00 independent audit — hardware & ROCm environment

Reviewer: independent subagent (general-purpose), read-only, own commands.
Verdict: **PASS**. BLOCKERS: none. MAJORS: none.

MINORS:
1. Distro-packaged `/lib/x86_64-linux-gnu/libamdhip64.so.5` (v5-era) is a third
   userspace fragment beyond the documented /opt/rocm-7.2.1 stack. Accepted into
   the contamination checklist: source-leg runs must show wheel libamdhip64.so.7
   (sha256 6f3c9fe6...) in provenance, never the .5 soname.
2. tmp/ holds a repo-like checkout early (the pinned-evidence worktree);
   superseded by tmp/r2-evidence-clone for verifier runs; worktree removed at
   publication cleanup.

Verified independently: GPU 8060S gfx1151 (rocminfo, no HSA_OVERRIDE anywhere);
Ubuntu 24.04.4 / 6.17.0-1032-oem; dual ROCm stacks (7.2.1 system ldconfig,
7.14 wheel with AMD clang 23.0.0git 46fcb339+PATCHED:440716f8); torch
2.12.0+rocm7.14.0 HIP 7.14.60850 cuda_avail=True; Phase-3 assets unmodified
(baseline clean @ b68f894; patched has exactly the 8 preserved P3 entries);
all 5 claimed SHA256s recomputed and matched; 32 threads / 94 GB RAM / 279 G
free; phase5_3b workspace contains zero symlinks into historical paths.
