# Gate P53 Independent Review — Linux Preservation (Windows/Linux source identity consistency)

- Reviewer: independent (P53), re-derived from direct observation; no executor numbers taken on trust.
- Date: 2026-10-08
- Environment: Git Bash on Windows; scratch reconstruction via `git worktree` in
  `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase3` (removed after review; no residue).
- Claim under review (evidence/phase4/linux_preservation.md): the canonical two-commit
  reconstruction validated on Windows in Phase 4 is byte-equal to the source+patches the
  independent Linux validator used, so the Linux PASS→PASS regression conclusion carries
  over to the canonical commits.

## VERDICT: PASS

No BLOCKER, MAJOR, or MINOR findings. Two NIT-level observations (no action required
beyond note-taking; neither affects the identity chain).

## Verification performed (all values independently recomputed 2026-10-08)

### 1. Linux handoff evidence — CONFIRMED

`evidence/phase3/raw/linux/patch_handoff/identity.json` records:

- `SOURCE_SHA` = `b68f8944300f104875d953fc8e4510908c9aaf0b`
- `PATCH_SHA256_0001` = `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20`
- `PATCH_SHA256_0002` = `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532`
- `patch_modified_by_linux` = `false`
- Notes: 3 new-file additions untracked by design; tracked-diff + 3 new files = full patch content.

### 2. Authoritative patch blobs at origin/main — CONFIRMED (re-hashed by reviewer)

```
git cat-file blob origin/main:patches/phase3/0001-miopen-hiprtc-selfcontained.patch | sha256sum
  -> f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20
git cat-file blob origin/main:patches/phase3/0002-miopen-hiprtc-selfcontained.patch | sha256sum
  -> 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532
```

Both equal the Linux-recorded values in `identity.json` and the values re-stated in
`findings/phase3/linux/linux_conclusion.json` (`patch_sha256_0001/0002`). Byte-identity
of the exact blobs Linux hashed to the blobs at origin/main is proven; the Linux
applied-content round-trip audit (`mutation_audit`, tracked-diff SHA
`972e9f5954724a36bc6729ad246f12bef438b5fe34a6bd096cabe70a183dd8cf` + 3 untracked headers)
is consistent with this.

### 3. Canonical reconstruction — CONFIRMED (independent reference construction)

Canonical worktree `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical`
(branch `prepare/miopen-hiprtc-selfcontained`, clean status):

- `git rev-list --count b68f894..HEAD` = **2** (commits `c86d1b9`, `4084759`).
- `git diff --name-status b68f894..HEAD` touches **exactly** the eight files
  (5 M + 3 A), matching the patch footprint observed on apply (5 modified + 3 new).
  No hidden changes outside the eight files.

Reviewer reference side (fresh scratch worktree `phase4_review_p53`, detached at
`b68f894`, clean checkout; both repos `core.autocrlf=false` so no line-ending drift):

1. `git -C rocm-libraries-phase3 worktree add --detach phase4_review_p53 b68f894`
2. Applied the two authoritative patch blobs (exported from `origin/main`, re-hashed
   before use) with `git apply` — both applied cleanly.
3. `git add -A`; `git ls-files -s` for the eight files; worktree removed with
   `git worktree remove --force` (verified gone from `git worktree list`).

Blob OID comparison (all eight MATCH):

| File (under projects/miopen/src/) | Canonical HEAD | Reference b68f894+0001+0002 | Match |
|---|---|---|---|
| kernels/miopen_type_traits.hpp | 983cdfe17691456b90e34b00ef946760d889cd9b | 983cdfe17691456b90e34b00ef946760d889cd9b | YES |
| kernels/miopen_utility.hpp | 770882aebf20983f68a1aa8242439e8e1b994d62 | 770882aebf20983f68a1aa8242439e8e1b994d62 | YES |
| kernels/miopen_freestanding_type_traits.hpp | 40bd307db59436d44656f8bedfce95ec2bc3c22b | 40bd307db59436d44656f8bedfce95ec2bc3c22b | YES |
| kernels/miopen_freestanding_utility.hpp | f335261b9976fb20c23cd96548607977773f9049 | f335261b9976fb20c23cd96548607977773f9049 | YES |
| kernels/miopen_freestanding_initializer_list.hpp | 79498fd8d39cf8047b6ad34a010527bbf425ec70 | 79498fd8d39cf8047b6ad34a010527bbf425ec70 | YES |
| kernels/radix.hpp | 99c29fda93463818b2bb8c91230527098b689687 | 99c29fda93463818b2bb8c91230527098b689687 | YES |
| kernels/tensor_view.hpp | d7963324b0de98900f105ca07e9264e12ae0b646 | d7963324b0de98900f105ca07e9264e12ae0b646 | YES |
| CMakeLists.txt | 7b8a3454452b6463aea5e1293cb57663d3a0ff7e | 7b8a3454452b6463aea5e1293cb57663d3a0ff7e | YES |

