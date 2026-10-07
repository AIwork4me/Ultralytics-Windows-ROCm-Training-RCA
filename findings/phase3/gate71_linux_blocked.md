# Phase-3 Gates 71-74 — Linux Regression: BLOCKED (record)

Date: 2026-10-07.

**BLOCKED — no Linux ROCm GPU environment available.**

- This investigation runs on a native Windows 11 workstation
  (Radeon 8060S / gfx1151). No Linux machine with an AMD GPU is
  attached, and no cloud/Linux-ROCm credentials or endpoints were
  provisioned for this engagement.
- Per the Phase-3 brief, no PR-readiness claim is made; Linux HIP>=7
  regression runs (Gates 72-74: patched build, RTC tests incl. the
  freestanding arms' complement — the real-STL arm — and numerics)
  remain a precondition for merge.
- Exact Linux CI requirements are recorded by Gate-83 Reviewer D
  (findings/phase3/reviewer_pr_readiness.md, "What Linux CI must show"):
  cold-cache suite A/B vs unpatched develop, probe-branch confirmation
  in compile logs, the compile-only no-STL test both arms, a legacy
  HIP<7 shim-arm compile check if such a lane exists, no perf lane.
- Analytical risk position (PATCH_DESIGN.md Design D): on Linux the
  probe evaluates true (system STL reachable) → wrappers byte-identical
  to current develop behavior; the freestanding arm activates only
  where compilation previously always failed.
