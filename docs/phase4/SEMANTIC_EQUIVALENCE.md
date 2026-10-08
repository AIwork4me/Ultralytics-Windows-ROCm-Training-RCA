# Semantic Equivalence — Canonical Commits vs Validated Patches (Gate P45)

Date: 2026-10-08.

## Construction

Two trees were built independently from the same baseline
`b68f8944300f104875d953fc8e4510908c9aaf0b` (ROCm/rocm-libraries):

- **Reference** — `rocm-libraries-phase4-baseline` worktree, pristine at
  SOURCE_SHA, then the ORIGINAL validated patches
  (`0001-miopen-hiprtc-selfcontained.patch`,
  `0002-miopen-hiprtc-selfcontained.patch`, exact git blob bytes from
  `origin/main` of the RCA repo) applied with `git apply` and staged.
  Not committed: the reference is a construction, not history.
- **Canonical** — `rocm-libraries-phase4-canonical` worktree, branch
  `prepare/miopen-hiprtc-selfcontained`, two standard Git commits created
  with `git apply --index` + `git commit`:
  - Commit 1 `c86d1b9` — "MIOpen: keep RTC type traits self-contained when
    no host STL is reachable"
  - Commit 2 `4084759` — "MIOpen: make remaining RTC kernel std includes
    self-contained"

## Result — HARD GATE

```text
8/8 files BYTE-IDENTICAL (git blob OID match, blob-byte SHA256 match,
working-tree byte equality)

scope proof: git diff --name-status b68f894..HEAD in canonical tree
changes EXACTLY the eight files below (5 M + 3 A), nothing else
git diff --check b68f894..HEAD: no whitespace errors
```

| File | Size | Verdict |
|---|---|---|
| `projects/miopen/src/kernels/miopen_type_traits.hpp` | 4327 B | MATCH |
| `projects/miopen/src/kernels/miopen_utility.hpp` | 2460 B | MATCH |
| `projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp` | 7159 B | MATCH |
| `projects/miopen/src/kernels/miopen_freestanding_utility.hpp` | 2257 B | MATCH |
| `projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp` | 2522 B | MATCH |
| `projects/miopen/src/kernels/radix.hpp` | 3848 B | MATCH |
| `projects/miopen/src/kernels/tensor_view.hpp` | 3179 B | MATCH |
| `projects/miopen/src/CMakeLists.txt` | 55129 B | MATCH |

Full matrix with per-side blob OIDs and SHA256:
`evidence/phase4/equivalence/file_hash_matrix.json`.

Cross-validation: the canonical blob OIDs of the five modified files
(`983cdfe…`, `770882a…`, `99c29fd…`, `d796332…`, `7b8a345…`) equal the
post-image blob IDs recorded in the original patch `index a..b` header
lines — i.e. the canonical commits reproduce exactly the content the
validated patches declared they would produce.

Hash domain: exact git blob bytes (LF), immune to the Windows CRLF
working-tree smudge trap.

## DCO status of the canonical commits

The two commits are **provisional local commits, not submittable**:

- Author/committer: `AIwork4me <AIwork4me@users.noreply.github.com>` —
  the configured identity for the RCA workstream; using it locally does
  NOT constitute DCO authorization for an upstream contribution.
- No `Signed-off-by` trailer is present. The validated patch envelope's
  placeholder trailer
  (`Signed-off-by: <AUTHOR NAME> <author@example.com>  # DCO: fill in
  before submission`) was replaced in the commit messages by an explicit
  `DCO: PENDING HUMAN CONFIRMATION` marker line.

```text
DCO_PENDING_HUMAN_CONFIRMATION
```

## Conclusion

The canonical two-commit reconstruction is byte-equivalent to the
validated P3-FINAL-R3 patch series on all eight affected files, with no
unintended tracked changes. Runtime validation of the canonical tree
(Gates P50–P52) may proceed on this basis.
