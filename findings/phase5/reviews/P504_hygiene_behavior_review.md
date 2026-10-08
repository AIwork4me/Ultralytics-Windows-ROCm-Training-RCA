# P5-04 Adversarial Review — Did the "Cosmetic" Hygiene Edit Change Executable Behavior?

Reviewer stance: hostile re-derivation. The primary agent's claims were NOT
trusted; every hunk, token, directive, blob OID, and tool invocation below was
re-derived independently in a fresh shell.

- Date: 2026-10-08
- Candidate: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5-candidate`,
  branch `prepare/miopen-hiprtc-phase5`
- Reviewed series (pinned by SHA, immutable): `135f775e855bc40185d0a39e13d0a1a97105c1b9`
  and `b1adc77ac58f7a4573a8abb4101fc47ab34e65b7`, base
  `7c5866144ac4b879be442563e2b49fa1c142ea36`
- Reference: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical`
  at `4084759f3804748b7935d882db2d0445a3e0c380` (c86d1b95 → 4084759)
- Claims under audit: `docs/phase5/SOURCE_CHANGE_JUSTIFICATION.md` (a) dead
  macro removal, (b) triple-blank-line fix, (c) clang-format 18.1.4 on 4 files
  only, (d) commit-2 message rewrite (metadata only)

## VERDICT: CONDITIONAL PASS

**Nothing executable changed inside the reviewed 2-commit series.** The
P4-validated content and the P5 series are provably preprocessing-equivalent
and pp-token-equivalent modulo one unreferenced `#define`. The strongest form
of the proof obtained: applying the repo-config clang-format 18.1.4 to the
P4 blobs reproduces the P5 blobs **byte-for-byte** for 6 of 7 headers, and for
the 7th (`miopen_freestanding_type_traits.hpp`) the output differs from P5
*only* by the two removed dead-macro lines.

The CONDITIONAL is a process condition, not a code condition: during this
review the candidate worktree's HEAD advanced from `b1adc77` to a new third
commit `6e9f6b1` (test-only, outside the audited scope), and the worktree
transiently reported mass deletions of `.s` assembly kernels (later clean
again). See F-1/F-2. Condition: consumers must pin to `b1adc77` (or the
third commit must pass its own review), and worktree cleanliness must be
re-asserted at consumption time.

## Findings

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| F-1 | MAJOR (process) | Candidate HEAD moved **during** this review: `b1adc77` → `6e9f6b11c2fe83dc42ea0b0668bca196c1ee1a02` ("MIOpen: add HIPRTC no-host-STL regression test", AuthorDate 13:44:37 +0800, i.e. minutes after the audited series). It touches only `projects/miopen/test/CMakeLists.txt` (+50) and `projects/miopen/test/hiprtc_selfcontained.cpp` (+491) — none of the 8 audited files — but the branch no longer equals the reviewed 2-commit series. All SHA-pinned analysis here is unaffected. | Pin consumption to `b1adc77`, or review `6e9f6b1` separately (it adds a new CTest driver + CMake wiring = executable build-graph change, benign but unreviewed). |
| F-2 | MINOR (process) | Transient dirty state: one `git status` invocation mid-review reported dozens of `D` (deleted) `projects/miopen/src/kernels/dynamic_igemm/.../*.s` assembly files; a re-run seconds later showed a fully clean worktree (0 porcelain lines). Cause unknown — consistent with OneDrive/Desktop file dehydration or a concurrent process racing the index. Had that state been committed, deleting `.s` kernels WOULD be an executable change; it was not committed. | Before any build/freeze step, assert `git status --porcelain` is empty and `git rev-parse HEAD` equals the pinned SHA. Consider relocating the candidate worktree off OneDrive-managed `Desktop`. |
| F-3 | NIT | Tooling trap for future reviewers: MSYS2 `grep -c $'\r'` reported every line of every LF-only file as matching (text-mode artifact), falsely suggesting CRLF endings. Python byte counts (`d.count(b'\r') == 0`) proved all 8 files are pure-LF on both sides. | Use Python/`od -c` for EOL audits on this host, not MSYS grep. |
| — | BLOCKER | none | — |

No code-severity findings (MAJOR+ code, MINOR code, NIT code): none. Every
hunk is provably whitespace, macro-removal, or line-continuation placement.

## Attack-vector coverage (all 8 requested vectors)

