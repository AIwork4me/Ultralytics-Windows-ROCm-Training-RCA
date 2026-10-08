# Gate P49 Adversarial RE-VERIFY — hardened `hiprtc_selfcontained` CI test

- **Reviewer role:** adversarial (red team), second round. Goal: independently re-break the
  hardened binary; re-run the original four false-PASS attacks; invent new attacks against
  the hardening; confirm the pristine-tree matrix.
- **Binary:** `C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\ci-test\hiprtc_selfcontained.exe`
  (rebuilt after `P49_adversarial_review.md`).
- **Source under review:** `patches\phase4\ci_test_proposal\hiprtc_selfcontained.cpp`
  (hardened: quoted-token signatures `'<hdr>' file not found`; single-error requirement via
  `count_generated_errors` parsing `N error(s) generated`; STL-unreachable probe mandatory,
  `--keep-isolated` removed; `--hip-flat` parse errors → exit 2).
- **Trees:** unpatched `rocm-libraries-phase4-baseline\projects\miopen\src\kernels`;
  patched `rocm-libraries-phase4-canonical\projects\miopen\src\kernels`. Real trees only
  ever executed, never modified. All manipulated copies live under
  `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\reverify\` (5.8 GB scratch, 33 `log_*.err/.out`
  evidence files; runner `run.sh`).
- **Environment:** PATH includes `_rocm_sdk_core\bin`; `CPATH` unset except where a leak is
  deliberately tested; default arch gfx1151, default `--hip-flat` derived; Git Bash.
- **Date:** 2026-10-08.

## VERDICT: **FAIL** (narrowly — one false verdict still achievable, sabotage-class)

A false PASS **is** still achievable: a one-line **content edit** in the tree under test
that forges the diagnostic text defeats negative mode on the **patched** tree (attack N1
below: exit 0 with the verbatim "PASS: unpatched kernel fails with the field signature …
as the sole error" on a tree that still contains the complete fix).

However, **every accident-class and environment-class vector from round 1 is now closed**:
all four original attacks (F1 rename, F2 CPATH, F3 `#error boom`, F4 rogue `type_traits`)
exit 4 on the hardened binary, `--keep-isolated` is rejected (exit 2), the probe is
mandatory and fired correctly in every leak scenario, and the pristine matrix holds. The
residual forgery requires an attacker (or reviewer-blind sabotage) to *write source text*
that mimics the clang diagnostic — not a rename, stray file, or env var. Root cause: the
signature is anchored to the quoted header token but **not to the `fatal error:` diagnostic
form**, so an ordinary `error:` from `#error` (or any custom diagnostic) with the right
text satisfies it as the "single error".

## 1. Pristine matrix (real trees, clean env) — all correct

| Mode / tree | Exit | Evidence |
|---|---|---|
| negative / unpatched | **0** | `PASS: … ('type_traits' file not found) as the sole error`; log: `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found`, `1 error generated` |
| positive / patched | **0** | `PASS: kernel compiled without host STL (5792-byte code object)` |
| positive / unpatched | **1** | `FAIL: positive compile did not produce a code object` |
| negative / patched | **1** | `FAIL: no-STL compile unexpectedly succeeded (self-containment regression?)` |

## 2. Re-run of the original four attacks — all now defended (exit 4)

