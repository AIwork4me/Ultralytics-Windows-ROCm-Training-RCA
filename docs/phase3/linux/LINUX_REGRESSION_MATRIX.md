# Linux Regression Matrix — Gate L40

Date: 2026-10-08. All "unpatched"/"patched" columns are SOURCE-BUILT MIOpen
from the SAME commit b68f8944300f104875d953fc8e4510908c9aaf0b, the only
difference being the handoff patch P3-FINAL-R3 (0001 f06d7ae5 + 0002 77f9fc16),
loaded via LD_PRELOAD with dladdr(miopenCreate) provenance per run, fresh
isolated MIOpen caches per matrix. Wheel column = shipped wheel stack
(baseline run 1).

| Test | Wheel (run 1) | Linux unpatched | Linux patched | Regression? |
|---|---|---|---|---|
| standalone HIPRTC header matrix | PASS 6/6 + GPU exec | n/a (source-level canaries instead) | n/a (same) | — |
| no-STL canary (L33: A equivalence / C fallback / D GPU) | — | — | PASS / PASS / PASS | NO |
| BN2d train (minimal / #3956 / yololike) | PASS | PASS (fresh cache, RTC-compile proof) | PASS (fresh cache) | NO |
| BN2d eval | PASS | PASS | PASS | NO |
| BN2d backward | PASS | PASS | PASS | NO |
| BN1d 3D (spatial) | PASS | PASS | PASS | NO |
| BN1d 2D control | PASS | PASS | PASS | NO |
| BN3d + backward | PASS | PASS | PASS | NO |
| GroupNorm control | PASS | PASS | PASS | NO |
| numerics (y/grads/running stats, 6 cases) | — | bit-identical to patched | bit-identical to unpatched (overall max_abs = 0.0) | NO |
| non-BN RTC matrix (g68 mirror, 11 ops) | — | 11/11 PASS | 11/11 PASS | NO |
| YOLO predict (bus.jpg) | PASS (wheel) | not run (see note) | PASS (exit 0, bound to patched) | NO* |
| YOLO train coco8 (amp default†) | PASS (wheel) | not run (see note) | PASS (exit 0, epoch+val+best/last.pt) | NO* |
| YOLO train coco8 (amp=False) | — | — | PASS (exit 0) | NO |

\* YOLO unpatched column is the WHEEL-stack baseline (MIOpen 3.5.2), not
the source-unpatched build — an integration smoke across two variables
(MIOpen version + patch), not a single-variable A/B; the single-variable
proof is the BN/numerics/non-BN source-build matrix above it.
† amp-default self-disabled AMP after its network-flaky asset download
(manual fp16 controls pass; amp=False leg ran true fp32 — same behavior
on baseline and patched runs).

## Verdict

```text
UNPATCHED PASS → PATCHED PASS on every workload; numerics bit-identical.
```

No Linux regression detected. The with-STL preprocessed-output equivalence
(L33 arm A) explains why: on Linux `__has_include(<type_traits>)` is true in
RTC, so the patched wrappers select the real headers exactly as develop
does — token-identical preprocessing, identical kernels, identical numbers.
