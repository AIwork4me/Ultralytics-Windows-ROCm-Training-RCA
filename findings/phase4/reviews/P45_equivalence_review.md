# P45 Independent Review — Eight-File Semantic Equivalence (HARD gate)

- **Reviewer method**: full independent reconstruction; executor's evidence NOT trusted as input.
- **Review date**: 2026-10-08
- **Baseline SOURCE_SHA**: `b68f8944300f104875d953fc8e4510908c9aaf0b` (ROCm/rocm-libraries)
- **Patch sources (git blobs, RCA repo `origin/main`)**:
  - `patches/phase3/0001-miopen-hiprtc-selfcontained.patch` → blob `37a36710d378e70a37f947555e3e11f2426d53fa`
  - `patches/phase3/0002-miopen-hiprtc-selfcontained.patch` → blob `458e0e24a99eb061dda7256f7228ad6ac92f68f1`
- **Canonical tree under review**: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical`, branch `prepare/miopen-hiprtc-selfcontained`, HEAD `4084759f3804748b7935d882db2d0445a3e0c380`

## VERDICT: **PASS**

## Independent procedure performed

1. Created a dedicated scratch worktree `C:\Users\rocm\Desktop\YOLO_AMD\phase4_review_p45` detached at `b68f894` from the shared object store (`rocm-libraries-phase3\.git`). Path was absent beforehand; executor's worktrees untouched.
2. Extracted both patch blobs via `git cat-file blob origin/main:patches/phase3/000X-...` with bash binary redirection. **Byte-preservation verified**: `git hash-object` of the extracted files returned exactly `37a36710d378e70a37f947555e3e11f2426d53fa` and `458e0e24a99eb061dda7256f7228ad6ac92f68f1`.
3. In the scratch worktree: `git apply` patch 1 → clean, `git apply` patch 2 → clean, `git add -A`. Resulting status: exactly 8 files (5 M + 3 A), nothing else.
4. Canonical branch structure verified: `b68f894..HEAD` contains exactly 2 commits — `c86d1b9` (MIOpen: keep RTC type traits self-contained when no host STL is reachable) then `4084759` (MIOpen: make remaining RTC kernel std includes self-contained). Matches the executor's `canonical_definition`.
5. For each of the eight files: compared staged blob OID (`ls-files -s`) in the scratch reconstruction vs `ls-tree HEAD` OID in canonical; computed SHA256 of each side's blob bytes (`git cat-file blob <oid>`) using `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe` with `subprocess` + `hashlib`.
6. Scope check: `git -C canonical diff --name-status b68f894 HEAD` — exactly the 8 expected files, 5 M + 3 A, no stragglers.
7. Extra diligence (executor claimed `working_tree_bytes_equal: true`): raw byte comparison of all 8 working-tree files between scratch and canonical — all equal, and CR-LF count is 0 on both sides for every file (no CRLF smudge corruption anywhere).
8. Cleanup: `git worktree remove --force` of the scratch worktree; temp patch files and temp matrix JSON deleted; executor's four worktrees verified untouched (`phase3` b68f894, `phase4-baseline` b68f894, `phase4-canonical` 4084759, `phase4-develop-check` 18e1985).

## Independently computed hash matrix

| # | File | Status | Blob OID (both sides) | SHA256 (both sides) | Bytes |
|---|------|--------|----------------------|---------------------|-------|
| 1 | `projects/miopen/src/kernels/miopen_type_traits.hpp` | M | `983cdfe17691456b90e34b00ef946760d889cd9b` | `e0a285bac67902b101035717c1cb65152e72fc01ee6c99a845c2c8261d4945e5` | 4327 |
| 2 | `projects/miopen/src/kernels/miopen_utility.hpp` | M | `770882aebf20983f68a1aa8242439e8e1b994d62` | `35071f3b07a8d882d582d7dd9335c5aabc7d323622622bf9f9b6abaa0d396cd8` | 2460 |
| 3 | `projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp` | A | `40bd307db59436d44656f8bedfce95ec2bc3c22b` | `7475b39cdb4bdf2f4b2ee70ef31119bb1a294152e20d116372196a8254e23495` | 7159 |
| 4 | `projects/miopen/src/kernels/miopen_freestanding_utility.hpp` | A | `f335261b9976fb20c23cd96548607977773f9049` | `db65c6882301814feb439f55d47f741bbf401dfb24a4e8c48ba956178840620f` | 2257 |
| 5 | `projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp` | A | `79498fd8d39cf8047b6ad34a010527bbf425ec70` | `8fdb1232c8ba3e0356c04fda7b303e58e22e511968bf28f7f06c572d2921e052` | 2522 |
| 6 | `projects/miopen/src/kernels/radix.hpp` | M | `99c29fda93463818b2bb8c91230527098b689687` | `ca28a20945adc51808f1d81c193ad47f7d6e6fd87be83c906096aef8f888b7a9` | 3848 |
| 7 | `projects/miopen/src/kernels/tensor_view.hpp` | M | `d7963324b0de98900f105ca07e9264e12ae0b646` | `902316a9f20bd11b11704c3a405adae51133630fba806a2ee3f637e533697300` | 3179 |
| 8 | `projects/miopen/src/CMakeLists.txt` | M | `7b8a3454452b6463aea5e1293cb57663d3a0ff7e` | `83598dcf2220c84e8756b20c1773c4449975ce832eb277387bc2208fe6c3976b` | 55129 |

**Result: 8/8 OID match, 8/8 SHA256 match, 8/8 byte-length match, 8/8 working-tree byte-equal.**

## Comparison against executor's evidence

`evidence/phase4/equivalence/file_hash_matrix.json` was compared field-by-field against the
independently computed matrix above:

- All 8 `reference_blob_oid` values identical to my scratch-side OIDs.
- All 8 `canonical_blob_oid` values identical to my canonical-side OIDs.
- All 16 SHA256 values (reference + canonical) identical to my computed values.
- All 8 `size_bytes` values identical.
- `scope_changes` list identical to my `diff --name-status` output (same 8 paths, same M/A).
- `scope_exactly_eight_files: true` confirmed.
- `working_tree_bytes_equal: true` confirmed for all 8 files (and no CRLF in any file on either side).

**Discrepancies found: none.**

## Findings

- **BLOCKER**: none.
- **MAJOR**: none.
- **MINOR**: none.
- **NIT**: none. (The evidence file's `hash_domain` note — exact git blob bytes, LF, independent of working-tree CRLF smudge — is accurate; I additionally confirmed the working trees themselves are byte-identical with zero CR-LF pairs.)

## Required actions

None. Gate P45 is satisfied: the canonical branch `prepare/miopen-hiprtc-selfcontained` (HEAD `4084759`) is byte-for-byte equivalent, in all eight in-scope files, to the independent reconstruction `b68f894 + patch 0001 + patch 0002`, and the canonical diff is scoped to exactly those 8 files (5 M + 3 A) with no out-of-scope changes.
