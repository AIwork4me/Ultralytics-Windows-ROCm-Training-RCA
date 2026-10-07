# Subagent Build/Provenance Audit — Gate L44

Date: 2026-10-08. Independent auditor (fresh context), re-verified with own commands.

## Verdict (reviewer)

PROVENANCE_CLEAN (artifact chain) — with ISSUES_FOUND (evidence bookkeeping)

## Reviewer's independently re-verified chain (all live)

1. uv env isolation exact (Python 3.13.15, torch 2.12.0+rocm7.14.0, rocm wheels 7.14.0; freeze line-for-line match)
2. Source identity: baseline HEAD == patched HEAD == b68f8944300f104875d953fc8e4510908c9aaf0b; linked worktrees, shared object store; **full-tree re-verification 8032/8032 blobs match git ls-tree** (not spot-check) — raw-backfill checkout provably equivalent to a faithful checkout; promisor off; baseline status 0 entries; only `fin` submodule gitlink uninitialized (as in non-recursive checkout; unused by build)
3. Patch application: patch files re-hashed == handoff; **definitive round-trip: pristine copy + git apply 0001+0002 diff -r byte-for-byte identical to patched worktree**; tracked-diff sha 972e9f59… matches; 3 untracked headers content-exact
4. CMake config: key flags equal in both caches (HIPRTC/COMGR ON, HIP backend, RelWithDebInfo, gfx1151, CK OFF, DRIVER OFF); full key-diff resolves to prefixes, FETCHCONTENT source-dir reuse, Eigen/Fortran/Qt first-configure residue, and `-dirty` user-db suffix (honest marker) — nothing behavioral
5. Contamination: 0 `/opt/rocm` in both caches, both build logs, both build.ninja; runtime ldd reproduced under harness env → all deps from .venv wheels + glibc + .deps sqlite, 0 /opt; libdrm at runtime resolves via wheel rocm_sysdeps (the /opt/amdgpu line is build-time ambient ldd only — driver userspace, benign, unreachable in validated runs)
6. Library provenance recomputed: unpatched 8694d2ba… (803090840 B), patched 02904c25… (803103088 B) — match records; SONAME libMIOpen.so.1; RUNPATH $ORIGIN-relative only; install trees structurally identical (154 files each)
7. Build logs end BUILD_RC=0 both; **690-vs-800 claim REFUTED as stated**: inlining-kernel batch sets identical (129 both); delta = ~110 hipconv/db targets pre-built during the unpatched tree's first configure window (incremental count) — patch adds ZERO new targets
8. Identity threading: strong per-build (dladdr/version/GetLibPath in gate_l29_l30, build_patched/provenance, yolo_predict_patched); weaker per-run for other matrices (labels only)

## Reviewer findings

- MAJOR-1: stale run-1 conclusion artifacts contradict evidence
- MAJOR-2: stale manifest (46 files; 23 run-2 files uncovered; BLOCKED marker file now FAILS its own checksum)
- MAJOR-3: superseded contaminated configure attempt undeclared in evidence (contained: 0 final build edges use /opt tools)
- MINOR: hand-built sqlite3 absolute path in DT_NEEDED (identical both legs; origin unrecorded); dladdr "per run" overstatement; build_unpatched provenance lacks SOURCE_SHA line; two-MIOpen mapping nuance (CK plugin loads wheel copy symmetrically)
- NIT: gitlink print empty; truncated header hashes; duplicate new-file-mode lines; 130 gfx942 objects (hipconv upstream baseline, symmetric)

## Validator remediation (GATE L46)

- MAJOR-1/2: conclusions/summary/final_gate rewritten (this commit); manifest regenerated over full run-2 set
- MAJOR-3: configure attempt history + parity_note.txt archived under build_unpatched/
- MINORs: sqlite3 provenance + SOURCE_SHA line added to build_unpatched provenance addendum; per-run vs per-build dladdr wording corrected in matrix; two-MIOpen nuance documented in L29 evidence already

(Full reviewer text preserved in the session record; the above is the
complete findings list as returned, reformatted for the repository.)
