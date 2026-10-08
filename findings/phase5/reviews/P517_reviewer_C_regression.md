# P517 — Reviewer C: final adversarial regression audit of the Phase-5 candidate

- Date: 2026-10-08
- Candidate: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5-candidate` @ `39319c4d2f51998529dc0f2144841ba4cbe82ff3` (3 commits over upstream `7c586614`)
- P4 canonical: `4084759f3804748b7935d882db2d0445a3e0c380` (on `b68f8944`), objects read from `rocm-libraries-phase3`
- Method: primary sources only (git blobs via `git cat-file`, raw evidence JSON, validation
  script source, machine state). No prior review verdict trusted. **No DLL swap was needed
  for this audit** — the wheel DLL was hash-checked untouched at the end (see "State left
  behind").

## VERDICT: PASS

(Conditional in exactly one sense already mandated elsewhere: the
`LINUX_PHASE5_TARGETED_REVALIDATION = PENDING` handoff must be executed before the patch
series is submitted upstream. That is a disclosed process gate, not a regression finding.
Nothing found in this audit blocks it or adds new conditions to it.)

No BLOCKER. No MAJOR. Three MINOR findings (all evidence-coverage or carried hardening
items, none a demonstrated or plausible behavioral regression), five NITs.

---

## 1. Surface 1 — source delta P4 → P5, token-level re-verification (independent)

Full `git diff --name-status 4084759 39319c4d -- projects/miopen` yields 15 files. Nine
are pure upstream drift (`b68f894→7c58661`): `kern_db.hpp`, `sqlite_db.hpp`, the three
`MIOpenBatchNorm*Spatial.cpp`, `configuration.hpp`, `default_configurations.hpp`,
`reduction_functions.hpp`, `test/gtest/cache.cpp` — **all nine verified blob-identical
between `39319c4d` and `7c58661`** (candidate did not touch them), and `git diff
7c58661 39319c4d` contains zero paths outside `projects/miopen`. The candidate's 3
commits touch exactly: 8 kernel headers + `src/CMakeLists.txt` (embedding list) +
`test/CMakeLists.txt` + `test/hiprtc_selfcontained.cpp` (new).

Of the 8 patched files, `radix.hpp`, `tensor_view.hpp`, `miopen_freestanding_utility.hpp`
and `src/CMakeLists.txt` are blob-identical to P4 canonical. The remaining 4 were
re-verified independently by whitespace-stripped blob comparison (`tr -d ' \t\r\n'`) plus
backslash-newline-splice normalization:

| file | result |
|---|---|
| `miopen_freestanding_initializer_list.hpp` | token-identical to P4 (pure formatting) |
| `miopen_type_traits.hpp` | splice-aware identical (pure formatting) |
| `miopen_utility.hpp` | splice-aware identical (pure formatting) |
| `miopen_freestanding_type_traits.hpp` | formatting + removal of `#define MIOPEN_FREESTANDING_TRAITS_ACTIVE` |

The macro removal is the only non-whitespace byte change in the whole P4→P5 delta.
`git grep MIOPEN_FREESTANDING_TRAITS_ACTIVE` at `4084759` finds only the define's own
line (zero consumers, zero `#ifdef`s); at `39319c4d` zero matches. Dead-code removal,
nonfunctional. The P504 formatter-equivalence claim is **confirmed by independent
token-level proof**; `source_delta/pre_cleanup_equivalence.json` additionally shows the
8 files were blob-identical to P4 before the hygiene pass.

## 2. Surface 2 — Windows no-STL validation (P5-11): was the isolation real?

Verified from `scripts/phase5/runtime_validation.py` + `evidence/phase5/runtime/nostl_validation.json`:

