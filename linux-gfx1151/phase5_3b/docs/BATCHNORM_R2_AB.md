# BatchNorm R2 A/B on Linux gfx1151 (Gate H06)

Direct public API (dlsym + dladdr -> correct leg library): forward
training + backward, N=8 C=16 H=64 W=64 FP32, miopenBNSpatial, eps=1e-5,
expAvgFactor=0.1; deterministic inputs; CPU float64 full-gradient
reference; PREDECLARED constexpr tolerances (never adjusted; auditor
rebuilt the harness from source to confirm).

| Check | legA = legB | Tolerance |
|---|---|---|
| y | 3.752e-07 | 1e-5 |
| dx | 2.303e-07 | 1e-5 |
| dw | 6.470e-07 | 1e-4 |
| db | 2.668e-07 | 1e-5 |
| running mean | 2.624e-12 | 1e-4 |
| running variance (rel) | 5.377e-08 | 1e-3 |

All finite; nontrivial running-stat updates (max|rv-1|=0.0999). Dispatch
proven: MIOpenBatchNormFwdTrainSpatial / BwdSpatial invokers with
`-mcpu=gfx1151` and `MIO_BN_GFX115X=1`; kernels RTC-compiled and SELECTed
from per-leg fresh kern_db. Values identical to the W7900 run because the
harness and inputs are deterministic and both platforms run the same wheel
HIP line — observed, not assumed. NO no-STL regression reproduction claim
is made from this gate.
