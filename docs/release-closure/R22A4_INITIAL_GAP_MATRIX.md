# R22A.4 Initial Gap Matrix — PR #17 (gfx1100) vs PR #18 (gfx1151)

- Generated: 2026-11-16 (R22A.4 independent gap audit, mission §2)
- Integration base under review: `81477298bb25af892a457b57b4401e8c96fb9b15`
- PR #17 HEAD reviewed: `f903f94fe40bd2d2f18e80fad5ac5e7bca4cad86` (5 commits ahead of base)
- PR #18 HEAD reviewed: `678d3a8bd6e41e8051dbd8d073fe89c186c860c9` (3 commits ahead of base)
- Both PRs branch DIRECTLY from the base (merge-base == base for both; 0 behind).
- Method: full read of both PR HEAD trees (scripts, tests, evidence JSON, logs, docs,
  manifests) plus `gh pr view/checks` live state. CI `cpu-contract` PASS on both
  exact heads (runs 43862231878 / 43847912285).

Classification legend (mission §2): `SAME_BEHAVIOR`, `COMPATIBLE_IMPROVEMENT`,
`TRUE_CONFLICT`, `EVIDENCE_SCHEMA_DIFFERENCE`, `GPU_SPECIFIC_REQUIREMENT`,
`UNSUPPORTED_CLAIM`.

---

## A. AdamW instrumentation

| Aspect | PR #17 (gfx1100) | PR #18 (gfx1151) | Classification |
|---|---|---|---|
| optimizer wrapper | wraps `opt.step` on the public instance; counts invocations + pre/post **whole-model parameter checksum** per step | wraps `opt.step`; per-step **sentinel tensor deltas** (3 smallest-numel params from EVERY group) + reads fused-path `found_inf`/`grad_scale` attributes | EVIDENCE_SCHEMA_DIFFERENCE |
| forced-optimizer guard | `evaluate_adamw_contract` rejects `optimizer_requested != "auto"` | `compute_adamw_verdict` A2 hardcodes `requested="auto"` into facts — a forged receipt cannot be caught | COMPATIBLE_IMPROVEMENT (PR17) — unified contract adopts the guard |
| synthetic rejection | `harness_fixture` / missing `gpu_name`/`gfx_target` → hard FAIL | absent from `compute_adamw_verdict` (only later `r22a3_acceptance.physical_provenance_ok` checks gpu_name/gfx1151) | COMPATIBLE_IMPROVEMENT (PR17) |
| sentinel-vs-checksum | checksum covers ALL params but only as a boolean change signal | sentinels give measured per-step delta magnitude per group; misses nothing required by contract (full `raw_trainer_model_delta` still computed) | SAME_BEHAVIOR at contract level; PR18 measurement is richer per-step |

## B. Fused/non-fused optimizer semantics

- PR #17: contract treats a step as effective IFF parameter checksum changed;
  docstring explicitly documents that with fused AdamW under GradScaler the
  Python-level call runs on every attempt and the skip happens inside the kernel.
- PR #18: additionally reads `opt.found_inf` / `opt.grad_scale` attributes
  (GradScaler-registered, fused path) and counts `skipped_found_inf_flagged`.
- Both refuse to count invocation counts as update evidence.
- Classification: **COMPATIBLE_IMPROVEMENT (PR18 attribute observation; PR17
  guard semantics)** — no conflict; unified harness records both.

## C. GradScaler step accounting

- PR #17 facts: `optimizer_steps_underlying=11`, `confirmed_update_events=6`,
  `scaler_step_attempts=11`, backoffs from per-attempt scale series = 5.
- PR #18 facts: `attempted_invocations=11`, `effective_updates_sentinel_proven=7`,
  `skipped_found_inf_flagged=4`, backoffs from series = 4.
- Both count backoffs from the full scale series, never endpoints.
- Classification: **SAME_BEHAVIOR** (different key names only —
  EVIDENCE_SCHEMA_DIFFERENCE for the adapters, not a semantic conflict).
  The 6-vs-7 / 5-vs-4 difference is a factual per-architecture observation
  (different GPUs, different runs), NOT a harness disagreement; both receipts
  carry per-step series proving their own numbers.

