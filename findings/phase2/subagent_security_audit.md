# Gate 44 — Phase-2 Security & Hygiene Audit (independent subagent)

- **Auditor scope:** all Phase-2 content, commits `2c86053..98e5abd` (6 commits; 345 files added, 2 modified: `.gitignore`-adjacent `.gitattributes` and `evidence/raw/batchnorm/bn_variants_results.json`).
- **Audit target:** `HEAD = 98e5abd78459d7968b473d4280892d8045f32588` ("phase2 gates 36-46 prep...").
- **Method note:** hashes were verified against **committed blobs** (`git cat-file blob HEAD:<path>`) and independently against **working-tree bytes**; secret scans via `git grep` over `docs findings evidence scripts patches` at HEAD, plus targeted scans of the 5 files added by `98e5abd`.
- **Concurrency note:** Phase-2 gate agents were committing during this audit (session started at `1ee5701`, one further commit `98e5abd` landed mid-audit and is included in scope). Findings below reflect `98e5abd`.
- **Note on MANIFEST self-coverage:** `evidence/phase2/MANIFEST.json` is not itself listed in `SHA256SUMS.txt` (by design, as the generator); this is acceptable.

## Verdict: **CONDITIONAL PASS**

No secrets, credentials, personal data, or unrelated-file leakage were found — the *security* core of Gate 44 passes cleanly. The conditional rating is driven by **custody-chain integrity breaks in the committed tree** (Section 5): 13 of 315 `SHA256SUMS.txt` entries do not match the committed bytes, 6 entries reference files that `.gitignore` keeps out of the repository entirely, and one Phase-2 commit silently modified a Phase-1-hash-covered evidence file. None of these leak information, but they defeat the tamper-evidence purpose of the manifest and must be remediated before final gate.

---

## 1. Tokens / credentials / secrets — CLEAN

Scanned (case-insensitive, at HEAD, over `docs findings evidence scripts patches`):

- GitHub / cloud tokens: `ghp_`, `github_pat_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `AKIA…`, `ASIA…`, `xox[baprs]-`, `sk-…`, `hf_…` — **no hits**.
- Private keys: `BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY`, `ssh-rsa AAAA…`, `ssh-ed25519 AAAA…`, `ecdsa-sha2…` — **no hits**.
- Credential assignments: `password[:=]`, `passwd`, `secret[:=]`, `api_key/apikey[:=]`, `token[:=]<value>`, `access_token`, `auth_token` — **no hits with values**.
- Headers/cookies: `Authorization: Bearer|Basic|Token`, `Bearer <blob>`, `Cookie:` — **no hits**.
- Token-bearing env vars (`GH_TOKEN`, `GITHUB_TOKEN`, `HF_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `WANDB`): **no hits** (the only `huggingface` matches are the package name `huggingface-hub==0.36.0` in `evidence/phase2/raw/environment/gate21_pip_freeze.txt:69` and Phase-1 equivalents).
- URL-embedded credentials (`scheme://user:pass@host`), Slack/Discord webhooks — **no hits**.
- Only textual matches for secret *patterns* are methodology mentions inside the Phase-1 review doc (`findings/subagent_evidence_review.md:53,65` — lists the grep patterns themselves; not secrets; Phase-1 file, out of Phase-2 scope).
- Commit authorship uses a noreply bot identity (`AIwork4me <AIwork4me@users.noreply.github.com>`) — no personal email exposure (good hygiene).
- `scripts/phase2/generate_manifest.py` and all 17 `scripts/phase2/*` scripts: no embedded credentials, no `gh api`/auth usage; upstream GitHub JSONs under `evidence/phase2/raw/upstream/` contain only public API fields (URLs, logins) — no auth material.

## 2. Machine-identifying data — ACCEPTABLE (within agreed provenance policy)

