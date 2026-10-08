# Gate P49 Adversarial Review — `hiprtc_selfcontained` CI regression test

- **Reviewer role:** adversarial (red team). Goal: make `--mode=negative` exit 0 while the
  semantic claim *"unpatched kernel fails because the host STL is unreachable"* is false;
  also probe positive / with-stl / ordinary for false verdicts.
- **Binary:** `C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\ci-test\hiprtc_selfcontained.exe`
- **Source under review:** `patches\phase4\ci_test_proposal\hiprtc_selfcontained.cpp`
- **Trees:** unpatched `rocm-libraries-phase4-baseline\projects\miopen\src\kernels` (b68f894,
  pristine); patched `rocm-libraries-phase4-canonical\projects\miopen\src\kernels`.
  Neither real tree was modified; all manipulated copies live under
  `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\` (5.1 GB scratch; logs `log_*.txt`).
- **Environment:** PATH includes `_rocm_sdk_core\bin` (hiprtc0714.dll); `CPATH` unset except
  where a leak is deliberately tested. Default arch gfx1151, `--hip-flat` derived.
- **Date:** 2026-10-08.

## VERDICT: **FAIL**

False PASSes were achieved and are reproducible. The most severe one requires **no special
flags and no environment manipulation** — only a missing/renamed MIOpen header in the tree
under test — and it defeats the negative control **on the patched tree** (the exact
protection Gate P49 relies on). Two further false PASSes are achievable behind the explicit
`--keep-isolated` probe bypass plus a polluted environment/kernels dir, and one
positive-mode false PASS on the unpatched tree.

The test is not worthless: on *pristine* trees and with the probe enabled it behaved
correctly in every scenario thrown at it (8/8 defensive checks held; see "Defenses that
held"). But the source comment's contract — *"any other failure is reported as
INCONCLUSIVE, not as a pass"* — is **false as implemented**, because the negative-mode
signature check is an unanchored substring match over the whole compiler log.

## Root cause

`hiprtc_selfcontained.cpp` lines 382–387:

```cpp
const bool signature =
    o.log.find(kMissingStdlibSignature) != std::string::npos &&   // "file not found"
    (o.log.find("type_traits") != std::string::npos ||
     o.log.find("utility")         != std::string::npos ||
     o.log.find("initializer_list")!= std::string::npos ||
     o.log.find("limits")          != std::string::npos);
```

Three distinct consequences:

1. **Name collision.** MIOpen's own headers are named `miopen_type_traits.hpp` and
   `miopen_utility.hpp` — they *contain* the signature tokens. A quoted-include failure
   `fatal error: 'miopen_type_traits.hpp' file not found` satisfies the signature.
2. **Whole-log search.** The tokens can come from *anywhere* in the log — an include-stack
   echo (`In file included from ...\include\type_traits:10:`) proves the header was
   *successfully included* and still supplies the substring, as long as some *other*
   include elsewhere says "file not found".
3. **Multi-error masking.** Clang keeps preprocessing after `#error`, so sabotage errors
   coexist with the genuine STL fatal error in one log; a substring search cannot tell
   "failed only for the STL reason" from "failed for arbitrary reasons AND mentions an
   STL-looking token".

## Findings

