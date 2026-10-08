# Source Change Justification — Phase 5 Maintainer Polish (Gate P5-04)

Date: 2026-10-08. Candidate branch `prepare/miopen-hiprtc-phase5`
(worktree `rocm-libraries-phase5-candidate`), base = frozen upstream
develop `7c5866144ac4b879be442563e2b49fa1c142ea36`.

Starting point (Gate P5-03): two commits reproducing the validated
P3-FINAL-R3 / Phase-4 canonical content on the new base — verified
**8/8 blob-identical** to Phase-4 canonical `4084759` before any hygiene
edit (`evidence/phase5/source_delta/pre_cleanup_equivalence.json`).

Phase-4 maintainer review (P56 Reviewer A + submission checklist §3)
requested five narrowly scoped fixes. Status of each:

## Fix 1 — Commit 2 message accuracy — DONE (metadata-only)

The old body implied the builtin-limits replacement in `radix.hpp`
affects "the runtime path". In reality `std::numeric_limits<…>::max()`
→ `__INT32_MAX__`/`__INT64_MAX__` is **unconditional** (all
compilation paths); only the *include selection* is path-dependent
(`miopen_cstdint.hpp` under `MIOPEN_HIP_RUNTIME_COMPILE`, `<limits>`
offline for transitive users). Commit 2's message was rewritten to say
exactly that; **no tree bytes changed**.

## Fix 2 — Dead macro — DONE (2 lines removed)

`MIOPEN_FREESTANDING_TRAITS_ACTIVE` was defined in
`miopen_freestanding_type_traits.hpp` and referenced nowhere (verified:
`grep -rn` over the whole candidate tree finds only the definition;
upstream develop has no consumer either — confirmed independently by
the P5-02 review). Removed the `#define` line and one blank line.
Preprocessor contract unchanged: no `#ifdef`/`#ifndef` of this macro
exists anywhere.

## Fix 3 — Triple blank line — DONE

`miopen_freestanding_initializer_list.hpp` had three consecutive blank
lines before `namespace std`. Reduced to one.

## Fix 4 — Formatting — DONE (4 files, changed lines only)

Tool: **clang-format 18.1.4**, the exact version pinned by the
repository's `.pre-commit-config.yaml`
(`pre-commit/mirrors-clang-format v18.1.4`, `-style=file`), installed
into an isolated venv (`phase5_buildtools`), not the conda env.

Files touched (formatting only):
- `miopen_freestanding_type_traits.hpp` (new file, ours — wholesale
  format): joined a short `#error` line, aligned consecutive
  assignments, reflowed long `static_assert` conditions.
- `miopen_freestanding_initializer_list.hpp` (new file, ours):
  blank-line squeeze (Fix 3) + single-line short constructor body.
- `miopen_type_traits.hpp` / `miopen_utility.hpp` (legacy files):
  **only the `#error` diagnostic lines added by our commit 1** were
  reflowed; a full-file diff vs the formatted output confirms the
  remainder of both files was already format-clean, so no unrelated
  churn exists.

After the change, all 7 kernel headers touched by the series are
clang-format-18.1.4-clean (`--dry-run -Werror` passes). `radix.hpp`,
`tensor_view.hpp`, `miopen_freestanding_utility.hpp` required no
changes (already clean). `CMakeLists.txt` is not in clang-format scope.
Legacy-file style in untouched regions preserved, per the mission rule
against wholesale reformatting.

## Fix 5 — Copyright attribution — PENDING (human decision)

The three new MIT headers still carry
`Copyright (c) 2026 [contributor name and notice to be set by the submitter]`.

The user confirmed `AIwork4me` as the Git author and as owner of that
GitHub identity — **authorship only**. No statement in this phase's
authorization establishes legal copyright ownership, so per the mission
identity policy the placeholder is retained and the candidate is marked:

```text
COPYRIGHT_ATTRIBUTION_PENDING
```

Consequence: the Phase-5 candidate is **provisional**, not a
release-ready submission package. When the human sets the attribution,
those three comment lines change (classification `COPYRIGHT_TEXT`,
non-functional); the required follow-up is a targeted revalidation
(rebuild + CI A/B spot-check) per the Phase-4 checklist §2. Do NOT
publish as final until then.

## Mandatory exclusions — respected

- `__has_include` strategy unchanged.
- Freestanding type-traits implementation unchanged except the dead
  macro removal and formatting.
- `__INT32_MAX__`/`__INT64_MAX__` semantics unchanged (no edit to
  radix.hpp in Phase 5; commit-2 message rewritten only).
- No unrelated ROCm components touched (repo-level diff vs P4 canonical
  shows only upstream's own b68f894→develop drift in kern_db/sqlite_db/
  BatchNorm kernels — classified `UPSTREAM_BASE_CHANGE`).
- Offline `<limits>` include retained in radix.hpp.
- No redesign.

## Byte-level result

P4-canonical → P5 delta confined to 4 files (all classification
`NONFUNCTIONAL_SOURCE_CLEANUP` + `FORMATTING`):

| File | +/− | Cause |
|---|---|---|
| `miopen_freestanding_type_traits.hpp` | +17/−24 | macro removal + format |
| `miopen_freestanding_initializer_list.hpp` | +1/−5 | blank lines + format |
| `miopen_type_traits.hpp` | +2/−1 | `#error` line wrap |
| `miopen_utility.hpp` | +2/−1 | `#error` line wrap |

`radix.hpp`, `tensor_view.hpp`, `CMakeLists.txt`,
`miopen_freestanding_utility.hpp`: byte-identical to validated content.
