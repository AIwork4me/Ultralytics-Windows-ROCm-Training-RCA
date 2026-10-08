# Gate P41 Independent Review — Immutable Patch Identity

- **Reviewer:** Independent verifier (Phase 4), fresh computation; executor's script NOT reused.
- **Date:** 2026-10-08
- **Repo:** `C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA`
- **Ref verified:** `origin/main` = `cb5e8cac615afff38bb8c78634a7cf130fc97a06`

## VERDICT: PASS

## Method (independent)

1. Extracted exact blob bytes with `git cat-file blob origin/main:patches/phase3/000{1,2}-miopen-hiprtc-selfcontained.patch` via subprocess (binary stdout), written to temp files in binary mode.
2. SHA256 via Python `hashlib` on the raw bytes (temp-file read-back round-trip also confirmed).
3. Series = SHA256(concat 0001 || 0002, no separator, no newline insertion).
4. Git blob OIDs via `git rev-parse`, **double-verified** by manually computing git's SHA-1 object hash (`blob <size>\0` + bytes) — both methods agree.
5. Working-tree EOL state via `git ls-files --eol` and byte-level comparison of working-tree files against blob bytes.

Interpreter: `/c/Users/rocm/miniconda3/envs/yolo_amd/python.exe`

## Computed values

| Item | Value | Expected | Match |
|---|---|---|---|
| SHA256 0001 blob (15,143 bytes) | `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20` | same | YES |
| SHA256 0002 blob (6,375 bytes) | `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532` | same | YES |
| SHA256 series (0001\|\|0002) | `b1150afcf2170a9d396f9a25669547c0ed4021c221f7feaa59e073d4b9706685` | same | YES |
| Git blob OID 0001 | `37a36710d378e70a37f947555e3e11f2426d53fa` (rev-parse = manual SHA-1 object hash) | — | consistent |
| Git blob OID 0002 | `458e0e24a99eb061dda7256f7228ad6ac92f68f1` (rev-parse = manual SHA-1 object hash) | — | consistent |

## Working-tree vs blob (CRLF check)

`git ls-files --eol` reports `i/lf w/crlf attr/text=auto` for both files. Byte-level comparison confirms the working-tree copies differ from the blobs (CRLF smudge on checkout):

- 0001 working tree: 15,547 bytes, SHA256 `521b6cc0be4c375b72d45c4acd924a52a58ebcdf317c2384c589cc4f60316a2a` (blob has no CRLF; working tree does) — **different from blob hash, as expected**.
- 0002 working tree: 6,531 bytes, SHA256 `e8d45e0385be1cef3a05e46d8b76ae57d49c17578c157861fa4b6c5b2a836c92` — **different from blob hash, as expected**.

`git status --porcelain` on both paths is empty — the files are unmodified; the difference is purely EOL smudge from `text=auto` on Windows. The recorded identities therefore must come from Git blob bytes (LF), and they do: all three recorded hashes equal the blob-byte hashes, not the working-tree hashes. Had the executor hashed working-tree files directly, the values would have been the 521b…/e8d4… hashes above — they are not. Confirmed: working-tree copies were NOT used.

## Evidence file cross-check (`evidence/phase4/identity/verification.json`)

- Recorded `verified_ref` / `source.origin_main` = `cb5e8cac615afff38bb8c78634a7cf130fc97a06` — matches the current `origin/main` commit.
- Recorded `sha256` for 0001, 0002, and series all equal this review's independent computation, and recorded `size_bytes` (15,143 / 6,375) equal the actual blob sizes. No discrepancies.
- `overall: "MATCH"` is justified.
- The evidence's `source.handoff_source_sha` (`b68f8944…`) refers to the **upstream Ultralytics source repo** baseline commit recorded in `evidence/phase3/raw/linux/patch_handoff/identity.json` (external to this repo; not resolvable by `git cat-file` here, as expected). The same phase3 handoff file records the identical 0001/0002 SHA256 values — chain of custody is consistent.

## Findings

- **BLOCKER:** none.
- **MAJOR:** none.
- **MINOR:** none.
- **NIT:** `verification.json` does not record the Git blob OIDs (`37a36710…`, `458e0e24…`). Adding them would tie the identity to the Git object graph in a third independent way. Optional, no action required for this gate.

## Required actions

None. Gate P41 evidence is accurate and reproducible; independently confirmed from Git blob bytes at `origin/main`.
