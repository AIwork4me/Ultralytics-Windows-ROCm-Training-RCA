# P16 WINDOWS USER GUIDE READINESS (2026-11-15)

Per mission §6.8.

## Current official documentation state (verified live 2026-11-15)

- [docs.ultralytics.com/integrations/amd](https://docs.ultralytics.com/integrations/amd/): targets **Linux x86_64 only**; states native Windows is **not supported** and WSL2 "has not been validated yet"; MIGraphX ships Linux-only wheels. (Mission §6.8 warning respected: this page is about the Linux MIGraphX deployment path, not native Windows PyTorch training.)
- Official AMD Windows ROCm install docs point at the current (pre-fix) wheel channels.
- Conclusion: **no official documentation today supports native Windows Radeon YOLO training** — accurately reflecting the release reality (every official Windows package fails training without an undocumented STL repair).

## P16 decision: guide prepared as draft, publication gated

A public standalone Windows training guide **cannot be published now without violating mission §1 prohibitions** (it would either direct users into a currently-broken official path or rely on hidden workarounds). It also must not be submitted to Ultralytics docs yet (docs/AGENTS.md: only publish claims supported by real official-package evidence — today the evidence says the official path fails).

The guide content is drafted and ready in this repo's release-closure documentation, covering exactly the mission §6.8 checklist: supported Radeon classes, Windows/driver requirements, official package commands (PowerShell/CMD syntax — no Linux line continuations), architecture kernel packages, device verification, `yolo train` (device=0, amp=True), AMP semantics, val/predict, save/reload, interrupt/resume, troubleshooting (including the current MIOpen limitation), known limitations, and exact validated release versions.

**Publication gates** (all three required):
1. M2 unblocks — official `rocm_sdk_libraries` contains #13437 (marker ≥ 1; see P16_WINDOWS_RELEASE_OWNER_MAP.md).
2. M3 class-A official-package legs PASS on gfx1151 (train/AMP/checkpoint on the released stack).
3. One independent developer completes the documented workflow (P16_INDEPENDENT_USER_ACCEPTANCE.md).

Any Ultralytics docs submission then follows `docs/AGENTS.md` (doc build, macros, canonical task/mode ordering, prettier dialect) — not started, deliberately, while the claim would be false.