- **MSVC include rename is real and complete for this machine**: the script renames
  `C:\BuildTools\VC\Tools\MSVC\14.44.35207\include` and asserts non-existence inside the
  try (an assert failure would have aborted before the workload with a failed gate).
  Machine check: `C:\BuildTools\VC\Tools\MSVC` contains **only** `14.44.35207`;
  `C:\Program Files\Microsoft Visual Studio` has only Installer/Shared (no toolset);
  no LLVM libc++ tree; the SDK's own llvm (`_rocm_sdk_core\lib\llvm`) ships **no
  `include/c++`** — hiprtc's clang has no bundled C++ headers, so with the single MSVC
  toolset renamed and `INCLUDE`/`CPATH`/`C*_INCLUDE_PATH` scrubbed from the child env,
  `<type_traits>` is genuinely unreachable. (Consistent with the CI probe behavior.)
- **No cached-kernel bypass exists, structurally**: no `*.kdb`/`*.fdb.txt`/`*.udb`
  anywhere in the wheel or in `phase5_build` (find run: zero hits); wheel log line
  `ParseAndLoadDb ... gfx115128.HIP.fdb.txt unreadable` confirms even the perf DB is
  absent; build had `MIOPEN_EMBED_BINCACHE=OFF`, `MIOPEN_BINCACHE_PATH=`; `MIOPEN_USE_HIPRTC=ON`
  (CMakeCache) so BN spatial kernels can only come from an in-process RTC compile.
- **Fresh profile**: unique `phase5_iso_nostl_<uuid8>` USERPROFILE/LOCALAPPDATA/TEMP,
  `MIOPEN_USER_CACHE_PATH`/`MIOPEN_USER_CACHE`/`AMD_COMGR_CACHE`/`ROCM_PATH` scrubbed;
  MIOpen's user cache resolves via `ExpandUser(USERPROFILE)` (`src/expanduser.cpp`) and is
  version-suffixed (`binary_cache.cpp`), so it landed inside the fresh dir. The workload
  (BN train fwd+bwd+running-stats) exercises exactly the RTC kernels whose include chain
  contains the patch (`MIOpenBatchNormFwdTrainSpatial/BwdSpatial` → `batchnorm_functions.hpp`
  → `configuration.hpp` → `vector_types.hpp` → `miopen_type_traits.hpp`), with in-process
  provenance `sha256 == d5974dad…` and all checks true.
- **Would it have caught STL leakage?** Yes for the patched DLL: the freestanding arm is
  the only way these kernels compile without STL (CI negative control proves unpatched
  7c58661 sources fail with the exact `'type_traits' file not found` signature under the
  same hiprtc DLL), and a compile failure inside MIOpen propagates to a failed torch op →
  non-zero exit / non-finite result → gate false.

Residual gap → finding **F-C1 (MINOR)**: the unpatched-7c58661 **DLL** was never swapped
in for a *runtime* negative control on Windows (the runtime A/B is assembled from a
compile-level negative plus a runtime positive), and the fresh profile is `rmtree`d in
`finally` before asserting that the comgr/MIOpen cache actually received entries, with no
MIOPEN logging enabled. The structural argument above is strong enough that this cannot
flip the verdict, but future runs should enable `MIOPEN_ENABLE_LOGGING` or assert
cache-dir non-emptiness pre-cleanup.

## 3. Surface 3 — Windows STL-present path

- The DLL bakes **no** host include paths into its RTC options: `src/comgr.cpp`
  `Hiprtc()` builds the option list itself (`-D…`, `-O3`, `-std=c++17`, arch, …) and adds
  exactly one conditional include, `-I$ROCM_PATH/include` when the `ROCM_PATH` env var is
  set — which every validation run scrubbed. So in both the DLL scenario and the CI test,
  `<type_traits>` reachability is decided solely by clang's ambient MSVC autodetection;
  there is no scenario where the DLL's own compiles and the wheel scenario resolve
  `__has_include` differently.
