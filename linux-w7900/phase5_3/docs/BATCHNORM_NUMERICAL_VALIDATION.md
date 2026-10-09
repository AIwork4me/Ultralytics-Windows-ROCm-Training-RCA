# BATCHNORM NUMERICAL VALIDATION — Direct Public API (Leg A + Leg B)

## Harness

New direct-API harness (`scripts/batchnorm_harness.cpp`): calls
`miopenBatchNormalizationForwardTraining` and `miopenBatchNormalizationBackward` via
dlsym with dladdr provenance; deterministic xorshift64* inputs; CPU **float64
full-gradient** reference; predeclared tolerances as compile-time constants — never
adjusted. Development iterations (derived BN descriptor, float alpha ABI, full-gradient
reference, NCHW strided indexing, input scaling per MIOpen's own gtest convention) were
harness-defect fixes, all disclosed; tolerances unchanged throughout. Final binary
`a8c4a141…`; both legs ran the same final binary; the Gate-L09 reviewer independently
recompiled and re-ran it.

## Workload

N=8 C=16 H=64 W=64 FP32, miopenBNSpatial, eps=1e-5, expAvgFactor=0.1,
running stats initialized (0, 1). GPU synchronization after forward and after backward;
finite checks on all outputs; zero-initialized gradient accumulators.

## Results (identical on both legs; margins 4–6 orders below tolerance)

| Check | Measured | Predeclared tolerance |
|---|---|---|
| y (fwd output) | 3.752e-7 abs | 1e-5 |
| dx (input grads) | 2.303e-7 abs | 1e-5 |
| dw (weight grads) | 6.470e-7 abs | 1e-4 |
| db (bias grads) | 2.668e-7 abs | 1e-5 |
| running mean | 2.624e-12 abs | 1e-4 |
| running variance | 5.377e-8 rel | 1e-3 |

Nontrivial running-stat updates confirmed (max |rv−1| = 0.1, consistent with
expAvgFactor semantics). Dispatch proven: `PrepareInvoker MIOpenBatchNormFwdTrainSpatial`
and `MIOpenBatchNormBwdSpatial` plus kernel run lines in both logs; fresh per-leg caches
(kern_db-miss/Prefetch-unreadable lines).

## Interpretation

R2 introduces no BatchNorm regression for this workload. This is a Linux HIPRTC gfx1100
validation — NOT a Windows no-STL runtime reproduction.
