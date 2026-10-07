# Phase-3 Gate 79 — Patch vs. Workaround Distinction

Date: 2026-10-07. These four are DISTINCT remedies at DISTINCT layers.
They are not mixed in any single upstream proposal.

| Remedy | Layer | Nature | Status |
|---|---|---|---|
| **MSVC Build Tools install** (VS 2022, C++ workload) | user machine | **practical existing-user remedy** — clang's MSVC auto-discovery provides the STL; zero code/config | validated Phase 2 (3 arms); documented-prerequisite-grade. Not part of any upstream change here. |
| **`ROCM_PATH` + freestanding shim dir** (`patches/shim_stl/`) | user machine (MIOpen `-I` channel) | **diagnostic/user workaround** — no admin, no DLL changes; type_traits-only shim covers the BN closure | validated Phase 2 (cache-isolated); sufficient for BN-class failures only. Not proposed upstream. |
| **MIOpen source patch** (`miopen_hiprtc_freestanding_v2.patch`) | rocm-libraries / MIOpen source | **candidate upstream fix** — restores RTC kernel self-containment via availability-probed freestanding headers | THIS package. Windows-validated (V1+V2 real builds); Linux regression pending. |
| **wheel-bundled STL / include-path config** | TheRock / wheel packaging | **alternative packaging-layer fix** — bundle a std subset (or full STL) for the wheel clang and export it | NOT part of the MIOpen patch; routed separately (Gate 80). TheRock PR #6179 attempted header-parity and was closed unmerged; the need remains. |

The MIOpen patch deliberately does NOT attempt to solve the wheel
packaging gap (no `-I` injection, no bundled headers): it makes the
kernel sources self-contained where no STL exists while preserving
real-STL behavior everywhere else. The wheel gap remains real for OTHER
ROCm components with the same exposure (e.g. any consumer following
hiprtc's real-std design); that is the TheRock routing item.
