# Subagent C — Evidence & Git Hygiene Review (pre-publication audit)

Reviewed: 2026-10-07, by SUBAGENT C (evidence & git hygiene). Repo:
`C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA`
(target: `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA`). Note: a `.git`
directory was initialized by another agent *during* this audit (branch
`rca/windows-gfx1151-rocm714`, no commits yet); observations below reflect
the final state.

## Checks performed

### 1. Reproducibility (README vs scripts/ vs raw logs) — PASS
Method: compared README.md "Reproduce it yourself" (lines 84–92) and
docs commands against the `scripts/` inventory, the `### command:` headers
inside raw logs, and `evidence/manifest.json` command fields.
- All 15 scripts the task lists are present (`00_capture_environment.ps1`,
  `00_env_probe.py`, `01`–`04` .py, `05`–`09` .ps1, `10_dll_provenance.py`,
  `10_collect_artifacts.ps1`, `run_all_rca.ps1`). No doc references a
  missing script (docs reference only `01`/`02`/`03`/`run_all_rca.ps1` —
  all exist).
- README `python scripts\02_batchnorm_minimal.py minimal` — script parses,
  accepts `minimal`/`issue3956`/`yololike` (matches the three
  `evidence/raw/batchnorm/minimal_*.txt` logs).
- `run_all_rca.ps1` orchestrates 00→10 in the exact order that the raw
  evidence implies, writing to the same `evidence/raw/...` paths.
- Manifest commands match raw-log headers verbatim (e.g.
  `evidence/raw/ultralytics/train_gpu.txt` header = manifest entry =
  docs/EXPERIMENT_MATRIX.md P3 row; gemm.txt records an absolute
  `C:/Users/rocm/miniconda3/python.exe` prefix — equivalent command).
- All 23 unique `evidence/...` paths cited across README + 8 docs + the
  conclusion JSON exist on disk (checked programmatically; 3 apparent
  misses were regex artifacts of glob-style citations like
  `dll_provenance.json/.txt`).

### 2. Raw log integrity (manifest + SHA256SUMS) — PASS, one tooling defect
Method: full re-hash of everything (not just 10).
- `evidence/manifest.json`: 39 entries; all 39 files exist; **all 39
  sha256 AND size_bytes verified against disk — 0 mismatches** (Python
  hashlib walk).
- `evidence/SHA256SUMS.txt`: 39 lines, identical hashes/paths to manifest.
- Files on disk under `evidence/` but not in the manifest: only
  `manifest.json` and `SHA256SUMS.txt` themselves — by design.
- **Defect**: SHA256SUMS.txt has CRLF line endings, so the canonical
  `sha256sum -c evidence/SHA256SUMS.txt` fails on Linux/macOS/Git-Bash
  ("No such file or directory" x39, the `\r` pollutes the filename).
  After `tr -d '\r' < evidence/SHA256SUMS.txt | sha256sum -c -` all 39
  verify OK. See BLOCKING-1.

### 3. Secrets scan — CLEAN
Method: recursive case-insensitive regex over every committable file
(66 content files; `evidence/tmp/` excluded as untracked) for:
token, secret, password, api_key, authorization, bearer, cookie,
github_pat, ghp_, gho_, AKIA, BEGIN PRIVATE KEY, aau_token.
Hits, all benign:
- `evidence/raw/environment/conda_list_base.txt:13,218,220` and
  `pip_freeze.txt:10,209,210` — package *names* (anaconda-auth, tiktoken,
  tokenizers), not credentials.
- `docs/ENVIRONMENT.md:24` — "the 'PRO' token used in the task" (marketing
  name discussion).
- `scripts/00_env_probe.py:94,110` — the probe's own DENY_SUBSTRINGS filter
  that *strips* secret-like env vars from captures (protective).
- `.gitignore:50` — "# Secrets" section header.
- `findings/final_gate.md:25` — the string `aau_token` as a filename
  mention describing this very scan; no credential value anywhere.
No `ghp_`/`gho_`/`github_pat`/`AKIA…`/private-key values in any file.

### 4. Giant files / banned types — CLEAN
Method: `find -size +1M` and extension sweep over the whole tree.
- Largest file: 37 KB (`evidence/raw/external/rocm_libraries_2169_body.txt`).
  Nothing >1 MB anywhere (`.git` internals included).
