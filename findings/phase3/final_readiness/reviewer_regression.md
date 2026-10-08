# Reviewer B — Regression Attack Review (P3-FINAL-R3 final readiness)

Date: 2026-10-08. Reviewer: independent regression attacker (fresh context).
Mandate: find a REAL code path, architecture assumption, std-header state, or
RTC mode still capable of being broken by the two-commit MIOpen patch
(0001 f06d7ae5… + 0002 77f9fc16…, sha256-verified against
docs/phase3/linux/PATCH_ID_NORMALIZATION.md) on rocm-libraries develop
b68f8944300f104875d953fc8e4510908c9aaf0b. Concrete mechanism + evidence
required; no speculation. Prior adversarial reviews
(subagent_kthvalue_review.md, subagent_maintainer_review.md,
subagent_regression_review.md, Gate-83 reviewers A/C/D) were read first and
their resolved findings are NOT re-litigated.

Environment: gfx1151, ROCm 7.14 wheel stack in .venv (clang 23.0.0git ROCm),
source-built A/B installs miopen-{unpatched,patched}, binding via
scripts/phase3/linux/run_with_source_miopen.sh (LD_PRELOAD + dladdr echo),
fresh caches per run. All scratch artifacts in /tmp only.

## Attack matrix (all executed on this machine unless noted)

| # | Attack (surface) | Mechanism hypothesis | Result |
|---|---|---|---|
| A1 | Adversarial RTC TUs outside tested matrices, with-STL semantic drift | Patched headers could change tokens/semantics of untested kernel closures | 10/10 TUs TOKEN-IDENTICAL; only kthvalue differs (radix, by design) |
| A2 | Real-hipRTC compile of untested families (fp8 / Getitem / RNN) | Compile regression invisible to host-level tests | rc=0/0 both trees, equal code size (fp8); no regression |
| A3 | BFP16 kthvalue runtime (untested dtype through the changed radix TU) | Radix include/builtin change could break or silently alter ushort encode | PASS/PASS; 9/9 dump files byte-identical A/B; cold HIPRTC compile proven both legs |
| A4 | Std-header states (full / partial / zero STL) compiling a DIFFERENT kernel than develop | Probe could select a semantically different header set | Full-STL: identical (A1). Partial-STL: probe-consistent (Getitem+fp8 -nostdinc++ compile rc=0 BOTH trees — comgr set has type_traits+initializer_list; no drift). Zero-STL: develop always failed (reproduced); patched = new capability only |
| A5 | is_trivially_copyable / hip_f8 fidelity | Freestanding trait could answer differently than real STL | Identical answers (7 static_asserts hold under real <type_traits> AND freestanding zero-stdlib); fp8 TU (hip_f8_impl user) compiles both trees |
| A6 | HIP-version gates: HIP<7 arms, HIP 10.x, MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS | Reordered #if could alter legacy arms; radix include swap could break HIP<7 RTC | Wrappers token-identical across HIP 5.x/6.0/6.2 × {RTC, host} (6 states); radix HIP<7 analysis: benign (see F-UP-2); MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS does not exist at this SHA (grep over whole project: 0 hits) |
| A7 | Architecture flips (gfx94x/110x/120x) | Arch- or mcpu-conditioned patch behavior | None: both patches contain zero arch conditioning; builtins/__has_include/initializer_list lowering are clang-level, arch-independent |
| A8 | Embedded-kernel list / packaging-install modes | New headers missing from some build/pack path | Same explicit MIOPEN_KERNEL_INCLUDES list consumed by add_kernels in both INCBIN and default branches (src/CMakeLists.txt:839-850); block guard at :359 covers HIPOC/HIP/HIPNOGPU; no separate disk-install list for kernel headers exists at this SHA (only db MODEL_FILES at :1073) |
| A9 | Windows/MSVC clang-lowering of freestanding initializer_list | msvc-triple clang could mis-lower braced-init-lists onto {ptr,size} layout | VERIFIED correct: --target=x86_64-pc-windows-msvc -nostdinc emits field stores (ptr, i64 4=size) exactly matching layout; constexpr path static_asserts; develop fails same state (include not found) |

## Evidence per attack

### A1 — with-STL token identity on adversarial TUs (surface 1)

Toolchain: wheel `amdclang++ -E -x c++ -DMIOPEN_HIP_RUNTIME_COMPILE
-DHIP_PACKAGE_VERSION_FLAT=7140060850 -I<kernels-of-tree>` vs baseline tree;
canonicalized token streams (line markers stripped, whitespace collapsed)
compared. TUs chosen from the audit families NOT in the 11-op/BN/kthvalue
runtime matrices:

- MIOpenGetitem.cpp, MIOpenReduceSum.cpp, MIOpenMultiMarginLoss.cpp,
  MIOpenSoftMarginLoss.cpp, MIOpenPReLU.cpp (the 6-entry
  `<initializer_list>`-reachable family per docs/phase3/linux/RTC_KERNEL_SELECTION.md)
  — TOKEN-IDENTICAL.
- gpu_reference_kernel/fp8_naive_conv.cpp (miopen_type_traits + std::conditional
  + hip_f8_impl.hpp:49 `std::is_trivially_copyable_v`) — TOKEN-IDENTICAL (97,460 B).
- MIOpenRNNHiddenStateUpdate.cpp × {float, half} (conditional/is_same) —
  TOKEN-IDENTICAL (~109 KB each).
- MIOpenBatchNormBwdSpatial.cpp — TOKEN-IDENTICAL (143,052 B).
- static_composable_kernel conv wrapper
  (static_kernel_gridwise_convolution_forward_implicit_gemm_v4r4_xdlops_nchw_kcyx_nkhw.cpp,
  the `<utility>`/std::forward family) — fully preprocessed rc=0/0,
  TOKEN-IDENTICAL (351,461 B).
- MIOpenKthvalue.cpp — differs exactly in the radix region (the `<limits>`
  chain removed; `std::numeric_limits<int32_t/int64_t>::max()` → literalized
  `2147483647` / `9223372036854775807L`, value-equal per E3 static_asserts).
  No other token differs.

### A2 — real-hipRTC (libhiprtc.so.7, gfx1151) compile of untested families

Same mechanism as extended_canary E3/E4 (hiprtcCreateProgram/CompileProgram,
-I kernels), extended to TUs never compiled through this channel before:

- fp8_naive_conv.cpp (with solver-realistic defines): unpatched rc=0,
  patched rc=0, identical code-object size 20,944 B. Also rc=0/0 under
  `-nostdinc++` (partial-STL state: comgr's set provides <type_traits>;
  Getitem/fp8 do not include miopen_utility → no <utility> dependency —
  consistent with the audit's per-TU reachability model).
- MIOpenGetitem.cpp with the dispatcher's real define set
  (-DINPUT_TYPE=float -DINDEX_TYPE=int -DERROR_TYPE=float -DOUTPUT_TYPE=float
  -DLOCAL_SIZE=256): rc=0/0 both trees, with-STL and -nostdinc++.
- MIOpenRNNHiddenStateUpdate.cpp with rnn_util.cpp's real define set
  (READ_BLOCK/DATA_TYPE/INFERENCE_MODE/LOCAL_SIZE/GLOBAL_SIZE/USE_CX/USE_DCY/
  IS_SEQ_BEGIN/IS_SEQ_END/DIRECTION, per src/rnn/rnn_util.cpp:104-117):
  rc=0/0 both trees.

### A3 — BFP16 kthvalue runtime A/B (surface 6; the assigned residual)

New harness /tmp/revb_kthvalue_bfp16.cpp (adapted from
scripts/phase3/linux/kthvalue_runtime_harness.cpp; dlsym/dladdr provenance;
per-slice permutations of bf16-exact integers so ties are impossible;
bf16-exactness asserted in-harness). 3 cases: {64,400} k=7 no-keep,
{4,16,350} k=349 keep, {2,5,7,512} k=512 (dim-size boundary). Runs through
scripts/phase3/linux/run_with_source_miopen.sh with fresh cache labels:

- unpatched: HARNESS_RESULT PASS (198 slices, value_mismatches=0,
  index_mismatches=0, all three cases).
- patched: HARNESS_RESULT PASS, identical per-case numbers.
- Binding proven: `bound miopenCreate -> installs/miopen-{unpatched,patched}/
  lib/libMIOpen.so.1 (MATCH)`; `miopenKthvalueForward <- …` per-leg;
  version markers 3.6.2.b68f894 vs 3.6.2.b68f894-dirty.
- Cold RTC compile proven per leg at MIOPEN_LOG_LEVEL=6: `[LoadBinary]
  MIOpenKthvalue.cpp.o; args: -DMIOPEN_USE_FP16=0 -DMIOPEN_USE_FP32=0
  -DMIOPEN_USE_BFP16=1 -DIN_OUT_TYPE=ushort -DLOCAL_SIZE=256 -mcpu=gfx1151`
  → "Unable to load binary" → `HIPRTC v.9.0` → `[SaveBinary]` INSERT — i.e.
  the BFP16 instantiation of the patched radix regime (no `<limits>`, builtin
  int paths) was compiled from empty cache on BOTH builds and executed.
- All 9 dump files (input/output/indices × 3 cases) byte-identical A/B (`cmp`).

Actual risk answer for surface 6: none from the patch — the changed TU's
bfloat16 path (IN_OUT_TYPE=ushort → encode<ushort>, radix.hpp:74-79, an
UNCHANGED line) runs correctly and bit-identically. See F-UP-1 for the
(uneventful, pre-existing) NaN-input observation.

### A4 — std-header states (surface 2)

- Full STL: A1/A2 identity — no state in which a different kernel is compiled.
- Partial STL (type_traits reachable, utility not — the comgr `-nostdinc++`
  state): the patch's cross-check `#error` fires only for TUs that include
  miopen_type_traits/miopen_utility; TUs that include neither (Getitem) or
  only need <type_traits> (fp8) compile IDENTICALLY in both trees — probe
  picks the real header, no drift, no new failure. This adjudicated design
  (Gate-83 C1 resolution) holds under my sampling.
- Zero STL: develop reproduced failing (`tensor_view.hpp:31: fatal error:
  'initializer_list' file not found` under msvc-triple -nostdinc; the E1
  'utility' failure for wrapper-including TUs); patched compiles — strictly
  new capability where develop never worked → regression impossible by
  definition in this state.

### A5 — is_trivially_copyable / hip_f8 (surface 3)

/tmp/revb_itc.cpp: identical 7-assert set compiles under real `<type_traits>`
(ambient STL) and under `miopen_freestanding_type_traits.hpp` with
`-nostdinc` (zero stdlib): both hold. Mechanism: both lower to clang's
`__is_trivially_copyable` builtin (freestanding by declaration, libc++ in
clang mode), so divergent answers are not constructible. cv-qualified
is_pointer fidelity was resolved upstream of this review (A2/C9) and is
pinned by the header's own self-tests; not repeated.

### A6/A7 — HIP gates and architecture (surface 4)

- Preprocessed both wrappers at HIP_PACKAGE_VERSION_FLAT ∈ {5001024000ULL,
  6000000000ULL, 6020000000ULL} × {RTC, host}: token-identical (6/6 states
  per header). HIP 10.x keeps HIP_PACKAGE_VERSION_FLAT >= 7000000000ULL →
  same HIP>=7 arm as 7.14 (numeric gate, no other conditioning).
- radix.hpp is the ONLY file whose RTC arm changed for HIP<7 as well
  (<limits> → miopen_cstdint). Mechanism analysis: its sole consumer
  MIOpenKthvalue.cpp includes miopen_cstdint.hpp itself, unconditionally,
  identically in both trees (MIOpenKthvalue.cpp:32), so the typedef
  availability (including the <6.0.25 miopen_cstdint window) is decided by
  the TU's own include in BOTH trees — the swap cannot flip a
  develop-compiles/patched-fails state. MIOpen at this SHA requires HIP>=6.2
  in its supported matrix anyway.
- MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS: `grep -rn` over the whole
  rocm-libraries project at b68f894 → 0 hits; the legacy-arm concern in the
  brief does not apply to this tree.
- Arch: neither patch text contains mcpu/gfx conditioning (verified by
  reading both). gfx94x/gfx110x/gfx120x flips are not constructible from
  these patches.

### A8 — embed list / packaging (surface 5)

The three new headers live in MIOPEN_KERNEL_INCLUDES
(src/CMakeLists.txt:514-516 after the patch), inside the backend guard at
:359 (`HIPOC OR HIP OR HIPNOGPU`) — the same guard and same list that
already carried miopen_type_traits.hpp/miopen_utility.hpp/radix.hpp/
tensor_view.hpp. Both embed variants consume this list:
`inline_kernels_src(... ${MIOPEN_KERNEL_INCLUDES} ...)` under MIOPEN_INCBIN
(:809-822) and default (:839-840). There is no disk-install path for kernel
headers at this SHA (only db MODEL_FILES install at :1073), so no packaging
mode can ship without the new headers while shipping the old ones.

### A9 — MSVC-triple initializer_list lowering (surface 7)

Wheel clang `--target=x86_64-pc-windows-msvc -nostdinc -std=c++17
-DMIOPEN_HIP_RUNTIME_COMPILE` (simulating the Windows-wheel no-stdlib
state; triple resolves to x86_64-pc-windows-msvc19.33.0):

- /tmp/revb_il_msvc.cpp (braced `use_list({1,2,3,4})` + constexpr
  consumption in tensor_layout_t's exact begin()[i] pattern): syntax OK,
  codegen OK, `static_assert(csum({10,20,30})==60)` holds.
- IR proof: `caller()` lowers to `store ptr %array` into field 0 and
  `store i64 4` into field 1 of `%"class.std::initializer_list" = type
  { ptr, i64 }` — field-store lowering exactly matching the freestanding
  {__begin_, __size_} layout; MSVC-mangled by-value passing consistent.
  Misfire mode would be a loud compile error, not silent wrong code; none
  observed on LLVM 23 (the wheel's compiler).
- Full tensor_view.hpp constexpr consumer (braced `tensor_layout_t<2> L{5,2}`
  + get_tensor_view_idx) compiles under patched headers in this state;
  baseline headers fail with `'initializer_list' file not found`
  (tensor_view.hpp:31) — the pre-patch always-fail.
- Residual exposure: wheels shipping older clang could theoretically differ;
  the freestanding header already #errors on non-clang. Classified
  UPSTREAM_CI_FOLLOWUP (see F-UP-3).

## Findings

- BLOCKER: none.
- MAJOR: none.
- MINOR-1 (evidence hygiene — baseline tree no longer pristine): the
  "pristine develop" reference tree
  ~/Desktop/YOLO_AMD/rocm-libraries-linux-baseline carries an UNTRACKED
  `projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp`
  (mtime 2026-10-08 07:44, byte-identical to the patched tree's file;
  `git -C … status` shows only this stray). This postdates the kthvalue
  review's "baseline git status clean" assertion. Inert to all recorded
  evidence (git-diffs ignore untracked; embed list is explicit; no develop
  source references that filename — verified by grep), and it cannot be
  picked up by any baseline TU include. Remediation: delete the stray (or
  amend the pristine-state record) before any future re-verification.
- NIT-1 (harness hygiene, mirrors prior MINOR-3 class): my scratch harness
  intentionally did not check hipMemcpy return codes; failures bias toward
  FAIL (zero-init outputs + non-zero expected values), so no false-PASS is
  constructible. No action needed.
- F-UP-1 / UPSTREAM_CI_FOLLOWUP (pre-existing, NOT patch-caused; surfaced by
  the BFP16 work): encode<ushort> (radix.hpp:74-79, line-identical in both
  trees) guards NaN via `isnan(v)` on a ushort bit-pattern. If the visible
  `isnan` resolves to the float overload (implicit conversion), bfloat16 NaN
  patterns are undetected and fall through to the mask-flip ordering —
  negative-sign NaN patterns would radix-order near the bottom rather than
  last. Unchanged by the patch (A/B dumps byte-identical; the changed lines
  are the int32/int64 branches only). Recommend an upstream CI case:
  kthvalue with NaN inputs on fp16/bf16 vs torch semantics.
- F-UP-2 / UPSTREAM_CI_FOLLOWUP: radix.hpp's RTC include swap also applies
  on HIP<7 RTC builds (develop included <limits> there). Benign today
  (single consumer self-includes miopen_cstdint; MIOpen@develop requires
  HIP>=6.2), but if upstream backports the patch to older branches, the
  <6.0.25 miopen_cstdint window becomes reachable — cherry-pickers should
  keep the consumer-side include or bump the typedef gate. Not a regression
  on any supported configuration.
- F-UP-3 / UPSTREAM_CI_FOLLOWUP: the freestanding initializer_list's clang
  lowering guarantee was re-verified on LLVM 23 (this wheel). Upstream CI
  spanning older HIPCC/clang versions should include the (already proposed)
  compile-only selfcontained CI test with a braced tensor_layout_t
  construction added, so a lowering regression on any supported clang is
  caught loudly.

## Scope notes / non-repetition

Resolved items from prior adversarial reviews are not re-argued: radix
numeric_limits parse-time BLOCKER (fixed via builtins, re-verified here only
as value-identity), partial-STL #error design (C1/A1 resolution), is_pointer
cv fidelity (A2/C9), utility wrapper asymmetry (B2), EOL/format churn (A1/D2),
CK-wrapper runtime non-execution (documented blocked; here closed at the
token + real-hipRTC compile level instead), kthvalue fp32/fp16 runtime
closure, YOLO/BN matrices, embed-INCBIN parity (Gate-83), probe
machine-state-dependence NIT.

## Conclusion

Eleven attack surfaces executed: every with-STL compile path reachable by the
patch is token-identical to develop except the single designed radix delta
(value-equal, runtime-proven on fp32/fp16 and now bf16); no partial/zero-STL
state compiles a kernel develop would have compiled differently; HIP<7/HIP10
gates are inert or token-identical; no arch conditioning exists; packaging
has no path that ships old-without-new headers; the MSVC-triple fallback
lowers correctly. No code path, architecture assumption, std-header state,
or RTC mode was found that the patch can break relative to develop
b68f894 on any supported configuration. The three follow-ups above are
pre-existing or backport/CI-hardening items, not regressions of this patch.

REVIEWER B VERDICT: NO REGRESSION FOUND