## D. Finite gradient checking

- PR #17: every step checks ALL param groups with non-None grads; contract
  requires finite at every CONFIRMED update (skipped nonfinite steps recorded
  separately as GradScaler working as designed).
- PR #18: every step checks ALL groups (fixes R21 group-0-only limitation);
  contract A11 requires finite on stepped (non-found_inf) updates.
- Classification: **SAME_BEHAVIOR**.

## E. Parameter delta evidence

- Both snapshot `named_parameters()` before vs raw trainer model after vs
  loaded (EMA) model after; both compute `tensors_changed_beyond_1e-9`.
- Both exclude buffers from update evidence (PR17 snapshots buffers separately
  and never counts them; PR18 relies on named_parameters never yielding buffers
  and has an only-BN-changed FAIL test).
- gfx1100: 366/366 changed; gfx1151: 366/366 changed.
- Classification: **SAME_BEHAVIOR** (+PR17 buffer_delta disclosure is a
  COMPATIBLE_IMPROVEMENT).

## F. Autocast dtype evidence

- PR #17: first Conv2d output dtype samples (list) → `low_precision_op_samples`;
  no low-precision observation → INCONCLUSIVE.
- PR #18: stem-conv dtype histogram `{"float16": 48}`; no low-precision
  observation → INCONCLUSIVE (A5); dtype-not-observed → INCONCLUSIVE (A6).
- Both: autocast enabled 48/48 forward samples; observed-not-assumed dtypes.
- Classification: **SAME_BEHAVIOR** (EVIDENCE_SCHEMA_DIFFERENCE: list vs histogram).

## G. Windows DataLoader worker monitoring

- PR #17: OS-truth CIM snapshots (`Get-CimInstance Win32_Process`) → process
  tree descent, `peak_concurrent_workers`, `worker_pids_observed`, orphan
  re-scan after child exit. No third-party dependency.
- PR #18: psutil `TreeMonitor` sampling thread with per-PID
  first/last-seen/sightings/`create_time` records; `lingering()` orphan check
  on known PIDs. Richer lifecycle identity (PID-reuse key) but requires psutil.
- Classification: **EVIDENCE_SCHEMA_DIFFERENCE** + partial TRUE_CONFLICT on
  "OS worker activity evidence": both are OS-level (neither trusts torch
  internals), PR17 measures peak concurrency, PR18 measures identity+lifetime.
  Unified harness adopts BOTH: identity/lifetime records AND peak concurrency,
  without inferring simultaneity from distinct-PID counts (mission §4-I).

## H. Spawn safety

- PR #17: `child_has_main_guard()` checks `__main__` guard + `freeze_support()`
  + `def main():` presence; recorded per run; matrix NO-GO if absent.
- PR #18: `child_spawn_safe()` additionally rejects module-level `train(`/`YOLO(`
  calls structurally, and the runner REFUSES to execute an unsafe child.
- Classification: **COMPATIBLE_IMPROVEMENT (PR18 structural check)**; unified
  harness keeps the refuse-to-run behavior AND the matrix-level gate.

## I. Timeout / exception handling

- Both bound per-run execution (PR17: poll loop + `bounded_terminate`
  terminate→kill escalation, exit 124; PR18: `communicate(timeout=)` + kill,
  exit 124, plus overall wall budget). PR17 timeout fails the whole matrix even
  if later runs succeed (`evaluate_workers_matrix` timeouts → NO-GO; PR18
  `overall_workers8_verdict` counts statuses — a timed-out run is status FAIL so
  it also NO-GOs; PR17 additionally has an explicit test).