| Attack | Command shape (scratch copy) | Exit | One-line log evidence |
|---|---|---|---|
| F1 rename `miopen_type_traits.hpp`→`.bak`, negative (unpatched copy) | `mv …/miopen_type_traits.hpp …/.bak; EXE <dir> --mode=negative` | **4** | `fatal error: 'miopen_type_traits.hpp' file not found` → `INCONCLUSIVE … (signature=0, errors=1)` — quoted anchor rejects the collision |
| F1d same rename on **patched** copy (round-1 BLOCKER, A2d) | as above | **4** | same `signature=0` INCONCLUSIVE |
| F2 `CPATH=<MSVC 14.44.35207\include>`, negative (unpatched copy) | `CPATH='C:\BuildTools\…\include' EXE <dir> --mode=negative` | **4** | probe: `stl_probe.cu:2:2: error: STL_PROBE_REACHABLE` → `INCONCLUSIVE: host C++ stdlib still reachable under -nostdinc` |
| F3 `#error boom` as line 1 of `batchnorm_functions.hpp`, negative (unpatched copy) | `sed -i '1i #error boom' …` | **4** | log has both errors + `2 errors generated` → `INCONCLUSIVE … (signature=1, errors=0)` — see V2: count is 0, not 2, but still ≠1 |
| F4 file named `type_traits` (freestanding copy) in kernels dir, positive (unpatched copy) | `cp miopen_freestanding_type_traits.hpp <dir>/type_traits` | **4** | probe fired (`STL_PROBE_REACHABLE`) — no bypass flag exists anymore |
| removed bypass `--keep-isolated` | `EXE <dir> --mode=negative --keep-isolated` | **2** | `usage: … [--mode=…] [--arch=…] [--hip-flat=N] [--isolate=OPT]` (flag gone) |

## 3. NEW attacks

### N1 — `#error` text-mimic forges the signature on the PATCHED tree → **FALSE PASS (exit 0)** — V1

```bash
cp -r patched_base scen_n1_errormimic
sed -i '1i #error '"'"'type_traits'"'"' file not found' scen_n1_errormimic/batchnorm_functions.hpp
EXE scen_n1_errormimic --mode=negative        # EXIT=0
```

Log evidence (`log_n1_errormimic_patched_neg.*`):

```
scen_n1_errormimic\batchnorm_functions.hpp:1:2: error: 'type_traits' file not found
    1 | #error 'type_traits' file not found
1 error generated when compiling for gfx1151.
PASS: unpatched kernel fails with the field signature ('type_traits' file not found) as the sole error, under no-STL isolation
```

Why it works: the check `o.log.find("'type_traits' file not found")` matches the *body* of
an `error:` diagnostic produced by a `#error` directive; `#error` is also the *single*
error on a patched tree (which otherwise compiles), so `count_generated_errors()==1`.
The tree still contains the complete fix — remove the sabotage line and it compiles
self-contained; the "field signature" was never hit. The probe is not involved (isolation
is genuinely real). **Missing anchor: `fatal error: ` prefix.**

### N2 — one-line STL include re-added to the patched tree → exit 0 (by the gate's matrix, a false PASS; semantically debatable) — folds into V1

`sed -i '1i #include <type_traits>' …/batchnorm_functions.hpp` on a patched copy,
negative → **exit 0**: `fatal error: 'type_traits' file not found`, `1 error generated`.
Unlike N1 this is a *genuine* missing-STL diagnostic — the tree genuinely depends on the
host STL again, so the PASS message's behavioral claim is true even though the
negative×patched matrix cell (must be 1) is violated. Any text-only negative control
behaves this way; it is listed for completeness, not as the headline.

### N3 — forging the single-error count → blocked (by a second parser accident) — V2

Patched copy with two sabotage lines (`#error 'type_traits' file not found` +
`#error 1 error generated`): exit **4**, message `signature=1, errors=2`. The count parser
found "1 error generated" **twice** — once in the diagnostic, once in clang's *source-echo*
line (`1 | #error 1 error generated`) — summing to 2. Separately, the real footer
`2 errors generated` (plural) is **never counted**: `log.find("error generated")` does not
match `"errors generated"` (the `s`). Consequences: (a) multi-error logs land on
INCONCLUSIVE with `errors=0` (F3 above) — correct verdict, wrong reason; (b) the count is
text-forgeable in principle; the diagnostic+echo doubling currently blocks odd-sum forges,
which is luck, not design.

### N4 — `--isolate` neutralization / sabotage — all safe on this host

