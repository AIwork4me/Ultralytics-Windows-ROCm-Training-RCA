# Reviewer A — MIOpen maintainer audit (G11), 2026-10-12
Audited: a5b5197e + e271f6df (content identical to final 1d2481cf + 1845028f
modulo one comment line and commit-message rewording done post-review).

VERDICT: GO WITH NITS (0 blockers, 0 majors)

Highlights:
- Native gtest usage real: file(GLOB) auto-registration, plain TEST(),
  naming passes check_names.py (CPU+NONE legal), unique suite name.
- Registration correct in both DISCRETE modes; standalone EXCLUDE entry,
  manual block and target removed together; no target collision.
- Net diff +521/−8 vs base; no CMake additions; no private terminology
  (in-tree grep clean; last canary phrase removed by the cleanup commit).
- Architecture selection: zero gfx1151 occurrences; live-handle derived.
- radix.hpp cleanup semantically equivalent; <limits> genuinely unused;
  nothing relied on it transitively (only consumer MIOpenKthvalue.cpp).
- Attempted attacks that failed: in-memory program_map short-circuit
  (nonce), persistent cache (options-keyed md5), option plumbing
  (-nostdinc passes; MIOPEN_HIP_RUNTIME_COMPILE auto-added), kernel/macro
  viability (MIO_BN_VARIANT=0 arm exists; geometry macros defaulted by
  default_configurations.hpp via configuration.hpp).

Nits (non-blocking): review-ID phrasing in the cleanup commit message
(fixed pre-push by rewording); header comment length; yaml quick-tier
comment about CPU_* tests (inherited from the cstdint precedent);
NonceOption atomic (harmless).
