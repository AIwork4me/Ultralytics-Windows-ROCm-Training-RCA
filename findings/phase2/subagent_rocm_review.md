# Phase-2 Reviewer A — ROCm/MIOpen specialist (Gate 45 panel)

Date: 2026-10-07. Mandate: adversarially attempt to FALSIFY the Phase-2
LEVEL-3 verdict in `docs/PHASE2_LEVEL3_RCA.md` and the fix-layer
conclusions, then rule PASS / CONDITIONAL PASS / FAIL.

Scope read: `docs/PHASE2_LEVEL3_RCA.md`, `docs/PHASE2_RUNTIME_STL_REQUIREMENTS.md`,
`docs/PHASE2_HYPOTHESES.md`, `findings/phase2/gate27_28_msvc_ab_decision.md`,
`docs/PHASE2_CLAIMS_AND_EVIDENCE.md`, plus the raw artifacts cited below.
Independent re-derivations performed by this reviewer (not just re-reading
the primary agent's logs) are marked **[R]**.

## Verdict: **PASS** (4 non-blocking findings; none overturns a load-bearing claim)

---

## 1. Falsification attempts and outcomes

### 1.1 "Is `<type_traits>` really the only std header the BN closure needs?" — attempt FAILED (claim holds), but the cited artifact is mislabeled (Finding 1)

`STD_INVENTORY.txt` lists, under the heading *"angle-include directives in
extracted closure (files actually reachable from MIOpenBatchNormFwdTrainSpatial.cpp)"*,
`<utility>` (4x), `<limits>` (3x), `<algorithm>` (3x), `<functional>`,
`<initializer_list>`, plus `std::forward`/`std::array`/`std::numeric_limits`
identifiers — which, if the heading were true, would falsify P2-C017 and the
"type_traits-only shim suffices" conclusion.

**[R]** I grepped every `#include` in the 13-file quoted closure directly
(`evidence/phase2/raw/miopen/extracted_kernel_tree/{MIOpenBatchNormFwdTrainSpatial.cpp,
include/batchnorm_functions.hpp, configuration.hpp, default_configurations.hpp,
vector_types.hpp, miopen_type_traits.hpp, bfloat16_dev.hpp, miopen_math.hpp,
activation_functions.hpp, bnorm_spatial_activation_functions.hpp,
reduction_functions.hpp, static_unroll.hpp, float_types.h}`): the ONLY non-HIP
angle-include in the closure is `<type_traits>` (two sites, both in
`miopen_type_traits.hpp` lines 147/151). The extra std headers in the inventory
come from the wider 158-header embedded tree (CK `functional*.hpp`,
`static_kernel_common_header.hpp` etc.), exactly as
`PHASE2_RUNTIME_STL_REQUIREMENTS.md` §1 states. The claim is also doubly
covered dynamically: the cache-isolated shim-only run passes
(`candidateA/A_minimal.txt`, `A_variants.txt` 5/5 PASS), and the failing include
chain in the logs is precisely `.cpp:8 → batchnorm_functions.hpp:30 →
configuration.hpp:34 → vector_types.hpp:8 → miopen_type_traits.hpp:151`
(`msvc/gate32_poison_header_test_v2.txt`). The doc's prose is correct; the
artifact's own title is wrong (Finding 1, non-blocking).

### 1.2 "Could the gate have arrived in the rockrel build by another route than ce14dab3?" — attempt FAILED (attribution solid), with one precision nit (Finding 2)

- The archived commit JSON (`upstream/commit_ce14dab3.json`) contains the actual
  diff hunk to `projects/miopen/src/kernels/miopen_type_traits.hpp`: the outer
  `+#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` … `+#else` /
  `+#include <type_traits>` / `+#endif` wrapper is ADDED by this commit — direct,
  not inferred. PR metadata (`upstream/pr3803_miopen.json`) confirms #3803
  "All 7.0 hipRTC fixes", merged 2025-06-16T18:15:28Z.
- **[R]** I binary-grepped the shipped wheel DLL
  (`..._rocm_sdk_libraries\bin\MIOpen.dll`): the string
  `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` occurs exactly **2** times
  (matching the "2 sites" of the naive-D patch) and
  `HIPRTC compile ROCm include path argument` occurs **1** time — the develop
  `comgr.cpp` `BuildHip()` logic cited in the docs is physically in the rockrel
  3.5.2 binary.
- **[R]** I diffed `upstream/miopen_type_traits.hpp` (develop fetch) against the
  wheel-extracted header: content-identical (CRLF/LF only), confirming P2-C018.
- Nit: at ce14dab3 the inner gate macro was `MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS`;
  the wheel/develop header uses `MIOPEN_HIP_RUNTIME_COMPILE`. So the file WAS
  edited again between June 2025 and the rockrel branch point, and no git-log of
  the file across that interval is archived. This does not disturb the
  attribution of the outer gate (the diff is direct evidence), and the RCA's own
  counter-evidence column for P2-C019 already flags that PR motivation is
  "partially inferred" — honest handling. See Finding 2.

### 1.3 Mechanism story (builtin header, -I precedence, kernel-DB cache) — no technical errors found

- **Builtin header / `__hip_internal`**: `upstream/hiprtc_clr.cpp` lines
  121–128 carry the comment ("decision to move type traits to `__hip_internal`
  namespace is made in 7.0…") and force-include `hiprtc_runtime.h` unless
  `--hiprtc-no-builtin-header`. Locally corroborated by the naive-D experiment
  itself: the compiler note in `candidateB/dll_gate_flip_experiment.txt` points
  at `hiprtc_runtime.h:1438` `__hip_internal::enable_if` — the builtin header
  is captured in the comgr temp (`extracted_kernel_tree/include/hiprtc_runtime.h`).
- **Windows triple / no stdlib path**: `upstream/hiprtcInternal.cpp` lines
  56–58 push `x86_64-pc-windows-msvc -fms-extensions -fms-compatibility` on
  `_WIN32`; no C++ stdlib include path is pushed anywhere in the archived
  source. Pre-MSVC clang search list
  (`hiprtc/gate25_amdclang_verbose.txt`) = resource dir + nonexistent
  VS8/9/10 fallbacks — matches the doc. MSVC absence pre-Gate-27 is proven
  (`msvc/gate26_msvc_discovery.txt`: no cl/vswhere/VS dirs/Windows Kits).
- **`-I$ROCM_PATH/include` honored + shadowing**: `upstream/comgr.cpp` lines
  838–844 gate the `-I` on the env var; poison v2
  (`msvc/gate32_poison_header_test_v2.txt`) proves at runtime that the `-I` dir
  resolves `<type_traits>` AHEAD of the auto-discovered MSVC STL. Include
  option support (`-I`/`-isystem` ok, `--include-path=` rejected) is archived in
  `hiprtc/include_option_probe.json`.
- **Kernel-DB cache effects**: the v1 poison test was cache-confounded and is
  retained as the confounder demonstration; v2 redirects
  HOME/USERPROFILE/LOCALAPPDATA with a positive control (the poison error proves
  recompilation occurred). `MIOPEN_USER_DB_PATH` not being honored is disclosed.
  The claims ledger pre-empts "warm cache masked the PASS results"
  (P2-C013/C016: scratch-DB forced-compile runs). I find no cache confound that
  survives v2.
- **Line-number cross-check [R]**: the naive-D failure lines quoted in the docs
  (`miopen_type_traits.hpp:112 expected class name`) match the extracted wheel
  header EXACTLY (line 111–119 `is_pointer_helper : false_type/true_type`,
  outside the 6.0.25–6.1.24 window gate at line 80); `enable_if` via
  `__hip_internal` at lines 105–108 matches; `std::is_same`/`std::enable_if`
  use sites in `vector_types.hpp:111` and
  `bnorm_spatial_activation_functions.hpp:40` match the requirements table.
- Cosmetic: the wheel's `hiprtcVersion()` self-reports `9.0` while
  `torch.version.hip = 7.14.60850` — consistent across all probe JSONs and the
  probe script (`scripts/phase2/hiprtc_probe/hiprtc_probe.py` reads the API
  directly); the RCA never equates the two, so no error (Finding 4).

### 1.4 Candidate-fix conclusions — supported by the raw logs

- **Candidate A validated**: three channels. A-1 MSVC plain shell
  (`msvc/gate27_armA_plain_shell.txt` 6/6 SUCCESS; `gate27_armA_bn_repro.txt`
  PASS); A-2 INCLUDE-only (`gate27_armC_include_only.txt`); A-3 shim via
  `ROCM_PATH` cache-isolated (`candidateA/A_minimal.txt`, `A_variants.txt`
  5/5, plus gemm/conv/eval/issue3956/yololike all PASS). Regression matrix 8/8
  (`regression/gate33_matrix_rerun.txt`), numerics max_abs 7.152557e-7 ≤ the
  claimed 7.2e-7 (`regression/gate34_numerics.txt`), YOLO closure both AMP
  modes exit 0 with exactly the metrics quoted in the RCA
  (`yolo_closure/train_default_amp.txt`: P=0.545 R=0.963 mAP50=0.942
  mAP50-95=0.668; `train_amp_off.txt`; fresh-shell re-validation
  `restart/gate36_fresh_shell.txt`).
- **Naive D falsified**: `candidateB/dll_gate_flip_experiment.txt` fails at the
  exact rotted-shim sites predicted from the extracted header. **[R]** I
  re-hashed the shipped MIOpen.dll after the experiment: SHA256 prefix
  `74b4ee038803606e` — identical to the pre-install/pre-patch record in
  `gate27_28_msvc_ab_decision.md`, confirming the restore claim (P2-C021).
- **Candidate B "principally validated"** is accurately hedged; the patch shape
  (`patches/candidate_B_miopen_type_traits.patch`) exists and does what the doc
  says (unconditional traits block `#if 1`, proper `enable_if` not via
  `__hip_internal`).

### 1.5 H10-vs-H11 honesty (brief question 1) — handled honestly

`PHASE2_HYPOTHESES.md` P2-H3 is explicitly split: "Unresolved as 'intended';
Supported as 'operative'", and the reading notes say claiming AMD "intended"
the MSVC prerequisite "would be unsupported — their public docs say otherwise
(that gap is itself part of the defect)". The docs-side anchor (Phase-1 C028:
AMD Windows install docs list no MSVC/VS prerequisite) exists in
`docs/CLAIMS_AND_EVIDENCE.md` line 39. The Gate-28 ownership analysis keeps
machine-level sufficiency (MSVC present → PASS, plain shell) separate from
product-level design ownership (wheel: no STL provision/discovery/docs; MIOpen:
HIP≥7.0 RTC gating), and refuses single-layer blame. No intent is attributed
without evidence.

## 2. Findings (all non-blocking)

1. **Mislabeled inventory artifact** —
   `evidence/phase2/raw/miopen/extracted_kernel_tree/STD_INVENTORY.txt`'s
   heading claims its angle-include/std-identifier counts are over the BN
   kernel's closure, but they demonstrably cover the full 158-header embedded
   tree (`<utility>`, `<algorithm>`, `std::forward`, `std::array`, … are not in
   the 13-file closure). The doc's prose explains this correctly, but P2-C017
   cites this artifact; re-label (e.g., "full embedded tree inventory") or split
   it into closure-only and tree-wide sections so the artifact cannot be read
   against the claim.
2. **Attribution precision** — between ce14dab3 and the rockrel snapshot the
   header was edited again (inner macro renamed
   `MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS` → `MIOPEN_HIP_RUNTIME_COMPILE` per the
   archived diff vs the extracted header). The outer-gate attribution to
   ce14dab3 stands on the direct diff, but the RCA should say in one sentence
   that the wheel header is not ce14dab3's exact product, and ideally archive a
   `git log` of the file from ce14dab3 to the wheel's branch point.
3. **"no MSVC" phrasing in A-3** — `candidateA/A_minimal.txt` says "no MSVC
   dependency" while MSVC was in fact installed on the machine at run time
   (13:40, post-Gate-27). The conclusion survives because the poison test
   (P2-C015) proves the `-I` shim dir SHADOWS MSVC discovery — the claims
   ledger's counter-evidence column states this — but the log header and the
   "(no MSVC)" shorthand in docs/tables invite over-reading. Reword to "does
   not rely on MSVC (shadowing-proven)".
4. **Version-string footnote** — the wheel hiprtc reports
   `hiprtcVersion()==9.0` against `torch.version.hip 7.14.60850`; harmless
   (never conflated in the RCA), worth one footnote to preempt reader
   confusion.

## 3. Open risks I concur with (already declared in the RCA)

- MIOpen #3956 correlation is external/signature-only (P2-C026, Medium).
- A type_traits-only shim does NOT cover the non-BN std-consuming runtime
  kernels (CK reduction/layernorm headers requiring `<utility>` etc. — visible
  in STD_INVENTORY and in the `a_grid_desc_*` CK tuning output during the YOLO
  closure runs); the RCA flags this and ties it to the Candidate-B shim-repair
  shape rather than overclaiming the BN result.
- Reboot persistence untested (Gate 37).

## 4. Bottom line

Every adversarial probe I ran — closure re-derivation, DLL binary grep,
header/line-number cross-checks, DLL re-hash, develop-vs-wheel diff, cache-confound
audit — corroborated the primary agent's evidence rather than breaking it. The
LEVEL-3 statement (MIOpen PR #3803's HIP≥7.0 RTC gating requires real
`<type_traits>`; the Windows wheels' msvc-triple clang/HIPRTC has no
discoverable C++ stdlib and no documented MSVC prerequisite; joint wheel ×
MIOpen ownership) is established at the stated confidence, and the fix-layer
conclusions (A validated, naive-D falsified, B as upstream shape) match the raw
artifacts.

**VERDICT: PASS**