- With STL reachable (numerics + both YOLO cells: MSVC present, ambient env), the
  `__has_include(<type_traits>)` arm takes the real MSVC header — the exact
  baseline-identical include — and BN numerics vs CPU fp64 match the pre-fixed Phase-4
  reference (y max_abs 6.71e-07 vs P4's 6.845e-07; all other diffs ≤ 2.4e-08). The
  `with-stl` CI cells pass on both trees with identical code-object sizes.
- `hiprtc0714.dll` used by the CI harness is the wheel's own (`_rocm_sdk_core\bin`),
  sha-pinned in `ci_matrix_phase5.json` — same compiler at test time and runtime.

No differential-`__has_include` vector found.

## 4. Surface 4 — Linux risk

- `-nostdinc` vs `-nostdinc++` on GNU triples: the STL-unreachable **probe cannot be
  broken by any isolation flag** — its source contains no `#include` at all (pure
  `__has_include` + trivial kernel). What full `-nostdinc` can do on GNU triples is hide
  `/usr/include` libc headers needed by the HIP headers hiprtc injects internally,
  failing the *kernel* compile for a non-STL reason. That direction is fail-closed:
  positive mode → exit 1 FAIL; negative mode → the failure lacks the exact
  `'type_traits' file not found` signature → exit 4 INCONCLUSIVE. No false PASS is
  reachable; the documented `--isolate=-nostdinc++` workaround (handoff §2 + test usage
  text) is the right leg configuration. → folded into **F-C2 (MINOR)** below.
- `radix.hpp` `__INT32_MAX__`/`__INT64_MAX__`: value-identical to the removed
  `std::numeric_limits<int32_t/int64_t>::max()` (2147483647 / 9223372036854775807),
  same `static_cast<Radix>` target. Predefined by clang and gcc in all modes; not by
  MSVC — but no MSVC-reachable path exists: the only in-tree consumer is
  `kernels/MIOpenKthvalue.cpp` (plus the CMake embedding list), a filesystem grep finds
  **zero** references to `radix.hpp`/`miopen_type_traits.hpp`/`miopen_utility.hpp`
  outside `projects/miopen`, host MIOpen code never includes it, and the non-RTC arm
  additionally includes `<hip/hip_runtime.h>` which already requires clang/hipcc. The
  public installed header `miopen/tensor_view_utils.hpp` does relatively include
  `../../kernels/tensor_view.hpp`, but in host compiles `MIOPEN_HIP_RUNTIME_COMPILE` is
  undefined so the `#if defined(...) && !__has_include(<initializer_list>)` dispatch
  short-circuits to plain `#include <initializer_list>` — baseline behavior; the host
  solvers (`forward_kthvalue.cpp`, `backward_getitem.cpp`, `forward_multimarginloss.cpp`)
  all compiled in the phase5 build.
- Runtime-neutral claim on Linux: with a full stdlib present (the normal Linux case) the
  `__has_include` arms resolve to the real headers, i.e. byte-identical includes to
  baseline; the freestanding arms only activate where baseline failed to compile at all.
  The upstream drift (`use_amdgcn→use_gfx9_dpp` rename in the BN spatial kernels) is
  upstream's own change, present in any develop-based build, and is covered by the
  mandated Linux revalidation + BN numerics (Windows numerics already show no effect).

## 5. Surface 5 — legacy HIP<7 arms vs baseline `b68f894`

Not byte-identical: the nesting of `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` /
`#ifdef MIOPEN_HIP_RUNTIME_COMPILE` was swapped (baseline: version outer / RTC inner;
candidate: RTC outer / version inner). Preprocessing is a pure intersection — the swap is
commutative, and the arm bodies (including the
`>= 6000025000 && < 6001024000` workaround arm) are token-identical to baseline. All
four (version × RTC) combinations map to identical behavior except the intended one:
(HIP≥7 ∧ RTC ∧ `<type_traits>` unreachable) now dispatches to the freestanding header
instead of unconditionally failing. Non-RTC arms on both headers compile `#include
<type_traits>` / `#include <utility>` exactly as baseline. → NIT (documentation).

`tensor_view.hpp`'s dispatch is deliberately version-independent
(`defined(MIOPEN_HIP_RUNTIME_COMPILE) && !__has_include(<initializer_list>)`): for every
combination where `<initializer_list>` is reachable this is baseline behavior; where it
is not, baseline failed. No HIP<7 regression.

## 6. Surface 6 — cache contamination

- Kernel/binary caches: no system DB exists (no `.kdb`/`.fdb` anywhere), no embedded
  bincache, user cache is under the (fresh, per-run-unique) USERPROFILE and
  version-suffixed. `yolo_train_validation.py` gives **each** YOLO run its own
  uuid-suffixed fresh profile with the same env scrub as the no-STL run — verified in
  source (lines 66–84). No P4-compiled kernel could be replayed into a P5 run (or vice
  versa): the caches were empty at process start, and the RTC sources differ textually
  anyway (formatting changes alter any content-derived key).
- The YOLO stderr noise (CK grouped-conv symbol warnings, `gfx115128.HIP.fdb.txt`
  unreadable, `EvaluateInvokers elapsed <= 0` errors) is **byte-identical (modulo source
  path) to the Phase-4 runs' stderr** (`evidence/phase4/windows_runtime/yolo_train.json`)
  — pre-existing dev-build characteristics of the swap-in harness (dev DLL vs wheel's
  CK-grouped-conv binary), not a Phase-5 regression. Noted so nobody mistakes them for
  one. → NIT.

## 7. Surface 7 — DLL provenance in every PASS run

Every runtime PASS cell proves `sha256 == d5974dad…` **inside the process that used the
DLL**, via `GetModuleHandleW("MIOpen.dll")` + `GetModuleFileNameW` + file hash:

| evidence | in-process provenance |
|---|---|
| `runtime/binding_probe.txt` | `d5974dad…` ✓ |
| `runtime/numerics_batchnorm.txt` | `miopen_sha256 d5974dad…` ✓ (`provenance_inside_process: true`) |
| `runtime/nostl_validation.json` | `result.miopen_sha256 d5974dad…` ✓ |
| `yolo/yolo_train.json` amp_false | `MIOPEN_PROVENANCE` line + `provenance.sha256 d5974dad…` ✓ |
| `yolo/yolo_train.json` amp_default | same ✓ |

No PASS run lacks provenance or carries null provenance. `ci_integration.json`'s
`test_exe/test_exe_sha256: null` is the known P508-F6 path bug (hash recovered in
`ci_matrix_phase5.json`); the CI legs don't load MIOpen, so in-process DLL provenance is
not applicable there (they pin test source/binary/tree/hiprtc-DLL hashes instead, all
verified matching). → NIT (carried).

Wheel restore: `wheel_restored_ok: true` in `dll_provenance.json`, `nostl_validation.json`
and `yolo_train.json`; independent end-of-audit hash check below.

---

## Findings

| ID | Severity | Finding |
|---|---|---|
| F-C1 | MINOR (evidence) | No-STL runtime freshness is proven structurally (no DBs exist, fresh profile, HIPRTC-only build) but not observationally: the fresh profile is deleted in `finally` without asserting comgr/user-DB entries were written, MIOPEN logging was off, and no runtime negative control with an unpatched-7c58661 DLL was performed on Windows (the runtime A/B pairs a compile-level negative with a runtime positive). Bridging assumptions verified in source: comgr.cpp adds no host include paths; `ROCM_PATH` scrubbed; compile failure propagates to workload failure. Recommend: enable MIOPEN logging or assert cache non-emptiness pre-cleanup in future runs. |
| F-C2 | MINOR (Linux leg operability) | On GNU triples the test's default `--isolate=-nostdinc` may also hide libc headers needed by internally-injected HIP headers, failing the kernel for a non-STL reason. Fail-closed only (positive→FAIL, negative→INCONCLUSIVE; the probe itself cannot break — it includes nothing). The handoff already documents `--isolate=-nostdinc++` for the Linux leg; CI wiring must not copy the msvc-triple default blindly. Not a source regression. |
| F-C3 | MINOR (carried, unchanged) | P508 F1/F3/F4 hardening of `test_hiprtc_selfcontained` (kernel-content marker, duplicate-arg rejection, probe widened to all four stdlib signature headers) is still open per the disposition log ("TO BE HARDENED after the P5-17 panel"). No new false-PASS vector found in this audit that those do not already cover. |
| F-C4 | NIT | HIP<7 arms are behavior-identical but not byte-identical to `b68f894` (version/RTC nesting swapped — commutative). Document if anyone runs a b68f894-style byte diff again. |
| F-C5 | NIT | Partial-STL environments (exactly one of `<type_traits>`/`<utility>` reachable) now fail earlier with an explicit `#error` tripwire instead of a later `'file not found'` (or, in one contrived TU shape, instead of compiling). Stricter-by-design; no realistic supported configuration loses functionality. |
| F-C6 | NIT | `radix.hpp` non-RTC arm now requires `__INT32_MAX__`/`__INT64_MAX__` predefined (clang/gcc yes, MSVC no). No MSVC-reachable consumer exists (verified zero references outside `projects/miopen`; only consumer is a kernels TU whose non-RTC arm already requires hip headers). |
| F-C7 | NIT | `ci_integration.json` `test_exe/test_exe_sha256: null` (P508-F6 path bug; hash preserved in matrix JSON). Carried. |
| F-C8 | NIT | CK-grouped-conv symbol warnings / fdb-unreadable / EvaluateInvokers stderr noise: identical in P4 — pre-existing dev-build swap-harness artifacts, not candidate regressions. |

## Strongest regression vector found

**None identified that survives primary-source verification.** The two strongest attack
families were:

1. *Vacuous no-STL PASS via surviving STL or a baked include path* — defeated: exactly one
   MSVC toolset exists on the machine (rename covers it), no bundled libc++ in the SDK
   llvm, and `comgr.cpp`'s RTC option list adds no host include path (only
   `-I$ROCM_PATH/include` behind an env var every run scrubbed).
