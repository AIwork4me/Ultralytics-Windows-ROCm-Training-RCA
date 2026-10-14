# Negative Control — unpatched baseline + final test file (leg C)

## Construction (no mutation of the PR branch)

- Baseline worktree `C:\wp` at `b8cf0e7b526f4a25c0623f5b2a4fe41e03ede179`
  (= parent of `c6ed8131`, the develop base of the PR) — tracked state clean.
- The **only** addition: `projects/miopen/test/gtest/hiprtc_selfcontained.cpp`
  copied **from the `f0f330c4` blob itself** (204 lines; LF-normalized SHA256
  `04fdffa6df8f6019e1e13dbf8a1aaba5721157e5241a3cc79d6b6ecbccf98497`,
  identical to the committed blob) — present as an *untracked* file, so the
  baseline source remains exactly the pre-fix develop state.
- The test executable was relinked in the existing baseline build tree
  `C:\bwp` — exact command (ninja rebuilt only the changed test object and
  relinked the exe; no other target was affected):
  `ninja -C C:/bwp bin/test_hiprtc_selfcontained.exe` →
  `[2/4] Building CXX object test/gtest/CMakeFiles/test_hiprtc_selfcontained.dir/hiprtc_selfcontained.cpp.obj` →
  `[3/4] Linking CXX executable bin\test_hiprtc_selfcontained.exe`.
- The PR branch was not touched; this control never contains the patch.

## Execution
- `MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.*`
  (from `C:\bwp`, `C:\bwp\bin` first on PATH)
- Raw log: `raw/negative_control/C_pristine_gtest_run_f0f330c4test.log`
- Process exit code **1**; gtest `[ FAILED ]` — as required.

## Provenance markers inside the log
- User-kernel-cache directory label **`3.6.2.b8cf0e7b`** — the running
  MIOpen was built from the clean baseline tree (no patch, no dirty files).
- `C:/wp/projects/miopen/test/gtest/hiprtc_selfcontained.cpp(147): error: Failed`
  — the gtest assertion in the **final** (204-line) test file; the assertion
  sits at line 147 in the committed file (line 141 in the pre-final 198-line
  file used in the earlier R2 round — the 6-line delta is visible exactly
  here).

## The defect signature (exact lines from the log)

```text
MIOpen: Error [Compile] 'hiprtcCompileProgram(prog.get(), c_options.size(),
  c_options.data())' gtest_rtc_selfcontained.cpp: HIPRTC_ERROR_COMPILATION (6)
MIOpen: Error [BuildHip] HIPRTC status = HIPRTC_ERROR_COMPILATION (6),
  source file: gtest_rtc_selfcontained.cpp
C:\Users\rocm\AppData\Local\Temp\comgr-36176-6-62f8d3\include\miopen_type_traits.hpp:151:10:
  fatal error: 'type_traits' file not found
```

This is the **original bug** the PR fixes: under `-nostdinc`, the unpatched
`miopen_type_traits.hpp` still `#include <type_traits>`, which the Windows
wheel hipRTC cannot reach. No unrelated failure is being counted: the probes
above it in the same run behaved identically to the patched leg (trivial and
STL-probe kernels compiled; nonce batch `114386408053500_*`, all five
compiles fresh `Unable to load binary` → attempted), so the toolchain and
isolation conditions were sound — only the self-contained kernel failed,
with the missing-STL diagnostic.

## Ambient-STL control within the negative run
Compile `_4` of `gtest_rtc_selfcontained.cpp` **without** `-nostdinc`
succeeded (saved + `run` lines present) — the same test content passes when
the STL is reachable, confirming the failure is specifically the no-STL
condition and not the kernel body or harness.

## Result

**EXPECTED_FAIL** — the unpatched baseline fails the final committed
regression test with exactly `'type_traits' file not found`, proving the
test detects the original defect; the same test PASSES on the patched
final HEAD (see `HIPRTC_NO_STL_VALIDATION.md`).