Blob OID equality ⇒ byte equality. **8/8 identical.** The canonical two commits are
content-equal to `b68f894` + the exact patch blobs Linux validated, and touch no other
files. This is the strongest form of the executor's P45 claim, re-derived independently.

### 4. Linux conclusion honesty — CONFIRMED

`findings/phase3/linux/linux_conclusion.json` (independently read):

- `linux_regression_verdict`: **PASS**
- `batchnorm_regression`: PASS — unpatched 8/8 → patched 8/8, fresh isolated caches per leg
- `numerical_regression`: PASS — **bit-identical, overall max_abs_error 0.0 across 37
  tensors** (y/xgrad/wgrad/bgrad/running stats; 6 cases incl. MIOpen#3956 repro and
  YOLO-like shapes; CPU-referenced)
- `kthvalue_runtime`: `unpatched: PASS`, `patched: PASS`, `regression: NONE`, values
  exact vs CPU and byte-identical A/B, indices exact (no ties), falsification review PASS
- `other_rtc_kernels`: 11/11 → 11/11; `patched_build` 800/800 vs `source_unpatched_build` 690/690
- `yolo_predict` / `yolo_train`: PASS (AMP self-disabled → FP32 and amp=False; v2 rerun
  with in-stream binding match)
- Same `source_sha` and both `patch_sha256_*` values as the handoff — internally consistent.

`findings/phase3/final_readiness/PR_READINESS.json`:

- `readiness`: **READY_FOR_HUMAN_SUBMISSION_PREP**
- `linux_pass_to_pass: true`, `linux_numerics_bit_identical: true`,
  `kthvalue_runtime_unpatched/patched: PASS/PASS`, `patch_mutated_after_validation: false`,
  `cross_platform_closure: PASS`, `technical_blockers: []`.

Supporting provenance cited by the executor also checks out: `origin/main` tip is
`cb5e8ca` ("phase3: add final upstream readiness audit"), with `f553c49` beneath it;
`origin/rca/linux-gfx1151-phase3-regression` exists; `evidence/phase3/raw/linux/source/
source_identity.txt` records HEAD `b68f894` clean, 8032 files, every file byte-verified
against tree blob SHA-1.

### 5. Executor evidence tables (evidence/phase4/linux_preservation.md) — ACCURATE

Every checkable claim in the two tables and the results list matches direct observation:

- Source-identity table: all six rows confirmed (handoff values, origin/main blob hashes,
  no-mutation flag, baseline verification record, 8/8 canonical equivalence).
- Provenance line (branch, merge commits f553c49/cb5e8ca) confirmed against origin/main.
- Linux results list matches `linux_conclusion.json` field-for-field (BN 8/8→8/8,
  0.0 max_abs_error across 37 tensors / 6 cases, 11/11→11/11, kthvalue PASS→PASS with
  falsification review, YOLO predict/train PASS, 690/690 → 800/800).
- The conclusion paragraph's scope statement (carry-over without rerunning Linux; no
  re-made Linux claims; Phase 4 modifies nothing) is consistent with the evidence.

No inaccuracies found.

## Findings

- **BLOCKER**: none.
- **MAJOR**: none.
- **MINOR**: none.
- **NIT-1**: `evidence/phase4/linux_preservation.md` cites `source_identity.txt` without
  its full relative path (`evidence/phase3/raw/linux/source/source_identity.txt`); a
  reader must search for it. Cosmetic only.
- **NIT-2**: The Linux `git_diff_SHA256_tracked` (`972e9f…`) is a Linux-side working-tree
  artifact that cannot be byte-reproduced from the committed canonical history (diff
  provenance/formatting differs between unstaged and committed diffs). It does not need
  to be: this review proved the strictly stronger property — full 8/8 blob-OID equality
  of canonical HEAD vs an independent `b68f894`+patches reconstruction — which subsumes
  the tracked-diff audit. Noted so a future reviewer does not chase it.

## Required actions

None. Gate P53 is satisfied: the canonical two-commit reconstruction is byte-equal to
what the independent Linux validator tested (same base `b68f894`, same patch blobs by
SHA-256, 8/8 file blob-OID equality independently re-derived), and the Linux
PASS→PASS regression conclusion honestly carries over to the canonical commits.
