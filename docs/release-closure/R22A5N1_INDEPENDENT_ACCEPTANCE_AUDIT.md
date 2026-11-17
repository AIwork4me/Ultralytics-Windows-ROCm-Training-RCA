# R22A.5N.1 Independent Acceptance Audit — hardened engine, gate-by-gate

- Generated: 2026-11-17 (mission R22A.5N.1 PHASE 3/5/6/7)
- Engine under audit: `scripts/r22a5n1/nightly_acceptance.py`
  (`r22a5n1-acceptance-v2`) — the historical R22A.5N engine is untouched and
  still reproduces pack A's original verdict (rechecked this mission).
- Evidence: original pack A (byte-frozen + recovered originals) and the new
  physical pack B `reports/r22a5n1/R22A5N1-GFX1151-20261117-B/`.

## 1. Trust-boundary eliminations (P0-C)

| Stored summary (old authority) | Independent recomputation (new) |
|---|---|
| `rules_checked.rocm_family_mix.ok` | families re-derived per package via `gp_lib.rocm_family_of`; single family {10} enforced |
| `rules_checked.device_wheel_present` | gfx1151 device-wheel trio re-derived from package names |
| `rules_checked.torch_is_amd_hip` | `gp_lib.torch_wheel_is_amd_hip(version, url)` on the lock's own torch record |
| `rules_checked.gpu_stack_origin_official_channel.ok` | per-artifact `gp_lib.classify_package_origin(…, channel="nightly")` |
| ABI (was implicit) | per-wheel python-tag/platform re-parse (abi3/py3/py2.py3 compatibility rules) |
| installed "looks right" | full 46-record lock ↔ 47-dist installed diff both directions (missing + rogue native) |
| `training_counts` counters | `recompute_step_statistics` from `per_step_events`: ordering, found_inf, sentinel deltas, unexplained no-update steps, moved-on-inf-skip, nonfinite-grads-on-effective, scale-history length + backoff consistency (every inf skip followed by scale decrease) |
| `orphan_verdict="CLEAN"` | leftover recomputed = all_pids − baseline − checker |
| census count | trainer PID + ≥8 distinct integer children with spawn_main command lines, ancestry chain to the envelope |
| G1 parent-process DLL | in-child identity required; pre-fix legs additionally captured AT-FAILURE (the child dies inside the BN HIPRTC compile) |
| checkpoint "restored" | optimizer state entries + post-resume effective updates + state-class serialization table |

New gate **LK** re-hashes the committed lock bytes and re-verifies every
training receipt's binding (`verify_lock_binding` reuse). Feeding pack A's
actual field values yields `SHA_MISMATCH` ×3 — the P0-A defect class is
detectable, demonstrated, and pinned as a unit test.

## 2. Gate results (pack B, engine output committed at
`08_acceptance/nightly_acceptance.json`)

| Gate | Verdict | Key recomputed facts |
|---|---|---|
| PKG | PASS | 46 records; family {10}; origin/ABI/device-wheel/installed-diff all clean; sdk wheel `b11baad9…`; audit DLL `f9312c3e…` build `25f28906`; ancestry ahead 1074/behind 0 (externally recorded, consistency-checked) |
| LK | PASS | lock SHA recomputed `cf147540…`; amp + workers receipts bound (channel nightly, gfx1151, runtime versions match lock records) |
| G0 | PASS | child DLL `f9312c3e…`, marker 2, op finite, parent==child, gfx1151 |
| G1 | PASS | candidate ×2 distinct PIDs/cold caches, in-child DLL `f9312c3e…`; control pre-fix (parent marker 0, at-failure in-child DLL `e97891df…`, signature `type_traits`/`HIPRTC_ERROR_COMPILATION` re-classified from RAW LOG bytes); characterized as strong source-lineage + behavioral control (not single-variable) |
| G2 | PASS | 9/9 gates, every numeric detail finite, no CPU fallback, runtime OFFICIAL_CANDIDATE |
| G3 | PASS | recomputed 11 attempts / 7 effective / 4 inf-skips; monotonic batch indices; no unexplained no-update steps; counters reconcile with stored; checkpoint exists; DLL `f9312c3e…` |
| G4 | PASS (AMP_PASS) | dtype histogram {float16:96} recomputed; autocast 48/48 enabled==sampled; 4 scale backoffs re-derived from the 11-point series |
| G5 | PASS | core resume verified — optimizer 366 state entries restored, start_epoch 1→4 continuity recomputed from numeric rows, 8/8 post-resume effective updates, third-process reload OK; state classes: model/optimizer/scaler/epoch/best_fitness/train_args/EMA serialized, scheduler NOT_SERIALIZED_BY_UPSTREAM; checkpoint bytes anchored to envelope artifact hashes |
| G7 | PASS | workers=8 as-run; census peak 16 spawn children (16 with `spawn_main` cmdlines), trainer tied to envelope via venv-launcher ancestry chain; orphan leftover recomputed empty |

Overall: **R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS** (exit 0).

## 3. Adversarial falsification (mission §9, 25 classes) — 45 CPU tests

All 25 mission cases pinned in `windows-golden-path/tests/test_r22a5n1_cpu.py`
plus engine-hardening and evidence-pack closure tests; 311 total suite green.
Every tampering is REJECTED or classified INCONCLUSIVE by contract (see the
test file for the case-by-case mapping; executed, not asserted).

Real defects found by this audit (fixed, disclosed):
1. P0-A DEV-lock misbinding (3 pack-A receipts) — root-caused, fail-closed
   gate added, receipts preserved.
2. Five caller-side raw logs never written by the instruments (lost) —
   envelope capture now owns them; gates re-proven by new physical runs.
3. G1 parent-only DLL capture weakness — in-child + at-failure capture added.
4. Census single-snapshot gap risk — bounded snapshot series with full
   process trees, peak cited, every snapshot retained.
5. Two instrumentation crashes during this mission (epoch-end `tloss` dict;
   state-class 'model'-vs-'ema' mapping) — attempts retained in the pack,
   instruments corrected, stages rerun.

## 4. Independent verification matrix

| Verification | Where | Result |
|---|---|---|
| Engine on pack B | `08_acceptance/nightly_acceptance.json` | AUDITED_PASS |
| Engine re-run in a CLEAN CLONE (no dev venv, no host paths) | fresh checkout cb0181c | identical overall + all 9 gates PASS |
| Pack B byte manifest | `SHA256MANIFEST.json` (106 entries) | verify ok, 0 problems |
| Pack A original manifest (29 entries) | clone re-hash | 29/29 match, byte-frozen |
| Historical engine semantics on pack A | `scripts/r22a5n/nightly_acceptance.py` | still `R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS` |
| CPU adversarial suite in clone | pytest | 311 passed |
| Closure verifier | `scripts/test_verify_release_closure.py` | 22/22 PASS |
| Ruff E4/E7/E9/F + compileall | changed trees | clean |

## 5. Honest limitations

- Ancestry (f0a5d266→25f28906) is an externally recorded gh fact; the engine
  consistency-checks it but does not re-clone TheRock offline. The load-bearing
  byte evidence (wheel + DLL SHA vs frozen audit) IS independently verifiable.
- Pack A weights (8 × 5.5 MB) remain host-side, hash-inventoried; pack B
  lifecycle checkpoints ARE committed for independent G5 byte verification.
- Single GPU (gfx1151); no Stable/dual-arch/G9 claim is made or possible.
