# H10 Reviewer B — GPU runtime engineer

VERDICT: PASS
BLOCKERS: none. MAJORS: none.
Reviewer wrote TWO independent probe programs from scratch (a dlsym/dladdr
FP32-kthvalue probe and a minimal hiprtc STL probe linking wheel
libhiprtc.so.7), rebuilt the batchnorm harness from source, re-hashed all
15 A/B dumps (15/15 identical), strings-extracted per-leg ukdb entries
(MIOpenKthvalue.cpp.o -mcpu=gfx1151 FP32/FP16; MIOPEN_USE_BFP16=1
IN_OUT_TYPE=ushort for the BF16 legs), hit the dimSize>=300 solver gate
personally (64-wide case -> No solver found — proving case shapes were not
cherry-picked), and verified: gfx1151 identity; wheel libamdhip64 sha
6f3c9fe6 (vs /opt/rocm-7.2.1 0bfd6cb0 and distro .so.5 32b6be1d — full
system inventory); identical NEEDED sets and $ORIGIN-only RUNPATH both
legs; per-log dladdr bindings; fresh-cache Database-created/SaveBinary
sequences; exit-4 INCONCLUSIVE mechanism from source; margins recomputed
(26.6x/43.4x/154.6x/37.5x/3.8e7x/1.86e4x — "26x-3.8e7x" accurate).
MINORS: ldconfig maps amdhip to 7.2.1 (wrapper LD_LIBRARY_PATH is the
tripwire — preserve exactly on re-runs); public-header miopen.h:6455
tag-only struct (pre-existing upstream, not R2); BF16 probe lacked a
checked-in runner (ADDED post-panel: scripts/h07_bf16_run.sh); H05 RTC
proof indirect at LOG_LEVEL=5 (ukdb contents close the gap); harness
compile commands not recorded (noted for future gates).
