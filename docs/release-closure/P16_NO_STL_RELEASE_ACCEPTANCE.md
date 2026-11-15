# P16 NO-STL RELEASE ACCEPTANCE (2026-11-15)

Per mission §5.3: LEG A (historical official PRE-FIX package) / LEG B (newest official candidate) / LEG C (corrected engineering reference) on Windows without host MSVC STL compensating for missing HIPRTC freestanding headers.

## P16 decision: evidence carry-forward, no redundant re-run

The no-STL acceptance legs were executed in P14/P15 with full controls (per-leg USERPROFILE cache isolation, `VCToolsInstallDir → empty directory` no-STL technique, same GPU same session, raw logs archived). P16 re-verified the artifacts those legs ran against are **byte-identical today** (see P16_OFFICIAL_WHEEL_BINARY_AUDIT.md):

- LEG B target `rocm_sdk_libraries-10.1.0` wheel: SHA256 today == P15 audit copy (`0c34bafb…`).
- Embedded MIOpen.dll today: SHA256 `266d716b…`, marker `miopen_initializer_list` = 0 — the exact binary LEG B failed on.

Re-running the legs against byte-identical binaries would re-produce the already-archived signatures without new information, so no new GPU hours were spent; the P16 acceptance therefore references the preserved legs:

| Leg | Binary | no-STL BatchNorm forward+backward | Raw evidence |
|-----|--------|-----------------------------------|--------------|
| A | official whl-multi-arch torch-2.12.0+rocm7.14.1 (MIOpen 3.5.2.cd957402, marker 0) | **FAIL** — HIPRTC `type_traits` compile failure, identical to MIOpen issue #3956 signature | P14/P15 archived logs (`p14_wheel_audit`, `golden_path_p14`) |
| B | official whl-next rocm_sdk_libraries-10.1.0 + torch-2.14.0+rocm10.1.0 (MIOpen 3.6.1.39d8d603, marker 0) | **FAIL** — same signature | P14/P15 archived logs |
| C | engineering reference, merged-source MIOpen 3.6.2.f0a5d266 (marker 2) | **PASS** — finite gradients, optimizer steps | P14/P15 archived logs (`pm13437_merged` env) |

## Verdict

**BLOCKED_RELEASE.** No official package contains the fix (marker 0 everywhere official; no post-2026-10-19 release cut exists). M2 PASS conditions (official wheel contains #13437 → no-STL regression PASS → real GPU YOLO train/AMP → checkpoint recovery on the official package) cannot be met until AMD/TheRock publish a post-fix `rocm_sdk_libraries`. The moment one ships, the standing P14/P15 harness re-runs LEG B verbatim; the whl-next torch 2.13.0/2.14.0 stack is already proven to perform real GPU compute on gfx1151 (P14), so it becomes the ordinary user path immediately.