- Hostname `DESKTOP-IF0424E`: 10 occurrences in Phase-2 files, all inside raw failure/capture logs (e.g. `evidence/phase2/raw/yolo_closure/train_amp_off.txt` x3, `evidence/phase2/raw/candidateA/*.txt` provenance headers). This is the auditor machine's name in failure-log provenance — the explicitly allowed category. No *other* hostnames appear anywhere in `evidence/phase2`, `docs`, `findings` (Phase-1 file `evidence/raw/external/miopen_3956_issue.json` contains a third party's `DESKTOP-FSHC0VD` inside a public upstream GitHub issue body — public data, out of scope).
- Username `rocm` appears in reproducibility provenance headers (e.g. `evidence/phase2/raw/candidateA/A_conv.txt:3` — interpreter `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe`, `ROCM_PATH=...patches\shim_stl`). Generic handle, required for env reproduction; consistent with Phase-1 policy.
- No MAC addresses, serial numbers, `MachineGuid`, Windows product IDs, `OneDrive`/`Dropbox` paths, or `Documents`/`Downloads`/`Pictures` references anywhere in Phase-2 files.
- No personal emails (gmail/outlook/hotlight/yahoo/proton/qq/163) in any tracked file.
- Non-local usernames in evidence (`/home/logan` in `evidence/raw/external/therock_842_body.txt`; `/Users/BrianHarrisonAMD`, `/home/runner`, `/home/task_*` in `evidence/phase2/raw/upstream/commit_ce14dab3.json` and pip-freeze `direct_url.json` paths) all originate from **public upstream GitHub issue/commit API JSON and PyPI wheel build metadata** — acceptable, not local leakage.

## 3. Personal / unrelated file leakage — CLEAN

- Zero tracked files under `runs/`, `datasets/`, `coco8/` (`git ls-files` verification).
- YOLO closure logs reference only the public dataset name `datasets\coco8` (`evidence/phase2/raw/yolo_closure/train_default_amp.txt`, `train_amp_off.txt`) — path strings only, no dataset contents.
- No model weights or media committed: no `.pt/.pth/.onnx/.png/.jpg/.zip/.tar/.gz` tracked anywhere (repo-wide check).
- Working tree: ignored-but-present `evidence/tmp/` and comgr `.o/.so` outputs remain untracked as designed.

## 4. `.gitignore` coverage & committed binaries — FINDINGS (hygiene)

`.gitignore` is well-designed: model weights, `datasets/`, `runs/`, `coco8/`, Python/conda caches, compiled artifacts (`*.dll *.so *.hsaco *.o *.obj *.exe *.cubin *.fatbin`), `evidence/tmp/`, OS/editor junk, and a secrets stanza (`*.env`, `*.token`, `credentials*`). `.gitattributes` correctly marks `evidence/phase2/** -text` for byte-exact custody (lines 17-20).

**F4.1 (Medium, hygiene): 3.43 MB of LLVM bitcode binaries committed.** 72 `.bc` files under `evidence/phase2/raw/miopen/comgr_temps_capture/` (e.g. `comgr-108888-2-a76203/rocm/amdgcn/bitcode/`). Breakdown:

- Bulk device-libs copies from the installed ROCm wheel: `opencl.bc` **2,653,712 bytes** (30% of the entire 8.9 MB tracked repo by itself), `ockl.bc` 268 KB, `ocml.bc` 203 KB, `asanrtl.bc` 35 KB, `hip.bc`, plus 60+ tiny `oclc_*` control bitcodes.
- Genuinely evidentiary compilation artifacts of the audited kernel: `output/CompileSource.bc` 48 KB, `input/linked.bc` 47 KB, `input/LLVM Binary` 48 KB (extension-less binary).
- Total tracked repo = 8,893,603 bytes across 423 files; `evidence/phase2` = 8.37 MB, of which bitcode = 3.43 MB (41%).

