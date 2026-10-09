# HIPRTC STL Isolation — Phase 5.2 (Gate B06)

Probe: `phase5_2/scripts/b06_stl_isolation_probe.cpp` (binary
`build/kthvalue-harness/b06_probe`). The four `__has_include` values are
computed BY RTC kernels ON the W7900 and read back from GPU memory; every
mode also compiles AND launches an ordinary axpy control kernel under the
same flags. Provenance printed per run via dladdr (libhiprtc, libamdhip64).

## Measurement matrix — ROCm 7.14.1 wheel SDK (validation environment)

| Flags | type_traits | utility | limits | initializer_list | control kernel |
|---|---|---|---|---|---|
| default | 1 | 1 | 1 | 1 | COMPILED+RAN |
| `-nostdinc++` | 1 | **0** | 1 | 1 | COMPILED+RAN |
| `-nostdinc` | 1 | **0** | 1 | 1 | COMPILED+RAN |
| `-nostdinc++ -nobuiltininc` | 1 | 0 | 1 | 1 | COMPILED+RAN |
| `-nostdinc -nobuiltininc` | 1 | 0 | 1 | 1 | COMPILED+RAN |
| `-nostdinc -nobuiltininc --sysroot=/nonexistent` | 1 | 0 | 1 | 1 | COMPILED+RAN |

Diagnostic comparison (NOT part of the validation environment): system ROCm
7.2.1 hiprtc under the same probe yields full isolation `[0,0,0,0]` with
`-nostdinc++`/`-nostdinc` — a documented toolchain behavioral difference;
the two-stack discipline forbids using 7.2.1 for validation.

## Why flags cannot remove the remaining headers (mechanism)

`libhiprtc-builtins.so.7` (7.14.1 wheel) EMBEDS a HIP-specific C++ header
subset (`strings` evidence: `__hip_internal` `numeric_limits` templates,
`#include <type_traits>` etc.). hipRTC registers these on the RTC include
search path outside the clang driver's standard/builtin include machinery,
so `-nostdinc`/`-nostdinc++`/`-nobuiltininc`/`--sysroot` do not affect
them. `<utility>` is not provided by the embedded set, hence its
disappearance with the libc++ system dir.

## Environment classification (mission B06 rubric)

* **A — Full-STL environment**: REPRODUCIBLE (default row).
* **B — Partial-STL environment**: REPRODUCIBLE (`-nostdinc++`:
  type_traits=1, utility=0, limits=1, initializer_list=1). This is exactly
  the patch's inconsistent-availability guard scenario (one wrapper header
  reachable, the other not).
* **C — Complete no-STL environment**: **INCONCLUSIVE** on ROCm 7.14.1
  Linux hiprtc. No tested flag combination makes all four
  `__has_include == 0` while ordinary kernels keep compiling. The
  adversarial auditor additionally tested (all ineffective or unusable):
  VFS overlays (accepted but bypassed via randomized comgr include dirs),
  add-only include flags, single-string option parsing, explicit
  headerSources registration, `AMD_OCL_BUILD_OPTIONS(_APPEND)` (honored but
  breaks device linking in every mode), `--rocm-path` to a nonexistent dir
  (breaks device libs), `-x c`/`-stdlib`/`-isysroot`. Windows retains the
  direct no-STL regression evidence (`nostl_runtime: PASS` in the freeze
  manifest).
* **D — Unusable config**: none observed (every combination kept the
  control kernel working).

## False-PASS safeguards

* The only `[0,0,0,0]`+control-OK configuration found by the auditor was a
  `-D__has_include(x)=0` **spoof** — disproved as isolation by compiling
  and RUNNING a real `#include <limits>` kernel under it
  (`numeric_limits<float>::max()` = 3.40282e+38 computed on GPU).
  Consequence: the final-validation runbook forbids `-D__has_include`
  overrides in RTC options (MIOpen constructs its own option list, so this
  is not exploitable in the planned A/B).
* Patch 0003's own isolation probe (rejects isolated mode if ANY of the
  four headers is reachable) means the Linux `--mode=negative` outcome will
  be an honest ISOLATION-INSUFFICIENT diagnostic rather than the Windows
  `'type_traits' file not found` signature. This must be stated in the next
  mission's expectations; positive/ordinary modes are unaffected.

## Logs

* `phase5_2/logs/B06_stl_isolation_probe.log` (7.14.1 validation env)
* `phase5_2/logs/B06_stl_probe_system721_diagnostic.log` (7.2.1 diagnostic)