| Option (negative, unpatched copy) | Exit | Evidence |
|---|---|---|
| `--isolate=-Dfoo` (no isolation) | **4** | probe `STL_PROBE_REACHABLE` (this host's clang auto-detects MSVC STL once `-nostdinc` is gone) |
| `--isolate=` (empty) | **4** | probe fired |
| `--isolate=--frobnicate` (breaks the probe itself) | **4** | `error: unknown argument: '--frobnicate'`; probe fails **without** the marker → still treated as "isolated" (V3), but the kernel then fails without the signature → INCONCLUSIVE |
| `--isolate=--include=type_traits` (pristine patched tree) | **4** | `--isolate` *replaces* `-nostdinc`, so the STL is ambiently reachable → probe fired → `INCONCLUSIVE: host C++ stdlib still reachable under --include=type_traits` |

V3 note: on a host **without** ambient MSVC auto-detection (i.e., exactly the no-STL hosts
this gate exists for), `--isolate=--include=type_traits` would make the *probe itself*
fail with `fatal error: 'type_traits' file not found` and no marker — the probe cannot
distinguish "isolated" from "probe broken" (round-1 F5, still true) — and the kernel would
fail with the same forged single error → false PASS with a pure CLI option, no tree edit.
Not demonstrable on this host (the probe catches it here); rated MAJOR-conditional.

### N5 — `--hip-flat` robustness — hardened, two NITs remain

| Value | Exit | Behavior |
|---|---|---|
| `abc` / empty / 20-digit overflow | **2** | `SETUP ERROR: bad --hip-flat value` (F7 fixed — no more 0xC0000409 crash) |
| `0x10` | 0 | parsed as `0` → silently falls back to the derived value |
| `5abc` | 0 | parsed as `5`, trailing junk silently ignored (`note: HIP_PACKAGE_VERSION_FLAT=5 (< 7)…`) — V4 |
| `-1` | 0 | `stoull` wraps to 18446744073709551615, no note — V4 |

### N6 — path / usage robustness

| Input | Exit | Note |
|---|---|---|
| nonexistent kernels dir, negative | **2** | `SETUP ERROR: cannot read …/MIOpenBatchNormFwdTrainSpatial.cpp` |
| trailing `/` on kernels dir | 0 | works |
| trailing `\` on kernels dir | 0 | works (`-I` tolerates it; log shows normal compile) |
| `--mode=NEGATIVE` (case) | **2** | usage |
| `--mode=ordinary` + nonexistent dir | **0** | F8 carryover: ordinary never validates the dir (V5) |

### N7 — spacing mimic (safe direction)

`#error 'type_traits'  file not found` (two spaces) on a patched copy → **4**,
`signature=0`: non-exact text is rejected. Only exact-text forgeries (N1) matter.

### N8 — `--hip-flat=5` arm flip (patched copy, negative) → 4

The `<7` arm (`#else → #include <type_traits>`) produces a *cascade* (`expected class
name`, `no template named 'enable_if'…`) — many errors, no signature → INCONCLUSIVE. The
bogus-flag arm flip cannot forge a clean PASS; the `< 7` note is printed.

### N14/N14b/N15 — probe blind spot on non-`type_traits` signature headers → blocked by the *tree's* guards

The probe compiles only `__has_include(<type_traits>)`, yet the signature list accepts
four names. Attacking the other three:

- Rogue file `utility` (`#include <type_traits>`) in a patched copy → **4**: the patched
  `miopen_type_traits.hpp:155` consistency guard fires first:
  `#error "inconsistent C++ standard library availability: <type_traits> is not reachable but <utility> is …"`
  (`signature=0`). Same result for the env-only variant CPATH→rogue-dir-with-`utility`
  against the **pristine** patched tree (**4**).
- Rogue file `initializer_list` in a patched copy → **1** (compile *succeeded*):
  `tensor_view.hpp`'s `__has_include(<initializer_list>)` arm — the only *unguarded* arm —
  is **not in this kernel's include chain** (used by Getitem/Kthvalue/… kernels), so the
  rogue file is never included and the patched tree compiles normally.

No false verdict via this class today, but the safety comes from the tree's consistency
guards + the chosen kernel's include set, not from the test (V6).

## Findings

| ID | Severity | Finding |
|----|----------|---------|
| V1 | **MAJOR** (false PASS achieved) | Negative-mode signature is not anchored to the `fatal error:` diagnostic form; an `error:` produced by `#error <mimic text>` satisfies the quoted-token signature and the single-error count on a patched tree → exit 0 with the field-signature PASS claim (N1). Requires deliberate in-tree content sabotage (no rename/env/flag accident reaches this anymore). |
| V2 | **MINOR** | `count_generated_errors` misses the plural footer `N errors generated` (matches only singular `error generated`) and double-counts diagnostic+source-echo lines. Multi-error logs → INCONCLUSIVE by accident (`errors=0` or `2`), and the count text is forgeable in principle (currently blocked by the echo-doubling parity accident). |
| V3 | **MINOR here / MAJOR-conditional** | Probe still cannot distinguish "stdlib unreachable" from "probe itself broken" (`--isolate=--frobnicate` treated as isolated). On hosts without ambient MSVC auto-detection, `--isolate=--include=type_traits` would turn this into a CLI-only false PASS (probe fails with the very injected `'type_traits' file not found`, no marker). Blocked on this host only because `--isolate` replaces `-nostdinc` and the ambient STL trips the marker. |
| V4 | **NIT** | `--hip-flat` accepts trailing junk (`5abc`→5) and negative wrap (`-1`→ULLONG_MAX) silently; `0x10`→0 silently falls back to derived. |
| V5 | **NIT** (F8 carryover) | `--mode=ordinary` never validates `<kernels-src-dir>`; nonexistent dir PASSes. |
| V6 | **NIT** | Probe checks only `<type_traits>` while the signature list has four names; currently backstopped by the patched tree's own consistency guards (`miopen_type_traits.hpp:155`, `miopen_utility.hpp:60`) and by `tensor_view.hpp` being outside this kernel's include chain — both incidental to the test. |

Defenses confirmed working (vs round 1): quoted-token anchor kills F1/F1d; mandatory probe
kills F2/F4 and every CPATH/INCLUDE-style leak tried; single-error requirement kills F3
coexisting-error masking; `--keep-isolated` gone (exit 2); `--hip-flat` parse failures exit
2 (no crash); usage text matches actual flags.

## Required actions

1. **(V1 — required before gate sign-off)** Anchor each signature to the full diagnostic:
   require `fatal error: 'type_traits' file not found` (likewise `utility`, `limits`,
   `initializer_list`) — the `fatal error: ` prefix plus quoted token. `#error`-produced
   `error:` lines then can never match. One-line change to `kMissingStdlibSignatures`.
   (N2-style genuine re-added includes will still "pass" negative mode — that is inherent
   to any log-matching negative control and is semantically defensible; document it.)
2. **(V2)** Replace footer-text counting with counting diagnostic header lines: lines
   matching `: error:` or `: fatal error:` (column-form), which excludes source-echo
   lines, or at minimum match `error(s) generated`. Re-run the F3/N3 battery.
3. **(V3)** Treat a probe compile that *fails without the marker* as INCONCLUSIVE
   ("isolation unverified"), not as "isolated": require `probe.compile_status ==
   HIPRTC_SUCCESS` for an isolated verdict. This closes the `--include=<STL name>` class
   on all hosts.
4. **(V6)** Extend the probe to all four signature headers
   (`__has_include(<type_traits> || <utility> || <limits> || <initializer_list>)` → marker),
   so the test no longer leans on the tree's consistency guards.
5. **(V4)** Reject `--hip-flat` values with trailing non-digit characters and leading `-`.
6. **(V5)** Validate the kernels dir in ordinary mode, or state in the usage text that
   ordinary ignores it.
7. Re-run this battery after the fix; scratch + `log_*` evidence retained under
   `C:\Users\rocm\Desktop\YOLO_AMD\phase4_attack\reverify\` (5.8 GB; safe to delete after
   sign-off).

## Caveat on severity framing

The single achieved false verdict (N1, plus the matrix-violating N2) requires writing
forged source text into the tree under test — reviewer/CI-visible sabotage, not the
accident-level corruption (a rename, a stray file, an env var, a bypass flag) that round 1
exploited. If the threat model for Gate P49 is "protect against accidental false PASSes",
the hardened binary already meets it in every scenario tried (original 4 + 15 new attacks).
If the threat model includes adversarial in-tree content, V1 must be fixed (action 1)
before the verdict text "field signature … as the sole error" can be trusted verbatim.
