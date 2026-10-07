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
| MIOpen user kernel DB | gained successful BN entries during Phase-2 passing runs | `C:\Users\rocm\.miopen\cache\3.5.1.98f923c854\gfx1151_20.ukdb` + `3.5.2.cd957402\gfx1151_20.ukdb` + perf DBs present — **every unpatched-control/no-MSVC Phase-3 run MUST isolate or flush these caches** (spurious PASS risk) | ⚠ |
| Ambient env vars | none set | `ROCM_PATH`/`INCLUDE`/`HIP*`/`MIOPEN*` unset in shell + User/Machine registry (checked this session; re-verify per session) | ✓ |
| Poison marker | inert experiment leftover | `C:\hiprtc_poison\include\type_traits` still on disk — inert unless added to `-I` | ⚠ |

Reviewer-C blocker status carried into Phase 3: B1 (narrowed — real-build
validation), B2 (partially resolved in v2: gate semantics correct, `#if 1`
remains), B3, B4, B5, B8 open; B6 (custody drift) and B7 (attribution
errors) were remediated and verified in the Phase-2 correction commits.

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

1. Exact patch applied to a REAL **built** MIOpen works through the real
   comgr/HIPRTC path with the full kernel closure and numerics.
   (Candidate-B v2's *header* was directly compiled via hiprtc with
   `-nostdinc` and GPU-executed — `candidate_b_v2_validation.txt` — so
   Reviewer-C B1's literal text is narrower than written — but no
   built-from-source patched MIOpen has ever been loaded by PyTorch.)
2. All RTC kernel std dependencies covered — the 13-file BN closure was
   enumerated and a tree-wide `STD_INVENTORY.txt` (158-header embedded
   set) exists; what's missing is the RTC-kernel × std-entity
   enumeration as a reusable static-audit script. Blocker B3 stands
   (`<utility>`/`<limits>`/`<functional>` consumers:
   reduction/layernorm/etc.).
3. Linux HIP>=7 regression-free — zero Linux runs exist. Blocker B4.
4. Second Windows ROCm line (7.2.1, MIOpen #3956's stack) behavior;
   requires parameterized probes (B5: `hiprtc_probe.py` hardcodes
   `gfx1151`/`hiprtc0714.dll` — useless on gfx1200 as-is).
5. Current newest Windows ROCm line state (is the gate still present?
   fixed?).
6. Correct final patch structure — candidate-B v2 ALREADY has the
   correct outer-gate semantics (outer HIP-version gate removed,
   `#ifdef MIOPEN_HIP_RUNTIME_COMPILE` as sole discriminator — exactly
   Reviewer C's demanded shape); remaining v2 defects: `#if 1` inner
   scaffolding, non-git-format-patch hygiene, no sign-off, no
   co-inclusion guard, `miopen_utility.hpp` scope, and no
   dedicated-header/static_assert option evaluated (Gates 55–56).
7. Maintainer-ready test coverage — no CI-able negative-control test
   exists (B5: DLL-flip and poison experiments unscripted; no
   orchestrator with expected-output fixtures;
   `hiprtc_compile_bnsources.py` has no archived output).
8. Artifact→destination routing plan (B8: MIOpen PR vs TheRock wheel
   issue vs ROCm docs — mapping required so a single package doesn't
   bounce between repos).

## Known constraints carried forward

- Upstream Reviewer-C verdict: RCA = issue-grade; candidate-B = NOT
  submittable (8 blockers B1–B8, all Phase-3 scope).
- Reviewer-C's preferred patch shape: revert the #3803 outer-gate hunk on
  `miopen_type_traits.hpp` AND the equivalent on `miopen_utility.hpp`;
  repair the rotted window (traits unconditional in RTC mode; proper
  `enable_if`, not `__hip_internal`); prefer a dedicated
  freestanding-traits header with `static_assert` self-tests AND a guard
  against co-inclusion with a real `<type_traits>` (fallback acceptable
  if argued: keep the inline restore as a minimal revert); clean git
  format-patch + commit message citing #3956 AND the Windows-wheel
  mechanism + sign-off. Also pending: maintainer-facing self-contained
  report (no gate jargon) and an audit note for
  `miopen_limits.hpp`/`miopen_cstdint.hpp`.
- "No-MSVC" proofs in Phase-2 used `-I` shadowing on an MSVC-present
  machine; Phase-3 must reprove without that caveat where feasible.
- ABSOLUTE: no upstream PR/issue/comment/push. Local work + RCA repo only.
