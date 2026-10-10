# PR #13437 Rename Follow-up — Independent Final Review

- Date: 2026-10-10
- Reviewer: independent subagent, ROCm/MIOpen CI Maintainer persona (fresh context; read-only)
- Subject: staged rename patch, later committed as 806f7e90 on fix/miopen-hiprtc-no-host-stl

## Verdict: PASS — 0 BLOCKER, 0 MAJOR, 1 MINOR (informational)

## Checklist summary

- **A. Filename convention** — PASS. `test_hiprtc_selfcontained.cpp` matches the bot's `test_*` basename pattern.
- **B. Source blob identity** — PASS. Index blob `aef56d68…` identical to the pre-rename committed blob; 100% similarity rename, numstat `0 0`.
- **C. Minimal CMake change** — PASS. Exactly two hunks: exclusion key (467) + add_executable source (510); target name, CTest registration, hiprtc linkage, arch detection, WIN32 DLL PATH logic, SKIP_RETURN_CODE 4, skip policy all untouched; `git status --porcelain` shows only the two intended entries.
- **D. Glob-collision reasoning** — PASS, verified from source: `file(GLOB TEST_SOURCES *.cpp)` (line 436), exclusion loop keyed on `test_<basename>` (472–479), `add_test_executable(test_${BASE_NAME} …)` (486–489), command built without the kernels-dir argument (373, 328). Without the exclusion-key fix, the renamed file would register a CI-breaking duplicate `test_test_hiprtc_selfcontained`. Exactly one `*.cpp` in the directory starts with `test_` — the renamed file — so the key collides with nothing.
- **E. Windows validation evidence** — PASS. Configure/build exit 0; discovery `Total Tests: 1` (phantom absent); ctest `Passed`, not Skipped (zero "Skipped" matches across logs); bare-env run proves hiprtc DLL resolution comes solely from the CMake ENVIRONMENT prepend; controls ordinary (exit 0, 3824-byte object) and with-stl (exit 0, 5784-byte object); direct positive `5784-byte code object`; all three code-object sizes match the round-2 validated run exactly; exe sha256 `729bd774…` differs from round 2 only by embedded debug paths.
- **F. No unintended changes** — PASS. `git diff --cached HEAD --stat` = exactly 2 files.
- **G. Frozen evidence untouched** — PASS. `logs/ci/` mtimes predate the `logs/ci_rename/` run; separate directory.
- **H. No false PASS / unsupported claims** — PASS. Every claim traces to a recorded command with exit codes.
- **I. Prior three commits untouched** — PASS. `1cc73f1c / cd3d36b2 / a9a34daa` on `54b079ca`.

## Findings

- **MINOR (informational, no action):** `ci_rename_integration.json` records `"configure"/"build_target"` exit fields as hardcoded constants (`ci_rename_validation.py`). Mitigated: the script returns 1 before writing the JSON if either step fails, and the raw logs record the true `exit=0` lines.

## Additional independent verification by the reviewer

The reviewer empirically re-ran configure + `--target test_hiprtc_selfcontained` on the staged tree: a single object built (`test/CMakeFiles/test_hiprtc_selfcontained.dir/test_hiprtc_selfcontained.cpp.obj`), `ctest -N` shows one test.
