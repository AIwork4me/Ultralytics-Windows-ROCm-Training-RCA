# Phase-2 Hypothesis Table (Gate 40)

Statuses: Supported / Falsified / Plausible / Unresolved (with confidence).
Phase-1 hypotheses H1–H13 retain their Phase-1 statuses (docs/HYPOTHESES.md).

| ID | Hypothesis | Supporting evidence | Contradicting evidence | Decisive experiment | Status | Confidence |
|---|---|---|---|---|---|---|
| P2-H1 | Dirty base environment causes failure | — | Gate 23: curated clean env (no paddlex/paddle/etc., native stack SHA256-identical) reproduces failure field-for-field | Gate 23 | **Falsified** | High |
| P2-H2 | HIPRTC globally cannot access any host C++ STL | Gate 24 (before MSVC): all 5 std headers fail standalone | Gate 27 arms A/B/C: with MSVC present (auto-discovery / INCLUDE / dev shell) all compile and BN passes | Gate 27 | **Falsified** (in its strong form: "cannot even when present") | High |
| P2-H3 | MSVC STL absence is an *intended* prerequisite | Gate 27: MSVC presence is sufficient; TheRock docs declare MSVC 19.43+ a build prerequisite (analogous intent inside AMD) | AMD's *user-facing* Windows PyTorch install docs declare no MSVC prerequisite (Phase-1 C028) — the prerequisite is UNdeclared for wheel consumers; nothing marks it intended | Gate 27 + docs evidence | **Unresolved as "intended"; Supported as "operative"** — MSVC presence is the operative machine-level remedy, but its intent is undocumented upstream | Medium-High |
| P2-H4 | MSVC is present but HIPRTC does not discover it | (pre-Phase-2 plausibility) | Gate 26: MSVC was ABSENT before Gate 27; after install, auto-discovery works in plain shell (clang `-v -E` search list) | Gates 26/27 | **Falsified** (was not the case here; discovery works when MSVC exists) | High |
| P2-H5 | MIOpen HIPRTC compile options omit required include discovery | MIOpen adds no stdlib include unless ROCM_PATH set; `-I$ROCM_PATH/include` honored (poison test) | Standalone HIPRTC (no MIOpen options) fails identically → MIOpen's options are not the differentiator; with MSVC present MIOpen's unchanged options pass | Gate 24 vs 27 | **Supported as contributing** (no proactive include config) but **not causal in isolation** — falsified as the sole owner | High |
| P2-H6 | HIP ≥ 7.0 miopen_type_traits gate creates the Windows regression | Commit `ce14dab3` (PR #3803) diff: outer version gate added → real `<type_traits>` unconditionally for HIP ≥ 7.0; hiprtc 7.0 moved std traits to `__hip_internal` (design context); pre-7.0 shim existed precisely for no-STL RTC | Naive re-enable fails (shim rotted) — supports that the gate change was the regression *window opener*, though the shim alone wouldn't have survived unmodified either | Gate 29 archaeology + Gate 32 DLL-patch experiment | **Supported** (as trigger of the regression window) | High |
| P2-H7 | Runtime compile should remain self-contained and avoid host STL | Pre-#3803 MIOpen architecture (no-STL shim); rocRAND-style runtime self-containment precedents; freestanding 48-line type_traits passes all BN cases through real MIOpen (Candidate A-3); wheel-side remedies also possible | hiprtc 7.0's design direction (traits moved to `__hip_internal`) pushed consumers toward real STL — an architectural argument against, not evidence against feasibility | Gate 32 | **Supported as feasible and validated**; whether it is *preferred* upstream is a design judgment | High (feasibility) |
| P2-H8 | A candidate source fix resolves BatchNorm without regressions | Candidate A-3 (ROCM_PATH + shim): all BN variants + controls PASS, cache-isolated; regression matrix 8/8 PASS; numerics vs CPU ≤ 7.2e-7 max abs; YOLO closure PASS (both amp modes) | none observed | Gates 32–35 | **Supported** (for remedy validated end-to-end; upstream PR text additionally needs the shim-repair shape from Candidate B) | High |

## Reading notes

- P2-H3's split verdict matters for the upstream recommendation: the
  *machine-level* remedy (install MSVC C++ Build Tools) is proven, but
  claiming AMD "intended" it would be unsupported — their public docs say
  otherwise (that gap is itself part of the defect).
- P2-H5 vs P2-H6 vs P2-H2 combine into the two-layer LEVEL-3 verdict in
  `docs/PHASE2_LEVEL3_RCA.md`: wheel packaging (no STL provision/discovery/
  docs) × MIOpen gating (std headers required in RTC for HIP ≥ 7.0).
