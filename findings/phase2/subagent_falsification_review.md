# Phase-2 Reviewer B — Falsification Specialist (Gate 45 panel)

Date: 2026-10-07. Mandate: find alternative explanations that still fit
ALL Phase-2 results — not to summarize them. Target conclusion:
`docs/PHASE2_LEVEL3_RCA.md` (MIOpen #3803 HIPRTC gating needs real
`<type_traits>`; Windows wheel clang/hiprtc has no discoverable STL; MSVC
install or `-I` shim fixes the chain including YOLO training).

Scope read: `docs/PHASE2_LEVEL3_RCA.md`, `docs/PHASE2_CLEAN_ENVIRONMENT.md`,
`docs/PHASE2_CLAIMS_AND_EVIDENCE.md`, `docs/PHASE2_SUMMARY.md`,
`docs/PHASE2_CROSS_VERSION.md`, `docs/PHASE2_HYPOTHESES.md`,
`findings/phase2/{gate27_28_msvc_ab_decision,clean_env_result,
subagent_gate_23_review}.md`, and the raw artifacts cited below.
Independent verifications performed by this reviewer (not re-readings of
the primary agent's logs) are marked **[R]**.

## Verdict: **PASS** — no alternative explanation survives; 3 non-blocking
wording/custody corrections requested (§7). The two strongest near-miss
alternatives (kernel-DB caching; MSVC leakage into the shim runs) were
carried to ground and eliminated with evidence the primary agent had not
archived (§2, §3).

---

## 1. Independent re-derivations and physical-evidence checks

1. **[R] Closure re-computation.** Wrote an include-graph BFS over
   `evidence/phase2/raw/miopen/extracted_kernel_tree/` starting at
   `MIOpenBatchNormFwdTrainSpatial.cpp`: exactly **13 local files**, and
   the only non-HIP angle-include in the closure is `<type_traits>`
   (two sites, `miopen_type_traits.hpp:147/151`). Independently
   reproduces P2-C017 and confirms Reviewer A's finding that
   `STD_INVENTORY.txt`'s heading mislabels a 158-header whole-tree
   inventory as the BN closure (`<utility>/<limits>/<algorithm>/
   <functional>` live in non-BN headers).
2. **[R] Isolation-dir forensics.** The candidate-A cache-isolation dir
   still exists on disk
   (`%TEMP%\gateA_iso_4c7e525c\`). Its `.miopen/cache/3.5.2.cd957402/
   gfx1151_20.ukdb` (mtime 13:41) physically contains **14 ×
   MIOpenBatchNormFwdTrainSpatial.cpp, 3 × MIOpenBatchNormFwdInferSpatial.cpp,
   4 × MIOpenIm2d2Col.cpp** entries, and its redirected
   `AppData\Local\comgr\` holds a populated llvmcache. The runner
   (`scripts/phase2/26_candidate_fix_isolated.ps1`) creates this dir from
   a **fresh GUID per invocation** and redirects HOME/USERPROFILE/LOCALAPPDATA.
   Therefore the shim-run BN passes cannot have been kernel-DB cache hits:
   the kernels were compiled *inside* the isolated HOME during the run.
3. **[R] RTC-mode include trace (new evidence, closes the MSVC-leakage
   gap).** Preprocessed the real extracted BN kernel with the wheel clang
   (`-x hip --cuda-device-only`, `-D__HIPCC__=1 -D__HIPCC_RTC__=1
   -D__HIP_DEVICE_COMPILE__=1 -DHIP_PACKAGE_VERSION_FLAT=7140060850ULL`,
   `-I` shim + wheel include root), `-E -H`: **exit 0, exactly one std
   header consumed — the shim's `type_traits` — and ZERO
   `C:\BuildTools` headers in the trace.** The `<array>/<functional>/
   <algorithm>` pulls seen without `__HIPCC_RTC__` are host-branch-only
   (guarded by `#if !defined(__HIPCC_RTC__)` in
   `hip/amd_detail/amd_hip_vector_types.h:30-33` and
   `amd_warp_sync_functions.h:18-23`). This directly proves, at include
   resolution level, that the BN closure + HIP headers need nothing from
   MSVC when the shim is on the `-I` path. (Caveat: macro set approximates
   comgr's; the runtime poison test remains the in-situ complement.)
4. **[R] DLL restoration re-verified.** SHA256 of the live
   `_rocm_sdk_libraries\bin\MIOpen.dll` =
   `74b4ee038803606e6ea4846362a8565f…` — identical to the pre-patch /
   Phase-1 record, confirming the naive-flip experiment's restore claim.
5. **[R] Default kernel-DB census.** `~/.miopen/cache/3.5.2.cd957402/
   gfx1151_20.ukdb` now holds 85 BwdSpatial / 90 FwdTrainSpatial / 8
   FwdInferSpatial entries — i.e., post-MSVC BN kernels were genuinely
   compiled into the default DB (pre-Gate-27 it had zero BN entries per
   the Gate-23 audit). Corroborates that arm A's PASS was a fresh
   compile, not a hit.
6. **[R] Probe hygiene.** `scripts/phase2/hiprtc_probe/hiprtc_probe.py`
   passes exactly one compile option (`--gpu-architecture=gfx1151`) and
   loads `hiprtc0714.dll` by absolute path; arm A's runner header shows
   `INCLUDE` explicitly cleared. The pre/post-MSVC standalone flip is
   option-identical and env-identical.
7. **[R] Phase-1 variants cross-check.**
   `evidence/raw/batchnorm/bn_variants_results.json`: bn1d_3d/bn2d/bn3d
   failed in Phase 1 with the type_traits chain (bn1d_2d/groupnorm passed
   then too); `candidateA/A_variants.txt` shows 5/5 pass under the shim.
   `miopen_kernel: null` on passing cases is a probe artifact (the script
   extracts kernel names only from failing MIOpen log lines), not
   evidence of native-path bypass.

## 2. Attack 1 — could kernel-DB caching explain the flips? NO (five
independent eliminations)

- **Standalone flips cannot be cache-mediated at all.** The decisive
  pre/post-MSVC flip (Gate 24 → arm A) is a ctypes probe calling
  `hiprtcCreateProgram`/`hiprtcCompileProgram` directly: no MIOpen, no
  kernel DB exists in that path, probe options identical, INCLUDE
  cleared. The failure (`'type_traits' file not found`) occurs in the
  clang frontend before any codegen caching could matter.
- **Arm A BN PASS could not be a hit.** Pre-Gate-27 the default ukdb had
  zero BN entries (BN compiles had never once succeeded on this machine);
  a hit was therefore impossible, and post-run the DB contains the BN
  entries ([R] §1.5). The scratch-DB propagation run
  (`gate32_rocm_path_propagation_v2.txt`, 13:37:26) additionally logs
  `KernDb database not present` before its PASS — a second, DB-level
  forced-compile confirmation.
- **Poison v2 is self-proving.** `gate32_poison_header_test_v2.txt`
  (13:38:21) FAILS *on the poisoned file itself* — a poison diagnostic is
  producible only by a fresh compile that read that file; a cache hit
  would have passed. v1 (13:37:45, PASS) is honestly retained as the
  cache-confounder demonstration.
- **Candidate A runs are cold by construction.** Fresh-GUID HOME redirect
  + physical ukdb/llvmcache contents inside it ([R] §1.2); the 22.76 s
  cold conv control in `A_conv.txt` is consistent.
- **Direction-of-bias audit (Gate 23) already showed the shared cache
  biases *against* reproducing the failure** (zero BN entries, conv-only
  content) — the failure reproduced anyway.
- Residual cache subtlety noted, non-causal: the comgr *llvmcache* under
  `LOCALAPPDATA` is a second persistent store; in candidateA it was
  inside the redirected dir (fresh), and a warm llvmcache cannot convert
  a frontend `'file not found'` failure into a success in any event.

## 3. Attack 3 — could the shim-dir successes be MSVC leakage? NO
(this was the most plausible surviving alternative; it does not survive)

The concern: MSVC was installed at 13:24 and never removed, so a
type_traits-only `-I` dir could pass while `<utility>`-class headers
silently resolve from `C:\BuildTools`, making "no MSVC" claim false and
the shim insufficient on a clean machine. Eliminated three ways:

1. Closure re-derivation ([R] §1.1): the 13-file BN closure contains no
   std header other than `<type_traits>`.
2. RTC-mode include trace ([R] §1.3): full preprocess of the real kernel
   with the shim consumes **zero** BuildTools headers — not even
   transitively via the HIP headers (their std includes are
   `__HIPCC_RTC__`-guarded).
3. Poison-shadowing (`gate32_poison_header_test_v2.txt`): the `-I` dir
   wins over auto-discovered MSVC for `<type_traits>`. One gap in that
   proof alone — the poison run aborts at the *first* fatal error, so it
   cannot show whether later std headers would also be needed — is
   exactly what (1)+(2) close.

Scope guard that remains true (and is honestly declared in the RCA's
Remaining-risks): this covers the **BN closure only**. Non-BN
std-consuming runtime kernels (CK `functional*.hpp` consumers using
`<utility>`, visible tree-wide in `STD_INVENTORY.txt` and in the
`a_grid_desc_*` tuning output during the YOLO closure runs) would NOT be
covered by a type_traits-only shim; those ran under full MSVC in Gate 35.
Consequently `PHASE2_SUMMARY.md`'s remedy #2 phrase "validated
end-to-end" overstates — the shim was validated end-to-end **for the BN
failure**, not for full YOLO training (see §6/F1).

## 4. Attack 2 — did VS Build Tools fix it via something other than STL
availability? NO

What the installer changed is enumerable: MSVC 14.44.35207 headers/libs,
WinSDK 10.0.26100.0, vswhere + VS setup registry; `cl` is NOT on PATH
(`gate27_post_install_record.txt`), and the failing-path ROCm DLLs are
SHA256-unchanged across the install (MIOpen `74b4ee03…`, hiprtc
`c6159dd1…`). The flip observed is on a ctypes probe that loads the
wheel DLL by absolute path with one fixed option and INCLUDE cleared —
no PATH, DLL-substitution, or env-var story can reach it. The only
mediator available to that process is clang's header search list, whose
change is directly observed (`gate25_amdclang_verbose.txt` before:
resource dir + nonexistent VS8/9/10 fallbacks; arm A re-probe after:
`-internal-isystem C:\BuildTools\...\include` + SDK dirs). Within "what
VS installed", the `<type_traits>` provider can only be the MSVC dir
(the SDK ships no type_traits), so even the MSVC-vs-SDK sub-alternative
collapses. Arm C (INCLUDE-only child) isolates the env-var channel;
candidate A isolates a non-MSVC content channel; arm A isolates pure
auto-discovery — three orthogonal channels converging on the same fix.
The one arm never run — "MSVC removed again → fails again" — is
mitigated by the DLL-flip experiment showing a header-broken BN still
fails in the MSVC-present world (MSVC presence does not globally mask
compile failures), and by the standalone probe's pre-install FAIL
residing in the same process shape as the post-install PASS.

## 5. Attack 4 — is the naive-flip falsification sound? YES

`candidateB/dll_gate_flip_experiment.txt` (13:45:31): the flipped gate
(`<7000000000ULL` → `<8000000000ULL`, 2 sites — string count in the
binary independently verified by Reviewer A) produces a *different*
failure signature than baseline — `miopen_type_traits.hpp:112 'expected
class name'` (rotted `false_type`), `no template named 'enable_if' in
namespace 'std'` with the note pointing at
`hiprtc_runtime.h:1438 __hip_internal::enable_if`, `std::is_same`
missing at `vector_types.hpp:111`. A signature change is itself proof
the preprocessor took the patched branch (the patch demonstrably took
effect); the failure is self-proof of a fresh compile (cache hits don't
fail); the errors are the *internal* pieces of the inline shim, so MSVC
presence is irrelevant to that branch (`<type_traits>` is never included
there). Restoration verified by my own re-hash ([R] §1.4) and by the
13:47 regression matrix passing 8/8 post-restore. Line numbers in the
experiment match the extracted wheel header exactly. Sound.

Related audit: `candidateB/standalone_compile_ab{,_v2}.txt` show BOTH
arms failing (`compile: 6`) on harness-config static_asserts ("only one
of these configs can and must be chosen") — a null result from a
standalone harness that lacks MIOpen's `-D` config macros. No doc cites
these as support; Candidate B is correctly hedged as "principally
validated" via A's injection channel. No overclaim, but the artifacts
could mislead a casual reader — worth a one-line README note (§7/F3).

## 6. Attacks 5–6 — overclaim audit and uncontrolled variables

Overclaim scan (docs vs raw evidence):

- **F1 (the one real wording defect):** `PHASE2_SUMMARY.md` remedy #2
  says the shim dir is "validated end-to-end", while
  `PHASE2_LEVEL3_RCA.md` Remaining-risks correctly restricts the
  type_traits-only shim to the BN closure and flags non-BN
  `<utility>`-consuming kernels as uncovered. A user who removes MSVC
  and relies on the 48-line shim alone could hit CK-kernel failures
  during full training. Fix the Summary to match the Level-3 scope.
- **F2:** RCA Q2's "(minimal BN → YOLO training) flips to PASS with no
  other change (Gate-27 arm A)" — YOLO closure was actually Gate 35, a
  separate experiment under the same machine state. The causal claim
  survives (identical state, nothing else changed), but the citation
  conflates two gates.
- **F3:** `candidateA/A_minimal.txt` header "no MSVC dependency" — MSVC
  was installed at run time. True in substance (poison shadowing + my
  [R] §1.3 trace), but phrase as "does not rely on MSVC
  (shadowing-proven; RTC-mode include trace consumes 0 BuildTools
  headers)" and archive the trace command/output as evidence.
- **F4:** `STD_INVENTORY.txt` heading mislabels the whole-tree inventory
  as the BN closure (already Reviewer A's Finding 1; confirmed by my
  independent BFS).
- **F5:** `standalone_compile_ab*.txt` null-result artifacts lack an
  explanatory note (§5 above).
- **F6 (custody, pre-flagged by the Gate-44 reviewer, reconfirmed):**
  `restart/gate36_fresh_shell.txt` (mtime 14:08) postdates the Gate-43
  manifest (14:05) — its SHA no longer matches `SHA256SUMS.txt`.

Hedges verified as accurate (no overclaim found): #3956 is claimed as
signature-identical only, with "not proven same root cause" stated
(`docs/EXTERNAL_EVIDENCE.md`, `PHASE2_CROSS_VERSION.md` "What Phase 2
does NOT claim"); the TheRock MSVC item is correctly scoped to
*build-time* prerequisites ("plausibility only", "does NOT prove the
#2169 user machine had MSVC"); "intended prerequisite" is explicitly
*not* claimed (P2-H3 "Unresolved as intended; Supported as operative");
ROCm 10.x wheels explicitly unclaimed; reboot explicitly untested.

Uncontrolled variables:

- **Python 3.13.13 vs 3.13.16** — affects only the Gate-23 base-vs-clean
  comparison, disclosed there; every remedy gate (24–36) used the same
  env interpreter and identical SHA256-verified native DLLs, so no
  remedy comparison crosses the interpreter variable.
- **Warm vs cold caches** — every load-bearing PASS/FAIL is either
  cache-impossible (standalone probes), cache-cold by construction
  (candidateA fresh-GUID iso; poison v2; scratch-DB propagation v2) or
  cache-empty for the relevant kernel family (arm A: zero pre-existing
  BN entries). Warm runs occur only in post-remedy regressions
  (Gates 33–36), where warm state is the realistic user condition.
- **MSVC discovery vs INCLUDE ordering** — arms A/B/C are separate
  processes with single-variable deltas (A clears INCLUDE; B sets full
  dev-shell env; C sets only INCLUDE); no cross-contamination observed
  (each log's env delta section shows only its own variable).
- **Post-13:24 permanence** — after Gate 27, MSVC is present for all
  subsequent gates. This is a one-way machine-state change inherent to
  the design; the DLL-flip FAIL at 13:45 in that same world rules out
  "MSVC presence magically fixes all BN compiles regardless of headers".
- **Timing plausibility check** — candidateA's per-run cadence (~3 s)
  is tight for a cold HIPRTC BN compile but is settled by the physical
  ukdb/llvmcache evidence in the fresh isolation dir ([R] §1.2); warm
  matrix runs in Gate 33 take ~2.4 s, leaving ~0.6 s for the small BN
  kernel compile, consistent with the 22.76 s conv outlier being a much
  larger kernel.

## 7. Requested corrections (non-blocking; none affects the verdict)

1. Reword `PHASE2_SUMMARY.md` remedy #2: "validated end-to-end for the
   BatchNorm failure chain (BN cases + controls); full-model training
   under shim-only (no MSVC) is NOT covered — non-BN runtime kernels
   need `<utility>`-class headers (see Level-3 Remaining risks)".
2. Reword the "(no MSVC)" phrasings (RCA Q8, P2-C016, A_minimal header
   context) to "does not rely on MSVC — shadowing-proven and
   include-trace-proven"; archive the RTC-mode `-E -H` command and its
   0-BuildTools trace as a phase2 artifact.
3. Hygiene: relabel `STD_INVENTORY.txt` (whole-tree vs BN closure);
   add a null-result note to `standalone_compile_ab*.txt`; refresh
   `SHA256SUMS.txt` for `gate36_fresh_shell.txt`; fix the RCA Q2 arm-A
   citation to include Gate 35.

## 8. Bottom line

Every alternative mechanism I attempted to construct — kernel-DB
caching, comgr llvmcache, VS-install side effects (DLLs/PATH/registry
beyond header discovery), SDK-instead-of-MSVC, MSVC leakage into the
shim runs, patch-not-applied artifacts in the naive-flip experiment,
interpreter-version confounds — is either structurally unable to produce
the observed signature set or is directly excluded by archived (and in
three cases newly-produced) physical evidence. The strongest surviving
*caveat*, not an alternative explanation: the validated remedies are
proven for the BN closure and (under MSVC) the full YOLO chain; a
type_traits-only shim without MSVC is proven only for the BN closure,
and user-DB persistence means post-remedy success can outlive later
header breakage until caches clear (reboot persistence separately
untested). The LEVEL-3 conclusion — joint MIOpen #3803 HIP≥7 RTC gating
× Windows wheel STL-provision gap, proximate cause "no discoverable C++
STL" — stands.

**VERDICT: PASS** (strongest surviving alternative explanation: **none**
for the stated conclusion; nearest survivors are scope caveats, §8).
