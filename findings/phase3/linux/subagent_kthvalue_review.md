# Adversarial Falsification Review — Kthvalue Runtime Closure (P3-FINAL-R3)

Reviewer role: hostile falsifier. Standing assumption under test: *the kthvalue
runtime harness does NOT actually exercise the changed runtime path* — the
patched `radix.hpp`/`tensor_view.hpp` code was never compiled or executed, and
the PASS is meaningless. Every challenge below was attacked with independently
recomputed evidence (not trust in the archived claims). All ten attacks failed.

Date: 2026-10-08
Scope: `evidence/phase3/raw/linux/kthvalue/`, `scripts/phase3/linux/`,
source trees `~/Desktop/YOLO_AMD/rocm-libraries-linux-{baseline,patched}`,
installs `~/Desktop/YOLO_AMD/installs/miopen-{unpatched,patched}`,
patches `~/Desktop/YOLO_AMD/tmp/patches/`.
All paths below relative to the RCA repo root unless absolute.

## Methodology

1. Read the plan/closure docs, harness source, wrapper script, both run logs,
   both metadata files, and comparison.json in full.
2. Recomputed every hash claim from raw bytes (lib SHA256s, harness sha256,
   all 30 dump-file SHA256s, byte-level `cmp` of all 15 dump pairs).
3. Verified git state of both source trees at SOURCE_SHA
   `b68f8944300f104875d953fc8e4510908c9aaf0b` and re-derived the patched tree
   by forward-applying 0001+0002 to a /tmp copy of the baseline
   (`patch -p1` + recursive `diff` → identical).
4. Extracted the **embedded kernel sources from the installed .so files
   themselves** (byte-offset context search) to prove which radix.hpp text the
   runtime compiler actually sees — independent of any log claim.
5. Re-verified output correctness **from raw dumps with my own Python** (k-th
   smallest semantics, value-at-reported-index consistency), not the harness's
   or the docs' word.
6. Reconstructed the harness inputs **from the harness source's PRNG
   algorithm** and compared byte-for-byte to the archived dumps, proving the
   executed binary matches the archived source.
7. Read the solver (`forward_kthvalue.cpp`), dispatcher (`kthvalue.cpp`),
   kernel (`MIOpenKthvalue.cpp`), `radix.hpp` (both trees), driver reference
   (`kthvalue_driver.hpp`), gtest reference (`cpu_kthvalue.hpp`), and the
   HIPRTC entry (`comgr.cpp BuildHip`) in the SOURCE_SHA trees.

## Challenge-by-challenge

### C1. Was REAL patched MIOpen loaded? — YES (proven three independent ways)

- `unpatched/run.log:6-7`: `miopenCreate <- .../installs/miopen-unpatched/lib/libMIOpen.so.1`,
  `miopenKthvalueForward <- .../miopen-unpatched/...` (dladdr on the **exact
  pointer called**, printed by the harness, `kthvalue_runtime_harness.cpp:417-421`).
  `patched/run.log:6-7`: same for `.../miopen-patched/...`. Wrapper adds its own
  dladdr check (`run.log:3`, "(MATCH)").
- SHA256 recorded in metadata (`unpatched/metadata.txt:4`
  `8694d2ba…242cd`, `patched/metadata.txt:4` `02904c25…5221`) match my fresh
  `sha256sum` of the files **currently on disk** at those paths, and match the
  earlier archived build evidence (`evidence/phase3/raw/linux/build_unpatched/provenance.txt:9`,
  `build_patched/provenance.txt:11` — same builds, file sizes 803090840 /
  803103088 bytes).
- Differential marker inside the logs themselves: unpatched reports
  `MIOpen version 3.6.2.b68f894` (clean tree) vs patched
  `3.6.2.b68f894-dirty` (patched tree) — `run.log:66` on both sides; cache
  subdirs differ accordingly (`…/3.6.2.b68f894[/-dirty]/gfx1151_20.ukdb`).
