# P16 TWO-GPU WINDOWS MATRIX (2026-11-15)

Per mission §6.1–6.3. Hardware frozen before testing; support matrix recorded with citations.

## Architecture class A — Radeon 8060S / gfx1151 (Ryzen AI MAX+)

| Item | Value |
|------|-------|
| GPU | AMD Radeon(TM) 8060S Graphics (gfx1151 iGPU) |
| Driver | 32.0.22032.6002, dated 2025-12-15 |
| Windows | Windows 11 build 26200 |
| Official packages tested (P14/P15, re-verified byte-identical today) | whl-multi-arch `torch-2.12.0+rocm7.14.1`; whl-next `torch-2.13.0/2.14.0+rocm10.1.0` + `rocm_sdk_*-10.1.0` |
| Real GPU compute on official torch 2.13.0/2.14.0 stack | PASS (P14) — installs, `torch.version.hip=7.16.26385`, finite GPU tensor math |
| Official-package YOLO training / AMP / checkpoint legs | **BLOCKED_RELEASE** — every official package ships pre-#13437 MIOpen (marker 0); no-STL BatchNorm FAIL (LEG A/B); training without the undocumented host STL repair is impossible |
| Engineering-reference legs (merged-source MIOpen 3.6.2.f0a5d266, `pm13437_merged`) | PASS per the frozen P15 contract: AMP fp16 proof, 30-epoch training 0.4927→0.5980, hard-kill→resume, val 0.5949, honest-AMP contract — evidence frozen in P15 reports; explicitly **not** user-facing acceptance (mission prohibition: no source-built packages in end-user acceptance) |
| P16 spot re-validation | `test_cuda.py::test_amp` (upstream PR branch) executing on this host at P16 time — see M1 evidence; gfx1151 upstream-PR regression tests 2/2 PASS |

## Architecture class B — RDNA3 discrete (preferred: RX 7900 XTX / gfx1100)

**BLOCKED_HARDWARE.** No second Radeon architecture class is connected to this host (`torch.cuda.device_count()` = 1; only the gfx1151 iGPU enumerates). Per mission §6.1, two devices of the same architecture do not count, and Linux W7900 validation does not substitute for Windows gfx1100. No M3 class-B legs were fabricated.

## Verdicts

- Class A hardware: present; official-release user path: **BLOCKED_RELEASE** (inherits M2).
- Class B: **BLOCKED_HARDWARE** — owner: user/hardware procurement; test plan ready in `platform-matrix/*` templates.
- M3 milestone: **NOT_MET** with precise blockers (release chain + second GPU class + independent tester).
