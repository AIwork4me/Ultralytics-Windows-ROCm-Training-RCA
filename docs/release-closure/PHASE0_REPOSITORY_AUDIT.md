# PHASE 0 — Repository Audit & Baseline Freeze

Date: 2026-11-14 · Branch: `work/windows-rocm-training-release-closure` · Base: `main` @ `f9f745e`

## 1. What was executed

| Step | Command | Exit | Result |
|---|---|---|---|
| fetch | `git fetch --all --prune` | 0 | origin/main updated 754e813 → f9f745e (PR #12 round-3 evidence merged upstream-side) |
| status | `git status` | 0 | clean except pre-existing untracked `phase5_5/docs/GTEST_ARCHITECTURE_COMPARISON.md` (left untouched) |
| HEAD | `git rev-parse HEAD` | — | `f9f745e4089621505e174b54a3f86ceb5b2f9ef2` (work branch created from this) |
| branches | `git branch -vv` | — | 12 historical branches verified; phase5_7/phase5_8 evidence branches **frozen, untouched** |
| manifest | `python -I phase5_8/pr13437_round3/scripts/verify_manifest.py` | 0 | **PASS** — 171 tracked payload files, zero mismatches; manifest_sha256 `2a3a23e8…` |
| ISA pairs | `python -I phase5_8/pr13437_round3/scripts/verify_isa_pairs.py` | 0 | **PASS** — 10/10 retained ELF pairs `.text`/`.note` equal; kth cache→ELF link verified |

Script safety audit (per §Phase0-9): both verify scripts were read before execution. Neither deletes
cache paths, replaces wheel DLLs, or writes outside its directory (manifest `--write` flag NOT used;
ISA verifier opens SQLite via a `TemporaryDirectory` copy with a `mode=ro` URI). Safe to run.

## 2. Mission-document facts re-verified live (2026-11-14)

| Claim | Verified | Via |
|---|---|---|
| RCA main = `f9f745e` | ✔ | git fetch + rev-parse |
| PR #13437 MERGED 2026-10-19, merge `f0a5d266` | ✔ | `gh pr view 13437 --repo ROCm/rocm-libraries` |
| TheRock #9359 MERGED 2026-10-20, merge `b0958085` | ✔ | `gh pr view 9359 --repo ROCm/TheRock` |
| #9359 = "Bump rocm-libraries cb26189 → d875648" | ✔ | PR title (exact) |
| d875648 contains fix | ✔ **PROVEN** | compare API: f0a5d266…d875648 → ahead_by=2, behind_by=0 |
| TheRock main submodule (2026-11-14) `9ea8cfc5` contains fix | ✔ **PROVEN** | compare API: ahead_by=1011, behind_by=0 |
| Latest TheRock release `therock-10.1` (2026-10-05) | ✔ | `gh release list` — predates merge; **no release contains the fix** |

Discrepancies: none material. `phase5_8` evidence lives at `phase5_8/pr13437_round3/`.

## 3. Local environment baseline (hardware probe)

- Windows 11 Home, build 26200; AMD Ryzen AI MAX+ 395; **Radeon 8060S, gfx1151**, driver `32.0.22032.6002`, 78.19 GB unified memory, 255 GB disk free.
- `torch.version.hip = 7.14.60850`, `torch.cuda.is_available() = True`, device recognized. **Native HIP GPU confirmed live.**
- Python 3.13.16 environments (all conda, isolated):
  - **A** `pm13437_official`: torch 2.12.0+rocm7.14.1 / ultralytics 8.4.182 — **pristine official wheel** (MIOpen.dll `e97891df…`, fix-marker 0) — never modified since creation 2026-10-19 (re-hashed today).
  - **B** `pm13437_merged`: same torch; MIOpen.dll at rest = official `e97891df…` (post-mission restore state); during patched legs the source-built `ed7c67a9…` (C:\b58m, marker=2, still present 2026-11-14) is swapped in and restored afterwards — never labeled "official".
  - `yolo_amd`: torch 2.12.0+rocm7.14.0 / ultralytics 8.4.174 — pristine 7.14.0 wheel (`74b4ee03…`, no fix).

## 4. Historical limitations carried forward (unchanged, still binding)

From phase5_8 (`EVIDENCE_FINAL_AUDIT.md`, `PERFORMANCE_AB_REPORT.md`, mission §1): 3-of-5 HIPRTC compiles were no-STL isolations; BN running_var CPU reference estimator caveat; AMP Round-3 FAIL was a wheel-reproduced environment condition, not proven-fixed; paired YOLO performance A/B **NOT_RUN**; ISA equality ≠ end-to-end performance equality; historical CI_STATUS is a snapshot; top-level README PR-status was stale (updated this phase). None of the frozen evidence was rewritten.

## 5. Exit criteria

- Historical evidence reproducibly verified (2/2 PASS). ✔
- New work tree clean on `work/windows-rocm-training-release-closure`. ✔
- Task dependencies & missing resources enumerated → see `EXECUTION_PLAN.md` (G0 provenance done same day: see `release-provenance/G0_VERDICT.md`). ✔
