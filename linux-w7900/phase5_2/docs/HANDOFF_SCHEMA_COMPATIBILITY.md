# Handoff Schema Compatibility — Phase 5.2 (Gate B02/B03)

The Linux consumer was corrected in Phase 5.2 to consume the ACTUAL frozen
Windows Phase-5.1 manifest schema. The Windows manifest was never modified.

## Actual frozen schema (findings/phase5_1/FINAL_HANDOFF.json @ 494907699f)

| Field | Role in the Linux consumer |
|---|---|
| `schema_version` (=1) | must be in supported set {1} |
| `handoff_type` | must equal `final_pre_upstream_linux_validation` |
| `candidate_id` | must equal `P5.1-CANDIDATE-R1`; stale P5/P4 ids rejected |
| `base_repo` / `base_sha` | `ROCm/rocm-libraries`; 40-hex; must equal frozen `7c5866144...`; stale `b68f8944` rejected |
| `ordered_commits[]` | exactly the 3 declared candidate commits, exact order, unique, 40-hex |
| `ordered_patches[]` | objects `{order, path, sha256, bytes}`; orders unique+contiguous 1..N; paths unique `.patch` |
| `series_hash.algorithm` | only `sha256_file_concat_v1` supported |
| `series_hash.sha256` | recomputed over concatenated raw LF bytes in order; also pinned to the frozen value |
| `source_tree_identity.head_tree_sha1` | 40-hex; pinned to `605d0d214...`; byte-level reproduction enforced separately (apply mode / verify_source_tree.py) |
| `dco_status` | must remain PENDING (no certification implied) |
| `copyright_status` | must be RESOLVED + RIGHT_TO_CONTRIBUTE=CONFIRMED; placeholders rejected |
| `linux_validation_status` | must be `PENDING` |
| `authorization_to_submit_upstream` | must be JSON `false` |
| manifest file itself | sha256 pinned (`58a6f9ce...`); when read from inside the pinned checkout, byte-matched against its git blob |

## Old provisional schema — REJECTED, no fallback

Presence of ANY of `upstream_base_sha`, `patch_series`, `series_sha256_mode`,
`rca_evidence_commit` fails closed. The previous Linux consumer expected
exactly those keys (pre-5.2 defect); a stale Phase-5 style manifest can
never validate against the corrected consumer.

## External invocation contract

    python3 scripts/check_final_handoff.py \
      --check-only <path>/FINAL_HANDOFF.json \
      --rca-root   <pinned RCA checkout> \
      --rca-evidence-sha 494907699f3b57095663f0a70b42278001a8efb7

* The evidence SHA is verified AGAINST the git checkout (`rev-parse HEAD`,
  clean status, `HEAD^{commit}`, blob equality for manifest + patches), not
  merely echoed from the CLI.
* The frozen evidence commit is a builtin default AND a CLI pin — both must
  agree with the checkout.
* `--expect-*` overrides exist ONLY for the adversarial test harness; the
  effective pin set is embedded in every PASS report.

## Patch-directory safety (B03)

Canonical dir pinned to `patches/phase5_1/canonical` (single dir, all
patches). Allowed entries: the declared `.patch` files + documented support
file `README.md` (never hashed into the series). Rejected: extra `.patch`
files, executables, symlinks (file or ANY parent component), absolute /
`..` / home paths, duplicate paths, nested directories, symlinked `.git`.

## Adversarial validation

22-attack matrix (`phase5_2/scripts/test_handoff_adversarial.py`) plus 10
auditor-owned bypass attempts — every attack failed for its intended
reason; frozen evidence byte-identical after all runs.
