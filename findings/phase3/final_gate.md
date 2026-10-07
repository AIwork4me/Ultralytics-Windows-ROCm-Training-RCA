# Phase-3 Final Gate (Gate 88)

Date: 2026-10-07. Branch `rca/windows-gfx1151-rocm714-phase3`.

## Gate checklist (50-88)

| Gate | Status |
|---|---|
| 50 Phase-2 handoff audit | PASS — challenged by subagent; amended (v2 semantics corrected, B8 added, cache/env confounders recorded) |
| 51 README refresh | PASS — phases 1/2 complete + 3 in progress; MSVC reframed as one sufficient STL provider |
| 52 upstream clone | PASS — develop `b68f8944`; blobs SHA1-verified via raw fetcher (network-adverse method documented) |
| 53 source audit | PASS — wrappers byte-identical to wheel; defect present in 10.x line; gate/macro census |
| 54 RTC dependency matrix | PASS — reusable script; 104 entries; full reachability/entity census |
| 55 patch design | PASS — Design D (availability probe) selected with falsifiable-decision record |
| 56 namespace-std risk | PASS — both failure directions (#3803 class + #7718 class) addressed structurally |
| 57 freestanding canaries | PASS — all entities compile+execute on gfx1151 via wheel hiprtc `-nostdinc`; probe both directions; std-starts-empty; initializer_list clang-lowering; `__is_trivially_copyable` |
| 58 candidate V1 applied | PASS — real tree; REAL BN kernel compiles no-STL exit 0 |
| 59 source-level tests | PASS — negative control (pristine tree → exact original signature); proposed CI test file |
| 60 build patched MIOpen | PASS — wheel toolchain, RelWithDebInfo, 3 iterations (V1/V2/V3) |
| 61 binary provenance | PASS — embedded-source markers verified; **caught the missing embed-list registration** |
| 62 safe injection | PASS — backup/swap/restore with SHA bookkeeping; loaded-path provenance per run |
| 63 no-MSVC confounder | PASS — single-variable A/B, MSVC tree renamed away, both arms live |
| 64 minimal BN | PASS — all builds |
| 65 BN matrix | PASS — 11/11 |
| 66 numerics | PASS — ≤9.5e-7 vs CPU |
| 67 YOLO closure | PASS — both amp modes, all builds |
| 68 next-header search | PASS — 11/11 both STL states; residuals identified→fixed in commit 2; kthvalue TU verified both states |
| 69 second Windows version | PARTIAL — runtime NOT TESTED (wheels delisted — documented with probe evidence); source gate VERIFIED in rocm-7.2.1 tag |
| 70 latest line check | PASS — gate still present in 10.x; full upstream-context dossier |
| 71-74 Linux | **BLOCKED — no Linux ROCm GPU environment** (record file; exact CI requirements documented) |
| 75 cross-platform summary | PASS — tested/correlated/reasoned/not-tested legend enforced |
| 76 final scope | PASS — 2-commit decomposition (defect fix + residual coverage) |
| 77 candidate V2→final | PASS — final series post-review-fixes |
| 78 full revalidation | PASS — V3: BN minimal/matrix/kernels(×2 envs)/YOLO(×2 amp)/no-MSVC A/B all green; wheel control FAIL reproduced |
| 79 distinction doc | PASS |
| 80 routing plan | PASS — amended per review (TheRock+docs first, clr lane added, export mechanism corrected) |
| 81 maintainer report | PASS |
| 82 PR draft | PASS — NOT submitted |
| 83 reviewer panel | DONE — 4 independent adversarial reviewers |
| 84 resolve blockers | PASS — all BLOCKER/MAJOR findings resolved or structurally scoped (see below) |
| 85 hygiene | PASS — secrets clean; 1,594 junk files removed; no binaries/weights tracked |
| 86 evidence integrity | PASS — manifest (self-excluding) + SHA256SUMS; Phase-1/2 untouched (accidental refresh reverted) |
| 87 README update | PASS (final commit) |
| 88 decision package | this file + `phase3_conclusion.json` + `docs/phase3/PHASE3_SUMMARY.md` |

## Gate-84 blocker/major resolution record

| Finding | Class | Resolution |
|---|---|---|
| B1 radix numeric_limits parse-time breakage (kthvalue, all platforms) | BLOCKER | `__INT32_MAX__`/`__INT64_MAX__` builtins; kthvalue TU now compiles no-STL AND with-STL (rc 0 both) |
| C1 partial-STL falsifies probe invariant | BLOCKER | loud `#error` cross-checks in both wrappers; verified live with the shim-dir state |
| A1/D2/C5 EOL churn (whole-file rewrites) | BLOCKER | LF-normalized; final series 560 lines (was 3,286); per-hunk real deltas |
| D1 no format-patch/DCO | BLOCKER | two-commit format-patch series with messages + `Signed-off-by:` placeholders (author identity intentionally left to the submitter) |
| D3 Linux missing | BLOCKER | structural — recorded as BLOCKED; no PR-readiness claim |
| A2/C9 is_pointer cv fidelity | MAJOR | helper+remove_cv pattern + 3 new self-tests |
| D4 AMD copyright on external work | MAJOR | contributor placeholder + PR-draft note |
| D5 CI test not in tree | MAJOR | proposed_ci_test/hiprtc_selfcontained.cpp (compile-only, no GPU) + wiring snippet |
| D6/A3/B-corroborated radix comment overclaim | MAJOR | comment states the actual invariant (builtin limits, no std dependency) |
| C2/C3/C4 routing misroutes | MAJOR | plan amended (ordering, clr lane, TheRock mechanism) |
| B2 utility→freestanding-traits asymmetry | MAJOR | utility now includes the WRAPPER (probe-consistent) |
| A4 design-doc guard promise | MINOR | `MIOPEN_FREESTANDING_TRAITS_ACTIVE` implemented |
| A5/A6/C6/C7/D7/D8/D13 wording/attribution artifacts | MINOR | all corrected; round-trip artifact + gate-71 record archived |

## Upstream actions taken

**NONE.** No PR, no issue, no comment, no push to any ROCm repository.
`upstream_pr_created: false`, `upstream_issue_created: false`,
`upstream_comment_posted: false`. Work products live only in
AIwork4me/Ultralytics-Windows-ROCm-Training-RCA (+ local build trees).

## Machine-state ledger (net changes vs Phase-2 handoff)

- `_rocm_sdk_core/lib/cmake/hip-lang/` build aid: ADDED for builds,
  REMOVED after (verified absent).
- Wheel MIOpen.dll: swapped to patched builds during Gates 62-78,
  RESTORED to pristine `74b4ee03…` (verified; sanity PASS).
- MSVC tree: renamed away twice for no-MSVC arms, RESTORED both times.
- Added (retained, outside the yolo_amd env): `rocm-libraries-phase3`
  clone, `phase3_deps` (shims/deps), `phase3_buildtools` venv,
  `build_phase3` outputs, `runs/phase3` YOLO outputs.
- No permanent change to the validated yolo_amd stack.

## Final gate result

**PHASE 3 CLOSED — WINDOWS PATCH CLOSURE PASS; UPSTREAM PR READINESS
BLOCKED ON LINUX REGRESSION** (the brief's sanctioned outcome). Stopped
for human/ChatGPT review. No upstream submission made.
