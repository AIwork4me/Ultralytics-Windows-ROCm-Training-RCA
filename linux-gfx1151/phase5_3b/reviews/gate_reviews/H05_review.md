# H05 independent audit — kthvalue runtime A/B

VERDICT: PASS. BLOCKERS: none. MAJORS: none.
Reviewer re-ran BOTH legs with the wrapper discipline (fresh /tmp caches,
LD_PRELOAD per leg, wheel LD_LIBRARY_PATH): legA exit 0, legB exit 0, 3/3
cases each with 0 value/index mismatches. Reviewer's own fresh dumps:
byte-identical to the recorded evidence dumps and across legs (15/15 files
per comparison). Harness readelf: zero link-time ROCm deps (dlsym-based);
exit-code semantics verified from source (exact-== vs CPU reference, both
values and indices; zero-init outputs preclude stale-memory false PASS).
No fallback markers; no /opt/rocm or libamdhip64.so.5 anywhere; CK warning
symmetric. Minors adopted: finiteness implicit via exact equality; the
"Loading binary" grep never fires at LOG_LEVEL=5 (RTC proof = HIPRTC v.9.0
line + fresh ukdb + comgr llvmcache) — wording updated in evidence JSON.
