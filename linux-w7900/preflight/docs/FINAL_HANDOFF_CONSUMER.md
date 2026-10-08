# Final Handoff Consumer — Design & Contract (G08)

Date: 2026-10-08 | Status: consumer implemented; **apply mode disabled until
Phase-5.1 freeze**

## Authority of the manifest

The future authoritative file is `findings/phase5_1/FINAL_HANDOFF.json`
(checked 2026-10-08 via api.github.com: **does NOT exist yet** ->
`FINAL_HANDOFF_AVAILABLE = FALSE`). Until it is published and passes
`--check-only`, NO patched build and NO A/B validation may run.

## Consumer

`scripts/check_final_handoff.py`

- `--check-only <manifest> --rca-root <dir> [--json-out PATH]` — zero
  source mutation; emits a JSON verdict report. (`--rca-root` may instead be
  supplied as manifest key `rca_repo_root`; if NEITHER is present the
  consumer FAILS — paths are never resolved against the manifest directory
  silently, eliminating the check/apply root-divergence attack.)
- `--apply <manifest> <target-dir> --rca-root <dir>` — refuses unless
  `ENABLE_APPLY=1` (deliberate interlock for the post-freeze session only).
  Re-verifies every patch sha256 immediately before `git apply` (TOCTOU
  hardening) using the SAME resolution routine as check-only.

## Required manifest schema (rejected otherwise)

```json
{
  "upstream_base_sha":  "<40-hex>",
  "rca_evidence_commit":"<40-hex>",
  "rca_repo_root":      "<optional path override>",
  "series_sha256_mode": "concat_bytes" | "hash_chain",
  "series_sha256":      "<64-hex>",
  "patch_series": [ {"path": "<relpath>", "sha256": "<64-hex>"}, … ]
}
```

## Series-hash definition (byte-exact, line-ending safe)

All hashes are SHA-256 over RAW BYTES (`open(…, "rb")`, hashlib). No text
decoding occurs anywhere in hashing.

- `concat_bytes`: sha256 of the concatenation of the patch files' bytes in
  the declared order.
- `hash_chain`: h₀ = sha256(b"MIOpen-P5.1-series-v1\0"); for each patch i
  (in order) hᵢ = sha256(hᵢ₋₁ ‖ sha256(patchᵢ bytes).digest());
  series hash = hₙ hex. (Deterministic, order-sensitive, length-safe.)

The mode is declared BY the manifest and enforced; unknown modes are
rejected. Both modes are order-sensitive.

## Stale-reference rejection

`upstream_base_sha` / `rca_evidence_commit` matching any known-stale anchor
is rejected. Seed list (extend before final validation):

- `b68f8944300f104875d953fc8e4510908c9aaf0b` — Phase-3 Linux source base
- `07959f8…` — Phase-3 run-1 blocked marker
- `013f6f005f97aca5ef46d841ca754f2283dc62f0` — RCA main head at prep time

## Check-only steps

1. Manifest itself hashed (raw bytes) and recorded.
2. Schema enforcement (all keys, 40-hex SHAs, non-empty ordered series).
3. Stale-reference rejection.
4. Path safety: patch paths must be RELATIVE, must not escape the RCA root
   (normpath + commonpath containment), must not be absolute, `~`, or
   symlinks; regular files only.
5. Per-patch: file exists, path set has no duplicates, sha256 recomputed
   from raw bytes must equal the manifest value.
6. **Unlisted-file rejection**: every regular file in each patch directory
   that is not part of the declared series is a FAILURE ("unexpected
   file"). Rule for the producer: a patch directory must contain EXACTLY
   the declared patches — nothing else.
7. Series hash recomputed per the declared mode must equal manifest value.
8. `upstream_base_sha` must exist as a commit in the local
   `repos/rocm-libraries` (fetch-on-demand is the operator's job — the
   consumer never guesses).
9. Verdict `PASS` only with zero failures; report JSON with failures+notes.

## Apply steps (post-freeze, `ENABLE_APPLY=1` only)

1. Re-run full check-only; refuse on any failure.
2. Refuse if target dir exists (final runs reconstruct into a clean dir).
3. `git worktree add --detach <dir> <upstream_base_sha>` from the local repo.
4. Assert worktree is clean before patching.
5. For each patch IN ORDER: `git apply --check` then `git apply`.
6. Record post-apply changed paths + timestamp to
   `evidence/G08_reconstructed_identity.json`.
7. The caller (`prepare_validation_legs.sh leg-b`) then builds with the
   IDENTICAL flags as leg A and verifies the leg-B library SHA256.

## Self-test & adversarial history (fabricated manifests, real hash math)

Round 1 (initial implementation) — independent adversarial subagent found:
- HIGH: check-only resolved patch paths against `rca_repo_root` while
  `--apply` used the manifest directory → tampered-twin attack could apply
  never-verified bytes. FIXED: single resolution routine for both modes +
  mandatory explicit root.
- MEDIUM: hash_chain implementation deviated from the documented chain
  definition. FIXED: implemented exactly h₀=sha256(seed);
  hᵢ=sha256(hᵢ₋₁ ‖ sha256(patchᵢ).digest()).
- MEDIUM: `../` traversal and absolute patch paths were accepted into
  hashing. FIXED: containment + absolute/`~`/symlink/non-regular rejection.
- MEDIUM-LOW: unlisted sibling patch files were ignored. FIXED: any
  unlisted regular file in a patch directory fails verification.

Round 2 (hardened) regression matrix: valid PASS; hash_chain PASS;
hash_chain with swapped order FAIL (order sensitivity proven); ambiguous
root FAIL; unlisted EXTRA.patch FAIL; traversal FAIL; absolute path FAIL;
tampered hash FAIL; stale anchors FAIL; `--apply` without ENABLE_APPLY=1
refused.

## Run-protocol guard

All final-validation builds and runs execute exclusively through
`scripts/prepare_validation_legs.sh`, `scripts/build_leg_miopen.sh` and
`scripts/run_validation_leg.sh` (which source the isolated 7.14.1
environment). Direct ambient-shell invocation of harnesses or compilers is
prohibited (binaries carry no RPATH; ldconfig would bind system 7.2.1).
