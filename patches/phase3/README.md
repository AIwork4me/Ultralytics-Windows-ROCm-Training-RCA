# Phase-3 patch artifacts

FINAL (post Gate-84 review fixes, round-trip validated against the
validated V3 build tree — all 8 files byte-identical):

- `0001-miopen-hiprtc-selfcontained.patch` — defect fix: availability-
  probed freestanding <type_traits>/<utility> (wrappers + 2 new headers +
  embed-list entries). Commit message + DCO placeholder inside; AUTHOR
  identity and sign-off must be filled by the submitter.
- `0002-miopen-hiprtc-selfcontained.patch` — residual coverage: radix.hpp
  builtin limits + miopen_cstdint routing, tensor_view.hpp initializer_list
  probe, freestanding initializer_list header + embed entry.
- `proposed_ci_test/hiprtc_selfcontained.cpp` — proposed CI test
  (compile-only, no GPU; negative-control capable).

SUPERSEDED (kept as history; do not submit):
- `miopen_hiprtc_freestanding_v2.patch` — single-commit V2 (pre-review:
  EOL churn, radix numeric_limits defect found by reviewer B, AMD
  copyright attribution, no partial-STL guard).
- `candidate_v1.diff` — first candidate (wrappers only).

Source of truth for the validated state: the working tree at
`C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase3` (develop b68f8944 +
0001 + 0002), built as MIOpen.dll SHA256 9fa28af5d3b9…
