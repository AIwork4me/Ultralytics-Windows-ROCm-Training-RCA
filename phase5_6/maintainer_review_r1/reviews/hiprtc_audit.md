# Reviewer B — HIPRTC/GoogleTest/CTest audit (G11), 2026-10-12
Audited: the test source, MIOpen production path sources, and the run logs.

VERDICT: GO WITH NITS (0 blockers)

Verified in depth:
- Isolation fidelity: probe TU runs the identical option pipeline as the
  BatchNorm TU (same BuildHip path, same auto-added defines), so probe
  reachability covers the gated headers; all residual misclassification
  scenarios are conservative (fail red or honest skip).
- Control fidelity from logs: same code path/args modulo the isolation
  flag; unpatched leg shows HIPRTC_ERROR_COMPILATION with the single
  'type_traits' diagnostic; with-STL control passed on BOTH legs →
  failure is STL-specific; identical arch/HIPRTC/args strings.
- Tri-state walk: no path reaches the main check when P1 failed; no path
  skips when P1 succeeded; inconsistent probes fail-closed.
- DLL identity: build-tree MIOpen.dll bound; cache-dir version strings
  tie each leg to its tree (3.6.2.64214f24 / 3.6.2.54b079ca).
- Cache false-PASS: defeated twice (kern_db args-keyed SELECT misses;
  program_map (name,params)-keyed with nonce); nonce collision
  practically impossible; negative leg recompiled rather than reusing.
- Cost 13-16s (5 RTC compiles); ctest green run reproduced (Test #111,
  13.51s).

MAJOR findings and their resolution:
1. Windows ctest PATH fragility + missing green ctest evidence →
   RESOLVED: green ctest run produced on the final commit
   (logs/final_ctest2.log: Test #111 Passed, 100%); the PATH requirement
   is a property of ALL gtest binaries that link MIOpen on Windows
   (upstream CI runs against system ROCm installs where the runtime DLLs
   are on PATH); the deleted standalone-only PATH wiring existed because
   that binary linked hiprtc directly outside the MIOpen runtime.
2. Category misfiling (CPU_ needs GPU, ~14s, in quick tier whose comment
   promises no-GPU/fast) → documented accepted deviation, identical to
   the maintainer's own CPU_MiopenCstdintLP64_NONE precedent; surfaced
   in the review reply (GPU-required trade).
3. Evidence-vs-commit drift (pre-rewrite line numbers, throwaway
   harnesses) → RESOLVED: final_run3.log + final_ctest2.log produced on
   the final commit content; throwaway harnesses (G06 forced-skip,
   G14 Kthvalue probe) were mission-mandated disposable prototypes and
   are documented as such.

MINORs documented: single-closure coverage (BN→miopen_type_traits),
Linux skip path unexercised on real Linux, nonce rows in user kern_db
for manual runs, ctest-level skip visibility via XML, ~14s per tier leg.