The audit brief expects "text/JSON only plus the extracted kernel tree .hpp/.cpp text files"; the wholesale comgr-temp capture violates that shape. The device-libs bitcode is re-distributable ROCm content (MIT/"AMD GPU open" style licenses with notice requirements) — committing it into this repo should be a deliberate, documented choice, and at minimum the four large library bitcades (`opencl/ockl/ocml/asanrtl`) could be replaced by hash references. Related inconsistency: `.gitignore:29-37` excludes `*.o`/`*.so`/`*.hsaco` comgr *outputs* but not `*.bc` *inputs*, which directly causes finding F5.3 below (manifest entries for files git refuses to track).

## 5. `evidence/phase2/SHA256SUMS.txt` verification — FINDINGS (custody integrity)

**Full verification, all 315 entries** (Python `hashlib` over `git cat-file blob HEAD:<path>`, cross-checked against working-tree bytes; plus 14 independent `sha256sum` CLI spot-checks):

- **297/315 PASS** — recorded hash == committed blob == disk. Spot-checks with `sha256sum` CLI (10 OK + 4 demonstrating failures): `candidateA/A_conv.txt`, `candidateA/A_yololike.txt`, `clean_env/F_yolo_train.txt`, `comgr_temps_capture/.../opencl.bc`, `.../CompileSource.bc`, `extracted_kernel_tree/include/hiprtc_runtime.h`, `extracted_kernel_tree/MIOpenBatchNormFwdTrainSpatial.cpp`, `upstream/commit_ce14dab3.json`, `yolo_closure/train_amp_off.txt`, `hiprtc/gate25_include_discovery.txt`, `.../input/LLVM Binary` — all **OK** (requirement of >=10 spot-checks exceeded).

**F5.1 (High, custody): 11 entries hash CRLF disk bytes while the committed blob is LF-normalized.** `SHA256SUMS.txt` lines 19-23, 25, 26, 28-31 (all `evidence/phase2/raw/environment/gate21_*.txt|json` and `gate22_*.txt|json`). Example: line 23 records `6808c15c…` for `gate21_pip_freeze.txt`, committed blob is `76b7b5aa…`. Root cause (verified): these files were committed in `2c86053` (gates 20-22) **before** the `evidence/phase2/** -text` attribute was introduced in `fa6f191`; with `core.autocrlf=true` git normalized CRLF→LF at add time, and the later attribute does not renormalize existing blobs. `git ls-files --eol` confirms: broken files `i/lf w/crlf`, healthy files `i/crlf w/crlf`. Gate 43's `generate_manifest.py` hashed *disk* bytes. Result: no fresh clone can ever verify these 11 lines (`-text` prevents smudge on checkout).

**F5.2 (High, custody): 1 entry stale after post-manifest commit.** `SHA256SUMS.txt:296` records `16685c41…` for `evidence/phase2/raw/restart/gate36_fresh_shell.txt`, but commit `98e5abd` appended the fresh-shell PASS section (85 insertions) **without regenerating** `SHA256SUMS.txt`/`MANIFEST.json`. Committed/disk hash: `6583ba08…`.

**F5.3 (High, custody): 6 entries reference files `.gitignore` keeps out of the repo.** `SHA256SUMS.txt` lines 40-42, 118-120: `comgr-108888-0-0a632a/output/Assembly Text.o`, `comgr-108888-1-3f12b0/input/Assembly Text.o`, `comgr-108888-1-3f12b0/output/a.so`, `comgr-108888-4-8c2693/output/linked.o`, `comgr-108888-5-efafd3/input/linked.o`, `comgr-108888-5-efafd3/output/a.so`. They exist on the auditor's disk only (hashes are locally valid); `*.o`/`*.so` ignore rules mean a fresh clone fails `sha256sum -c` with missing files. Root cause: `generate_manifest.py:19` walks the tree with `os.walk` (blind to `.gitignore`).

