# R22A.5N-GFX1100.1 — Final integration & fail-closed evidence audit

## Scope and decision

Purpose: reconcile the **real** Windows Radeon RX 7900 XTX (gfx1100) Nightly
evidence with the fully merged gfx1151 integration baseline, without rerunning
GPU experiments or changing original physical evidence.

The claim ceiling remains:
`R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS`.
This is **not** a Stable release, G9 clean-install or fully serialized
scheduler/GradScaler restoration claim.

## Git reconciliation — append-only merge

- Prior gfx1100 physical HEAD: `f4cf7208a4663ef16623be0cd94a04b4986c6a7f`.
- Verified integration HEAD from merged PR #22:
  `2545924a7d6b381551d9235cd24dd080ccd8ae80`.
- Explicit non-forced two-parent merge:
  `0b0ab0d9b54e12085d6d10a3d94457826044ac58`.
- Parents are the original gfx1100 head and the full integration head,
  respectively. The merge tree incorporates five exact upstream final G5/G7
  closure Git blobs, leaving the existing gfx1100 experiment files unchanged.
- PR #23 was retargeted from the now-merged PR #22 head branch to
  `work/windows-rocm-training-release-closure`. No rebase or force-push.
- The original branch point `568981d` and stacked Draft description were
  historically accurate **at experiment time** only and are not the current
  Git state. The gfx1151 FULL-state wording cited in the frozen gfx1100
  publication report is similarly superseded by PR #22's final closure:
  `RESUME_PASS_CORE_STATE_VERIFIED`.

## Critical code reconciliation

The initial gfx1100-specific G5/G7 copies were weaker than the final
integration engine and have been retired:

- The merged `r22a5n1/nightly_acceptance.py` is the single source of truth
  for **both** G5 resume continuity and G7 parentage/orphan controls.
- A backward-compatible **optional explicit gfx target** was added to
  `evaluate_g5`. Its historical default stays gfx1151; gfx1100 passes
  `profile["frozen"]["gfx_target"]` explicitly. No GPU identity field in the
  source receipt is rewritten.
- G5 now requires all eight typed numeric state/epoch facts, including nested
  checkpoint epoch; rederives epoch continuity from recorded numbers and
  limits FULL to independent per-class serialization **and** restoration.
- G7 now requires actual `spawn_main` process identity and matching PPID in
  one real live snapshot; validates trainer ancestry against the execution
  envelope; requires orphan/census/envelope **three-way baseline match**,
  with all owned workers and trainer terminated.
- A synthetic/stored PASS cannot bypass these shared gates.
- The gfx1100 function wrappers deliberately contain no duplicated G5/G7
  validation logic; other profile-specific gates remain independent.

## Evidence scope and immutable original observations

Source:
`reports/r22a5n/R22A5N-GFX1100-20261117-A/`

Evidence has 83 SHA256-manifest entries, including original physical receipts,
raw logs, pre-fix control, both cold candidates, actual checkpoint bytes and
the disclosed failed/retried workers census attempts. Pack files and
`SHA256MANIFEST.json` are **not edited by R22A.5N-GFX1100.1**.

Historical gfx1151 pack A, pack B, and their manifests are also unchanged.

The previously generated gfx1100 `09_acceptance/nightly_acceptance.json`
is an immutable **historical derived result** from
`r22a5n1100-acceptance-v1`; it is not rewritten. GitHub CI additionally
runs the current strict acceptance engine on those same physical bytes
and uploads the **new derived** acceptance JSON as a workflow artifact.

## Mandatory reproducibility / false-claim gates

On the complete PR checkout, the Windows CPU-only workflow executes:

1. Compile the complete harness, R22A.5A, R22A.5N.1 and gfx1100 scripts.
2. Run the full shared gfx1151 + gfx1100 CPU contract suite, including the
   new adversarial checks for missing checkpoint epochs, resume
   discontinuity, missing execution envelope, missing envelope baseline and
   forged baseline with surviving worker.
3. Run `scripts/verify_release_closure.py` with zero violations.
4. Verify **all 83** gfx1100 physical manifest entries directly from files
   committed to GitHub.
5. Recompute **all nine** PKG/LK/G0/G1/G2/G3/G4/G5/G7 gates using the
   current shared strict G5/G7 against committed gfx1100 receipts, without
   GPU access or a developer's environment.
6. Upload the independently derived JSON as
   `r22a5n-gfx1100-acceptance-recomputed` to the exact-HEAD Actions run.

The CPU runner **does not** execute GPU tests: it independently audits the
original GPU experiment. The actual GPU tests remain exactly those captured
at the physical Windows RX 7900 XTX host.

The integration's original gfx1151 frozen default and its regression suite
remain intact. The only new shared API behavior is the explicitly supplied
gfx target for G5.

## Historical CI attempts / final verdict

Some interim CI runs during gate unification correctly failed because the
previous synthetic gfx1100 fixtures and assertions assumed the less strict
engine (and one real-pack test initially omitted a `json` import). Those
attempts remain visible in GitHub Actions; neither they nor the original
physical experiments were hidden. After updating fixtures to the actual
strict contracts, full CPU tests, SHA manifest, and new nine-gate acceptance
replay must all pass on the **final PR HEAD**.

**Publication rule**: Owner approval of PR #23 requires a success run at the
current PR head, full replay against immutable evidence and no unresolved
review comments. Leave PR #23 Draft, and do not merge or post upstream yet.

## Release boundary / next dependency

After owner review and merge, report dual-architecture **Nightly functional
evidence**, not Stable readiness. Upstream fixed Stable wheels, two physical
Stable architecture revalidations, clean Windows G9 and independent-user
acceptance are still separate deliverables.
