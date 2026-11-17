# R22A.5N.1 Final Freeze — evidence state attestation

- Generated: 2026-11-17 (mission R22A.5N.1 PHASE 8)
- Branch: `validation/r22a5n-gfx1151-official-nightly` → Draft PR #22
  (target `work/windows-rocm-training-release-closure`; NOT merged; owner review)
- Evidence/code freeze commit: `d613e39` (atop `cb0181c` atop R22A.5N `9713eec`
  atop integration HEAD `ff52f873`). Final PR HEAD = the documentation commit
  carrying this file; its exact-HEAD CI run is recorded in the PR description.
- Parentage (no force-push, forward commits only):
  `ff52f873` → `9713eec` (R22A.5N) → `cb0181c` (R22A.5N.1 evidence+engine)
  → `d613e39` (CI workflow step fix) → final docs commit.

## Frozen identities

| Artifact | SHA256 |
|---|---|
| Nightly lock (46 records, git blob) | `cf147540a166a623bcf4f7961e07540980af5e117c7a0cc1f2cf38c2b013a7ac` |
| rocm_sdk_libraries wheel | `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0` |
| MIOpen.dll (candidate) | `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6` |
| MIOpen.dll (pre-fix control, pm13437_official, at-failure capture) | `e97891df7ea0ba2b…` (full value in `03_nostl_negative_control/nostl_prefit_control_v2.json` leg_detail) |
| yolo26n.pt (init weights both missions) | `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef` |

## Verdict

`R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS` — hardened-engine recomputed
(PKG/LK/G0/G1/G2/G3/G4/G5/G7 all PASS), clean-clone verification 5/5, CPU
suite 311 PASS (266 baseline + 45 new), historical engine semantics preserved
(pack A recheck still CANDIDATE_PASS). No Stable/dual-arch/G9 claim.

## Immutability attestations

- Pack A original 29 manifest entries: re-hashed in a clean clone — 29/29 match.
- Pack A + recovery additions are append-only (`raw_host_recovery/`, 21 files,
  leg logs byte-identical to previously committed copies).
- Pack B: 106-entry SHA256MANIFEST (evidence_pack verify ok) including the
  lifecycle checkpoints (11 MB) so G5 is independently byte-verifiable.
- Failed attempts retained in `stage_logs/` (stage_c_amp exit 1; superseded
  stage_d/stage_e orchestrations; all intermediate no-STL instrument revisions).

## Test/verification ledger

| Item | Result |
|---|---|
| `pytest windows-golden-path/tests` | 311 passed |
| adversarial (mission §9 25 classes) | 45 tests, all rejected/inconclusive as contracted |
| compileall (windows-golden-path, r22a5a, r22a5n1) | clean |
| ruff E4/E7/E9/F (changed trees) | clean |
| closure verifier self-tests | 22/22 |
| hardened engine on pack B | AUDITED_PASS (exit 0) |
| hardened engine in clean clone | identical |
| historical engine on pack A | CANDIDATE_PASS (semantics preserved) |

## Residual state (post-mission)

- Mission venv `C:\r22a5n1\venv` (fresh, lock-bound) retained for re-inspection;
  scratch roots under `C:\r22a5n1\` retained (cold-cache evidence).
- Known P19B-era zombie pair (37120/12052) predating this mission, disclosed
  in every census; no mission-created orphans (recomputed leftover empty).
- `bus.jpg` / `windows-golden-path/reports/r22a-gfx1151/SHA256SUMS.txt`
  remain untracked pre-existing leftovers (documented, untouched).
