# CROSS-PLATFORM EVIDENCE CONSOLIDATION — Gate P54-06

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS` · Compiled 2026-10-09.

## Source-version identities (kept strictly separate)

| Identity | Value | Role |
|---|---|---|
| `FROZEN_R2_SOURCE_TREE` | `b983cadd…` @ commits `01a77dab/8188b803/f18c4de9`, base `7c586614` (2026-10-07) | Windows-frozen candidate; **immutable** |
| Linux W7900 validated tree | R2 series reconstructed from bytes → **identical tree `b983cadd`** (3 independent methods, L03) | Same source as Windows R2 |
| `LATEST_DEVELOP_REPLAY_TREE` / `P5.4-SUBMISSION-CANDIDATE-R1` | tree `81e39c3b…` @ commits `0af085f1/69e7ff07/cab3f08a`, base `681bc9ed` (2026-10-09) | Prospective submission tree; ten changed-file blobs **byte-identical** to R2's; only upstream base moved |

Equivalence statement (precise): replaying R2 onto latest develop reproduced the identical ten-file patch payload (10/10 git blob SHAs equal to R2's) with zero conflicts; the full-tree SHA differs **only because** upstream's own 61 commits changed other files. This is a payload equivalence, NOT a claim that the full upstream trees are identical.

## Platform matrix

| Dimension | **Windows** (Radeon 8060S, gfx1151, Win 11, ROCm 7.14.0 wheel, PyTorch 2.12.0+rocm7.14.0) | **Linux W7900** (Radeon PRO W7900, gfx1100, Ubuntu 24.04.4, ROCm 7.14.1 isolated wheel, PyTorch 2.12.0+rocm7.14.1) | **Linux 8060S** (gfx1151) |
|---|---|---|---|
| Source validated | R2 tree `b983cadd` (frozen) **and** latest-develop replay `81e39c3b` (this phase) | R2 tree `b983cadd` (reconstructed, verified) | **PENDING Phase 5.3B** |
| Original failure reproduced | ✅ unpatched wheel/control: `'type_traits' file not found` RTC failure (R2 evidence; re-proven today on unpatched develop `681bc9ed` kernels via negative/positive controls) | n/a (host STL reachable — by design not reproducible on that install) | historical Phase-3 PASS only |
| Patched behavior validated | ✅ genuine no-STL CTest **Passed** (not skipped) on R2 **and** on replay; no-STL runtime scenario PASS | ✅ via source-built A/B (not the no-STL ctest) | PENDING |
| no-STL CTest | **PASS, mandatory, genuine** | **SKIPPED — legitimately** (ROCm 7.14.1 `libhiprtc-builtins` embeds C++ headers; probe reports INCONCLUSIVE exit 4; never counted as pass) | PENDING |
| Ordinary + with-STL controls | ✅ (matrix cells; today re-proven on replay) | ✅ L07 | PENDING |
| Kthvalue A/B (radix.hpp + tensor_view.hpp closure) | not in Windows R2 gate set (Windows runtime validation is BN-based; kthvalue A/B is Linux evidence) | ✅ 3/3 cases, 15/15 byte-identical dumps, fresh caches, direct `miopenKthvalueForward`, dispatch proven | PENDING |
| BatchNorm numerics | ✅ R2: y≈6.71e-07 (fixed pre-registered tolerances); **replay DLL today: identical values** (y=6.706602642125858e-07, dx=3.20e-12, dw=2.44e-08, db=1.86e-09, running stats finite) | ✅ A/B 6/6 checks, 4–6 orders of margin, identical both legs, direct public API | PENDING |
| YOLO26n coco8 1-epoch | ✅ R2 `amp=False` PASS; replay re-run: see `LATEST_DEVELOP_WINDOWS_REVALIDATION.json` (gate P54-04) | ✅ smoke PASS (B-leg patched, `amp=False`, in-process binding proof) | PENDING |
| AMP behavior (default) | R2 frozen evidence: `genuine_amp_evidence=false` (AMP precheck fell back to FP32 in that environment). **This phase re-runs and reports the same dimensions honestly — raw logs preserved; no claim upgrade.** | n/a (not asserted) | PENDING |
| Library provenance | ✅ in-process `GetModuleFileNameW` + sha256 (wheel-location DLL = replay build `44d43887…` during gates; wheel restored to `74b4ee03…` after) | ✅ in-process `dladdr` both legs; zero system-ROCm 7.2.1 contamination after real GPU init | PENDING |
| False-pass defenses | ✅ 13-cell adversarial matrix (R2) + **13/13 re-proven on replay today**; identity markers, isolation probe, signature checks | ✅ 14/14 attack matrix (L11) | PENDING |

## What each platform proves (explicit)

- **Windows**: the original no-STL RTC failure is real, reproduced, and **fixed** by the patch — the only platform of the three with a genuine no-STL capability, hence the load-bearing positive evidence (frozen R2 + fresh replay revalidation).
- **Linux W7900**: the patch causes **no regression** where a full host STL exists — source-built A/B equivalence for runtime numerics (kthvalue + BatchNorm) and working CTest integration with honest skip semantics. It does **NOT** claim to have validated the latest-develop replay tree (validated tree = R2 `b983cadd`; payload-identical to the replay, see equivalence statement above).
- **Linux 8060S (gfx1151)**: **PENDING** Phase 5.3B. Historical Phase-3 PASS exists for an ancestor of the fix on this hardware class, but the final R2 status on this platform must come from actual, verified Phase-5.3B evidence (none published as of 2026-10-09; no `*5.3B*` remote branch exists). No claim is made from the historical result.

## Immutable evidence links

- Windows R2 freeze: [`phase5.1/windows-r2-ci-portability-freeze` @ `c841716`](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/tree/c841716) — `findings/phase5_1_r2/FINAL_HANDOFF.json`; DLL `48a1eee2…` gates; series SHA256 `48308f6d…`.
- Linux W7900 Phase 5.3: [PR #8 merge](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/8), branch [`linux-w7900/phase5.3-r2-final-ab` @ `166c33d`](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/tree/166c33d) — verdict `PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP`; Leg A lib `7e045dc0…`, Leg B lib `bf21a5fa…`.
- Latest-develop replay + Windows revalidation: this branch's `phase5_4/evidence/` (manifest inside); replay DLL `44d43887…`.

## Verdict

Consolidation is accurate and boundaries are explicit: **Windows owns the positive no-STL proof (twice: R2 + latest-develop replay), Linux W7900 owns the no-regression A/B (R2 source), Linux gfx1151 remains honestly PENDING.** No cross-platform claim exceeds its raw evidence.

**PASS.**
