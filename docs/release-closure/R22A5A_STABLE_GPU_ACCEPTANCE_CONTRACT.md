# R22A.5A Stable Dual-Architecture GPU Acceptance Contract

- Generated: 2026-11-17 (mission R22A.5A Phase E, §8)
- Scope: the CONTRACT for R22A.5B physical validation. No GPU execution
  occurred in R22A.5A and none is implied here.
- Engine policy: REUSE the frozen unified R22 engine
  (`windows-golden-path/scripts/supplemental_acceptance.py`) semantics —
  Part A/B recompute, stored-PASS rejection, cache-role derivation from
  home identity, monitor fail-closed, runtime-provenance gate. A
  versioned Stable ADAPTER may be added; the DEV evidence format and its
  interpretation are NEVER changed.

## 1. Evidence model (four strictly separated layers)

| Layer | Content | Mutation rule |
|---|---|---|
| L1 frozen DEV evidence | `evidence/raw/r22a2-gfx1100/`, `evidence/raw/r22a3-gfx1151/`, r22-dev packs, R22A41 reports | byte-frozen; NEVER rewritten; NEVER relabeled Stable |
| L2 new official package provenance | scan + audit JSONs (`release-provenance/r22a5a/…`) + the hash-pinned Stable lock from `resolve_package_set.py` | append-only; must exist BEFORE any physical run |
| L3 new Stable physical observations | raw per-run records (G0..G9 evidence files) of the Stable wheels | append-only; produced only by R22A.5B runs |
| L4 Stable acceptance results | recomputed verdicts from L3 facts via the unified engine + Stable adapter | derived; may be regenerated; never authority |

Hard rule: a DEV run record can never appear in L3/L4. The runtime-
provenance gate already rejects mixed identities (R22A.4.1 test cases 1–8);
the Stable adapter extends the same gate with
`channel=stable` + Stable wheel/DLL SHA256 equality.

## 2. Future GPU matrix (independent per-architecture verdicts)

| Gate | gfx1100 (RX 7900 XTX) | gfx1151 (Radeon 8060S) |
|---|---|---|
| G0 package provenance | Required | Required |
| G1 no-STL BatchNorm | Required | Required |
| G2 genuine GPU compute | Required | Required |
| G3 standard YOLO train/val | Required | Required |
| G4 AMP numerical integrity | Required | Required |
| G5 checkpoint save/resume | Required | Required |
| G6 workers & stability | Required | Required |
| G9 clean installation | Required | Required |

- Per-architecture verdicts are independent:
  `STABLE_SUPPLEMENTAL_PASS(gfx1100)` / `...PASS(gfx1151)`.
- **Never force the same effective-update count or GradScaler trajectory
  across GPUs** — the DEV baseline legitimately differs (gfx1100 6/11
  confirmed updates, gfx1151 7/11 in the frozen evidence); each arch's
  receipt must carry its own per-step series.
- Combined ceiling verdict only when BOTH arches pass:
  `R22_STABLE_DUAL_ARCH_SUPPLEMENTAL_VALIDATED` — the Stable analog of the
  frozen DEV verdict, computed by the same engine semantics.

## 3. Checkpoint integrity contract (beyond existence)

`verify_checkpoint_resume.py` semantics extended-checklist for the Stable
adapter (items already measured by the harness are marked ✔):

| Check | Source |
|---|---|
| model weights present & finite | ✔ existing |
| checkpoint SHA256 recorded | ✔ existing |
| epoch continuity (resume starts at last completed + 1; NO reset) | ✔ existing |
| optimizer state restored (not reinitialized) | ✔ (AdamW param-group state read) |
| learning-rate scheduler state restored | adapter: read scheduler.state_dict() before/after |
| GradScaler state restored (scale + growth tracking) where AMP active | adapter: scaler.state_dict() comparison |
| best-metric tracking continues (no amnesia of best.pt) | adapter: best fitness value carries over |
| continued legitimate parameter updates after resume | ✔ (named_parameters delta post-resume) |
| validation completes after resume | ✔ (val stage) |
| bitwise equivalence NOT assumed: justified numeric tolerance (float summation order differs) + nondeterminism disclosure | contract: tolerance ≤ 1e-5 relative on reproduced loss unless deterministic kernels were forced; any larger deviation = investigation, not PASS |

## 4. AMP integrity taxonomy

| Verdict | Meaning |
|---|---|
| `AMP_PASS` | genuine low-precision execution OBSERVED (autocast dtype samples) AND successful scaled parameter updates AND finite grads on every confirmed update |
| `AMP_DISABLED` | probe/check failed → training continued FP32 (disclosed) |
| `AMP_INCONCLUSIVE` | autocast enabled but no low-precision sample captured (dtype not observed) |
| `AMP_FAIL` | low-precision execution produced non-finite loss/grads without correct scaler skip |
| `BACKEND_FAILURE` | the ROCm runtime itself faulted (e.g. AcceleratorError/MIOpen) — diagnosed at its owning layer and REPORTED, never swallowed |

Hard rules: FP32 fallback NEVER counts as AMP_PASS. A broken ROCm runtime
must surface as BACKEND_FAILURE with its own classification — never be
concealed by broad exception handling in Ultralytics (PR #27198 lesson;
the merged #27203 approach — precise detection — is the shipped behavior).

## 5. Train/validation reliability criteria (R22A.5B matrix)

| Scenario | Requirement |
|---|---|
| cold start | fresh USERPROFILE identity recorded; first-run success |
| warm start | same-home re-run; cache role WARM (not priming — first use of a fresh shared home is CACHE_PRIMING per the frozen contract) |
| DataLoader workers=0 | completes; contract preserved (G8 compat) |
| DataLoader workers=8 | Windows worker lifecycle: peak concurrency + per-PID identity records; zero unexplained orphan/fatal anomalies |
| process interruption | controlled kill mid-epoch; no corruption |
| cross-process recovery | NEW process `resume=True`; epoch continuity + post-resume updates |
| invalid checkpoint | clean EXPECTED_FAIL/CLASSIFIED error, never a fabricated PASS |
| missing dataset | actionable failure (exit ≠ 0 with classified reason) |
| incompatible runtime | pre-fix wheel → G1 EXPECTED_FAIL signature (the negative control) |
| GPU unavailable | explicit BLOCKED_ENVIRONMENT — GPU absence is never success |
| bounded OOM | graceful, classified failure on an oversized batch; recovery after reducing batch |

Matrix sizing: ≥10 independent training processes per arch with cold+warm
coverage (inherited G8 semantics; 2 COLD distinct homes + ≤1 priming + 3
qualifying WARM per the frozen contract).

## 6. Verdict vocabulary and ceilings

- `STABLE_CANDIDATE_PENDING_GPU_VALIDATION` (this mission's ceiling for a
  qualifying stable artifact) → R22A.5B promotes it ONLY via completed
  physical gates.
- `OFFICIAL_STABLE_PASS` requires: stable/GA channel + provenance complete
  (ancestry behind_by=0 + wheel/DLL SHA match) + no workaround detected +
  all gates PASS on that arch. Nothing else may ever produce this string.
- DEV/RC/nightly artifacts cap at `*_CANDIDATE_PASS` forever
  (`candidate_ceiling` in acceptance-contract.json, unchanged).
