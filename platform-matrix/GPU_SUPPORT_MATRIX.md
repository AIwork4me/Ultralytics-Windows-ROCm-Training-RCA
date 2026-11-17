# GPU SUPPORT MATRIX — cross-architecture status

Date: 2026-11-14 · Rule: a family is only claimed for what was actually executed on that hardware.

| Family | Machine | Driver | Wheel stack | MIOpen | G1 primitives | G2 lifecycle | AMP | Status |
|---|---|---|---|---|---|---|---|---|
| **gfx1151** (Radeon 8060S / Strix Halo) | local workstation (P0 target) | 32.0.22032.6002 | torch 2.12.0+rocm7.14.1 official | wheel `e97891df` (no fix) + source-built `ed7c67a9` (f0a5d266) | **PASS** (16/16 ×3 STL + ×3 no-STL) | **PASS** (7 tasks 14/14) | works on official wheel; cache-state-dependent precheck on source-built | **VALIDATED** |
| gfx1100 (RX 7900 XTX / W7900) | not connected | — | — | — | BLOCKED_HARDWARE | BLOCKED_HARDWARE | BLOCKED_HARDWARE | runnable tooling delivered (`windows-training-validation/`), no results claimed |
| gfx1200 (RDNA4) | not connected | — | — | — | BLOCKED_HARDWARE | BLOCKED_HARDWARE | BLOCKED_HARDWARE | same |
| Linux gfx1100 reference (W7900) | not connected | — | — | — | BLOCKED_HARDWARE | BLOCKED_HARDWARE | BLOCKED_HARDWARE | Linux regression scope of the fix: source-level no-STL change is inert when host STL visible (verified historically at source level; no Linux GPU run claimed) |

Per-machine pages: `WINDOWS_GFX1151.md` (filled), `WINDOWS_GFX1100.md` / `WINDOWS_GFX1200.md` / `LINUX_W7900.md` (templates with the exact commands to run when hardware is available).

## Hard rules applied

- No result from one GPU family may be presented as another family's PASS.
- Architecture coverage override (HSA_OVERRIDE_GFX_VERSION etc.) was **not** used to fake compatibility.
- Every executed leg carries an in-process loaded-DLL probe (sha256 recorded) — "GPU test without GPU provenance" is impossible by construction in this repo's harnesses.