| ID | Severity | Finding |
|----|----------|---------|
| F1 | **BLOCKER** | Negative-mode signature substring match accepts *missing MIOpen header* failures. False PASS on the unpatched tree (A2b) **and on the patched tree** (A2d) with no flags/env tricks. |
| F2 | **MAJOR** | With `--keep-isolated` + `CPATH` (MSVC STL), negative mode PASSes while `<type_traits>` was **successfully included**; the actual fatal error is `'stddef.h' file not found` (`-nostdinc` removed clang's builtin dir; CPATH added MSVC's). The probe is the only guard and the flag disables it; the signature is too weak to backstop (A5a). |
| F3 | **MAJOR** | Wrong-reason masking: a prepended `#error boom` in `batchnorm_functions.hpp` still yields PASS on the unpatched tree because clang continues past `#error` and the genuine STL fatal error also lands in the log (A2-prepended). "Refusing to count arbitrary failures" only works when the arbitrary failure *erases* the STL error (e.g. on a patched tree). |
| F4 | **MAJOR** | Positive mode false PASS on the **unpatched** tree: a file literally named `type_traits` in the kernels dir (content = the patch's own freestanding header) + `--keep-isolated` → "PASS: kernel compiled without host STL". The probe catches the rogue file in all four mode/tree combos when enabled — the bypass flag is what turns detection into a false verdict (A3). |
| F5 | **MINOR** | Probe semantics: any probe compile failure without the `STL_PROBE_REACHABLE` marker is treated as "stdlib unreachable" — including failures caused by a broken `--isolate` option (`--isolate=--frobnicate`). Benign here (the kernel compile then lacks the signature → exit 4) but the probe cannot distinguish "isolated" from "probe itself broken". |
| F6 | **MINOR** | Misleading FAIL texts behind `--keep-isolated`: env pollution (CPATH) or a rogue header on an unpatched tree in negative mode reports "self-containment regression?" when the real cause is that isolation was never real / a kernels-dir shadow header. Direction is safe (non-zero), message is wrong. |
| F7 | **NIT** | `--hip-flat=abc` → uncaught `std::invalid_argument` from `std::stoull` → fail-fast crash, Windows exit code `0xC0000409` (-1073740791); outside the documented {0,1,2,4} contract. Should be usage/setup (2). |
| F8 | **NIT** | `--mode=ordinary` never validates/uses `<kernels-src-dir>`: a nonexistent dir still PASSes (toolchain-only control — arguably intended, but undocumented). |
| F9 | **NIT** | INCONCLUSIVE probe message hardcodes "-nostdinc++" even when the configured `--isolate` is `-nostdinc` (default), empty, or garbage — confusing in CI logs (seen in A3/A4/A6 outputs). |

## Evidence per attack

Common prelude for every command (Git Bash):

```bash
export PATH="/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin:$PATH"
unset CPATH
EXE="/c/Users/rocm/Desktop/YOLO_AMD/phase4_build/ci-test/hiprtc_selfcontained.exe"
```

### Baselines (clean env, pristine trees) — all as designed

| Command (mode/tree) | Exit | Result |
|---|---|---|
| `--mode=negative` unpatched | **0** | PASS — log line 7: `...\miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` |
| `--mode=negative` patched | **1** | FAIL "no-STL compile unexpectedly succeeded" (attack 1: held) |
| `--mode=positive` unpatched | **1** | FAIL (attack 8: held — STL genuinely isolated) |
| `--mode=positive` patched | **0** | PASS, 5792-byte code object |
| `--mode=with-stl` unpatched / patched | 0 / 0 | PASS both (this host's hipRTC clang auto-detects MSVC STL ambiently — consistent with A6a) |
| `--mode=ordinary` | 0 | PASS |

### A2 — wrong-reason failures on scratch copies of the unpatched tree

| Scenario | Manipulation | Exit | Log evidence |
|---|---|---|---|
| A2-append | `#error boom` appended to end of `batchnorm_functions.hpp` | 0 | STL fatal error at `miopen_type_traits.hpp:151` fires *before* the appended line — semantically the PASS is right, the sabotage was preempted (include processing is top-down) |
| **A2-prepend** | `#error boom` as line 1 of `batchnorm_functions.hpp` | **0 (F3)** | log has BOTH `batchnorm_functions.hpp:1:2: error: boom` AND `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` (clang continues past `#error`); "2 errors generated" |
| **A2b** | `miopen_type_traits.hpp` renamed to `.bak` | **0 — FALSE PASS (F1)** | `vector_types.hpp:8:10: fatal error: 'miopen_type_traits.hpp' file not found` — a missing *source-tree* header, not the host STL; `miopen_type_traits.hpp` ⊃ `type_traits` satisfies the substring check |
| A2c (control) | `configuration.hpp` renamed | 4 | `fatal error: 'configuration.hpp' file not found` → no token collision → INCONCLUSIVE, as designed |
| A2-patched-boom | patched tree + `#error boom` prepended | 4 | only `error: boom` in log (patched `__has_include` arm avoids the STL include) → INCONCLUSIVE |
| **A2d** | **patched** tree, `miopen_type_traits.hpp` renamed | **0 — FALSE PASS (F1)** | same `'miopen_type_traits.hpp' file not found` collision; pristine patched tree correctly exits 1 in negative mode, so this silences the negative control exactly where it matters |

Commands (representative):

```bash
cp -r .../unpatched_copy .../scen/a2b_rename_tt
mv .../scen/a2b_rename_tt/miopen_type_traits.hpp .../scen/a2b_rename_tt/miopen_type_traits.hpp.bak
"$EXE" .../scen/a2b_rename_tt --mode=negative      # EXIT=0  <- false pass
"$EXE" .../scen/a2d_patched_rename_tt --mode=negative # EXIT=0  <- false pass on patched tree
```

### A3 — rogue `type_traits` file in the kernels dir

Rogue file: copy of the patched tree's `miopen_freestanding_type_traits.hpp` saved under
the literal name `type_traits` (no extension) in the kernels dir. `-I<kernels-dir>` makes
`#include <type_traits>` resolve to it.

| Tree | Mode | Probe | Exit | Result |
|---|---|---|---|---|
| unpatched | negative | on | **4** | probe fired: `stl_probe.cu:2:2: error: STL_PROBE_REACHABLE` → INCONCLUSIVE |
| unpatched | positive | on | **4** | probe fired |
| patched | negative | on | **4** | probe fired |
| patched | positive | on | **4** | probe fired |
| unpatched | negative | `--keep-isolated` | 1 | FAIL "unexpectedly succeeded" — non-zero (safe direction) but misleading text (F6) |
| unpatched | positive | `--keep-isolated` | **0 — FALSE PASS (F4)** | "PASS: kernel compiled without host STL (5792-byte code object)" on the *unpatched* tree |

The probe is effective whenever it runs (it compiles with `-I<kernels-dir>`, so
`__has_include(<type_traits>)` sees the rogue file). The false verdict requires the
explicit bypass flag.

### A4 — CPATH leak, probe enabled

```bash
CPATH='C:\BuildTools\VC\Tools\MSVC\14.44.35207\include' "$EXE" .../unpatched_copy --mode=negative
```

Exit **4** — probe fired (`STL_PROBE_REACHABLE`), INCONCLUSIVE. The leak detector works.

### A5 — CPATH leak + `--keep-isolated` (probe skipped)

```bash
CPATH='C:\BuildTools\VC\Tools\MSVC\14.44.35207\include' "$EXE" .../unpatched_copy --mode=negative --keep-isolated
```

Exit **0 — FALSE PASS (F2)**. Full log (`log_cpath_neg_keep.txt`):

```
In file included from ...\unpatched_copy\miopen_type_traits.hpp:151:
In file included from C:\BuildTools\VC\Tools\MSVC\14.44.35207\include\type_traits:10:
C:\BuildTools\VC\Tools\MSVC\14.44.35207\include\cstddef:11:10: fatal error: 'stddef.h' file not found
...
PASS: unpatched kernel fails with the field signature ('type_traits' file not found) under no-STL isolation
```

`<type_traits>` **was found and included** (line 2 of the trace) — the semantic claim is
the opposite of what happened. The failure is `'stddef.h' file not found` (MSVC `cstddef`
needs clang's builtin `stddef.h`, removed by `-nostdinc`); the substring `type_traits`
comes from the include-stack echo. Companion runs:

- `positive` + CPATH + `--keep-isolated` on unpatched → exit 1 (same `stddef.h` breakage;
  no positive false pass via CPATH).
- Residual risk confirmed: `--keep-isolated` is a documented, explicit opt-out, but with
  the current weak signature it converts "probe skipped" into "wrong verdict possible",
  not merely "unverified".

### A6 — `--isolate` robustness (negative mode, unpatched)

| Option | Exit | Behavior |
|---|---|---|
| `--isolate=` (empty) | 4 | probe fired — with no isolation at all, this host's clang auto-detects the MSVC STL → INCONCLUSIVE (sane) |
| `--isolate=--frobnicate` | 4 | probe fails without marker → treated as isolated (F5); kernel compile fails without signature → INCONCLUSIVE |
| `--isolate=-nostdinc++` | 4 | probe fired (msvc-triple auto-detection bypasses `-nostdinc++`, exactly as the source comment warns) |

No crash, no false pass in any variant.

### A7 — missing inputs

| Input | Exit |
|---|---|
| nonexistent kernels dir | 2 (`SETUP ERROR: cannot read .../MIOpenBatchNormFwdTrainSpatial.cpp`) |
| existing dir without the kernel file | 2 |
| `--mode=ordinary` with nonexistent dir | 0 (F8 — dir never validated in ordinary mode) |

### A9 — argument robustness

| Input | Exit |
|---|---|
| `--hip-flat=abc` | crash, `0xC0000409` (-1073740791) via uncaught `std::stoull` exception (F7); Git Bash surfaces it as 127 |
| unknown flag `--bogus-flag` | 2 (usage) |
| `--mode=nonsense` | 2 (usage) |
| no args | 2 (usage) |

## Defenses that held

1. Negative on pristine patched tree → 1 (attack 1 held; only defeatable via tree
   corruption, F1).
2. Positive on pristine unpatched tree → 1 (attack 8 held).
3. STL-unreachable probe fired correctly on: CPATH leak (A4), rogue kernels-dir header
   (all four A3 combos), empty `--isolate`, `-nostdinc++` on msvc-triple clang.
4. Renaming a non-colliding header (`configuration.hpp`) → 4, and patched-tree
   `#error`-only failure → 4: the INCONCLUSIVE path itself works when the log is clean.
5. Missing dir / missing kernel → 2; unknown flags / bad mode / no args → 2.
6. `with-stl` and `ordinary` controls behave as documented.

## Required actions

1. **(F1, BLOCKER — must fix before gate)** Anchor the signature to the exact quoted
   header token: require the log to contain `'type_traits' file not found` /
   `'utility' file not found` / `'limits' file not found` /
   `'initializer_list' file not found` *including the quotes* (or a regex
   `fatal error: '<name>' file not found` with `<name>` restricted to the four exact
   header names). This single change kills A2b, A2d, and A5a: `'miopen_type_traits.hpp'
   file not found` no longer matches, and neither does an include-stack echo of a
   *resolved* `type_traits` path.
2. **(F3)** Require the STL fatal error to be the *only* error in the log (count
   `error`/`fatal error` diagnostics; if any non-STL error coexists — e.g.
   `error: boom` — classify INCONCLUSIVE). Clang's continue-past-`#error` behavior makes
   a single-token check insufficient.
3. **(F2/F4)** Re-scope `--keep-isolated`: either refuse it in negative mode, or when it
   is set additionally reject logs whose include stack shows an STL header *resolved*
   from outside the kernels dir (A5a's log literally proves `<type_traits>` was included).
   At minimum, print a loud "VERDICT UNVERIFIED: probe bypassed" banner so a CI reader
   cannot mistake the exit code for a probed verdict.
4. **(F7)** Validate `--hip-flat` numerically → usage/setup exit 2 instead of an uncaught
   exception.
5. **(F9)** Echo the actual `--isolate` value in the INCONCLUSIVE message.
6. **(F8)** Document or validate the unused kernels dir in ordinary mode.
7. Re-run this adversarial battery after the fix (scratch area and `log_*.txt` evidence
   retained under `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\` for diffing; ~5.1 GB,
   safe to delete after sign-off).

## Caveat on severity framing

Every achieved false pass requires the tree-under-test or the environment to deviate from
the pristine state (missing header, rogue file, CPATH, or `--keep-isolated`). On pristine
trees in a clean environment the test gave correct verdicts throughout. F1 is nonetheless
rated BLOCKER because (a) it needs nothing but a plausible accident (partial checkout,
bad merge, header moved — and Windows case-insensitivity makes name state fuzzier), and
(b) it defeats the control on the *patched* tree, i.e. the exact direction Gate P49 exists
to protect, while printing the field-signature claim verbatim.
