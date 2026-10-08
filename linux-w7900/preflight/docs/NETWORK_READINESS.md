# Network Readiness — W7900 Linux Validation Prep

Date: 2026-10-08 | Gate: G03

## Reachability matrix

| Endpoint | Result |
|---|---|
| api.github.com | HTTP 200 (stable, authenticated, 5000 req/h) |
| github.com (git smart HTTP) | **UNSTABLE / TIME-VARYING** — egress proxy observed returning `CONNECT tunnel failed, response 503` (4 consecutive), black-hole CONNECT hangs (subagent audit: 0/8), and occasional success (rocm-libraries `ls-remote` OK once; HEAD seen: `1f0a2ad23b33600b85de4814870d9e6200505a6c`). Treat as unreliable; retry + fallback mandatory |
| raw.githubusercontent.com | TIMEOUT via proxy |
| codeload.github.com | Reachable per prior bootstrap evidence (tarball fallback) |
| repo.amd.com/rocm/whl-multi-arch/ | HTTP 200, TLS verified |

## Proxy

- `http(s)_proxy = http://notebook-egress-proxy.amd-oneclick-lablab.svc.cluster.local:3128`
  (cluster egress proxy; **no credentials embedded** — verified sanitized).
- `no_proxy` covers cluster-internal suffixes only.
- TLS verification is enabled everywhere (`ssl_verify_result=0` on successes);
  it is never disabled anywhere in this mission.

## Mitigations

1. All git network operations run through `scripts/git-retry.sh`
   (10 attempts, escalating sleep). Copied from machine bootstrap evidence.
2. api.github.com (stable) is the preferred metadata path:
   - commit/tree/branch inspection via `gh api`
   - `FINAL_HANDOFF.json` existence checks (G08)
3. codeload tarball + git-data API is the documented fallback for source
   acquisition if smart HTTP stays broken (source identity preserved via
   commit SHA + tree hash verification).
4. Clones use `--filter=blob:none` (blobless) to minimize traffic through the
   flaky proxy while keeping full history/SHA resolvability (no shallow
   checkout — frozen-SHA resolution must remain possible).

## Git authentication

- `gh` CLI authenticated as **AIwork4me** (scopes: `gist`, `read:org`,
  `repo`, `workflow`); git credential helper configured.
- Token values are never written to logs or evidence (gh redacts).
- Push to the evidence branch will be attempted at G11 via the retry wrapper;
  failure is non-fatal for local preparation (local commits preserved).

## RCA repository state (via api.github.com)

- Default branch `main`, pushed 2026-10-08T06:58Z.
- Existing branches: `phase4/windows-upstream-submission-prep`,
  `phase5/windows-final-upstream-prep`, `rca/linux-gfx1151-phase3-regression`,
  `rca/windows-gfx1151-rocm714-phase2`, `rca/windows-gfx1151-rocm714-phase3`,
  `rca/windows-gfx1151-rocm714`.
- `findings/phase5_1/FINAL_HANDOFF.json` **does not exist** (404) ->
  `FINAL_HANDOFF_AVAILABLE = FALSE` (expected; see G08).