- **Decisive, log-independent proof**: byte-search of the installed binaries'
  embedded kernel-source strings —
  unpatched `.so`: `std::numeric_limits<int32_t>::max()` present (1×, inside
  `encode`'s int32 branch), `__INT32_MAX__` absent;
  patched `.so`: `__INT32_MAX__` present (context shows
  `return static_cast<Radix>(__INT32_MAX__) + v + 1;` followed by the
  `__INT64_MAX__` line), `numeric_limits<int32_t>` absent.
  The patched library physically carries the patched `radix.hpp`; the
  unpatched carries the original.

### C2. Same source-built unpatched MIOpen on the A side? — YES

`8694d2ba…` (kthvalue unpatched metadata) == archived Gate-L28 build provenance
== current install file. Both trees sit at commit `b68f894` (git log); baseline
`git status` clean; patched tree modified in exactly the 8 files created by
0001+0002 (5 M + 3 ??), verified by `diff -rq` of the two trees. A/B difference
between the installed libs is exactly the patch series (tree diff == patch
content; forward-apply of the patches to a baseline copy reproduces the patched
tree bit-for-bit, `diff -rq` empty).

### C3. Was MIOpenKthvalue.cpp actually used? — YES

Both logs, all three cases each:
- `[FindSolutionImpl] KthvalueFwd (not searchable)` / `[SearchForSolutions] KthvalueFwd: Success.`
- `[PrepareInvoker] Preparing kernel: KthvalueFwd`
- `[LoadBinary] Loading binary for: "MIOpenKthvalue.cpp.o"; args: … -DIN_OUT_TYPE=float|half … -mcpu=gfx1151`
- `[Register] Invoker registered for algorithm kthvalue_fwdi_dtype… and solver KthvalueFwd`
- `[run] kernel_name = KthvalueFwd, global_work_dim = {25600|51200|61440,1,1}, local_work_dim = {256,1,1}`
  (= slices×256, matching `GetSolution`'s `xgridsize = output_size * 256`,
  `forward_kthvalue.cpp:75-80`).

Applicability (baseline `solver/kthvalue/forward_kthvalue.cpp:49`):
`dimNum >= 2 && dimStride == 1 && dimSize >= 300`, rank ≤ 5 —
{100,500} d=-1→1 (stride 1, size 500) ✓; {10,20,300} d=2 (stride 1, size 300,
boundary-inclusive `>=300`) ✓; {8,3,10,2000} d=-1→3 ✓. The dispatcher
(`kthvalue.cpp`) has a single-solver container
(`SolverContainer<solver::kthvalue::KthvalueFwd>`) and **no fallback path**;
`GetSolution` unconditionally names kernel file `MIOpenKthvalue.cpp` /
kernel `KthvalueFwd` (`forward_kthvalue.cpp:88-89`). No prebuilt alternative:
`grep -ci kthvalue` = 0 in all four `share/miopen/db/gfx115128*.db.txt` files of
both installs, and the runtime system kern DB logged "database not present".

### C4. Could the cache hide compile behavior? — NO

Wrapper (`run_with_source_miopen.sh:22-29`) sets a fresh
`MIOPEN_CUSTOM_CACHE_DIR` + `XDG_CACHE_HOME` per label
(`kthvalue_unpatched_final3` vs `kthvalue_patched_final3`; additionally the
version-suffixed subdir differs, so even a shared dir could not cross-load).
Both logs show the full cold chain per dtype per run:
`LoadBinary … MIOpenKthvalue.cpp.o` → SELECT (0.02–0.06 ms) → `Unable to load
binary` → `[PrintVersion] HIPRTC v.9.0` (proof the HIPRTC build path
executed) → `SaveBinary … MIOpenKthvalue.cpp.o` (INSERT, 3–11 ms).
Case 2 (FP32 3D) shows no LoadBinary because it reuses the identical
in-process FP32 program (same kernel name + same args: `-DIN_OUT_TYPE=float
-DLOCAL_SIZE=256`); this reuse is symmetric in both runs. `MIOPEN_HIP_RUNTIME_COMPILE`
is added unconditionally by the HIPRTC path (`comgr.cpp:805`,
`opts.push_back("-DMIOPEN_HIP_RUNTIME_COMPILE")`; comgr.cpp is identical in
both trees), so the patched header's conditional include logic was live.

### C5. Could the harness CPU reference be wrong? — NO (three references agree)

Harness (`kthvalue_runtime_harness.cpp:220-228, 259-269`): per slice, sort
indices by value ascending; answer value = slice[ids[k-1]], index = ids[k-1].
Official driver reference `mloKthvalueFwdRunHost`
(`driver/kthvalue_driver.hpp:43-86`): identical (elements → `std::sort` on ids
by value → `elements[ids[k-1]]`, `indices = ids[k-1]`). Upstream gtest
reference `test/cpu_kthvalue.hpp:36-75`: identical. The harness additionally
recomputes ground truth on the storage-round-tripped values before comparing
and compares FP16 outputs through the same lossless converters.
**Independent of all three**: my own Python recomputation from the raw dumps
confirms, for every slice of every case in both runs, that the output value is
the k-th smallest of the raw input slice and equals `input[slice_base +
index[s]]`, with `index` unique under pairwise-distinct values.

### C6. Were ties handled? — YES (ties are impossible by construction)

Harness lines 199-218: each dim-slice is a Fisher–Yates **permutation** of
{0..n-1} mapped injectively to `base + 0.25·perm[j]` — pairwise distinct by
construction in FP32 and (see C9) in FP16 bits. The kernel's tie
non-determinism note (`MIOpenKthvalue.cpp:152` "For case 2, this will be
non-deterministic") can only trigger on **equal encoded values**; with
distinct values, the radix descent terminates on a unique candidate
(`counts[j] == 1`) — for distinct encodings, a bucket with >1 survivor at
`pos == 0` would imply identical encodings, a contradiction. My
reconstruction-from-source confirms the dumps really are permutations
(distinct f16 bit patterns per slice, verified programmatically).

### C7. Did only ONE variable change? — YES

- Harness binary sha256 `4d77a96f…0414` identical in both metadata files
  (tail of `unpatched/metadata.txt` and `patched/metadata.txt`) and matches
  the current `/home/amd/Desktop/YOLO_AMD/tmp/kthvalue_harness`.
- Seeds are compile-time constants in the source; `*_input.bin` dumps are
  byte-identical across runs (all three, verified by `cmp` and matching
  SHA256s recomputed by me — they equal every `input_sha256_*` field in
  `comparison.json`).
- **All 15 dump pairs byte-identical A/B** (`cmp` clean), including outputs
  and indices: the two libraries produce bit-identical results.
- Only environmental differences: the LD_PRELOAD target (the variable under
  test) and the fresh cache dir names. The two builds differ only by the
  patch series (C2); `MIOpenKthvalue.cpp` itself is byte-identical in both
  trees, as is `comgr.cpp` (the RTC driver code).

### C8. Does the test cover the radix code changed by 0002? — COMPILE-PATH YES;
runtime-branch coverage honestly partial (see MINOR-1)

What 0002 changes in `radix.hpp` (verified hunk-by-hunk against both trees):
the unconditional `#include <limits>` becomes
`#ifdef MIOPEN_HIP_RUNTIME_COMPILE → #include "miopen_cstdint.hpp"`, and the
int32/int64 `encode` branches swap `std::numeric_limits<…>::max()` for
`__INT32_MAX__`/`__INT64_MAX__`.

- The `<limits>`-include change **is on the executed compile path for both
  dtypes**: `MIOpenKthvalue.cpp:37` includes `radix.hpp`; the RTC compile ran
  under `-DMIOPEN_HIP_RUNTIME_COMPILE` (C4), so the patched compile of both
  the FP32 and FP16 instantiation parsed `radix.hpp` **without `<limits>`**
  and compiled successfully to a kernel that then produced bit-correct
  results. A broken freestanding conversion would have failed the compile or
  the run. `tensor_view.hpp` (probe from 0002) is included at
  `MIOpenKthvalue.cpp:36` and `miopen_type_traits.hpp` (0001) via
  `radix.hpp:33` — all three modified headers are on this TU's compile path.
- Runtime `encode` execution for the tested dtypes takes the `float` branch
  (`__float_as_uint` + sign-xor mask, radix.hpp:93-98) and the `__half`
  branch (`__half_as_ushort` + mask, :87-92); both run in the radix-digit
  loop (`MIOpenKthvalue.cpp:99` histogram, `:148` candidate check, with
  `GetBitFieldImpl`/`SetBitFieldImpl` at :102/:160-161 and
  `RadixType<DTYPE>` at :66). The changed int32/int64 branch **expressions**
  are not executed (nor instantiated — `if constexpr` discards them).
  This is unavoidable: `MIOpenKthvalue.cpp` is the **only** consumer of
  `radix.hpp` in the tree (grep), and kthvalue's `IN_OUT_TYPE` ∈
  {float, half, ushort} only — no runtime path on this stack can execute
  `encode<int32_t>`/`encode<int64_t>` at all. Their residual risk is
  (a) parse-time under the new include regime — covered by this test for
  both dtype compiles — and (b) the value identity
  `__INT32_MAX__ == std::numeric_limits<int32_t>::max()` (both 2147483647;
  compiler builtins), which is auditable by inspection.

### C9. Is FP16 conversion exact? — YES (proven empirically for the full value sets)

Value sets are `{-0.125·n + 0.25·j, j=0..n-1}` for n ∈ {500, 300, 2000}:
multiples of 0.25 within ±250. Simulating the harness's exact converter
(`kthvalue_runtime_harness.cpp:100-123`) over **all** values of all three
cases: round-trip `f16_bits_to_f32(f32_to_f16_bits(v)) == v` for every value;
all n values map to n distinct f16 bit patterns (injective); the only value
hitting the `exp <= 0` special branch is exact 0.0 (correctly → ±0); all
nonzero values have exponent field 13–22 (normal range, no rounding, no
denormals, no overflow). The truncating mantissa shift (`>> 13`) is exact
because the dropped 13 bits are always zero for this value set. No rounding
can occur.

### C10. Could the PASS be vacuous? — NO

- Outputs are zero-initialized on device before the call
  (`kthvalue_runtime_harness.cpp:303-307`); expected values are never zero
  (−60.25 / −3.5 / 249.75), so unwritten or stale memory cannot satisfy the
  comparison.
- Verification compares **every** slice exactly (values `==`, indices `==`,
  float NaN-safe: NaN != expected → FAIL) and only reports PASS when
  `values_ok && indices_ok` with counters `value_mismatches=0
  index_mismatches=0`; `HARNESS_RESULT: PASS` prints only when `rc == 0`
  (`:474`). Logs show `slices=100/200/240` (n_slices > 0) with
  `max_abs_err=0`.
- Independent confirmation from raw dumps: outputs all non-zero, non-constant
  indices per slice (e.g. case 1 indices span 4..486), values equal input at
  the reported index, and equal my independently computed k-th smallest.
- Harness binary == archived source: reconstructing the inputs by
  re-implementing the source's xorshift64* + Fisher–Yates + converters
  reproduces `FP32-2D-nokeep_input.bin` and `FP16-4D-keep-kmax_input.bin`
  byte-for-byte.

## Findings

- BLOCKER: none.
- MAJOR: none.
- MINOR-1 (coverage scope, acknowledged): the `encode` int32/int64 branch
  rewrites are never executed (nor instantiated) by any possible runtime test
  on this stack — `MIOpenKthvalue.cpp` is the only `radix.hpp` consumer and
  never dispatches int dtypes. What this test does prove for them is
  parse-time compilation under the new freestanding include regime for both
  FP32 and FP16, plus the builtin/limits value identity by inspection. The
  closure doc's own scope-honesty section is consistent with this; nothing in
  the evidence overclaims it.
- MINOR-2 (observability): which branch of `tensor_view.hpp`'s new
  `__has_include(<initializer_list>)` probe the HIPRTC preprocessor took is
  not recoverable from the archived logs (source-text logging was not
  enabled). If the stack's real `<initializer_list>` was reachable, the new
  freestanding fallback header was embedded in the TU list but not included
  by this particular compile. The probe itself (new 0002 code) was evaluated
  and the compile+run succeeded either way; the claim under test (radix path)
  is unaffected. Suggest enabling `MIOPEN_DEBUG_COMGR_LOG_SOURCE_TEXT`-style
  capture in any follow-up if per-include provenance is wanted.
- MINOR-3 (hardening, non-exploitable): the harness does not check return
  codes of the zero-init and readback `hipMemcpy` calls
  (`kthvalue_runtime_harness.cpp:306-307, 325-326`). Any such failure biases
  toward FAIL (readback buffers are fresh zero-initialized vectors and
  expected values are non-zero), so it cannot create a false PASS — cosmetic
  only.
- OBSERVATION: per-slice expected values are constant within a case by
  construction (k-th of a fixed permutation value set = `base + 0.25·(k−1)`),
  so per-slice value discrimination reduces to the k-semantics check; the
  per-slice discriminating power lives in the indices, which are unique per
  slice, were verified exactly by the harness, re-verified independently by
  this review against raw input bytes, and are byte-identical A/B.

## Conclusion

Every falsification avenue was closed with independently recomputed evidence:
the exact patched library (dladdr + SHA + embedded-source extraction) serviced
the call; the solver chain selected `KthvalueFwd`/`MIOpenKthvalue.cpp.o`; a
cold-cache HIPRTC compile of the kernel — carrying the patched `radix.hpp`
text, without `<limits>` — occurred per dtype per run and its binary was
saved; the executed kernel produced bit-identical, exactly-correct values and
indices vs an independent recomputation on both sides; only the library
differed between runs. The claimed changed-runtime-path execution is real.

VERDICT: PASS