- Classification: **SAME_BEHAVIOR** (PR17's explicit matrix rule +
  PR18's overall budget are COMPATIBLE_IMPROVEMENTs to union).

## J. Process termination

- PR #17: `bounded_terminate` (terminate → wait(grace) → kill) only ever kills
  OUR OWN child; orphan scan observes only.
- PR #18: `proc.kill()` on timeout; `lingering()` observes known descendants —
  never kills foreign processes.
- Classification: **SAME_BEHAVIOR** (PR17's graceful escalation retained).

## K. Cache classification

- PR #17: `assign_cache_roles` + strict matrix — first use of a fresh shared
  warm home is `cache_priming`, NOT pre-warmed; `home_pre_existed` direct
  evidence wins; matrix requires exactly 2 COLD (distinct homes) + ≤1 priming +
  exactly 3 qualifying WARM on ONE shared home. gfx1100 frozen matrix honestly
  reclassified (2C+1P+2W) + ONE justified ADDITIONAL warm run (26.0 s,
  `home_pre_existed=true`) = 3 qualifying.
- PR #18: `overall_workers8_verdict` classifies by `"cold(" in cache_class` /
  `"warm" in cache_class` — **no priming distinction, no home-identity check,
  no home_pre_existed evidence**. The frozen gfx1151 record claims
  `warm 3/3`, but run R3 (198.4 s ≈ cold 199.2/195.3 s; first use of fresh
  `warm-home-b`; R4/R5 = 82.9/60.7 s) is a **CACHE_PRIMING run** by exactly the
  evidence pattern PR #17 established. True composition: **2 COLD + 1
  CACHE_PRIMING + 2 WARM**.
- Classification: **UNSUPPORTED_CLAIM (PR #18 "warm 3/3") + TRUE_CONFLICT
  (classification algorithms disagree)**. Unified contract adopts PR #17's
  semantics; gfx1151 needs either honest downgrade or ONE additional warm run
  on the retained home (mission §5/§13) to complete 2C+3W.

## L. Raw evidence completeness

- PR #17: original failed attempts preserved (`_attempt1_harness_bug.log`,
  `_attempt2_contract_semantics.log`), 8 restored `runs/` files verified
  against frozen SHA256SUMS before staging (P0-A root cause: repo-wide
  `runs/` .gitignore silently excluded them), child logs for all 6 runs
  committed, derived reports cite original records (RECONCILIATION json).
- PR #18: attempts A1/A2/A3 preserved as separate logs + json, `runs/` child
  logs present via `R22A3_WORKERS8_RUNS.json` + per-run child facts embedded;
  `R22A3_WORKERS8.log` preserves the monitor traceback verbatim (correctly
  NOT deleted).
- Classification: **SAME_BEHAVIOR** (both preserve history honestly).

## M. SHA256 / manifest verification

- PR #17: `SHA256SUMS.txt` (28 entries, posix repo-relative), manifest 196→225,
  every entry verified against the EXACT GIT TREE (`git ls-tree` + `cat-file
  --batch`) by the extended `scripts/verify_release_closure.py` (P0-B);
  uncommitted worktree files are violations.
- PR #18: `SHA256SUMS.txt` (13 entries), manifest 196→212; no git-tree audit
  extension.
- Cross-PR manifest conflict surface: 29 vs 16 added entries with ZERO path
  overlap; only 2 same-path sha conflicts — both DERIVED files
  (`windows-golden-path/reports/r22a-gfx1151/report.json`,
  `R22A_DUAL_ARCH_MATRIX.json`) which each PR legitimately refreshed from its
  own side. Raw evidence: NO conflicts.
- Classification: **COMPATIBLE_IMPROVEMENT (PR17 git-tree audit adopted and
  extended to r22a3*/r22a4 packs)**; the 2 derived-file conflicts are
  reconciled by regenerating both from the unified tree (derived data may be
  regenerated; raw evidence is never rewritten).

## N. Combined acceptance recomputation

- PR #17: no dedicated combined-acceptance script on the branch; Part A/B
  verdicts recomputed by pure functions and consumed by the report builder +
  `verify_release_closure.py` gate rescan.
- PR #18: `r22a3_acceptance.py` recomputes Part A via
  `compute_adamw_verdict` — good — BUT line 62:
  `b_overall = part_b.get("workers8_overall") or overall_workers8_verdict(...)`
  **trusts the stored serialized overall verdict when present** (fail-open), and
  `overall_workers8_verdict` itself trusts stored per-run `status=="PASS"`.
- Classification: **TRUE_CONFLICT + fail-open defect (mission §5)**. Unified
  acceptance ALWAYS recomputes from frozen `runs[]` facts; stored verdicts are
  inputs-only, never authority.

## O. CPU adversarial tests

- PR #17 `test_harness_cpu.py`: 108 tests — `TestAdamwAmpContract` (20, incl.
  forced-optimizer + wrapper-save/call semantics) and `TestWorkersContract`
  (35, incl. strict matrix, cache roles, benign-vs-fatal, exit-0-fatal,
  duplicate identity, cold-home-sharing, two-priming, synthetic rejection).
- PR #18 `test_harness_cpu.py`: 94 tests — `TestAdamWAmpVerdict` (13),
  `TestWorkers8Verdict` (12), `TestChildSpawnSafety` (3, structural
  module-level-train rejection), `TestR22A3Acceptance` (5, combined verdict,
  wrong-arch, engineering-reference ceiling).
- Shared prefix (55 base tests): byte-identical scope.
- Classification: **TRUE_CONFLICT on file (both re-wrote the same file)** but
  complementary coverage; mission §10 union keeps every unique negative
  behavior and removes only provably-equivalent duplicates.

---

## Substantive discrepancies requiring action (P0/P1)

1. **P0 — PR #18 stored-PASS bypass** (`r22a3_acceptance.py:62` +
   `overall_workers8_verdict` trusting `status`): forged
   `workers8_overall=PASS` or per-run `status=PASS` must be rejected. Fix in
   unified acceptance; negative fixtures required (mission §5 list 1–13).
