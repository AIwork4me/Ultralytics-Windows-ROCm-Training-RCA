# Targeted coverage hardening (Gate H07) — beyond W7900

Risk-ranked additions (evidence/coverage_matrix.json):

1. RTC canaries from the ACTUAL frozen trees (scripts/h07_rtc_canaries.py,
   Phase-3 tool adapted): legA partial-STL FAILS with 'utility not found'
   (the Windows failure class reproduced through real comgr RTC on
   gfx1151 Linux); legB's designed guard fires cleanly. tensor_view /
   radix / MIOpenKthvalue TU RTC-compile from both trees; freestanding
   initializer_list chain compiles zero-STL offline; radix int32/int64
   equivalence static asserts.
2. BF16 kthvalue RUNTIME (new; closes W7900 gap M2): [100x300] k=10 dim=-1
   keepDim=false, miopenBFloat16 + miopenInt64 indices, 300 distinct
   exactly-BF16-representable integers per slice; KthvalueFwd dispatched,
   HIPRTC-compiled from fresh caches; PASS on BOTH legs with 0 value/index
   mismatches vs exact CPU sort. Solver precondition verified in source
   (dimSize>=300, dimStride==1, dimNum>=2); BF16 arm builds with
   -DMIOPEN_USE_BFP16=1 -DIN_OUT_TYPE=ushort.
3. Radix int32/int64 KEY-encode arms: static-assert + compile-level only
   (documented limitation; runtime covered for FP32/FP16/BF16 encode arms
   and 64-bit index outputs).

Explicitly NOT pursued: PReLU/ReduceSum kernel closures (not touched by
R2; no R2-specific risk reduction within the mission's 1-3 test budget).
Probe development iterations are disclosed in the evidence JSON
(harness-defect fixes, none MIOpen-side).
