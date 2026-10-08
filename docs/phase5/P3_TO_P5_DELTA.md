# P3/P4 → P5 Source Delta (Gate P5-05)

Identity: **P5-CANDIDATE-R1** (manifest: `findings/phase5/PATCH_IDENTITY.json`).

```text
P5 is derived from P3/P4 with an explicitly audited delta.
It is NOT byte-identical to P3-FINAL-R3.
```

## Chain of derivation

```text
P3-FINAL-R3 (patches, source base b68f894, Windows+Linux validated)
  == byte-content == Phase-4 canonical commits c86d1b95/4084759
    → P5-03 reconstruction on frozen develop 7c58661
       (verified 8/8 blob-identical to 4084759 pre-cleanup:
        evidence/phase5/source_delta/pre_cleanup_equivalence.json)
    → P5-04 audited hygiene edits
    → P5 commits 135f775e / b1adc77a
    → P5-06/07 CI-test commit 39319c4d
```

## Base change (classification: UPSTREAM_BASE_CHANGE)

| | P3/P4 | P5 |
|---|---|---|
| rocm-libraries base | `b68f894` | `7c58661` (develop frozen 2026-10-08) |
| 8 affected files | — | **zero drift** between the two bases |
| other MIOpen files | — | upstream's own drift: kern_db.hpp, sqlite_db.hpp, 3 BN spatial kernels, configuration.hpp, default_configurations.hpp, reduction_functions.hpp, test/gtest/cache.cpp (the `use_amdgcn`→`use_gfx9_dpp` rename + KernDb/SQLite plumbing + gtest cache test; include closure of the CI-test kernel unchanged) |

The P5 DLL therefore compiles upstream's newer BN kernel sources; that is
upstream's own change, not part of the patch.

## Source-fix file delta (P4 canonical → P5)

| File | Δ | Classification |
|---|---|---|
| `miopen_freestanding_type_traits.hpp` | +17/−24 | NONFUNCTIONAL_SOURCE_CLEANUP (dead `#define MIOPEN_FREESTANDING_TRAITS_ACTIVE` removed; zero references anywhere) + FORMATTING (clang-format 18.1.4, repo config, whole new file) |
| `miopen_freestanding_initializer_list.hpp` | +1/−5 | FORMATTING (triple blank line → one; short ctor joined) |
| `miopen_type_traits.hpp` | +2/−1 | FORMATTING (our added `#error` line wrapped per repo style) |
| `miopen_utility.hpp` | +2/−1 | FORMATTING (same) |
| `miopen_freestanding_utility.hpp` | 0 | byte-identical |
| `radix.hpp` | 0 | byte-identical |
| `tensor_view.hpp` | 0 | byte-identical |
| `src/CMakeLists.txt` | 0 | byte-identical |

Adversarial verification: `findings/phase5/reviews/P504_hygiene_behavior_review.md`
— CONDITIONAL PASS with the proof that running clang-format 18.1.4 on the
P4 blobs reproduces the P5 blobs byte-for-byte (6/7 headers exactly; the
7th differs only by the removed dead-macro lines). Token streams,
preprocessor directive sets, string literals, all 12 self-test
static_asserts: identical. The "condition" was procedural (the branch tip
advanced during the review when the planned CI-test commit landed); the
audited two-commit series itself has zero executable delta.

## Metadata delta

- Commit 2's message rewritten (AUTHORSHIP_METADATA class, tree bytes
  unaffected): the builtin-limits substitution in radix.hpp is now
  described as unconditional (it is), with only the include selection
  path-dependent.
- Commit 3 added (TEST_ADDITION): the Phase-4 standalone CI test, format
  normalized and `-Wnrvo`-clean for in-tree flags, plus real
  CMake/CTest wiring (see `docs/phase5/CI_INTEGRATION.md`).
- DCO: all three commits unsigned with the `DCO: PENDING HUMAN
  CONFIRMATION` marker retained → **DCO_ATTESTATION_PENDING**.
- Copyright: FOUR files still carry the submitter placeholder in their
  MIT headers (3 kernel headers + `test/hiprtc_selfcontained.cpp`;
  count corrected 3→4 by Phase 5.1 Gate 05) →
  **COPYRIGHT_ATTRIBUTION_PENDING** (comment-only lines; when the human
  sets attribution, classify as COPYRIGHT_TEXT and rerun the targeted
  validation. Phase 5.1 executed exactly this under the confirmed
  right-to-contribute: see `findings/phase5_1/FINAL_HANDOFF.json`).

## Series identity

```text
0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch
  SHA256 76fd6623958fb58fc71a9fabbf662bc28a22cfd19aeacba76ca9eee841abc586
0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch
  SHA256 d37376c9318c79f750b456ff6491ed1e6978d0eafa45a49a34fc66cf85f7a9ea
0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch
  SHA256 593061053e113c5005040d6d9b1dee39c4d0d7cb2d0c27626749815ed6877821
series (concat, sha256_file_concat_v1)
  5ad951c716fbf986e627a94f65db679f4f49519d672912cb2e407bf3b714391d
```

## Post-panel amendment (2026-10-08, after the P5-17 reviews)

Final commits `135f775e` / `66f66944` / `29846fc4` (commit 1 unchanged;
commit 2 rebuilt for message precision — same tree bytes; commit 3
hardened). Changes applied from the review wave:

- Reviewer B MAJOR M1: test linkage now mirrors upstream's platform
  split (`if(WIN32) hiprtc::hiprtc else() hiprtc`, as
  `src/CMakeLists.txt:1093-1099` does) — stock-Linux configures no
  longer break on a non-exported namespaced target.
- P508 F1: the test refuses substituted kernel sources (identity
  markers `MIOpenBatchNormFwdTrainSpatial` + `__global__`), verified:
  trivial-kernel substitution → SETUP exit 2 (previously exit 0).
- P508 F3: duplicate `--mode/--arch/--hip-flat/--isolate` arguments are
  usage errors, verified directly (exit 2).
- P508 F4: the STL-unreachability probe now covers all four gated
  headers (`<type_traits> <utility> <limits> <initializer_list>`).
- Reviewer A MINOR 3: commit 2's message no longer calls tensor_view's
  probe "the same" — it documents that it is not HIP-version-gated and
  needs no partial-STL cross-probe, and why that is sound.
- Reviewer A MINOR 4 (accepted, disclosed): radix.hpp's RTC arm relies
  on miopen_cstdint typedefs that exist for RTC only at
  `>= 6000025000ULL`; HIP 6.0.x pre-6.0.25 RTC (EOL) is an untested
  legacy arm. No change made — semantics scope untouched.
- Reviewer C F-C2 (disclosed): on GNU triples the handoff recommends
  `--isolate=-nostdinc++` for the negative control.

Revalidated after the amendment: CI integration 4/4 PASS at `29846fc4`;
A/B matrix 13/13 PASS; src/ tree identical to the DLL-built commit
`39319c4d` (delta test-only), so MIOpen.dll `d5974dad…` remains the
validated runtime artifact.

(Hashes over exact file bytes, LF; the files are LF-only in
`patches/phase5/canonical/`.)
