# Gate Reviews B04 + B05 + B06 — Independent Subagent Audits (W7900-PHASE52-BRIDGE-R1)

All three audits ran as fresh-context general subagents with their own
command lists; each received only claims + filesystem pointers.

## B04 — Independent upstream commit/source integrity review

VERDICT: **PASS**

- Frozen base commit 7c586614^{tree} = 8b0bf035e4568a1d994512b4346fed0dde3c591b confirmed
- EXHAUSTIVE blob inventory (beyond the requested >=10 sample): all 47,775
  ls-tree entries tested with GIT_NO_LAZY_FETCH=1 -> 47,771 real blobs
  present; the only 4 "missing" are the submodule gitlinks (by design)
- refs/phase52/frozen-base pin present
- Named samples verified: radix.hpp base blob f8a91fed..., test/CMakeLists.txt
  f6a0e662..., +12 random blobs

## B05 — Independent reconstruction from scratch

VERDICT: **PASS**

Auditor's OWN disposable worktrees:
- Method B (apply --cached x3 + write-tree): 605d0d214acdbc06086fdb27c61fec970c0f2798 EXACT
- Method A (git am x3, sparse checkout): HEAD^{tree} = 605d0d21... EXACT;
  3 commits; author AIwork4me <AIwork4me@users.noreply.github.com>; all 3
  subjects match the manifest ordered_commit_subjects
- Manifest changed_files_vs_base: 10/10 git_blob SHAs MATCH; diff-tree vs
  base shows exactly 10 paths, set-identical to manifest (no unmanifested
  changes)
- install/patched, build/patched-miopen, source/final-patched all EMPTY
  (no premature Leg B)

Findings + resolutions:
- MINOR-1 recon worktrees still registered: CLEANED (worktree remove +
  prune done after audit; frozen-base-checkout retained intentionally for
  B08 leg-A).
- NIT-1 method-A commit SHAs committer-dependent: expected git behavior;
  tree SHA is the load-bearing invariant and reproduces exactly (matches
  Windows git_am_roundtrip.json note).
- NIT-2 4 submodule gitlinks unresolved: documented by design
  (BUILD_TESTING=OFF).

## B06 — Adversarial false-positive assessment

VERDICT: **PASS**

- Probe re-runs reproduced BOTH logs byte-identically (7.14.1 and 7.2.1)
- Independent reimplementation of the measurement (separate code path)
  reproduced [1,0,1,1] -> measurement genuine, on-device
- Auditor attacked full-isolation conclusion with 8 strategies; ALL
  ineffective or unusable (see adversarial_audit_addendum in
  B06_hiprtc_stl_matrix.json); the ONLY [0,0,0,0]+axpy-OK config was a
  -D__has_include(x)=0 SPOOF, disproved by compiling+running a real
  #include <limits> kernel under it (numeric_limits<float>::max() executed
  on GPU)
- strings on libhiprtc-builtins.so.7 confirmed embedded __hip_internal
  numeric_limits templates -> mechanism claim supported

Findings + resolutions:
- MINOR-1 spoof caveat: recorded in B06 evidence + runbook will forbid
  -D__has_include overrides in final validation options.
- MINOR-2 axpy host-over-read: documented as cosmetic (devOut unused;
  results read back separately); no evidential impact.