### 0. Scope grounding (prerequisite)

- Candidate HEAD at review start: `b1adc77` on `prepare/miopen-hiprtc-phase5`,
  exactly 2 commits over `7c5866144ac4b879be442563e2b49fa1c142ea36`. Clean worktree.
- P4 canonical HEAD: `4084759` (= c86d1b95 + 1). Different upstream base:
  `git merge-base 4084759 b1adc77` = `b68f894` (P4's base). The P5 series was
  rebased onto the newer upstream `7c586614`. The upstream range
  `b68f894..7c586614` touches `projects/miopen/src/kernels/{MIOpenBatchNormActivBwdSpatial,MIOpenBatchNormBwdSpatial,MIOpenBatchNormFwdTrainSpatial,configuration,default_configurations,reduction_functions}.*`
  — **none of the 8 audited files** — so a direct blob comparison of the 8
  files isolates exactly the P5 hygiene edits.
- Full series footprint `7c586614..b1adc77`: exactly 8 files (below), nothing
  outside `projects/miopen`.

### 1. Token-level diff of every changed file (P4@4084759 vs P5@b1adc77)

All 8 blobs extracted via `git show` to /tmp; `cmp` results:

| File | P4→P5 | Byte-identical? |
|---|---|---|
| `projects/miopen/src/CMakeLists.txt` | 1224→1224 lines | YES |
| `kernels/miopen_freestanding_initializer_list.hpp` | 64→60 | no (claim b, c) |
| `kernels/miopen_freestanding_type_traits.hpp` | 216→209 | no (claims a, c) |
| `kernels/miopen_freestanding_utility.hpp` | 56→56 | YES |
| `kernels/miopen_type_traits.hpp` | 165→166 | no (claim c, #error line) |
| `kernels/miopen_utility.hpp` | 69→70 | no (claim c, #error line) |
| `kernels/radix.hpp` | 115→115 | YES |
| `kernels/tensor_view.hpp` | 97→97 | YES |

Exactly the claimed set differs; diffstats match the justification doc's table
verbatim (−24/+17, −5/+1, −1/+2, −1/+2).

Hunk classification (from full `diff -u`, no other hunks exist):

- `miopen_type_traits.hpp` (1 hunk) and `miopen_utility.hpp` (1 hunk): each
  splits `#error "long message"` into `#error \` + newline + 4 spaces +
  `"same long message"`. Hexdump of the P5 bytes at the splice:
  `# e r r o r SP \ \n SP SP SP SP "` — i.e. byte 0x5C immediately followed by
  0x0A, a valid ISO C++ translation-phase-2 line splice (no trailing
  whitespace after the backslash that would defeat it). After splicing, the
  pp-token sequence after `#error` is the identical single string literal.
- `miopen_freestanding_initializer_list.hpp` (2 hunks): triple blank line →
  single; private ctor body joined onto the signature line. Whitespace-only.
- `miopen_freestanding_type_traits.hpp` (5 hunks): `#error` continuation
  **joined** (reverse direction of the legacy files); `#define
  MIOPEN_FREESTANDING_TRAITS_ACTIVE` + one blank line removed; `using`
  alignment re-aligned (intra-line spaces before `=`);
  `is_trivially_copyable` base-clause joined; four `static_assert` conditions
  reflowed (`&&` moved to end of line; one `static_assert(` opening paren
  moved). All whitespace/line-break placement only.

Machine proofs run (checker scripts mirror C++ phases: phase-2 splice, then
tokenize):

- **pp-token stream** (punctuation-aware tokenizer, string literals kept
  whole): EQUIVALENT for 7/8 files. For
  `miopen_freestanding_type_traits.hpp` the *only* delta in the entire token
  stream is `- # - define - MIOPEN_FREESTANDING_TRAITS_ACTIVE`. No identifier,
  template argument, literal, keyword, or punctuator differs anywhere else.
- **string-literal set**: identical in all 8 files (no clang-format string
  wrapping/splitting occurred).
- **directive set** (post-splice, whitespace-normalized): identical in all 8
  files except the one removed `#define`. The `#error` joins/splits cancel
  exactly under splice+normalize, i.e. the emitted diagnostic text is
  token-identical (inter-token whitespace is not part of any token).

### 2. Dead macro `MIOPEN_FREESTANDING_TRAITS_ACTIVE`

- P4 canonical worktree: exactly one occurrence — the definition
  (`miopen_freestanding_type_traits.hpp:50`). No `#ifdef`, `#ifndef`,
  `#if defined`, no `#undef`, no build-script reference.
- P5 candidate worktree (full-tree grep, all file types incl. `.py`, `.cmake`,
  `.yaml`): **zero** occurrences.
- Out-of-tree consumers: `Ultralytics-Windows-ROCm-Training-RCA` hits are
  documentation/findings only (phase3 design doc, phase4 review that
  *requested* the removal — P56 Reviewer A finding F-2; phase5 justification).
  `phase5_buildtools`: zero hits.
- Conclusion: removal cannot alter any conditional compilation. Dead-macro
  removal is behavior-neutral by exhaustion.

### 3. `miopen_freestanding_type_traits.hpp` content integrity

- 12 `static_assert`s before and after; token streams identical (proof in §1),
  so none was weakened, reordered, or had its condition altered.
- All trait definitions and partial specializations token-identical:
  `integral_constant` (value/`value_type`/`type`/conversions),
  `true_type`/`false_type`, `remove_reference` + `T&`/`T&&` specializations,
  `remove_const`/`remove_volatile`/`remove_cv` + specializations, `is_same` +
  specialization, `enable_if`, `conditional`, `is_pointer` family,
  `is_trivially_copyable` on `__is_trivially_copyable`, `*_t`/`*_v` aliases.
- Self-test block intact: `namespace miopen_freestanding_selftest` with
  `non_trivial` (lines 196–202 in P5), consumed by the final static_asserts.
- Header guard / `#ifndef MIOPEN_HIP_RUNTIME_COMPILE` → `#error` arm intact.

### 4. `miopen_freestanding_initializer_list.hpp` class-body equivalence

Token-equal (§1). Layout confirmed identical: members `const E* __begin_;`
and `__SIZE_TYPE__ __size_;`; private constexpr copy ctor
`(const E*, __SIZE_TYPE__) noexcept`; public constexpr default ctor
`nullptr`/`0`; same public `begin()/end()/size()` signatures. The single-line
join of the private ctor body is whitespace-only (verified at pp-token level;
`__begin_`/`__size_` initializer order unchanged).

### 5. Preprocessor directive-set equivalence

See §1 "directive set": every changed file emits an identical directive
sequence after line splicing, with the sole exception of the removed
`#define MIOPEN_FREESTANDING_TRAITS_ACTIVE` in
`miopen_freestanding_type_traits.hpp`. Include directives are inside the
token stream → unchanged in all 8 files (CMakeLists.txt byte-identical, so the
embedded-kernel registration is unchanged too).

### 6. Commit decomposition

- `git show --stat 135f775`: exactly 5 files — `src/CMakeLists.txt` (+2),
  `kernels/miopen_freestanding_type_traits.hpp` (new, 209),
  `kernels/miopen_freestanding_utility.hpp` (new, 56),
  `kernels/miopen_type_traits.hpp` (18 ±), `kernels/miopen_utility.hpp` (16 ±).
- `git show --stat b1adc77`: exactly 4 files — `src/CMakeLists.txt` (+1),
  `kernels/miopen_freestanding_initializer_list.hpp` (new, 60),
  `kernels/radix.hpp` (11 ±), `kernels/tensor_view.hpp` (+7).
- Union = the 8 audited files; nothing else in either commit. Matches the
  claimed decomposition exactly.

### 7. Commit metadata

`git log --format=fuller` for both commits: Author = Committer =
`AIwork4me <AIwork4me@users.noreply.github.com>`; AuthorDate/CommitDate
2026-10-08 13:37:28 / 13:37:37 +0800. Both messages end with the line
`DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream
submission; replace this line with a real Signed-off-by per DCO before
submitting.` `git log --format="%G?"` = `N` for both (unsigned) — expected and
correct at this stage. Commit-2 message differs from P4's 4084759 message
(claim d) — messages are metadata, tree bytes unaffected (proven by the blob
analysis; the P5 tree delta is fully accounted for by formatting + macro
removal).

### 8. Tool provenance and formatter re-run

- `C:\Users\rocm\Desktop\YOLO_AMD\phase5_buildtools\Scripts\clang-format.exe
  --version` → `clang-format version 18.1.4`. Matches the pin in the repo
  root `.pre-commit-config.yaml` (`pre-commit/mirrors-clang-format`,
  `rev: v18.1.4`).
- Config integrity: blob OID of `projects/miopen/.clang-format` =
  `0d9e7127e9d0160ea05fcfa4fb5721ef53557f25` at upstream base `b68f894`, at
  `7c586614`, and at `b1adc77` — identical; worktree copy matches HEAD
  (porcelain clean). `--dump-config` from a kernel path confirms discovery of
  the repo config (ColumnLimit 100, IndentWidth 4, Standard Latest).
- Worktree copies of all 7 headers hash-match the `b1adc77` blobs
  (`git hash-object` vs `git rev-parse b1adc77:<path>`), so the dry-run tested
  the audited bytes.
- **Dry-run `-Werror` on all 7 P5 headers: rc=0 for every file** (format-clean).
- Adversarial reverse proof — dry-run on the *P4* blobs (layout-reconstructed
  with the repo `.clang-format` on the search path): NEEDS-FMT for exactly
  `miopen_freestanding_initializer_list.hpp`, `miopen_freestanding_type_traits.hpp`,
  `miopen_type_traits.hpp`, `miopen_utility.hpp`; CLEAN for
  `miopen_freestanding_utility.hpp`, `radix.hpp`, `tensor_view.hpp`. This
  independently confirms "applied to 4 files only" was the complete set, and
  that no unrelated legacy region was reformattable (the legacy files' only
  violations were our own added `#error` lines).
- **Byte-exactness of the transformation**: `clang-format <P4 blob>` vs P5
  blob, `cmp`: BYTE-IDENTICAL for 6/7 headers (both legacy `#error` files,
  `freestanding_utility`, `radix`, `tensor_view`, and
  `freestanding_initializer_list`); for `freestanding_type_traits.hpp` the
  diff is exactly the two removed lines `#define
  MIOPEN_FREESTANDING_TRAITS_ACTIVE` + blank. Therefore the P5 series is
  *literally the formatter output* of the validated P4 content, minus the dead
  macro. (Also cross-checked the P5-03 intermediate `b82d950`: its 8 blob OIDs
  equal P4 canonical `4084759`'s — the pre-cleanup equivalence claim in
  `evidence/phase5/source_delta/pre_cleanup_equivalence.json` is truthful.)

## Commands run (complete log)

All in Git Bash, working dirs as shown; `<CF>` =
`C:/Users/rocm/Desktop/YOLO_AMD/phase5_buildtools/Scripts/clang-format.exe`,
`<PY>` = `C:/Users/rocm/Desktop/YOLO_AMD/phase5_buildtools/Scripts/python.exe`.

Grounding / scope:
1. `cd rocm-libraries-phase5-candidate && git log --format=fuller -3 && git status --short && git rev-parse HEAD`
2. `cd rocm-libraries-phase4-canonical && git log --oneline -5 && git rev-parse HEAD`
3. `git show --stat 135f775 && git show --stat b1adc77` (candidate)
4. `git show --stat c86d1b9 | head -30 && git show --stat 4084759 | head -30` (P4)
5. `git diff --stat 4084759 b1adc77` (full-tree; revealed different upstream bases)
6. `git merge-base 4084759 b1adc77`; `git log --format='%h %p %s' -1` for 4084759, c86d1b9, b1adc77, 135f775
7. `git diff --name-only c86d1b9^ 4084759` (the 8 files)
8. `git diff --name-only b68f894 7c586614 -- projects/miopen/src/kernels projects/miopen/src/CMakeLists.txt`
9. `git diff --name-only 7c586614 b1adc77` (series footprint = 8 files)

Blob extraction and byte compare:
10. `for f in <8 files>; do git show 4084759:$f > /tmp/p504/p4/...; git show b1adc77:$f > /tmp/p504/p5/...; done && wc -l`
11. `for f in p4/*; do cmp p4/$n p5/$n; done`

Hunk inspection:
12. `diff -u p4/...miopen_type_traits.hpp p5/...miopen_type_traits.hpp`
13. `diff -u p4/...miopen_utility.hpp p5/...miopen_utility.hpp`
14. `diff -u p4/...miopen_freestanding_initializer_list.hpp p5/...miopen_freestanding_initializer_list.hpp`
15. `diff -u p4/...miopen_freestanding_type_traits.hpp p5/...miopen_freestanding_type_traits.hpp`
16. `od -c` around the `#error` splice in P5 `miopen_type_traits.hpp` (bytes `#error \ \n SP SP SP SP "`)
17. Python byte counts: `d.count(b'\r')`, `d.count(b'\n')`, `d.count(b'\r\n')` for all 16 extracted blobs → all LF-only, zero CR

Token/directive/string-literal equivalence (custom checkers written to
%TEMP%\p504_tokcheck.py and %TEMP%\p504_cpptok.py; phase-2 splice = remove
backslash-newline, then compare):
18. `<PY> p504_tokcheck.py p4/X p5/X tokens` (whitespace-split) — all 8
19. `<PY> p504_cpptok.py p4/X p5/X` (punctuation-aware pp-tokens, strings whole) — all 8
20. `<PY> p504_tokcheck.py p4/X p5/X directives` — all 8
21. `<PY> p504_tokcheck.py p4/X p5/X strlits` — all 8

Dead macro:
22. `grep -rn MIOPEN_FREESTANDING_TRAITS_ACTIVE .` in P5 worktree (excl. .git) → 0 hits
23. same in P4 worktree → 1 hit (the definition, line 50)
24. `grep -rn "FREESTANDING_TRAITS\|ifdef MIOPEN_FREESTANDING\|defined(MIOPEN_FREESTANDING\|defined (MIOPEN_FREESTANDING"` in P5 → 0 hits
25. `grep -rn MIOPEN_FREESTANDING_TRAITS_ACTIVE` in RCA repo and phase5_buildtools → docs-only hits / 0

Content integrity:
26. `grep -c static_assert` both type_traits versions → 12/12; `grep -n "namespace miopen_freestanding_selftest"` → present
27. structural skim of P5 type_traits (traits/specializations listing)

Metadata / decomposition / config:
28. `git branch --show-current`; `git log -2 --format=fuller`; `git log -2 --format="%h %G? %an <%ae>"`
29. `git rev-parse b68f894:projects/miopen/.clang-format 7c586614:... b1adc77:...` (all `0d9e7127...`); `git status --porcelain projects/miopen/.clang-format`
30. `grep -B2 -A4 mirrors-clang-format .pre-commit-config.yaml` → `rev: v18.1.4`
31. `git hash-object` vs `git rev-parse b1adc77:<path>` for the 7 headers → MATCH

clang-format verification:
32. `<CF> --version`
33. `<CF> --dump-config projects/miopen/src/kernels/radix.hpp | grep -E "BasedOnStyle|ColumnLimit|IndentWidth|Standard"`
34. `<CF> --dry-run -Werror <each of the 7 worktree headers>` → rc=0 all
35. Reconstruct P4 layout under /tmp with repo `.clang-format`; `<CF> --dry-run -Werror` on the 7 P4 blobs → NEEDS-FMT for exactly the 4 changed files, CLEAN for the other 3
36. `<CF> <P4 blob> > out` for all 7; `cmp out vs p5 blob` → 6/7 byte-identical; `diff -u out p5/freestanding_type_traits.hpp` → only the 2 removed macro lines
37. `head -40 .../evidence/phase5/source_delta/pre_cleanup_equivalence.json`; `git cat-file -t 98bbc6c`, `b82d950`
38. `git ls-tree b82d950 -- <8 files>` vs `git ls-tree 4084759 -- <8 files>` (in P4 repo) → all 8 OIDs identical

Mid-review anomalies:
39. `git show --stat 6e9f6b1` (test-only: `test/CMakeLists.txt` +50, `test/hiprtc_selfcontained.cpp` +491)
40. `git status --porcelain | awk '{print $1}' | sort | uniq -c` (clean at end); earlier transient `D` wall on `dynamic_igemm/*.s` captured
41. `git rev-parse HEAD` (end of review: `6e9f6b11c2fe83dc42ea0b0668bca196c1ee1a02`), `git log --oneline -3`

## Bottom line

The hygiene edit is provably non-executable: P5 = clang-format-18.1.4(P4
validated content) minus an everywhere-unreferenced `#define`. The single most
dangerous thing found is **not** in the diff — it is that the "candidate"
worktree mutated while under review (new third commit; transient mass `.s`
deletions), so any downstream consumer must re-pin to `b1adc77` and re-assert
a clean tree rather than trusting "branch tip = reviewed state".
