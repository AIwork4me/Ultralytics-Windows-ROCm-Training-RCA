# R22A.5A Initial Gap Matrix — CPU-only Stable preflight readiness

- Generated: 2026-11-17 (mission R22A.5A §2, mandatory repository reconnaissance)
- Audited baseline: R22A.4.1 frozen integration HEAD
  `0b91aa92d3206402f8d66e235c1fb588ea9abdaf` (PR #19 merged; exact-HEAD CI run 43985283035)
- Branch: `release/r22a5a-stable-preflight` (direct child of the baseline; `main` untouched)
- Method: full read of the mandated HEAD files (§2 list), the frozen R22 evidence packs,
  the unified acceptance engine, the CPU test suite and the CI contract, plus live probes
  of the five official AMD channels, `download.pytorch.org` and TheRock GitHub releases
  (all reachable 2026-11-17; TheRock latest tag is still `therock-10.1` 2026-10-05 —
  no release tag postdates the `f0a5d266` merge).

Legend per mission §2: for each capability — (1) existing capability, (2) evidence it
works, (3) missing behavior, (4) release risk, (5) is a code change necessary?

---

## A. Multi-channel official release discovery (Phase A)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `windows-golden-path/scripts/discover_official_wheels.py` scans the 5 AMD channels (multi-arch / stable / rc / nightly / dev) across 10 package families; every wheel URL comes from an observed index href (never synthesized). |
| 2 | Evidence | R21 five-channel scan 2026-11-15 (`wheel_discovery.json` facts embedded in `windows-golden-path/compatibility-matrix.yaml` and the R22 candidate watchlist); re-probed live 2026-11-17 (all channels HTTP 200). |
| 3 | Missing | (a) TheRock **release tags** are not scanned by any script (RELEASE_LINEAGE.md §2 was assembled by hand via `gh`); (b) `download.pytorch.org` ROCm-Windows appearance check exists only as a documented audit note, not code; (c) no deterministic **classification** stage producing the mission §4.3 vocabulary (`NO_NEW_ARTIFACT`, `OFFICIAL_PRE_FIX`, …) from discovery + binary-audit + lineage facts; (d) discovery output mixes observation timestamps with candidate data. |
| 4 | Release risk | A new stable wheel could appear and be manually mis-classified (rc `10.2.0rc2` precedent: post-merge build date, pre-fix source). Without a coded classifier, "new version" and "contains fix" remain human judgements. |
| 5 | Change necessary | **Yes — bounded**: new `scan_official_releases.py` (Phase A) that REUSES `discover_official_wheels.py` as its AMD-index layer and adds TheRock tags + PyTorch index + classification + deterministic normalized output. `discover_official_wheels.py` itself is NOT modified (R22A.4.1 freeze discipline). |

## B. MIOpen binary provenance gate (Phase B)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `verify_provenance.py` (in-venv, GPU-context) with fail-closed `evaluate_lineage()`; `gp_lib.classify_package_origin()`; frozen channel binary audits (`evidence/raw/r22-dev/r22_channel_binary_audit.json`, gfx1151 counterpart) with wheel SHA256 → embedded DLL SHA256 → marker count → build-commit → GitHub compare ancestry. |
| 2 | Evidence | rc channel DISPROVEN by ancestry (`behind_by=92`) despite newer version; nightly/dev PROVEN `behind_by=0`; `verify_provenance.py` consumed the same JSON via `--ancestry-evidence` in the R22 DEV gates. |
| 3 | Missing | (a) The wheel-download → ZIP-inspect → DLL-hash → compare-API chain has **no reproducible script** — the frozen audits were assembled ad hoc; (b) no CPU-only negative-control test set for the gate (fake marker, higher-version-older-DLL, wrong hash, Linux wheel, wrong ABI, nightly-as-Stable, unknown ancestry); (c) no written binary-provenance contract doc consolidating the marker/screening vs ancestry/authoritative distinction. |
| 4 | Release risk | When a candidate appears, the next engineer must re-derive the whole method by hand — the highest-probability point for a false Stable PASS. |
| 5 | Change necessary | **Yes**: `audit_wheel_provenance.py` (bounded download, safe ZIP inspection, no install) emitting the SAME schema the in-venv verifier already consumes; CPU adversarial tests; contract doc. `verify_provenance.py` NOT modified. |

## C. Stable package compatibility matrix (Phase C)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `windows-golden-path/compatibility-matrix.yaml` (source of truth: channels, rules, verified stacks) + `resolve_package_set.py` (pip dry-run resolution, SHA256 pinning, family-mix / device-wheel / vendor-origin rules, exit 3 = BLOCKED_OFFICIAL_ARTIFACT). |
| 2 | Evidence | R22 DEV locks resolved + hash-pinned this way for both architectures (46-artifact locks; frozen in `evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json`). |
| 3 | Missing | (a) An **installation-plan generator** that emits commands classified `OFFICIAL_STABLE` / `OFFICIAL_RC` / `OFFICIAL_DEV` / `UNQUALIFIED` only for independently coherent candidate sets — `resolve_package_set.py` resolves a chosen channel but does not gate on channel class vs Stable labeling; (b) a candidate lock TEMPLATE for the future fixed Stable build (mission: must not rewrite historical `golden-path/requirements-lock.txt`); (c) a consolidated compatibility matrix doc separating official support from engineering feasibility for gfx1100/gfx1151. |
| 4 | Release risk | A user could be handed a nightly/dev plan labeled as production install instructions. |
| 5 | Change necessary | **Yes — adapter**: `gen_install_plan.py` layering channel-classification over the existing resolver facts; yaml and resolver untouched. |

## D. Golden Path G9 preflight (Phase D)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `golden-path/` user suite (verify_environment / train / validate / resume / verify_checkpoint, acceptance manifest+schema, WINDOWS_SETUP.md); `run-golden-path.ps1 -Mode Preflight`; `install_official.ps1`; `verify_miopen_nostl.py` (the G1 no-STL verifier with VCToolsInstallDir redirect + fresh cache technique, validated C+D and R21-D). |
| 2 | Evidence | Harness validated on physical gfx1100 (R21) and both architectures at DEV level (R22A.2/3/4/4.1); `golden-path/` MODE B physically executed on gfx1151 (P14.3). |
| 3 | Missing | (a) A **qualified-input gate**: nothing stops a future user from running the golden path against a pre-fix Stable wheel and reporting a false success (on hosts with VS Build Tools the no-STL failure is masked — WINDOWS_SETUP.md §5 even documents the MSVC fallback); (b) a hidden-requirements scanner (VCToolsInstallDir / HIPRTC_* / MIOPEN_* / VS Build Tools / editable checkout / private index …) as code; (c) the G1 no-STL negative control "host STL genuinely unreachable" is implemented at runtime but has no **static contract** proving the negative-control design before GPUs are involved; (d) BLOCKED_RELEASE entry-point semantics for the stable flow. |
| 4 | Release risk | Independent tester (issue #14, still OPEN / 0 comments — invitation NOT accepted) would hit the masking trap. |
| 5 | Change necessary | **Yes**: `g9_preflight.py` (CPU-only, no torch import) + G9 preflight doc; golden-path scripts NOT modified. |

## E. Stable dual-arch acceptance contract (Phase E)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `acceptance-contract.json` gates G0–G9 + `supplemental_acceptance.py` unified engine (Part A/B recompute, stored-PASS rejection, runtime-provenance gate, dual-arch verdicts, DEV ceiling) — FROZEN semantics per R22A.4.1. |
| 2 | Evidence | 261/261 manifest entries blob-exact; `R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED` recomputed by the single engine. |
| 3 | Missing | (a) The **Stable evidence model** (frozen DEV vs new provenance vs new physical observations vs new acceptance) is implied but not specified anywhere; (b) future GPU matrix G0–G9 × {gfx1100, gfx1151} per-arch verdict table; (c) checkpoint-integrity criteria beyond existence (optimizer/scheduler/GradScaler state, epoch continuity, tolerance policy); (d) AMP taxonomy (`AMP_PASS`/`AMP_DISABLED`/`AMP_INCONCLUSIVE`/`AMP_FAIL`/`BACKEND_FAILURE`) — the DEV harness records AMP facts but codifies no Stable taxonomy; (e) reliability scenario list (cold/warm/workers/interrupt/invalid-checkpoint/missing-dataset/OOM …) as a contract. |
| 4 | Release risk | R22A.5B could improvise gate definitions, breaking comparability with the frozen DEV baseline. |
| 5 | Change necessary | **Docs only** (contract doc referencing the frozen engine; engine NOT touched). |

## F. Independent user & upstream handoff (Phase F)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `golden-path/` self-contained suite; issue #14 invitation (OPEN, 0 comments — not accepted); `R20_RELEASE_READINESS_20261115.md` + `R20_RELEASE_REQUEST_COMMENT.md` release-owner request; `windows-golden-path/docs/r23/` draft developer docs. |
| 2 | Evidence | P16 independent-user acceptance report; R20 verdict RELEASE_REQUEST_READY / BLOCKED_EXTERNAL_PUBLICATION. |
| 3 | Missing | (a) A Stable-flow independent-validation package with explicit PASS/FAIL/BLOCKED semantics wired to the preflight (current suite predates the Stable gate); (b) consolidated release-engineering handoff (R20 is a decision request; the mission wants the concise technical handoff covering wheel identity, acceptance tests, hardware, minimum info needed). |
| 4 | Release risk | Handoff re-derived per conversation; independent tester instructions drift from the harness. |
| 5 | Change necessary | **Docs + thin wiring** (Stable acceptance guide referencing existing scripts; handoff doc). No new upstream posting (mission forbids auto-posting; #15862 untouched). |

## G. CPU regression / adversarial testing (Phase G)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `windows-golden-path/tests/test_harness_cpu.py` — 197 tests (183 R22A.4 baseline + 11 provenance-gate + 3 wrapper-compat), incl. 22+ adversarial fail-closed classes; `scripts/verify_release_closure.py` — 902 checks + 22 adversarial self-tests; CI `cpu-contract.yml` (compileall + pytest + verifier, windows-latest, py3.11). |
| 2 | Evidence | Exact-HEAD CI run 43985283035 green at the freeze HEAD. |
| 3 | Missing | Negative controls for the NEW R22A.5A surfaces only (mission §10 list 1–20: index failure/partial HTML, conflicting versions, new-wheel-old-DLL, fake marker, hash mismatch, Windows/Linux confusion, ABI, wrong device package, mixed SDK generations, missing dep, archive path traversal, unverified source, DEV/RC mislabeled Stable, DEV-reuse-as-Stable, serialized fake PASS, GPU-unavailable-as-success, unqualified plan, network-outage-as-no-release). |
| 4 | Release risk | None to existing coverage — new tests are additive in a separate file; the 197-test file stays byte-stable. |
| 5 | Change necessary | **Yes**: new `test_r22a5a_cpu.py` (deterministic fixtures, no network, no GPU); CI extended by one compileall step for `scripts/r22a5a` (additive; no existing step weakened). |

## H. One-command CPU release preflight (Phase H)

| # | Item | Findings |
|---|---|---|
| 1 | Existing | `run-golden-path.ps1 -Mode Preflight` (host baseline only) and `-Mode PrepareRelease` (channel scan, no GPU) — closest precedents. |
| 2 | Evidence | Both modes exercised during R21/R22 missions. |
| 3 | Missing | A single entry point integrating: repo baseline → discovery → classification → provenance → compatibility → G9 readiness → Stable contract completeness → CPU tests → machine-readable report → meaningful exit code, with `--offline` (zero network) / `--live` separation and result semantics `R22A5A_CPU_PREFLIGHT_READY` + `BLOCKED_RELEASE` / `CANDIDATE_FOUND_PENDING_PHYSICAL_VALIDATION`. Nothing like this exists. |
| 4 | Release risk | Without it, readiness is a 15-file manual checklist — the exact duplication trap the mission warns about. |
| 5 | Change necessary | **Yes**: `scripts/r22a5a/release_preflight.py` orchestrating EXISTING components (verifier, pytest, compileall, golden-path manifest checks, new Phase A–D tools). One new framework entry point, not a second verification framework. |

---

## Duplicate-engineering avoidance decision record

1. **Reuse unchanged**: `discover_official_wheels.py`, `resolve_package_set.py`,
   `verify_provenance.py`, `verify_miopen_nostl.py`, `supplemental_acceptance.py`,
   `acceptance-contract.json`, `compatibility-matrix.yaml`, `golden-path/*`,
   `run-golden-path.ps1`, `test_harness_cpu.py` (197), `verify_release_closure.py`.
2. **Add (new, thin, shared-helper style)**: `scripts/r22a5a/` —
   `r22a5a_lib.py` (classification + safe wheel ZIP inspection + plan rules),
   `scan_official_releases.py`, `audit_wheel_provenance.py`, `gen_install_plan.py`,
   `g9_preflight.py`, `release_preflight.py`, plus `windows-golden-path/tests/test_r22a5a_cpu.py`.
3. **Do NOT create**: a second acceptance engine, a second golden-path suite, a parallel
   wheel resolver, or any modification to frozen DEV evidence/verdicts.

## Headline conclusion

The repository already owns ~85% of the needed machinery; the genuine gaps are the
**classified candidate pipeline** (discovery→provenance→plan), the **qualified-input G9
gate**, the **Stable acceptance contract docs**, and the **one-command preflight** —
all implementable CPU-only without touching frozen evidence or the unified engine.