- Zero `*.pt/*.pth/*.onnx/*.dll/*.exe/*.hsaco/*.pyc/*.obj` in the repo.
- `.gitignore` covers all banned classes (weights, datasets/, runs/,
  __pycache__, *.dll/*.exe/*.hsaco, evidence/tmp/). Verified live:
  `git check-ignore` confirms `evidence/tmp/` ignored via `.gitignore:40`;
  `evidence/tmp` contains only one 0-byte MIOpen lockfile.

### 5. Unsupported claims — 7 ledger rows spot-checked, ALL SUPPORTED
Method: opened each cited evidence file and compared to the claim text.
- C001 (`windows_os.txt`): "Windows 11 家庭版 中文版, 10.0.26200, 64位" — matches.
- C005 (`gpu-control/gemm.txt`): PASS, mean=0.015937, EXIT=0 — matches.
- C006 (`ultralytics/predict.txt`): "4 persons, 1 bus, 11.1ms", exit 0 — matches.
- C008 (`ultralytics/train_cpu.txt`): full metrics table + EXIT=0 — matches.
- C011 (`batchnorm/matrix_results.json`): case C fail w/
  `MIOpenBatchNormFwdInferSpatial.cpp`, case D fail w/
  `MIOpenBatchNormFwdTrainSpatial.cpp`, both HIPRTC_ERROR_COMPILATION(6) — matches.
- C014 (`ultralytics/train_gpu_amp_off.txt`): exit_code=1, same TrainSpatial
  signature incl. type_traits chain — matches.
- C019 (`toolchain/toolchain_probe.txt`): "no type_traits anywhere under
  `_rocm_sdk_libraries`", all compilers NOT FOUND, INCLUDE/CPATH unset —
  matches. (Citation nit: see NON-BLOCKING-2.)
- Bonus cross-check: normalized `training_failure_signature.txt` line refs
  [50],[52],[56],[132] verified against the 133-line raw train_gpu.txt — exact.
- Bonus: EXPERIMENT_MATRIX "F first-call compile 16.8 s" = matrix_results.json
  `seconds: 16.76` — consistent.

### 6. Command provenance headers — PARTIAL (acceptable, gaps listed)
Method: `head -5 | grep '### command'` over all 29 `evidence/raw/*.txt`.
- 12 experiment logs HAVE `### command:` headers (all batchnorm minimal/matrix,
  conv, gemm, dll_provenance, miopen-logging, predict, train_cpu/gpu/amp_off).
- LACKING `### command:` (have only `### captured <ts>`, and empty
  `command` in manifest.json): the 11 `environment/*.txt` captures,
  `miopen/temp_tree_inventory.txt`, `toolchain/toolchain_probe.txt`; plus
  sidecars `matrix_results.json`, `dll_provenance.json`, and the 2
  `normalized/` files (no command by nature).
- The 3 external body files (`rocm_libraries_2169_body.txt` etc.) carry no
  header at all — third-party verbatim content; retrieval provenance is
  documented in `evidence/raw/external/EXTERNAL_INDEX.md` (`gh api ...`).

### 7. Git cleanliness prep — PASS
Method: root listing + banned-name sweep + `git status`.
- Repo root contains only: `.gitignore`, `LICENSE`, `README.md`, `docs/`,
  `evidence/`, `findings/`, `scripts/`. No `bus.jpg`, `yolo26n.pt`,
  `runs/`, `datasets/`, `weights/` — those live in the parent
  `C:\Users\rocm\Desktop\YOLO_AMD\` directory, outside the repo (confirmed
  via paths inside predict.txt/train logs).
- `git status --short` shows exactly the 6 intended top-level entries
  untracked; nothing ignored leaks, nothing stray appears.

### 8. Locale/encoding artifacts (zh-CN Windows) — PRESENT, COSMETIC
Method: byte-level scan for high-bytes + known mojibake sequences.
- Mojibake (`鈹€鈹佲攣` — UTF-8 progress-bar glyphs re-encoded through GBK)
  in exactly 2 files, 6 lines total:
  `evidence/raw/ultralytics/train_gpu.txt:38,41,62` and
  `evidence/raw/ultralytics/train_gpu_amp_off.txt:36,39,60`.
- All evidentiary signature lines (the MIOpen/HIPRTC/type_traits/traceback
  block, lines ~50–132) are pure ASCII and unaffected;
  `train_cpu.txt` renders its bars correctly, showing the mojibake is a
  per-capture console-codepage artifact, not data corruption.
- Does not harm evidentiary value; do NOT "fix" (any edit would invalidate
  the recorded SHA256s). Document only — this section is that documentation.

### 9. phase1_conclusion.json vs docs/RCA.md — CONSISTENT
Method: `json.load` + field-by-field comparison.
- Valid JSON. `rca_depth_reached: "LEVEL 2"` = RCA.md "Root-cause depth
  reached: LEVEL 2 … LEVEL 3 not proven". `no_fix_applied: true` +
  `workaround_status: "none proposed; … diagnostic only"` = RCA.md
  §"What Phase 1 Does NOT Claim" + README Status section. Falsified /
  unresolved hypothesis lists (H1–H5, H12–H13 falsified; H10/H11 open;
  H8/H9 external-only) match RCA.md §Falsified/§Remaining.

## BLOCKING issues (must fix before publish)

1. **`evidence/SHA256SUMS.txt` uses CRLF line endings — the canonical
   verification command fails on Linux/macOS.**
   `sha256sum -c evidence/SHA256SUMS.txt` returns "FAILED open or read"
   for all 39 files on Linux (and in Git Bash on this very machine)
   because `\r` becomes part of each filename. The hashes themselves are
   correct (all 39 verify after `tr -d '\r'`), but an evidence-first repo
   whose checksum file cannot be verified with the standard tool on the
   majority-GitHub audience's OS undercuts its own integrity story.
   Fix (30 seconds, breaks nothing — SHA256SUMS.txt/manifest.json are not
   themselves checksummed): rewrite the file with LF endings
   (e.g. `tr -d '\r' < evidence/SHA256SUMS.txt > tmp && mv tmp evidence/SHA256SUMS.txt`)
   and add a `.gitattributes` line such as
   `evidence/SHA256SUMS.txt eol=lf` (or `-text`) so a Windows checkout
   cannot reintroduce CRLF.

## NON-BLOCKING issues

1. **Provenance gaps (checklist 6):** 14 raw/normalized files have no
   `### command:` header and an empty `command` field in manifest.json —
   notably `toolchain/toolchain_probe.txt` and `temp_tree_inventory.txt`
   (produced by `09_toolchain_probe.ps1` / `08_miopen_logging.ps1`) and the
   11 environment captures (produced by `00_capture_environment.ps1` /
   `00_env_probe.py`). The producing scripts are identifiable from
   `run_all_rca.ps1`, so rerunnability is not impaired; consider backfilling
   the manifest `command` fields for these in a later commit.
2. **C019 citation imprecision** (`docs/CLAIMS_AND_EVIDENCE.md:27`): the
   claim covers "no `type_traits` … under `_rocm_sdk_libraries` OR
   `_rocm_sdk_core`", but the cited `toolchain_probe.txt` only shows the
   `_rocm_sdk_libraries` sweep; the `_rocm_sdk_core` half is evidenced in
   `evidence/normalized/gate0_review.md:122`. I independently re-ran
   `find …/site-packages/_rocm_sdk_core -name type_traits` on the live
   machine — zero hits, so the claim is TRUE; only the evidence column is
   incomplete. Suggest adding `gate0_review.md` to C019's evidence cell.
3. **Mojibake in 2 GPU training logs** (see check 8) — progress-bar glyphs
   only; ASCII signatures intact. Documented here; no action (re-capture
   would change hashes and buys nothing).
4. **Forward references now partially satisfied:** `phase1_conclusion.json:5`
   (`"branch": "rca/windows-gfx1151-rocm714"`) and C030's "git history of
   this repo" (`CLAIMS_AND_EVIDENCE.md:38`) were written before git init.
   The branch now exists with the matching name (verified), but there are
   zero commits — C030's citation becomes true only after the first commit.
   Ensure the initial commit happens before the claims ledger is pushed.
5. **`findings/final_gate.md:23,25` cites `findings/subagent_*_review.md`**
   — only this file exists so far (final_gate.md itself appeared at 12:13,
   mid-audit, and pre-records the results of this review). If subagents
   A/B do not write their review files, that citation dangles; verify all
   cited review files exist at publish time.
6. **`run_all_rca.ps1` defaults hardcode machine-specific paths**
   (`C:\Users\rocm\miniconda3\python.exe`, `-WorkDir C:\Users\rocm\Desktop\YOLO_AMD`).
   They are parameterized, but README doesn't say another machine must pass
   `-Python/-Yolo/-WorkDir`. One sentence in README would help.
7. **UTF-8 BOM** at the head of several captured logs
   (e.g. `torch_probe.txt`, `conda_env_list.txt`) — cosmetic; PowerShell
   5.1 default encoding artifact; harmless to checksums (already baked in).
8. **Upstream kernel-name nuance:** #3956 reports
   `MIOpenBatchNormFwdTrainSpatialHIP.cpp` vs local
   `MIOpenBatchNormFwdTrainSpatial.cpp` (no `HIP` suffix). C022's
   "field-for-field" is slightly generous, but the difference is disclosed
   verbatim in `EXTERNAL_INDEX.md` §A, so no reader is misled.

## Verdict

**FIX THEN PUBLISH** — with exactly one trivial fix (BLOCKING-1: LF-endings
for `evidence/SHA256SUMS.txt` + a one-line `.gitattributes`). Everything
else the audit covered — reproducibility wiring, 39/39 checksum integrity,
secrets, file hygiene, sampled claim accuracy, JSON/RCA consistency, git
cleanliness — is publication-ready as-is; the remaining items are
documentation niceties that can land in follow-up commits.
