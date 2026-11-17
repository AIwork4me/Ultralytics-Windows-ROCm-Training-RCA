# R22A.4 Dual-Arch Supplemental Reconciliation — gfx1100 + gfx1151

- Generated: 2026-11-16 (mission R22A.4 §9)
- Unified engine: `windows-golden-path/scripts/supplemental_acceptance.py`
  (+ `audit_adamw_amp.evaluate_adamw_contract` + `run_stability.evaluate_workers_matrix`)
- Evidence categories: every input below is IMMUTABLE_RAW_EVIDENCE (bytes
  frozen in Git, SHA-verified); this document and
  `windows-golden-path/reports/r22a4/dual_arch_acceptance.json` are
  DERIVED_RECONCILIATION (recomputed from the raw records via versioned
  adapters `r22a2-flat-v1` / `r22a3-nested-v1`).

## Verdicts

**R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED** — ceiling DEV_CANDIDATE
(OFFICIAL_STABLE / R23_RELEASE_READY / CLEAN_WINDOWS_INSTALL are NOT claimed).

Each architecture independently earned BOTH distinct conclusions:

| | gfx1100 | gfx1151 |
|---|---|---|
| Physical training (hardware trained) | PHYSICAL_TRAINING_FUNCTIONAL_PASS | PHYSICAL_TRAINING_FUNCTIONAL_PASS |
| Release-grade evidence (strict contract) | RELEASE_GRADE_EVIDENCE_ACCEPTED | RELEASE_GRADE_EVIDENCE_ACCEPTED |
| Per-arch verdict | R22A2_GFX1100_SUPPLEMENTAL_PASS | R22A3_GFX1151_SUPPLEMENTAL_PASS |

## Side-by-side facts (every cell recomputed from frozen records)

| | gfx1100 (PR #17) | gfx1151 (PR #18 + R22A.4) |
|---|---|---|
| GPU | AMD Radeon RX 7900 XTX | AMD Radeon(TM) 8060S Graphics |
| gfx_target | gfx1100 | gfx1151 |
| Official DEV snapshot | TheRock ff576965 / torch 2.15.0+gitf6cd88cb.devrocm10.3.0 | same |
| MIOpen DLL SHA256 | 47a2e32c…83b91 (expected) | 47a2e32c…83b91 (expected) |
| runtime_class (receipts) | OFFICIAL_CANDIDATE | OFFICIAL_CANDIDATE (frozen five); additional sample receipt INCONCLUSIVE (channel arg default — disclosure below) |
| AdamW auto selected | observed (args rewritten → AdamW) | observed (args rewritten → AdamW) |
| Autocast forward | 48/48 | 48/48 |
| Low-precision dtype OBSERVED | torch.float16 (48 samples) | float16 (48 samples) |
| Step attempts | 11 | 11 |
| Effective updates (sentinel/checksum-proven) | 6 | 7 |
| Nonfinite skip / scale backoff | 5 | 4 |
| Named param delta | 366/366 tensors > 1e-9, all finite | 366/366 tensors > 1e-9, all finite |
| Workers configured / resolved | 8 / 8 | 8 / 8 |
| Worker identities observed (OS) | 13 per run (peak 13, CIM snapshots) | 13 per run (13 with create_time; peak 13 on the additional sample; interval-overlap lower bound 13 on frozen runs) |
| Matrix runs | 6 = 2 COLD + 1 CACHE_PRIMING + 3 WARM | 6 = 2 COLD + 1 CACHE_PRIMING + 3 WARM |
| Derived cache roles | [cold, cold, cache_priming, warm, warm, warm] | [cold, cold, cache_priming, warm, warm, warm] |
| Monitor health | independent corroboration (CIM sample counts + peak; per-run facts) | frozen five: independent corroboration (13 ids × 33–148 sightings); additional sample: full health record (59 samples, 0 unexpected exceptions) |

6-vs-7 effective updates and 5-vs-4 backoffs are FACTUAL observations of
different hardware/runs (different GPUs, different GradScaler trajectories) —
the unified contract contains no architecture-specific target numbers, and
both receipts carry full per-step series proving their own counts.
No dGPU vs APU performance comparison is made or implied.

## Cache-classification reconciliation (mission §5)

Both frozen matrices were re-derived from home identity, NOT from labels:

- **gfx1151**: run R3 (198.4 s ≈ cold 199.2/195.3 s) was the FIRST use of the
  fresh shared home `warm-home-b` (started 09:59:49, immediately after R2) —
  it derives **CACHE_PRIMING**. The frozen receipt's "warm 3/3" over-counted
  exactly like gfx1100's original claim (R22A.2.1 P0-D precedent). True frozen
  composition: **2 COLD + 1 CACHE_PRIMING + 2 WARM**. The historical claim is
  recorded as superseded (role_claim_discrepancy), never silently trusted and
  never deleted.
- **Completing the coverage** (mission §5/§13): ONE additional justified warm
  sample `R22A4-B-ADD1` was executed on the retained `warm-home-b`
  (`home_pre_existed=true`, own run id / timestamp / committed original log):
  exit 0, workers 8/8, 13 identities, peak concurrency 13, 64.5 s (warm
  range), monitor health fully recorded, MIOpen DLL 47a2e32c…, unified
  harness at committed SHA ed90141. Final qualifying composition:
  **2 COLD + 3 WARM** per arch. This was the ONLY new GPU run in R22A.4.
- gfx1100's composition was already completed the same way by R22A.2.1
  (additional sample at 26.0 s on the retained home, harness c07aa9b).

## Monitor-exception reconciliation (mission §4)

The frozen `R22A3_WORKERS8.log` preserves verbatim a `psutil.NoSuchProcess`
traceback that killed run-1's sampler thread mid-run (pre-R22A.4 harness
revision: `p.ppid() if p.is_running()` race). Disposition:

- Classified `MONITOR_PROCESS_EXIT_RACE` (expected Windows process-lifecycle
  race: worker exited between `children()` and `ppid()`).
- The traceback was NEVER deleted; the runner still certified PASS — the
  defect was the absence of monitor-health state, not the race itself.
- Independent corroboration (committed `R22A3_PROCESS_LIFECYCLE.json`):
  all five runs have 13 python.exe descendant identities, every one with
  ppid + create_time (PID-reuse key), 258–979 total sightings per run →
  the function-level training PASS for all five runs STANDS.
- The R22A.4 unified monitor makes the silent-death mode structurally
  impossible: the sampling loop cannot die silently (last-resort catch),
  health state (`monitoring_started/completed`, `thread_alive_at_shutdown`,
  `unexpected_exception_count`, `observation_samples`,
  `first/last_observation`) is always recorded, `NoSuchProcess` /
  `ZombieProcess` / `AccessDenied` are handled as distinct classified events,
  acceptance fails closed on unhealthy monitors without corroboration, and
  orphan detection is PID-reuse aware. 12 negative CPU tests pin these
  semantics.

## Stored-verdict bypass elimination (mission §5)

`r22a3_acceptance.py` previously did
`part_b.get("workers8_overall") or overall_workers8_verdict(...)` — a stored
serialized PASS was authority. The unified engine NEVER reads stored
verdicts: Part B is recomputed from frozen `runs[]` facts; Part A is
recomputed via schema adapters. Spoof fixtures prove: forged
`workers8_overall=PASS` with `runs[2].exit_code=1` → NO-GO; forged per-run
`status=PASS` → rejected; `optimizer_class=AdamW` with 0 effective updates →
rejected; `harness_fixture=true` with a real GPU name → rejected.

## Log-authenticity reconciliation (three historical hash FORMS)

Each era's runner hashed child logs differently; the adapter verifies a
committed log against the frozen receipt hash in ANY of the three forms and
records which matched:

| Pack | frozen receipt hash form | verification |
|---|---|---|
| r22a2 (gfx1100) | universal-newline decoded text (`read_text(errors=replace)`; progress-bar CR runs) | 6/6 match |
| r22a3 frozen five (gfx1151) | LF-normalized text (CRLF-translating write defect) | 5/5 match |
| R22A.4 additional sample | exact committed bytes (LF-written) | 1/1 match |

The recovered gfx1151 per-run child logs were staged ONLY after each file's
LF-normalized SHA256 equaled the frozen `raw_log_sha256` receipt value;
original bytes preserved (byte-exact via `evidence/raw/** -text`), no
synthetic replacements.

## Manifest reconciliation (mission §8)

- True UNION of both PRs' manifests: **257 entries** (228 + 29, zero path
  overlap); every hash aligned to committed Git blobs.
- Latent PR-#18-branch defects repaired and disclosed per-entry:
  (a) `678d3a8` edited the R22A3 doc without refreshing its manifest hash;
  (b) the R22A.3 manifest generator hashed CRLF working bytes while json
  blobs store LF (3 derived reports) — both classes are now STRUCTURALLY
  caught by the extended git-tree verifier (pack completeness for
  r22a2*/r22a3*/r22a4*, path-traversal / duplicate-conflicting-hash /
  self-referential-entry rejection). Verifier on the merged tree:
  **825+ checks, 0 violations** (22/22 adversarial self-tests).
- Both raw packs coexist byte-frozen; the merger invalidated neither side's
  raw hashes (zero overlapping raw paths).

## Disclosure: additional-sample receipt runtime_class

`R22A3_WORKERS8_WARM_ADDITIONAL.json` records `runtime_class: INCONCLUSIVE`
because the probe did not pass `--channel dev` (the first PASS result is
preserved; not re-run for a classification field). Classification authority
remains the package-lock provenance gate; stack identity is proven by the
receipt itself: torch 2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-ff576965…,
ultralytics 8.4.214, loaded MIOpen DLL SHA256 47a2e32c…83b91 — identical to
the frozen gfx1151/gfx1100 receipts. No claim is derived from the
INCONCLUSIVE field.

## Relationship of PRs

- PR #17 (gfx1100) merged FIRST (merge 4afe2fc, parents 8147729 + f903f94).
- PR #18 (gfx1151) carries the R22A.4 unified-harness commits and merges the
  integration branch in (merge commit reviewed conflict-by-conflict; unified
  implementations verified as supersets of PR #17's versions; manifest union
  rebuilt). No history rewritten; no force-push.

## What is NOT claimed

OFFICIAL_STABLE_PASS, R23_RELEASE_READY, CLEAN_WINDOWS_INSTALL — those
require their own future release gates (AMD Stable post-fix wheel, Stable
gfx1100/gfx1151 validation, G9 clean-Windows, independent user validation,
R23 documentation).