**F5.4 (High, cross-phase custody): Phase-2 modified a Phase-1-hash-covered file.** Commit `1ee5701` rewrote `evidence/raw/batchnorm/bn_variants_results.json` (bn1d_3d/bn2d cases flipped to `pass: true` after the Candidate-A shim — a legitimate experimental result, recorded nowhere as a Phase-1 amendment). Phase-1 `evidence/SHA256SUMS.txt:2` records `c962a271…`; the committed file is now `c1c6090d…`. The Phase-2 manifest note "Phase-1 evidence/SHA256SUMS.txt untouched" (true of the sums file itself) masks that a covered artifact changed underneath it. Verifying Phase-1 sums now fails on this one line.

**F5.5 (Low, documentation accuracy):** `docs/PHASE2_CLAIMS_AND_EVIDENCE.md:39-41` states Phase-2 raw artifacts "are committed byte-exact" — false for the 12 files in F5.1/F5.2.

**Net effect:** on a fresh clone at `98e5abd`, `sha256sum -c evidence/phase2/SHA256SUMS.txt` fails on **18 of 315** lines (12 hash mismatches + 6 missing files), and Phase-1 verification fails on 1 line.

## Remediation required for unconditional PASS

1. Re-commit the 11 `environment/gate21_*/gate22_*` files byte-exact (`git add --renormalize` inverse: checkout blobs, replace with the recorded CRLF disk bytes, re-commit under the existing `-text` rule) **or** regenerate `SHA256SUMS.txt` from committed blobs — pick one source of truth and state it in the manifest.
2. Regenerate `SHA256SUMS.txt`/`MANIFEST.json` after the `98e5abd` gate36 update (and after any future evidence change — make manifest generation the last step of every evidence-touching commit).
3. Either `git add -f` the six `.o/.so` comgr outputs (they are small: 3.5 KB `Assembly Text.o`, `a.so`, `linked.o`) or drop their entries from manifest/sums; if dropped, record their hashes in a sidecar note since the comgr output identity is evidentiary.
4. Restore `evidence/raw/batchnorm/bn_variants_results.json` to its Phase-1 hash and record the shim-on result as a *new* Phase-2 artifact (e.g. `evidence/phase2/raw/candidateA/bn_variants_with_shim.json`), or add an explicit Phase-1 amendment entry re-hashing it.
5. Decide and document the `*.bc` policy: keep only the kernel-compilation bitcode (`CompileSource.bc`, `linked.bc`, `LLVM Binary`) in-repo and reference the installed device-libs by hash, or document the bulk inclusion as intentional; add `*.bc` to `.gitignore` if the former.
6. Update `docs/PHASE2_CLAIMS_AND_EVIDENCE.md:39-41` to match the final state.

## Summary table

| # | Check | Result |
|---|-------|--------|
| 1 | Tokens/credentials/keys/auth headers/cookies | PASS — none found |
| 2 | Machine-identifying data beyond allowed provenance | PASS — only `DESKTOP-IF0424E` (allowed) + generic username `rocm`; no MAC/serial/personal paths/emails |
| 3 | Personal/unrelated leakage (runs/, datasets/, weights) | PASS — none tracked |
| 4 | `.gitignore` coverage & binary hygiene | FINDING F4.1 — 3.43 MB device-libs `.bc` binaries committed (incl. 2.65 MB `opencl.bc`); `*.bc` absent from ignore policy |
| 5 | SHA256SUMS integrity | FINDINGS F5.1-F5.5 — 297/315 OK; 11 CRLF/LF normalization breaks, 1 stale after later commit, 6 gitignored phantom entries, 1 Phase-1 covered file silently modified |

**Verdict: CONDITIONAL PASS** — security-clean (no secrets, no personal data, no leakage), conditional on remediating the custody-chain breaks F5.1-F5.4 and the binary-bulk decision F4.1.

*Audit artifacts: full-file hash classification and spot-check commands reproducible from this report; audit performed 2026-10-07 against `98e5abd`.*
