# External Evidence — Signature Comparison (Phase 11)

Retrieved 2026-10-07 (UTC+8). Raw snapshots + URLs: `evidence/raw/external/`.

## Local failure vs ROCm/MIOpen #3956

| Field | Local (this RCA) | MIOpen #3956 | Match? |
|---|---|---|---|
| OS | Windows 11 (10.0.26200) native | Windows 11 25H2 | Yes (both native Windows) |
| GPU | Radeon 8060S (iGPU) | Radeon RX 9060 XT (dGPU) | Different models |
| gfx target | gfx1151 | gfx1200 | **Different** |
| Python | 3.13.13 | 3.12.7 | Different |
| PyTorch | 2.12.0+rocm7.14.0 | 2.9.1+rocm7.2.1 | Different builds |
| ROCm | 7.14.0 / HIP 7.14.60850 | 7.2.1 | Different |
| Operation | `nn.BatchNorm2d(16)`, (8,16,64,64), train mode | `nn.BatchNorm2d(100)`, (20,100,35,45) | Same op class, different shapes |
| MIOpen kernel | `MIOpenBatchNormFwdTrainSpatial.cpp` | `MIOpenBatchNormFwdTrainSpatialHIP.cpp` | Near-match (filename differs by `HIP` suffix; consistent with MIOpen source rename across versions) |
| HIPRTC error | `HIPRTC_ERROR_COMPILATION (6)` | `HIPRTC_ERROR_COMPILATION (6)` | **Exact** |
| Missing header | `'type_traits' file not found` at `miopen_type_traits.hpp:151:10` | `'type_traits' file not found` at `miopen_type_traits.hpp:151:10` | **Exact (same header, same line)** |
| Compile layer | hiprtcCompileProgram → comgr temp dir | hiprtcCompileProgram → comgr temp dir | **Exact** |
| Terminal exception | `RuntimeError: miopenStatusUnknownError` | `RuntimeError: miopenStatusUnknownError` | **Exact** |
| Reproduces w/o Ultralytics | Yes (this RCA, Phase 4) | Yes (pure `nn.BatchNorm2d` in issue) | **Exact** |
| Upstream status | — | OPEN, `status: triage`, 0 comments since 2026-04-22 | Unresolved upstream |

**Statement (evidence-qualified):** The local failure has a highly similar —
in the compiler-diagnostic fields an identical — error signature to
MIOpen #3956, and reproduces independently of Ultralytics. It occurs on a
different gfx target (gfx1151 vs gfx1200), different Python (3.13 vs 3.12)
and different ROCm (7.14 vs 7.2.1), which is consistent with a
Windows-wide HIPRTC include-path mechanism rather than a single-version
regression. The exact upstream root cause has not been demonstrated here, so
we do **not** claim "same root cause" — only "same failure signature".

## Local failure vs rocm-libraries #2169 / TheRock #842 / PR #1288

| Field | Local | #2169 (Windows log) | TheRock #842 |
|---|---|---|---|
| Windows HIPRTC `type_traits` signature | Present | **NOT present** — see correction below | n/a (Linux log shows OpenCL path) |
| DPP inline-asm `not a valid operand` | Not observed locally | Reported on Windows AND Ubuntu | Reported (gfx1151) |
| Compile stage reached | Fails at header resolution (`reduction`/`type_traits` chain never reached) | **Compiled past the full include chain**, failed at inline asm in `reduction_functions.hpp:83` | Same DPP stage (OpenCL) |
| Fix | — | Reporter verified TheRock nightly ≥ 20251016 | PR #1288 (merged 2025-10-08) |

**Correction (v2, after independent review):** the #2169 Windows log does
NOT contain the `type_traits` failure (`grep -c type_traits` on the
archived body = 0). Both #2169 logs — Ubuntu (OpenCL `.cl` path) and
Windows (HIPRTC `.cpp` path) — show the **same gfx1151 DPP inline-asm
defect** ("not a valid operand", `v_add_f32 … row_bcast:15 row_mask:0xa`),
fixed by PR #1288. The duplicate closure of #2169 vs TheRock#842 was
therefore sound. #2169 is a *different mechanism* from our failure: same
APU (Ryzen AI MAX+ 395 / 8060S), same op (BatchNorm2d), same HIPRTC layer
on Windows — but a later compile-stage error.

**Why #2169 still matters to our RCA:** its Windows log proves that
TheRock's Oct-2025 Windows build resolved the **entire C++ include chain**
during HIPRTC compilation (the failure occurred deep inside
`reduction_functions.hpp`, well past all `#include`s), while our
ROCm 7.14 rockrel wheels fail at the very first standard header
(`<type_traits>`). The include-resolution behavior therefore differs
across AMD Windows builds — a Phase-2 lead pointing at a build/packaging
difference (H11) rather than an inherent Windows limitation.

## Supporting platform statements

- ROCm 7.14.0 release notes list Ryzen AI Max+ 395 (Radeon 8060S) / gfx1151
  as supported hardware and PyTorch 2.12.0 as supported on Windows — the
  failing configuration is an officially supported combination.
- AMD's Windows PyTorch install documentation states only Python 3.12 and a
  graphics driver as prerequisites; **no Visual Studio / MSVC / C++
  toolchain requirement is documented**, and the wheels do not ship a C++
  standard library (local evidence: no `type_traits` anywhere under the
  ROCm wheel tree; `docs/ENVIRONMENT.md`).
- Ultralytics' AMD guide targets Linux x86_64: "native Windows is not
  supported" — native-Windows ROCm is outside Ultralytics' documented
  matrix, but Phase 4 shows Ultralytics is not needed to reproduce the
  failure, so this does not localize the defect to Ultralytics.

## Related-issue search (2026-10-07)

GitHub search over ROCm/MIOpen, ROCm/rocm-libraries, pytorch/pytorch for
`type_traits` / `BatchNorm HIPRTC` / `windows rocm type_traits` found:

- Direct (same signature): MIOpen#3956 (open, unanswered). rocm-libraries#2169
  and TheRock#842 describe a **different** compile-stage defect (gfx1151 DPP
  inline asm) fixed by PR #1288 — related hardware/op, not our mechanism.
- Loosely related (not same signature): pytorch#169882, rocm-libraries#10563,
  #8847, #9016 — excluded as unrelated after inspection.
