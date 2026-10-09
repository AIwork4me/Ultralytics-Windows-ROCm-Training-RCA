# H04 independent audit — two source-built legs

VERDICT: PASS. BLOCKERS: none. MAJORS: none.
All eight claims verified independently: clean worktrees at the pinned
trees; lib hashes 7f282a6f.../b14e907a... recomputed (differ from each other
and from all Phase-3 hashes — no stale reuse); 11-variable CMake semantic
identity (only MIOPEN_USER_DB_SUFFIX additionally differs — source-derived,
isolation-positive, benign, now listed in the final report); ZERO /opt/rocm
anywhere in either build tree (grep -rl over builds/leg{A,B}: 0 hits,
build.ninja carries 943 wheel references); RUNPATH relative-only; wheel-first
ldd framing honest (plain ldd = ldconfig defaults — disclosed in install
logs); same amdclang++; same preseed dirs both legs; MIOpen version strings
consistent per leg (3.6.2.7c586614 / 3.6.2.9fc2d03b).
Carry-forward (delivered by H05/H06): per-run dladdr wheel binding proofs.