2. *Cached-kernel replay masking a compile failure* — defeated: no `.kdb`/`.fdb`/embedded
   bincache exists anywhere on the box for gfx1151, every validation run started from a
   virgin uuid-suffixed profile, and the user cache is version-suffixed under
   `ExpandUser(USERPROFILE)`.

The strongest *remaining* (accepted, disclosed) coverage gap — not a found regression —
is that the `radix.hpp`/`tensor_view.hpp` consumer kernels (Kthvalue, Getitem,
MultiMarginLoss, ReduceSum, PReLU, SoftMarginLoss) get zero Windows runtime exercise:
the CI matrix compiles only the BN spatial kernel's include chain, and those ops are not
on the BN/YOLO path. Their no-STL correctness rests on the identical header pattern
already runtime-proven for BN, on value-identical `__INT_MAX__` substitutions, and on the
mandated (still PENDING) Linux `torch.topk/kthvalue` PASS→PASS check. This is exactly
what the Linux handoff already requires; no additional condition is imposed by this
review.

## State left behind

- Wheel DLL **never swapped by this audit**; end-of-audit hash verified:
  `74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a` (pristine, MATCH),
  no `.p5bak`/`.p5bak2`/`.p5bak3`/`.attackbak` leftovers in the wheel bin dir.
- Phase-5 DLL in place at `C:\Users\rocm\Desktop\YOLO_AMD\phase5_build\miopen\bin\MIOpen.dll`,
  sha256 `d5974dad0da85b3b9849b5f678fff13b3e678ae14029b98aa0cd87dded9f9a36` (verified).
- Candidate and pristine worktrees clean (`git status --porcelain` empty); pristine at
  `7c586614`.

**Final verdict: PASS** (regression audit; upstream submission additionally gated on the
already-documented PENDING Linux targeted revalidation).
