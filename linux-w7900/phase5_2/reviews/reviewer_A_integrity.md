# Reviewer A — Source and Supply-Chain Integrity (Gate B11)

Fresh-context subagent; independent command list; scratch /tmp/opencode/rA/.

VERDICT: **PASS**

BLOCKERS: none. MAJORS: none. MINORS: none.

Verified independently:
- Frozen RCA evidence checkout: HEAD 494907699f3b57095663f0a70b42278001a8efb7,
  clean, origin = AIwork4me/Ultralytics-Windows-ROCm-Training-RCA;
  origin/phase5.1/windows-final-candidate-freeze == 494907699f...
- Manifest uses the ACTUAL frozen schema; consumer validates exactly those
  keys and rejects provisional keys with no fallback.
- All three patch sha256 + sizes + series hash recomputed three ways
  (sha256sum, cat|sha256sum, python hashlib) == manifest == consumer pins
  (incl. manifest_sha256 58a6f9ce...).
- README allowance exactly as documented (never hashed); extra files fail.
- Own mutation tests: '../' traversal FAIL, symlinked patch FAIL, extra
  notes.txt FAIL.
- METHOD B reconstruction in reviewer's own worktree:
  write-tree == 605d0d214acdbc06086fdb27c61fec970c0f2798; all 10
  changed_files_vs_base git_blob SHAs match; diff base->tree touches
  exactly those 10 paths.
- phase5_2 deliverable hygiene: no files >1MB; no repos/build/install/
  runtime content.

NITs: space-pruned develop checkout (pre-existing; integrity unaffected);
HEX40/HEX64 alphabet duplication (cosmetic). Positive corroboration: patch
'From <sha>' headers match ordered_commits exactly.

REPRODUCTION COMMANDS: see reviews/B11_panel_and_B10_second_pass.md
(Reviewer A section) and the panel transcript.

REQUIRED FIXES: none.
