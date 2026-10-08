# G03 Independent Subagent Review — Network & Credential Hygiene Audit

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## VERDICT: CONDITIONAL PASS

All hygiene claims verified clean. The "intermittent git / CONNECT 503"
characterization was NOT reproducible during the review window.

## Reviewer probe results

| Probe | Result |
|---|---|
| curl api.github.com/rate_limit | 200 (TLS 1.3, verify ok) |
| curl repo.amd.com/rocm/whl-multi-arch/ | 200 |
| git ls-remote github.com/ROCm/rocm-libraries x4 | 4x EXIT=124 timeout (0/4) |
| curl github.com x3 + /info/refs | timeouts; CONNECT sent, proxy never answers (hang, not 503) |
| curl raw.githubusercontent.com | SSL_ERROR_SYSCALL / timeout |
| proxy env | no credentials embedded |
| TLS-bypass grep across scripts/docs | empty |
| token leak grep (gh[pousr]_) across workspace | empty |
| git config --global | standard gh credential helper only, no tampering |
| scripts/git-retry.sh | plain retry loop, no TLS bypass / credential capture |
| gh auth status | AIwork4me, scopes gist,read:org,repo,workflow; token redacted |

## Findings

- MAJOR — Primary agent's "INTERMITTENT (503)" claim not reproducible in the
  review window: 0/8 github.com git-transport probes succeeded; failure mode
  observed was a CONNECT-tunnel black-hole hang. Earlier primary-agent runs
  DID observe both a success (rocm-libraries ls-remote attempt 1) and literal
  503 responses (4 consecutive), so the truth is "unstable / time-varying
  proxy behavior". Operational consequence unchanged: every github.com git
  operation must go through the retry wrapper and may fail entirely; clones
  must be attempted early with api.github.com as fallback transport.
- NIT — git-retry.sh merges stderr into stdout (cosmetic).
- NIT — retry budget (10 tries) can burn ~5 min during a hard outage.

## Resolution during preparation

- docs/NETWORK_READINESS.md updated: git transport status reclassified as
  "UNSTABLE/TIME-VARYING (503s and black-hole hangs both observed; occasional
  success)". No hygiene issues to fix.

Gate G03 final: PASS with documented unstable-git-transport risk.
