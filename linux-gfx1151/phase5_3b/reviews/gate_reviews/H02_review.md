# H02 independent audit — exact source reconstruction

VERDICT: CONDITIONAL PASS -> remediated to PASS. BLOCKERS: none. MAJORS: none.
MINOR (remediated): evidence/source_reconstruction.json legA_head/legA_tree
were originally captured with cwd=src/legB (script helper default cwd) —
mislabeled fields only; the bash-level guard had verified the true legA state
at run time. Fixed by re-querying src/legA + correction_note embedded; script
helper now takes explicit per-call cwd.

Independently verified by reviewer: legA HEAD=7c586614 tree=8b0bf035 clean;
legB HEAD=9fc2d03 tree=b983cad HEAD~3=base, subjects in order, committer
phase53b-linux (author AIwork4me preserved by git am); METHOD 2 re-derived by
the reviewer in a /tmp scratch repo via alternates + read-tree + git apply
--cached + write-tree = b983cadd... (third independent method); 10/10 changed
files match manifest blob SHAs; nothing outside projects/miopen touched;
sparse-checkout scope proven not to affect tree identity (reviewer's
non-sparse replay identical); legB-m2 reset to base by design.
