# F-C2-4 Subagent B — CMake/CTest portability & false-PASS audit

Reviewer: fresh-context general-purpose subagent (agent_673234d5), read-only,
scratch fixtures under Temp only.

## VERDICT: PASS (2 MINOR, 4 NIT — MINOR-1 RESOLVED by hardening, MINOR-2 neutralized/limited)

Key confirmations:
- CMake 3.15 floor: all constructs legal (get_filename_component DIRECTORY/ABSOLUTE,
  foreach IN LISTS, list APPEND, imported-target get_target_property, bracket-arg
  CTestTestfile generation round-trips on >=3.0).
- Escaping: empirically proven (scratch fixture) that CTest splits ENVIRONMENT on
  unescaped ';', unescapes '\;' within an entry, silently drops '='-less entries →
  pre-hardening child PATH = <derived dir>;<first inherited entry> only (tail
  dropped) — functionally harmless for this test (no subprocess spawning; loader
  finds System32 independent of PATH) but the comment overstated.
  → RESOLVED on final HEAD d758aed7: string(REPLACE ";" "\;" ...) on the captured
    PATH tail + comment corrected; generated file now shows fully-escaped tail
    (every separator '\;'); clean-env ctest PASS re-verified.
- False-PASS surface unchanged: SKIP_RETURN_CODE only 4; verdict semantics live in
  the test binary; isolation flags from argv not env; CPATH cell re-run → exit 4;
  positive control → 5784-byte object exit 0.
- Selection policy holds: set_tests_properties outside guard; BF16 leg = echo
  skipped + DISABLED + Not Run.
- Linux: no break vector (PATH irrelevant to .so resolution; test execs nothing).
- Degradation safety: multi-config packages without plain IMPORTED_LOCATION,
  plain-hiprtc arm, MODULE-found packages → no PATH entry → exactly R1 ambient-PATH
  behavior; never worse than R1; only direction of change is fail-visible.
- $ENV{PATH} bake-in: defensible (canonical pre-3.22 idiom; ENVIRONMENT_MODIFICATION
  needs 3.22 which violates the 3.15 floor); MINOR-2 (MSYS-mangled configure PATH
  when configured from Git Bash — inert, test disabled in that tree; real build
  configured via sanitized env) noted; the REPLACE hardening keeps the derived dir
  first in all cases.
- Scope: diff e7ff6d75..61410b68 = one file, registration block only; worktree clean.
