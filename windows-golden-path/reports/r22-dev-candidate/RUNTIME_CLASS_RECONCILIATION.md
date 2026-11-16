# R22-DEV Evidence Reconciliation — runtime_class mismatches (R21.1 TASK D)

Run ID: `R22-DEV-RECONCILIATION-20261116`
Scope: `evidence/raw/r22-dev/*` (physical gfx1100 runs of 2026-11-15) and the
committed harness bytes at PR #15 HEAD `84f2949`.

**Rule: no raw JSON evidence file was rewritten.** Every historical file keeps
its bytes and its entry in the R22 SHA256SUMS; `scripts/verify_release_closure.py`
keeps passing unchanged over the same inputs. This report EXPLAINS the recorded
mismatches and points to the 2026-11-16 re-run that supersedes them
classification-wise.

## 1. Defect R21.1-D1 — committed gate scripts were syntactically invalid

At commits `31526a1..84f2949` four gate scripts DID NOT PARSE (unclosed
`gp_lib.classify_runtime(` call, `SyntaxError` at parse time):

| file | error site |
|---|---|
| `windows-golden-path/scripts/verify_torchvision_ops.py` | line 157 |
| `windows-golden-path/scripts/audit_optimizer.py`        | line 141 |
| `windows-golden-path/scripts/verify_checkpoint_resume.py` | line 240 |
| `windows-golden-path/scripts/run_stability.py`          | line 128 |

Consequence (provenance gap, now disclosed): the r22-dev evidence JSONs of
2026-11-15 (r22cB*, r22cE*, r22cF*, r22cG2/G3 among others) **cannot have been
produced by the committed bytes** — they were produced by pre-commit working
copies whose runtime_class logic differed from what the repository claimed to
contain. The physical hardware observations (GPU selection, exit codes, logs,
checkpoint hashes) remain genuine; the *classification labels* recorded by the
uncommitted code are what this document reconciles.

Repair: the four scripts were repaired (parenthesis closure) and the whole
candidate gate suite was re-executed on the same physical gfx1100 host from the
committed bytes on 2026-11-16 (see §4).

## 2. Defect R21.1-D2 — runtime_class hardcoding

The code paths that produced the historical labels could only ever emit:

- `ENGINEERING_REFERENCE` when a workaround was detected in the recording
  process, else
- `OFFICIAL_PRE_FIX`

There was no path to `OFFICIAL_CANDIDATE` outside `verify_provenance.py`
(which is why `r22cA2_provenance_clean.json` alone carries the correct class).
The stack under test was the dev channel `torch 2.15.0+gitf6cd88cb.
devrocm10.3.0.dev0.ff5769655…` + `rocm-sdk-libraries 10.3.0.dev0+ff5769655…`
with MIOpen.dll marker=2, build commit `4e7d93e3`, GitHub compare
`f0a5d266...4e7d93e3` behind_by=0 (fix present). Correct class for the clean
records is `OFFICIAL_CANDIDATE`; recorded was `OFFICIAL_PRE_FIX`.

| historical file | recorded runtime_class | correct class | cause |
|---|---|---|---|
| r22cB2_torch_gates_clean.json  | OFFICIAL_PRE_FIX | OFFICIAL_CANDIDATE | D1/D2 uncommitted copy, hardcoded fallback |
| r22cD2_train_cli_clean.json    | OFFICIAL_PRE_FIX | OFFICIAL_CANDIDATE | train-summary hardcoded binary (generate_report.py L86-88 at 84f2949) |
| r22cE2_optimizer_clean.json    | OFFICIAL_PRE_FIX | OFFICIAL_CANDIDATE | D1/D2 |
| r22cF2_resume_clean.json       | OFFICIAL_PRE_FIX | OFFICIAL_CANDIDATE | D1/D2 |
| r22cG3_stability_clean_cold.json | OFFICIAL_PRE_FIX | OFFICIAL_CANDIDATE | D1/D2 |
| r22cA2_provenance_clean.json   | OFFICIAL_CANDIDATE | OFFICIAL_CANDIDATE | correct (classify_runtime existed here) |
| r22cA_provenance.json          | ENGINEERING_REFERENCE | ENGINEERING_REFERENCE | correct (parent shim disclosed) |

## 3. Defect R21.1-D3 — parent-environment shim stamped onto shim-free children

`verify_miopen_nostl.py` (84f2949) computed the RECORD's `runtime_class` from
the *parent* process environment: `ENGINEERING_REFERENCE if leg == "engineering"
or ambient_shim else "OFFICIAL_PRE_FIX"`. In the 2026-11-15 session the parent
shell still carried `HIPRTC_COMPILE_OPTIONS_APPEND` (recorded as
`ambient_hiprtc_shim` inside `r22cC_nostl.json` itself), while the `--leg
official` CHILD process ran with the shim explicitly removed and PASSED
behaviorally:

- `r22cC_nostl.json`: `classification = OFFICIAL_CANDIDATE_PASS` (behavioral,
  shim-free child, exit 0) but `runtime_class = ENGINEERING_REFERENCE` (parent
  label). The behavioral fact and the label contradict each other; the label
  described the parent, not the leg under test.
- Same parent-shim mechanism explains `r22cG2_stability_cold.json`
  (ENGINEERING_REFERENCE) vs its clean sibling `r22cG3` (OFFICIAL_PRE_FIX).

## 4. 2026-11-16 re-run from the repaired committed bytes (supersedes labels)

- Truly shim-free PARENT environment (HIPRTC/MIOPEN_*/PYTHONPATH/miopen-PATH
  scrubbed before launching; scrub facts recorded in the launcher log) AND
  shim-free child (official leg pops the shim as before).
- Fresh isolated venv `r22-candidate` installed from
  `evidence/raw/r22-dev-rerun/resolved_wheel_lock.json` — the COMPLETE resolved
  wheel lock (46 wheels, every SHA256 recorded, exact official dev-channel
  origin per package, reproduction pins) that the 2026-11-15 session never
  committed (legacy gap: only the engref lock existed).
- Full candidate gate suite executed through the fail-closed orchestrator
  (`run-golden-path.ps1 -Mode OfficialCandidate`), including the exact
  Ultralytics CLI gate G3 (`train_yolo.ps1`), with per-gate exit-code checks
  and `gate_status.json`.
- Results: `evidence/raw/r22-dev-rerun/` (records + sibling logs +
  `gate_status.json` + `resolved_wheel_lock.json` + SHA256SUMS) and the
  acceptance report at `windows-golden-path/reports/r22-dev-rerun/report.json`.
- Note on iteration honesty: two intermediate orchestrator attempts (2026-11-16
  ~07:0x and ~07:4x local) stopped NO-GO by design — one on the
  URL-encoded-wheel install defect, one on missing artifact linkage, one on a
  BOM-encoded `gate_status.json`. Each stop was the fail-closed contract doing
  its job; every defect was fixed in the committed scripts and the suite
  re-executed. Only the final complete run is packaged as evidence.

## 5. Verdict impact

- The R22 verdict `R22_CANDIDATE_VALIDATED(DEV)` rests on the union of:
  (a) the 2026-11-15 physical functional evidence (unchanged), and
  (b) the 2026-11-16 re-run from committed bytes with correct classification,
  complete wheel lock + SHA256, and orchestrator-enforced gate accounting.
- Historical labels listed in §2/§3 are superseded by the re-run; the raw
  files are retained byte-identical as the audit trail of the harness defect.
- The stable channel remains BLOCKED_OFFICIAL_ARTIFACT; nothing in this
  reconciliation promotes any candidate.
