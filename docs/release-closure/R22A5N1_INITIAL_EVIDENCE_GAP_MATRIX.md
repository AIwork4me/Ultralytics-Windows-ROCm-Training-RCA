# R22A.5N.1 Initial Evidence Gap Matrix — cold audit of the R22A.5N nightly pack

- Generated: 2026-11-17 (mission R22A.5N.1 PHASE 0 §3)
- Audited baseline: PR #22 HEAD `9713eec1bf8987a50916e0afd3d982ac068400c3`
  (branch `validation/r22a5n-gfx1151-official-nightly`, Draft, targeting
  `work/windows-rocm-training-release-closure`; exact-HEAD CI run 44014733379 success)
- Frozen integration HEAD: `ff52f87393d66f5773e95b70c1721550d8065b0b` (PR #21 merge)
- Method: `git ls-tree`/`git cat-file` byte-level inspection of all 29 manifest
  entries, independent SHA256 recomputation of every committed blob, cross-read of
  every receipt against the original host run root `C:\r22a5n` (still present),
  and code review of the instrumentation that produced each receipt.
  No repository file, receipt or log was modified during this audit.
- Repository has no `AGENTS.md`; contribution conventions are the R22A.4.1 freeze
  discipline carried in `docs/release-closure/` (append-only evidence, forward
  commits, no history rewrites).

## A. Manifest integrity (ground truth before any judgement)

`reports/r22a5n/R22A5N-GFX1151-20261117-A/SHA256MANIFEST.json` carries 29 entries;
all 29 recomputed SHA256 values match the committed git blobs byte-for-byte
(`reports/r22a5n/**` is `-text` in `.gitattributes`, so checkout bytes == blob bytes).
`SHA256SUMS.txt` (untracked working-tree copy) is a duplicate and is ignored.

Installer logs are NOT placeholders: `install_attempt1_maxpath_failure.log` =
17 492 B, `install_official.log` = 35 164 B, `resolve.log` = 2 732 B — all real
execution output (verified blob lengths and content).

## B. Traceability table (every original claim → its evidence)

| # | Claim | Raw evidence | Derived JSON | Code revision | Package identity | Independently reproducible? |
|---|---|---|---|---|---|---|
| 1 | Official nightly package provenance | committed lock `resolved_wheel_lock_nightly_gfx1151.json` (46 pkgs), frozen audit `release-provenance/r22a5a/nightly_wheel_audit_20261117.json`, `installed_manifest.json` (47 dists) | discovery/*.json, g9_preflight_nightly.json | resolve_package_set.py @9713eec | wheel `b11baad9…`, lock SHA `cf147540…` | YES — hashes re-verified this audit |
| 2 | Loaded DLL identity | G0 child-process receipt + child.log on host | `02_runtime_identity/g0_child_identity.json` | verify_gpu_child_identity.py | DLL `f9312c3e…` | YES (receipt); child.log NOT committed → recover |
| 3 | No-STL positive (G1) | committed `raw/candidate_leg.log` (804 B) + host copy | `nostl_candidate.json` | verify_miopen_nostl.py | candidate venv DLL `f9312c3e…` | YES |
| 4 | Pre-fix negative control (G1) | committed v2 leg.log (2 828 B) + v1 investigation md + host copies | `nostl_prefit_control_v2.json` (v1 INCONCLUSIVE retained) | verify_miopen_nostl.py | `pm13437_official` DLL marker=0 | YES |
| 5 | GPU core ops (G2) | `torchvision_ops.json` ONLY — **raw `torchvision_ops.log` referenced by receipt is NOT committed and NOT on host** | gates dict inside receipt | verify_torchvision_ops.py | runtime DLL not recorded in this receipt | PARTIAL — **P0-B rerun** |
| 6 | AdamW real updates (G3) | `adamw_amp.json` with full 11-event `per_step_events` — **raw `adamw_amp.log` NOT committed, NOT on host** | training_counts in receipt | audit_adamw_amp.py @9713eec | **receipt records DEV lock SHA `97a2da63…` — WRONG** | numeric facts recomputable; raw log **P0-B rerun** |
| 7 | AMP dtype + GradScaler (G4) | same receipt: dtype histogram {float16:96}, scale history 11 pts 65536→4096 | amp/gradscaler dicts | audit_adamw_amp.py | same wrong lock field | recomputable from per-step series |
| 8 | YOLO validation | inside adamw_amp receipt + host `runs/amp_coco128/` artifacts (results.csv, curves, weights 5.5 MB) | receipt `pass_fail_skip` | audit_adamw_amp.py | — | PARTIAL — val metrics not separately logged → improved Stage C |
| 9 | Checkpoint save/reload (G5) | **host**: `stage1.log` 18 421 B, `stage3.log` 22 166 B, `stage4.log` 277 B + stage scripts + weights; **`lifecycle_summary.log` referenced by receipt NOT on host** | `checkpoint_resume.json` stages dict | verify_checkpoint_resume.py | receipt records NO lock field | logs recoverable (commit); summary log P1; state-introspection depth insufficient → Stage D |
| 10 | Resume state | stages fields (optimizer state flag, epoch continuity) | same | verify_checkpoint_resume.py | — | per-state serialization classes NOT recorded → Stage D |
| 11 | Workers=8 (G7) | census + orphan JSONs WITH raw PID lists (16 spawn children, ppid=trainer) + **raw `workers8_amp_v2.log` / `workers8_amp.log` NOT committed, NOT on host** | census/orphan JSONs | census captured via Win32_Process | workers8 receipts share the WRONG DEV lock SHA | census recomputable; raw log **P0-B rerun** |
| 12 | Overall acceptance | stored `08_acceptance/nightly_acceptance.json` = `R22A5N_GFX1151_NIGHTLY_CANDIDATE_PASS` | — | scripts/r22a5n/nightly_acceptance.py @9713eec | — | NO — engine consumes `rules_checked` + summary counters (stored-summary authority) → **P0-C hardening** |

## C. Gap classification

### P0 — blocks independent acceptance; must be fixed before/with new physical runs

| ID | Gap | Root cause | Closure path |
|---|---|---|---|
| **P0-A** | Three training receipts (`05_yolo_training_amp/adamw_amp.json`, `07_reliability/workers8_amp.json`, `workers8_amp_v2.json`) record `wheel_lock_sha256=97a2da63…` — the **historical DEV lock** — instead of the nightly lock identity `cf147540…`. Runtime was NOT DEV (torch 2.16.0a0+rocm10.3.0a20261116 and DLL `f9312c3e…` in the same receipts prove the nightly venv), so this is receipt-attribution corruption, not a wrong runtime. | `audit_adamw_amp.py:54` hardcodes `WHEEL_LOCK = evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json` (DEV) and line 616 hashes it unconditionally; `--channel` only feeds `classify_runtime`. | PHASE 1: `--wheel-lock` explicit-lock contract (fail-closed, channel/gfx/runtime-version binding, negative tests) + PHASE 4 Stage C/E reruns emit correctly-bound receipts. Original receipts stay byte-frozen. |
| **P0-B** | Raw logs referenced by receipts but absent everywhere: `adamw_amp.log`, `workers8_amp.log`, `workers8_amp_v2.log`, `torchvision_ops.log`, `g5_resume/lifecycle_summary.log`. The training scripts never wrote those files themselves (`raw_log_path` points at a caller-side redirect that was not committed/kept). | Instrumentation gap: stdout capture was the caller's job and the captured files were lost. | `ORIGINAL_LOG_NOT_RECOVERABLE` for all five. Every mandatory gate affected (G2, G3/G4, G7, G5-summary) gets a NEW real GPU run with an execution-time logging envelope (PHASE 2/4). G5 stage1/3/4 logs + G0 child.log + G1 leg logs ARE recoverable from host → committed as recovered originals. |
| **P0-C** | Acceptance engine trusts stored summaries: `evaluate_pkg()` consumes `rules_checked.*` booleans and string fields from the frozen audit; `evaluate_g34()` trusts `training_counts` counters without recomputing from `per_step_events`; `evaluate_g7()` trusts `orphan_verdict=CLEAN` without rechecking PID observations. | Engine designed as cross-check, not independent recomputation. | PHASE 3: hardened engine recomputes source policy (gp_lib `classify_package_origin`), family mix, device wheels, ABI tags, installed-vs-lock 46-record diff, per-step AMP/AdamW statistics, worker parentage, from raw observations only; stored booleans become inputs to DIFF against, never authority. |

### P1 — real but non-blocking for rerun correctness; closed during this mission

| ID | Gap | Closure |
|---|---|---|
| P1-1 | Recoverable originals not in git: `stage1/3/4.log`, `stage1_train.py`/`stage3_resume.py`/`stage4_infer.py`, G0 `child.log` ×2, host ultralytics artifacts (`args.yaml`, `results.csv`) for amp_coco128 / lifecycle / workers8 / workers8_v2 | Commit as `…/raw_host_recovery/` with SHA256 inventory; byte-frozen, clearly labelled recovered-not-rerun |
| P1-2 | Checkpoints/weights (5.5 MB ×8) exist only on host; no SHA inventory | Hash-inventory + size + retention/access disclosure in the completeness report; no fake "independently byte-verifiable" claim |
| P1-3 | G5 state serialization depth: receipt proves optimizer state present + epoch continuity, but does not record WHICH state classes (scheduler, GradScaler, best-fitness, trainer args) this Ultralytics version serializes | Stage D rerun with state-class introspection; `NOT_SERIALIZED_BY_UPSTREAM` reporting |

### Non-blocking observations (no action)

- Negative-control v1 contamination is already honestly documented
  (`negctrl_v1_inconclusive_investigation.md`); retained per immutability rules.
- `bus.jpg` + `windows-golden-path/reports/r22a-gfx1151/SHA256SUMS.txt` are untracked
  working-tree leftovers, unrelated to PR #22 evidence; left untouched.
- AMP 11/7/4 was already documented as shape-not-criterion; the hardened engine will
  derive counts from events (no hardcoding anywhere).

## D. Rerun scope decision (drives PHASE 4)

| Stage | Why required | Gate affected |
|---|---|---|
| A fresh runtime identity | new isolated venv from the SAME verified nightly bytes; lock↔runtime binding proof | PKG/G0 |
| B no-STL ×2 + pre-fix control ×1 | original control v2 identity IS complete; mission allows 1 targeted confirmation — candidate needs 2 cold trials for regression confidence | G1 |
| C YOLO/AMP training (≥3 epochs) + G2 ops | P0-A + P0-B (adamw_amp.log, torchvision_ops.log lost) | G2/G3/G4 |
| D checkpoint lifecycle w/ state introspection | P1-3 + lost lifecycle_summary.log | G5 |
| E workers=8 bounded rerun | lost workers8_amp_v2.log | G7 |

Every stage runs under the new execution envelope (stdout/stderr bytes, PIDs,
timestamps, command, env subset, git SHA, lock SHA — captured at execution time).
