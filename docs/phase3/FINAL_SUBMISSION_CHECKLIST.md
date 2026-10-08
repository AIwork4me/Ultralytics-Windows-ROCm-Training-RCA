# Final Submission Checklist — human steps at upstream submission time

The validated patch series `P3-FINAL-R3`
(`patches/phase3/0001-miopen-hiprtc-selfcontained.patch` +
`patches/phase3/0002-miopen-hiprtc-selfcontained.patch` against
`ROCm/rocm-libraries` develop `b68f8944300f104875d953fc8e4510908c9aaf0b`)
deliberately carries DCO/author **placeholders**. Changing commit
metadata or patch artifacts now would change the validated patch
identity, so the following steps are deferred to the human submitter.
No agent may perform them, and none were performed during validation.

## At upstream submission time

1. **Set the real Git author identity** on both commits (the
   `Signed-off-by: <AUTHOR NAME> <author@example.com>` lines and commit
   author fields). Use the identity the contributor wants on record for
   DCO purposes. NOTE (final-readiness Reviewer A): the placeholder lines
   end with a trailing `# DCO: fill in before submission` comment — the
   comment itself must be REMOVED when filling, or the upstream DCO bot
   will not recognize the trailer.
2. **Add the correct `Signed-off-by:` line(s)** under the Developer
   Certificate of Origin (`git commit -s` semantics / `git
   format-patch` regeneration with `-s`), preserving or adapting the
   existing two-commit messages.
3. **Regenerate the formal commits from the validated semantic diff**
   (e.g. `git am` the current series on a fresh `b68f8944` checkout,
   then re-tag authorship) — do NOT hand-edit the validated tree.
   Regeneration also self-heals the known MINOR formatting artifact
   (duplicated `new file mode 100644` lines in the three new-file diffs
   of the validated series — tolerated by git am/apply, but the
   regenerated commits should carry clean headers).
4. **Verify the semantic diff is byte/patch-equivalent in content** to
   the validated series: the 8 touched files must be identical; recompute
   and compare per-file diffs between the regenerated commits and
   `~/path/to/rocm-libraries-linux-patched` (or the archived round-trip
   evidence in `evidence/phase3/`).
5. **Rerun targeted patch tests if artifact bytes change** (they will —
   commit metadata is part of format-patch bytes): at minimum the
   compile-only no-STL CI canary, one BatchNorm RTC compile, and — on
   any available gfx platform — the kthvalue runtime harness
   (`scripts/phase3/linux/kthvalue_runtime_harness.cpp` +
   `run_with_source_miopen.sh` pattern) and/or
   `MIOpenDriver kthvalue -D 100x500 -k 10 -V 1`.
6. **Fill the copyright attribution** in the new headers if AMD
   maintainers request the AMD copyright line instead of the
   contributor placeholder (currently a placeholder per reviewer
   guidance — maintainer preference wins upstream).
7. **Attach/refresh upstream references** in the PR description:
   MIOpen#3956 (the reported defect), plus the correlation dossier in
   `docs/EXTERNAL_EVIDENCE.md` and the routing notes
   (`docs/phase3/UPSTREAM_ROUTING*.md` / PR_DRAFT.md) as needed.
8. **Do not claim more than validated**: suggested wording lives in
   `docs/phase3/PR_DRAFT.md`; the validated claims are exactly
   Windows FAIL→PASS (no-MSVC live A/B) and Linux PASS→PASS
   (source-built A/B, numerics bit-identical, kthvalue runtime closed)
   on gfx1151 / ROCm 7.14; cross-arch and 10.x remain upstream-CI
   follow-ups.

## Upstream CI follow-ups (maintainer/CI scope, not local blockers)

- Enforce the freestanding compile test (proposed CI test,
  compile-only, no GPU) on gfx94x / gfx110x / gfx120x.
- Run `MIOpenDriver kthvalue` (or gtest kthvalue) on at least one
  non-gfx1151 target.
- One HIP 10.x line leg (the patch touches a HIP-version-gated region;
  pre-HIP7 arms are preserved byte-identically, but CI confirmation is
  the right enforcement point).

## Status fields (machine-readable)

See `findings/phase3/final_readiness/PR_READINESS.json`:
`upstream_pr_created: false`, `upstream_issue_created: false`,
`upstream_comment_posted: false`, `patch_mutated_after_validation:
false` — these must remain true/false respectively until the human
submitter acts.
