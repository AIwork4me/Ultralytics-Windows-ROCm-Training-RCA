# PHASE 0 — BASELINE (Round-3 mission, 2026-10-16)

## PR state (live GitHub API, queried 2026-10-16)

- PR: ROCm/rocm-libraries#13437 "MIOpen: make HIPRTC kernel includes self-contained without host STL"
- State: OPEN, mergeable: MERGEABLE, base: `develop`, head: `fix/miopen-hiprtc-no-host-stl` @ **f0f330c4837a3c4ca9736a8059410cca1a7c2b85** (unchanged since 2026-10-14 push; still matches mission's stated Round-2 HEAD)
- Third-round review: #5537906287 by `averinevg` (2026-10-15T18:52:26Z, commit f0f330c4): "Thanks, round 2 looks good." + **8 inline comments** (IDs below), all unresolved, none outdated.
- Older unresolved thread #4257536410 (round-2, radix.hpp IWYU): answered by AIwork4me reply #4273386178 (c6ed8131 added unconditional `miopen_cstdint.hpp` + `miopen_type_traits.hpp` includes); thread is `outdated=True` — code moved past it; reviewer's "round 2 looks good" covers it. No code change required beyond new comment #4286683533 (same file).

## Revision identities (three-way, per mission §2)

| Revision | SHA | Role |
|---|---|---|
| Unpatched develop baseline | b8cf0e7b526f4a25c0623f5b2a4fe41e03ede179 | Negative control only — NOT a performance baseline |
| Round-2 patched HEAD | f0f330c4837a3c4ca9736a8059410cca1a7c2b85 | Functional + performance baseline (2 commits: c6ed8131 source, f0f330c4 test) |
| Round-3 candidate | TBD this mission | Must preserve Round-2 behavior/perf |

## CI snapshot on f0f330c4 (runs 2026-10-14T16:16Z)

| Workflow | Run | Result |
|---|---|---|
| Libraries PR Bot | 38597078942 | success |
| PR Base Freshness / Auto Label | 38596611098 / 38596611005 | success |
| clang-tidy | 38596617172 | success |
| Component CI | 38596617223 | success |
| TheRock CI | 38596617364 | success |
| TheRock Multi-Arch CI ASAN | 38596619955 | success |
| **pre-commit** | 38596617241 | **failure** — clang-format: `std::forward` one-line bodies in `miopen_utility.hpp` must be multi-line (CI log evidence/`precommit_job.log`; exactly reviewer comments 7/8) |
| **TheRock Multi-Arch CI** | 38596620066 | **failure** — gfx942 shard 3/4 BatchNorm/Activation inference, `GPU Hang` (Phase 7 RCA target; job 116645608429) |

No other CI runs on this SHA. The two failures are the only red checks.

## Local repository state

- Main worktree of record: `C:\w56` (branch `fix/miopen-hiprtc-no-host-stl` @ f0f330c4, clean)
- Remotes: `origin` = ROCm/rocm-libraries (fetch-only, push=no-push), `fork` = AIwork4me/rocm-libraries (push target)
- `origin/develop` advanced b8cf0e7b → **c7943b12** (2026-10-16, hipdnn docs #11956; ~207 commits, none touching our 7 files; PR mergeable ⇒ no conflict ⇒ **no rebase**, per mission §5)
- Backup ref created & verified: `backup/pr13437-round2-f0f330c4` → f0f330c4 (existing ref pointed at correct SHA; not overwritten)
- Round-3 implementation worktree: `C:\w58`, branch `round3/wip` @ f0f330c4 (clean)
- Negative-control worktree (unpatched): `C:\wp` @ b8cf0e7b (detached) — reuse for Phase 4.2; do not modify feature branch for it

## Environment (Phase-4/5 targets, from machine state + memory)

- Windows 11, Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151), ROCm 7.14.0 wheels, torch 2.12.0+rocm7.14.0 in conda env `yolo_amd`
- Pristine wheel MIOpen.dll SHA256 `74b4ee03…` — must verify + restore around any DLL swap
- Existing validated build trees from Phase 5.7: build `C:\bfin` from worktree `C:\w56` @f0f330c4 (Round-2 A-side binaries); Round-3 build to fresh dir (e.g. `C:\b58`) from `C:\w58` after commit
- Known traps: flaky GitHub network (retry loops); CRLF smudging (hash `git cat-file blob` only); MIOpen per-label kernel cache needs USERPROFILE redirection for fresh-cache runs; PATH sanitization for configure (base-conda hipconfig leak)

## Reviewer requirements summary (Phase-1 input)

Eight inline comments, all by averinevg on f0f330c4:

| # | Comment ID | File:line | Requirement |
|---|---|---|---|
| 1 | 4286683533 | radix.hpp:35 | Drop the comment above the unchanged HIP-include block |
| 2 | 4286709599 | miopen_type_traits.hpp:41 | Drop partial-STL `#error` checks here and in miopen_utility.hpp |
| 3 | 4286753510 | miopen_type_traits.hpp:35 | Shorten file-header comments (type_traits, utility, initializer_list) to ~1–2 lines |
| 4 | 4286772017 | miopen_type_traits.hpp:107 | Add blank line |
| 5 | 4286919855 | miopen_type_traits.hpp:56 | Keep develop's ordering: integral_constant/true_type/false_type stay after remove_cv; remove obsolete HIP 6.x `#if` |
| 6 | 4286957313 | miopen_type_traits.hpp:61 | Don't modernize `typedef` → `using`; keep PR focused |
| 7 | 4287009694 | miopen_utility.hpp:47 | clang-format: multi-line `std::forward` (also failing CI pre-commit) |
| 8 | 4287010768 | miopen_utility.hpp:51 | clang-format: multi-line `std::forward` (also failing CI pre-commit) |

**Gate A+D: PASS** — every third-round comment mapped to a concrete change; no scope beyond the 8 comments + CI-red pre-commit fix; no rebase needed.
