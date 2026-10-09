# Kthvalue R2 A/B on Linux gfx1151 (Gate H05)

Dispatch chain proven per run: `miopenKthvalueForward` (dladdr ->
installs/leg{A,B}/lib/libMIOpen.so.1) -> `KthvalueFwd` solver
(FindSolutionImpl) -> `MIOpenKthvalue.cpp` RTC (HIPRTC v.9.0, fresh
per-leg cache; gfx1151_20.ukdb created from empty; comgr llvmcache
populated) -> GPU. hipMalloc resolved from the wheel libamdhip64.so.7.

Cases (same Phase-3 harness binary 4d77a96f… on both legs; deterministic
pairwise-distinct inputs; CPU reference with unique per-slice answers):
FP32 [100,500] k=10 dim=-1; FP32 [10,20,300] k=137 dim=2 keepDim;
FP16 [8,3,10,2000] k=2000 dim=-1 keepDim.

Results: legA exit 0 (3/3, 0 value/index mismatches); legB exit 0 (3/3);
all 15 dump files byte-identical between legs. Independent auditor re-ran
both legs with fresh /tmp caches — identical dumps again (evidence/
h05_kthvalue/, logs in leg{A,B}/run.log). No fallback markers; CK-plugin
warning symmetric (CK=OFF config).
