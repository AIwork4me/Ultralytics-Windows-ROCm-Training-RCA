# H07 independent audit — targeted coverage / false-coverage

VERDICT: PASS. BLOCKERS: none. MAJORS: none.
Reviewer re-ran the canary suite (6/6 arms PASS, fresh comgr temp dirs prove
real RTC), rebuilt the BF16 probe from source and re-ran BOTH legs (exit 0,
PASS, KthvalueFwd + HIPRTC v.9.0, correct per-leg dladdr), independently
recomputed the deterministic LCG permutation in Python (slice0 expected k-th
16912 @ idx 257 — matches probe CPU ref AND GPU), verified all 300 values
distinct + BF16-exact, verified solver dimSize>=300 threshold and
-D MIOPEN_USE_BFP16=1/-DIN_OUT_TYPE=ushort construction, verified legA/legB
hashes and version strings differ (genuine A/B), verified the E1/E2 guard
design in source, and confirmed the zero-STL chain genuinely resolves the
three freestanding headers with a no-std negative control. No spoofing, no
false coverage, debug iterations disclosed as harness defects.

MINORS (adopted): stale probe header comment fixed; priorities line
clarified (radix int32/int64 KEY-encode arms are static/compile-level only;
runtime int64 evidence is the 64-bit index output); static asserts verify
the equivalence precondition while E4 RTC-compiles the changed TU.
