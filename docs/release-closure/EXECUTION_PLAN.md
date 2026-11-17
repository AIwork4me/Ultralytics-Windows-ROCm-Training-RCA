# EXECUTION PLAN — Release-to-Upstream Closure

Branch: `work/windows-rocm-training-release-closure` (from main `f9f745e`, 2026-11-14)

| Phase | Gate | Scope | Status | Notes |
|---|---|---|---|---|
| P0 | — | Repo audit, baseline freeze | **DONE** | `PHASE0_REPOSITORY_AUDIT.md`, `BASELINE_STATE.json` |
| P1 | G0 | Release provenance | **DONE (BLOCKED_RELEASE)** | `release-provenance/G0_VERDICT.md` — no official release contains fix; source-built env B |
| P2 | G1 | Windows native HIP training primitives matrix | **DONE** | 16-primitive matrix + HIPRTC no-STL regression + 3× independent runs |
| P3 | G2 | Ultralytics task lifecycle (T01–T15 per task × FP32/AMP) | **DONE** | Detect first; other tasks per current-version support check |
| P4 | G3 | AMP root cause analysis | **DONE** | Round-3 anomaly: reproduce → isolate → classify (A/B/C/D) |
| P5 | G4 | Long-run stability, quality, performance | **DONE (third env — audit-corrected)** | Detect ≥30 epochs public dataset; matched A/B only where baseline exists |
| P6 | — | Cross-architecture | partial | gfx1151 local only; gfx1100/gfx1200/Linux = BLOCKED_HARDWARE with runnable tooling |
| P7 | G5 | Upstream tests/CI/docs PR drafts | **DONE (drafts)** | Own-repo only; no upstream action without Owner approval |
| P8 | — | Adversarial review + GO/NO-GO | **DONE** | Three-reviewer audit executed 2026-11-14 evening (`P8_INDEPENDENT_AUDIT.md`); FINAL_REPORT/GO_NO_GO corrected accordingly |

## Environment plan

- **ENV A** `pm13437_official` — pristine official wheel 7.14.1 (**no fix**). Role: pre-fix behavior, EXPECTED_FAIL controls, wheel-reproduction of AMP anomaly.
- **ENV B** `pm13437_merged` — official wheel with **source-built patched MIOpen** (`ed7c67a9…` from f0a5d266) swapped in per leg, restored after. Role: fixed-binary validation. Label: `SOURCE_BUILT_PATCHED`, never "official".
- Every GPU leg: fresh MIOpen cache home (`MIOpen` db path via USERPROFILE redirect), loaded-DLL probe inside the process, machine-readable JSON + raw logs.

## Blocking rules (binding)

- SKIP/NOT_RUN never counted as PASS; GPU tests require GPU provenance (loaded-DLL JSON per run).
- Failures traced to first error; upstream-scope problems produce minimal repro + issue draft, not workarounds.
- All AMD/ROCm/Ultralytics upstream actions = **Owner Action Required**; own-repo pushes allowed.
