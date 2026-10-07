# Phase-2 Next Steps (for human/ChatGPT review before any upstream action)

Nothing here has been executed against upstream. All items are
recommendations pending review of this evidence package.

1. **Human review of the decision package**
   (`findings/phase2/phase2_conclusion.json`, `final_gate.md`,
   `docs/PHASE2_LEVEL3_RCA.md`, and the four independent reviews under
   `findings/phase2/subagent_*`).

2. **If pursuing the MIOpen source fix (recommended primary):**
   - Rebase `patches/candidate_B_miopen_type_traits.patch` onto
     rocm-libraries develop; extend the same treatment to
     `miopen_utility.hpp` (its shim is intact but window-gated the same
     way) and audit `miopen_limits.hpp`/`miopen_cstdint.hpp`.
   - Add CI: a Windows HIPRTC no-STL compile test of the BN closure
     (this repo's `scripts/phase2/hiprtc_probe/` is a template) plus
     Linux HIP≥7 regression (ensure removing real-`<type_traits>` in RTC
     mode does not break Linux, where the shim was already dead code
     post-#3803).
   - Cover non-BN std-using RTC kernels (functional*.hpp consumers:
     `<utility>`/`<limits>`) — same pattern, wider shim set.

3. **If pursuing the wheel-packaging fix:** propose to TheRock that
   Windows wheel layouts include a freestanding C++ std-subset for the
   bundled clang and export it through the existing `-I$ROCM_PATH/include`
   hook (honored today — poisoned-header proof).

4. **Interim doc fix (cheapest):** AMD ROCm Windows-install docs should
   state that MIOpen runtime-compiled operators (spatial BatchNorm without
   fused inference) currently require MSVC C++ Build Tools on the machine.

5. **External corroboration (optional):** comment on MIOpen #3956 with a
   pointer to this repository (needs human approval; the issue has been
   unanswered since 2026-04-22 and this package likely closes it).

6. **Verify on the next ROCm release** whether the defect persists
   (prediction: yes for any HIP ≥ 7.x rockrel Windows wheel without MSVC).

## Machine-state changes made during Phase 2 (for the record)

- Created/populated conda env `yolo_amd` (Python 3.13.16 + curated clone).
- Installed VS 2022 Build Tools (VCTools workload) to `C:\BuildTools`
  (MSVC 14.44.35207 + WinSDK 10.0.26100.0) — deliberately retained as the
  validated remedy state.
- `C:\hiprtc_poison\include\type_traits` (experiment marker, inert) and
  pip-installed `pyparsing/python-dateutil/six` into yolo_amd.
- MIOpen.dll was binary-patched for one experiment and **restored +
  SHA256-verified** (`74b4ee03…`); the MIOpen user kernel DB gained
  successful BN entries from the passing runs.
- No ROCm/PyTorch/Ultralytics component was upgraded, modified
  (permanently), or removed.