2. **P0 — PR #18 cache priming misclassification**: gfx1151 frozen matrix is
   2 COLD + 1 CACHE_PRIMING + 2 WARM, not "warm 3/3". Honest reclassification
   (derived, raw untouched) + ONE additional warm run on the retained
   `warm-home-b` (home_pre_existed=true) to reach 3 qualifying — exactly the
   gfx1100 R22A2.1 P0-D precedent.
3. **P0 — PR #18 monitor exception semantics**: `psutil.NoSuchProcess`
   traceback (from the pre-HEAD harness revision) killed the run-1 sampling
   thread mid-run; the receipt still certified PASS with no monitor-health
   state recorded. Historical evidence independently sufficient (13 PIDs ×
   33–148 sightings, all with ppid+create_time, per-run totals 258–979) →
   function-level training PASS PRESERVED with bounded monitor exception
   disclosed. Unified monitor: explicit `NoSuchProcess`/`ZombieProcess`/
   `AccessDenied` handling, `MONITOR_PROCESS_EXIT_RACE` vs
   `MONITOR_INTERNAL_FAILURE`, health state fields, fail-closed acceptance,
   bounded shutdown (mission §4 A–J).
4. **P0 — duplicated harness implementations**: two divergent
   `audit_adamw_amp.py` + `run_stability.py` + `test_harness_cpu.py` trees.
   Converge to ONE shared implementation + versioned adapters for both
   evidence schemas (mission §6/§7).
5. **P1 — manifest derived-file conflicts**: regenerate the two
   r22a-gfx1151 derived files from the unified tree; extend git-tree audit
   coverage to `r22a3*`/`r22a4*` packs.

## Non-conflicts (explicitly verified)

- Both PRs preserve `workers=0` default behavior (G8 contract unchanged;
  PR17 has a byte-shape test, PR18 keeps historical defaults).
- Both PRs never edit installed torch/Ultralytics; no new runtime deps except
  psutil (PR18, declared and used in CI already via base? — NO: psutil is a
  new dependency, CPU-CI must import-guard it; unified monitor keeps a CIM
  fallback so the CPU contract never requires psutil).
- Both PRs forbid arbitrary URL downloads; weights resolved locally.
- Raw evidence byte-sets are disjoint (zero path overlap) — the merger does
  not invalidate either architecture's raw hashes.
