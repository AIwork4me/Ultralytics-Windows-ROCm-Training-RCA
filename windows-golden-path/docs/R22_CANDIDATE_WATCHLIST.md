# R22 CANDIDATE WATCHLIST (live as of 2026-11-15T16:20Z)

Re-run `run-golden-path.ps1 -Mode PrepareRelease` to refresh; verdicts below
carry their proof method — none are date-guesses.

| Channel | Package set | Fix in MIOpen? | Proof (2026-11-15) | Action |
|---|---|---|---|---|
| multi-arch | torch 2.12.0+rocm7.14.1 | ❌ ABSENT | P14/P16 frozen binary audits + R21-D1 live no-STL FAIL on this host | none (frozen) |
| stable whl-next | torch 2.14.0+rocm10.1.0, rocm-sdk-libraries 10.1.0 | ❌ ABSENT | P16: wheel `0c34bafb…` byte-identical, DLL `266d716b…` = `3.6.1.39d8d603` (2026-09-16), marker 0 | **watch for >10.1.0** → full OfficialStable sequence |
| **rc whl-next** | torch 2.15.0+rocm10.2.0rc2, rocm-sdk-libraries 10.2.0rc2 | ❌ ABSENT **(new proof)** | wheel `ffbf6c77…`, DLL `2a3a026c…` = `3.6.2.8faffed0f` marker 0; compare `f0a5d266...8faffed0f` **diverged, behind_by=92** (built 2026-11-06 from a pre-merge branch) | watch 10.2.0rc3+ — must re-prove ancestry, never assume |
| **nightly whl-next** | rocm-sdk-libraries 10.3.0a20261115 | ✅ PRESENT | wheel `33f5ea8a…`, DLL = `3.6.3.9ea8cfc5` **marker 2**; `9ea8cfc5` behind_by=0 (ahead 1011) — re-verified today | gfx1100 device wheels **not listed** on nightly; full gfx1100 stack blocked there; watch for their appearance |
| **dev whl-next** | rocm-sdk-libraries 10.3.0.dev0+\<TheRock sha\> | ✅ PRESENT | installed `+ff576965` → submodule `4e7d93e3` behind_by=0 (ahead 604); gfx1100+gfx1151 device wheels present; torch 2.15.0+git dev runs on gfx1100 (CUDA available) | **validated at DEV_CANDIDATE level tonight (see evidence/r22-dev)**; ceiling DEV_CANDIDATE_PASS |

## What unlocks OFFICIAL_STABLE_PASS

1. A TheRock release tag cut from a post-`f0a5d266` rocm-libraries pointer
   (therock-10.2/10.3…), landing as `rocm-sdk-libraries >10.1.0` on
   **stable** whl-next with the full gfx1100+gfx1151 device-wheel set, or
2. an AMD post-release (`.postN`) of 10.1.0 carrying the fixed MIOpen —
   either way the artifact must pass: wheel+DLL SHA256 → marker → ancestry
   compare → no-STL runtime → full gate suite on BOTH architectures.

## Owner dependency

[ROCm/rocm-libraries#15862](https://github.com/ROCm/rocm-libraries/issues/15862)
remains the routing issue (no assignee as of R20). The R20 release-owner
request (4 questions) is posted in-repo; nothing here closes it.
