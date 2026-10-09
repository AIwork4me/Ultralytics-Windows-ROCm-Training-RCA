# Reviewer C — Source and Binary Integrity
Session: ses_edfc6e818ffeG8lfYLiywGUZB1 (fresh, Gate L12)
## VERDICT: PASS
Every pinned identity reproduced bit-exactly under independent commands.
## Independent verification highlights
- Fresh 3rd tree reconstruction (fresh temp index over frozen-base-checkout): sequential
  git apply --cached -> 46dc99d5, ad49e582, b983cadd (4th independent reconstruction of the
  R2 tree across the mission).
- All 10 changed-file blob SHAs match patch_identity.json; diff-tree base->R2 exactly 10 files.
- Patch hashes + series hash + as_used_patch_copies byte-identical.
- Both libMIOpen sha256s, both CMakeCache semantic-equality (10 flags), zero /opt/rocm in
  caches and configure logs, compilers from rocm_sdk_devel-7.14.1.
- 5 wrapper scripts match WRAPPERS_MANIFEST sha256s byte-for-byte.
- All runtime in-stream provenance lines re-hashed vs disk (no drift).
## MINORS (resolved: erratum + publication pins; see resolutions.md)
- 65-char hash typo propagated in published phase5_2 artifacts (erratum added; historical
  artifacts not rewritten).
- legB hash bf21a5fa pinned by this package's publication.
