# Phase-3 Gate 50 — Phase-2 Handoff Audit

Date: 2026-10-07. Auditor: Phase-3 primary agent. Branch created:
`rca/windows-gfx1151-rocm714-phase3` (from clean Phase-2 HEAD `0e72959`).

## Sources read

- `docs/PHASE2_LEVEL3_RCA.md`, `docs/PHASE2_SUMMARY.md`,
  `docs/PHASE2_NEXT_STEPS.md`, `docs/PHASE2_HYPOTHESES.md`,
  `docs/PHASE2_RUNTIME_STL_REQUIREMENTS.md`,
  `docs/PHASE2_CLAIMS_AND_EVIDENCE.md`
- `findings/phase2/final_gate.md`, `findings/phase2/phase2_conclusion.json`
- `findings/phase2/subagent_rocm_review.md`,
  `findings/phase2/subagent_falsification_review.md`,
  `findings/phase2/subagent_upstream_readiness_review.md`
- `patches/candidate_B_miopen_type_traits.patch`,
  `patches/candidate_B_miopen_type_traits.hpp`
- Final Phase-2 correction commits: `0e72959` (manifest self-exclusion),
  `81859d1` (manifest regen), `6488e5d` (review wording),
  `2a9bcd1` (custody renormalization, attribution split, candidate-B v2).

## Machine-state verification (this session, before any Phase-3 work)

| Item | Expected (Phase-2 record) | Observed 2026-10-07 | Match |
|---|---|---|---|
| conda env `yolo_amd` Python | 3.13.x | 3.13.16 (Anaconda MSC v.1942) | ✓ |
| PyTorch | 2.12.0+rocm7.14.0 | 2.12.0+rocm7.14.0 | ✓ |
| GPU visible | AMD Radeon 8060S (gfx1151) | `torch.cuda.is_available()=True`, device name "AMD Radeon(TM) 8060S Graphics" | ✓ |
| MIOpen.dll SHA256 | `74b4ee03…` (restored after binary-patch experiment) | `74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a` (`_rocm_sdk_libraries/bin/MIOpen.dll`) | ✓ |
| MSVC Build Tools | 14.44.35207 at `C:\BuildTools` | `C:\BuildTools\VC\Tools\MSVC\14.44.35207` present | ✓ |
| Git state | clean tree on phase2 branch | clean; new phase3 branch cut from `0e72959` | ✓ |

## Proven (carried into Phase 3 as working facts)

1. **Clean-env reproduction** — curated SHA256-identical env reproduces the
   failure field-for-field; dirty-env hypothesis falsified (Gate 23).
2. **Standalone HIPRTC failure without STL** — ctypes reproducer on the
   wheel's own `hiprtc0714.dll`, no torch/MIOpen/Ultralytics: all std
   headers fail with `HIPRTC_ERROR_COMPILATION(6)`; no-include control
   compiles AND executes on GPU (Gate 24).
3. **MSVC sufficient to restore std headers** — plain-shell clang
   auto-discovery; dev-shell and INCLUDE-only arms also pass (Gate 27).
   MSVC is *one sufficient provider*, not an intrinsic requirement.
4. **MIOpen HIP>=7 gate is the trigger** — commit `ce14dab3`
   (PR ROCm/MIOpen#3803) added the outer `HIP_PACKAGE_VERSION_FLAT <
   7000000000ULL` gate to `miopen_type_traits.hpp`; commit `b514736610`
   (PR #3147) added the analogous gate to `miopen_utility.hpp`
   independently (attribution split verified in Phase-2 review).
5. **Candidate freestanding traits implementation is viable** — 48-line
   freestanding `type_traits` served via `-I$ROCM_PATH/include` passes all
   BN cases + controls cache-isolated; candidate-B v2 shim content
   compile+exec validated (Gate 32).
6. **YOLO training closure is possible** — epochs=1 + validation +
   best/last.pt + exit 0, amp=False AND default AMP (Gate 35).

## Not yet proven (Phase-3 obligations)

1. Exact patch applied to a REAL **built** MIOpen works — Phase-2
   validated shim *content* through an injection channel, never a
   built-from-source patched MIOpen. Reviewer-C blocker B1 stands.
2. All RTC kernel std dependencies covered — only the 13-file BN closure
   was enumerated; `<utility>`/`<limits>`/`<functional>` consumers
   (reduction/layernorm/etc.) un-audited. Blocker B3 stands.
3. Linux HIP>=7 regression-free — zero Linux runs exist. Blocker B4.
4. Second Windows ROCm line (7.2.1, MIOpen #3956's stack) behavior.
5. Current newest Windows ROCm line state (is the gate still present?
   fixed?).
6. Correct final patch structure — candidate-B v2 still carries `#if 1`
   scaffolding and a gate-flip shape rejected by Reviewer C (B2); the
   correct semantics (RTC-mode discriminator, dedicated-header option)
   must be designed and proven (Phase-3 Gates 55–56).
7. Maintainer-ready test coverage — no CI-able negative-control test
   exists (B5: DLL-flip and poison experiments unscripted).

## Known constraints carried forward

- Upstream Reviewer-C verdict: RCA = issue-grade; candidate-B = NOT
  submittable (8 blockers B1–B8, all Phase-3 scope).
- Reviewer-C's preferred patch shape: revert the #3803 outer-gate hunk on
  `miopen_type_traits.hpp` AND the equivalent on `miopen_utility.hpp`;
  repair the rotted window (traits unconditional in RTC mode; proper
  `enable_if`, not `__hip_internal`); prefer a dedicated
  freestanding-traits header with `static_assert` self-tests; clean git
  format-patch + commit message citing #3956 + sign-off.
- "No-MSVC" proofs in Phase-2 used `-I` shadowing on an MSVC-present
  machine; Phase-3 must reprove without that caveat where feasible.
- ABSOLUTE: no upstream PR/issue/comment/push. Local work + RCA repo only.
