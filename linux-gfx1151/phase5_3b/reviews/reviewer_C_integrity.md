# H10 Reviewer C — supply-chain and evidence auditor

VERDICT: PASS
BLOCKERS: none. MAJORS: none.
Verified: evidence clone exactly at c841716, clean; all four hashes
recomputed from bytes; consumer byte-identical (b82bb227) to the published
W7900 version; 10/10 changed-file blob SHAs match the manifest (git blob +
sha256 + size); adversarial matrix PASS semantics require actual==expected
AND rc!=0 AND intended_reason_hit for negatives — no false-PASS path;
sample-verified wrong-tree/tamper/reorder/unauthorized-apply entries;
isolation (separate builds/installs, zero /opt/rocm in all three caches,
8 symlinks all internal SONAME); Phase-3 assets and RCA repo untouched
(phase5_3b is a SIBLING dir; RCA worktree clean); scripts hard-fail on
identity mismatches; exit codes match log outcomes; h08 asserts lib path
AND hash before torch import; 16b annotation consistent in four places.
MINORS (hardening adopted where applicable): h05/h06 lacked pre-run
lib-hash assertions (ADDED post-panel: assert_leg_hash guards); h06
same_binding_paths field naming (annotated); h02 delegates patch-hash
verification to H01's consumer (defense-in-depth note; hashes verified
independently); local RCA main 29 commits behind origin/main — fetch
state, not tampering.
