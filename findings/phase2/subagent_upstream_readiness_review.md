# Upstream Readiness Review — Reviewer C (rocm-libraries/MIOpen maintainer simulation)

Date: 2026-10-07. Branch: `rca/windows-gfx1151-rocm714-phase2`.
Mandate: review the Phase-2 evidence package as a **pre-PR submission to
rocm-libraries/MIOpen** (and, secondarily, TheRock/ROCm docs). Question:
what evidence, tests, or design justification would BLOCK acceptance?

Reviewed: `docs/PHASE2_LEVEL3_RCA.md`, `docs/PHASE2_RUNTIME_STL_REQUIREMENTS.md`,
`docs/PHASE2_CLAIMS_AND_EVIDENCE.md`, `docs/PHASE2_CROSS_VERSION.md` (untracked),
`patches/candidate_B_miopen_type_traits.patch`,
`patches/shim_stl/include/type_traits`,
`evidence/phase2/raw/upstream/{commit_ce14dab3.json,pr3803_miopen.json,miopen_type_traits.hpp,comgr.cpp}`,
`evidence/phase2/raw/candidateB/*` (all three files),
`evidence/phase2/raw/candidateA/A_variants.txt` + siblings,
`evidence/phase2/raw/regression/gate34_numerics.txt` + `gate33_matrix_rerun.txt`,
`evidence/phase2/raw/miopen/extracted_kernel_tree/` (closure re-derived
independently — the 13-file closure in the doc checks out against the
sources), `evidence/phase2/raw/msvc/gate32_poison_header_test_v2.txt`,
`evidence/phase2/SHA256SUMS.txt` (verified against working tree),
`scripts/phase2/*` (read for runnability), git state.

---

## 0. Preamble — what this reviewer accepts going in

The **diagnosis** is good and I would not dispute it: the standalone ctypes
HIPRTC reproducer (no torch/MIOpen), the no-include control that executes,
the MSVC A/B/C arms, the poisoned-header proof that `-I$ROCM_PATH/include`
is honored and shadows discovery, and the binary gate-flip falsification
together establish, at LEVEL 3, that PR #3803's HIP>=7.0 gate makes
runtime-compiled MIOpen kernels depend on a host C++ STL that the ROCm
7.14 Windows wheels do not ship or discover. The commit archaeology is
correct for `miopen_type_traits.hpp`. As an **issue report on MIOpen
#3956** with this repo attached, this package would be welcomed.

Everything below is about what blocks the **fix PR** (candidate B) and the
package's packaging/ownership claims.

---

## 1. Reproducibility from the repo alone

**Verdict: partial. A CI engineer can reproduce the *failure*, but not
most of the decisive experiments, and nothing reproduces the *fix*.**

What works:
- Phase-1 minimal repro scripts are runnable and parameterized enough;
  `gate22_env_verify.txt` + closure manifest pin the 45-package environment
  and 10-DLL SHA256 provenance.
- `scripts/phase2/hiprtc_probe/hiprtc_probe.py` is a clean standalone
  reproducer (see section 2).
- `26_candidate_fix_isolated.ps1` / `21_clean_repro.ps1` take
  `-EnvPython/-RcaRoot/-WorkDir` parameters and embed provenance headers in
  every artifact. Good practice.

Gaps:
1. **Hardcoded machine assumptions**: `hiprtc_probe.py` hardcodes
   `--gpu-architecture=gfx1151` and `hiprtc0714.dll`; no `--arch`, no
   DLL-version discovery. Useless as-is on gfx1200 (#3956's GPU) or any
   other ROCm wheel version. `hiprtc_compile_bnsources.py` likewise
   hardcodes `hiprtc0714.dll` and a default site-packages path.
2. **The two most persuasive experiments are not scripted**: the MIOpen.dll
   binary gate-flip (`dll_gate_flip_experiment.txt` — a length-preserving
   patch at 2 sites, SHA256-verified restore) and the poisoned-header test
   (`C:\hiprtc_poison\include\type_traits` with `#error`) exist only as
   output logs. No script in `scripts/` can re-run them. For a
   falsification experiment this load-bearing, that is not acceptable.
3. **No phase-2 orchestrator or CI hook**: `scripts/run_all_rca.ps1` covers
   Phase 1 only. Gates 24-36 are individually scripted (some parameterized,
   some not) with no entry point, no ordering, no expected-output fixtures.
   A reviewer cannot run "the Phase-2 suite" and compare against the
   archived results.
4. **Evidence-custody drift in the working tree**:
   `evidence/phase2/raw/restart/gate36_fresh_shell.txt` was re-run at
   14:08, *after* the Gate-43 manifest (14:05) — its current SHA256
   (`16685c41...`) does not match `SHA256SUMS.txt` (`6583ba08...`), and
   `docs/PHASE2_CROSS_VERSION.md` is untracked. For a package whose
   credibility rests on "committed byte-exact, checksummed" provenance,
   shipping a submission with stale checksums is self-inflicted damage.
   Regenerate the manifest or drop the later run.

## 2. Minimal reproducer quality (standalone HIPRTC ctypes probe)

**Verdict: acceptable, better than a PyTorch repro; minor fixes needed.**

This is exactly the right shape of evidence for a rocm-libraries issue:
zero torch/MIOpen/Ultralytics dependencies, direct
`hiprtcCreateProgram`/`hiprtcCompileProgram` on the wheel's own DLL,
per-header A/B matrix, executing control proving the toolchain otherwise
works. I would ask an issue filer for precisely this. Before it goes in a
PR description: parameterize arch and DLL name, print the resolved
`HIP_PACKAGE_VERSION_FLAT`, and attach the JSON fixtures
(`header_matrix.json`) rather than prose summaries.

One caveat the PR text must carry: the "no-MSVC" condition for the Gate-32
shim experiments was **emulated by `-I` shadowing** (poison test), not by
machine state — MSVC Build Tools were installed at Gate 27 and never
removed, so every later "shim, no MSVC" run happened on an MSVC-present
machine. The shadowing proof makes the inference sound, but the PR must
state it; a maintainer will find Gate-27 in the timeline.

Also note `A_variants.txt` records `miopen_kernel: null` for all five
cases: the harness detects the compiled kernel only via MIOpen log text,
which was not enabled. PASS is therefore inferred from exit code + absence
of `type_traits` errors under cache isolation (fresh compiles). Acceptable,
but the PR wording should not claim "kernel confirmed compiled" from these
files.

## 3. Fix quality — candidate B patch and shim

**Verdict: not upstream-quality. This is the core blocker. I would close
the PR with "request changes" on sight of the diff.**

Findings on `patches/candidate_B_miopen_type_traits.patch`:

1. **The patch has never been compiled.** Both archived validation runs
   (`candidateB/standalone_compile_ab.txt`, `..._v2.txt`) show
   `compile: 6` for **both** the baseline and patched arms — the harness
   failed at `configuration.hpp:80` (`(UseFp16+UseFp32+UseFpmix+UseBfpmix)
   == 1` evaluated 0) because the mirrored `-DMIOPEN_USE_*` options did not
   take effect in the runs that were archived. The baseline arm didn't even
   fail on `type_traits` (MSVC was present by then), contradicting the
   file's own "expect FAIL at type_traits" annotation. The repo's
   `hiprtc_compile_bnsources.py` (which does pass the full option set) has
   **no archived output at all**. So the only artifact proposed for
   upstream merge exists as a diff between a fetched header and a session
   temp directory (`/c/Users/rocm/AppData/Local/Temp/gate32_candB/...`),
   with zero successful compile evidence anywhere in the package. The
   claims ledger words this carefully ("principally validated ... via A's
   injection channel"), but what was validated is the **shim content**
   served as `<type_traits>` through `-I`; the **patched
   `miopen_type_traits.hpp`** was never in any compile path.

2. **The gate flip is wrong.** `#if HIP_PACKAGE_VERSION_FLAT <
   7000000000ULL` → `> 7000000000ULL` inverts the branch for **HIP 6.x**
   (RTC kernels would now get real `<type_traits>` where they previously
   got the shim — a regression for exactly the population the shim was
   built for), takes real STL at exactly 7.0.0, and re-enables the shim
   for HIP 8.x — none of which is intended or defended. The correct shape
   is to delete the outer version gate entirely and restore
   `#ifdef MIOPEN_HIP_RUNTIME_COMPILE` as the sole discriminator (RTC ⇒
   shim, offline ⇒ real STL), i.e., revert `miopen_type_traits.hpp`'s
   #3803 hunk. `#if 1` is experiment scaffolding and must not survive.

3. **Scope: one header fixed, defect class is two.** The extracted wheel
   `miopen_utility.hpp` carries the **same** outer HIP>=7 gate (its
   `std::forward` shim is disabled; real `<utility>` required in RTC
   mode). The patch does not touch it, and no justification is given for
   why `type_traits` alone suffices upstream — it suffices for the **BN
   closure only** (this is honestly documented as an open item in the RCA,
   but then the patch should not be titled as *the* candidate-B fix).
   `miopen_limits.hpp` (RTC-gated custom `numeric_limits`, fine) and
   `miopen_cstdint.hpp` (RTC-only gate, fine) need only an audit note.

4. **No test coverage beyond BN / beyond Windows.** The shim defines 11
   entities. `STD_INVENTORY.txt` shows the embedded 158-header set also
   uses `std::forward` (23x), `std::numeric_limits` (5x), `std::array`,
   `std::plus`, `std::is_trivially_copyable_v` (2x), etc. Any RTC kernel
   whose closure needs a trait outside the shim set will now hard-fail at
   compile time on **Linux too** (where real STL is present and post-#3803
   kernels may have come to rely on it). Nobody has enumerated the
   RTC-compiled kernel set (`MIOpenKthvalue.cpp` — made to include
   `miopen_type_traits.hpp` by #3803 itself — CK reduction wrappers,
   GroupNorm/LayerNorm/SoftmaxAttn, etc.) against the shim's coverage.
   That enumeration is a prerequisite for the PR, ideally shipped as a
   static-audit script + a compile-canary in MIOpen CI.

5. **Patch hygiene**: not a `git format-patch` against rocm-libraries
   paths (`projects/miopen/src/kernels/...`), no commit message, no
   sign-off, dead version-window scaffolding left in place, no
   `patches/README` explaining provenance.

6. **Design question I would raise in review**: reviving `namespace std`
   definitions is technically UB (and was the source of the original
   hiprtc builtin-header conflicts that #3803 was reacting to — see
   `hiprtc_clr.cpp` comment re `__hip_internal`). Restoring the
   pre-#3803 property is defensible (and matches #3803's *own* commit
   bullet "Include miopen_type_traits.hpp instead of type_traits for
   backwards compatibility"), but I would want the freestanding traits in
   a **dedicated header** (e.g., `miopen_freestanding_type_traits.hpp`)
   with `static_assert` self-tests for every trait, included by
   `miopen_type_traits.hpp` in RTC mode — rather than re-growing an
   ad-hoc `std` namespace inline — plus a guard against co-inclusion with
   a real `<type_traits>`. Alternative (less good, still acceptable if
   argued): keep the inline restore as a minimal revert.

7. The shim itself (`patches/shim_stl/include/type_traits`) is a clean,
   readable 48-line subset — fine as a *user workaround* artifact. It is
   Candidate A's experiment, not upstream material, and should not be
   presented in the PR as the proposed source change.

## 4. Scope / ownership — does the package over-claim?

**Verdict: the layer analysis is fair, but the package has no routing plan,
and one factual over-attribution.**

- The joint-ownership conclusion (wheel distribution + MIOpen gate) is
  well-argued and the three remedies (docs prerequisite, wheel STL
  bundling, MIOpen shim restore) are correctly classified by layer. But
  there is **no submission plan mapping artifact → destination repo**:
  candidate B → rocm-libraries PR; wheel STL bundling / `-I` injection →
  TheRock (or whichever repo owns "rockrel" wheel assembly — the package
  itself admits "pipeline itself not audited", P2-C006); MSVC prerequisite
  → ROCm docs. As submitted, a single PR narrative mixing all three will
  bounce between repos. `docs/NEXT_STEPS.md` is stale (still frames
  LEVEL-3 discrimination as future work).
- **Factual over-attribution**: LEVEL3_RCA item 5 and
  PHASE2_RUNTIME_STL_REQUIREMENTS §3 say commit `ce14dab3` wrapped
  `miopen_type_traits.hpp` "(and `miopen_utility.hpp`)". The package's own
  archived `commit_ce14dab3.json` lists 30 files — `miopen_utility.hpp`
  is **not** among them. The `<utility>` gate's introducing commit is
  unidentified. Fix the narrative before filing; a maintainer will check.
- Internal inconsistency: `STD_INVENTORY.txt` is labeled "angle-include
  directives in extracted closure (files actually reachable from
  MIOpenBatchNormFwdTrainSpatial.cpp)" and yet counts `<utility>` (4x),
  `<limits>` (3x), `<functional>`, `<algorithm>`, `<initializer_list>` —
  which the docs say are *not* in the BN closure. I re-derived the
  13-file quoted-include closure from the extracted tree: it is correct
  and contains only `<type_traits>` as a non-HIP angle include. So the
  *inventory's* "closure" label is wrong (it spans a broader reachable
  set) and the closure-computation is "archived in-session", not in-repo.
  Ship the closure script (`25_runtime_stl_inventory.py` exists — make it
  emit the closure + effective angle-includes under the RTC predefine
  set) and fix the label; otherwise P2-C017 reads as self-contradictory.

## 5. What a maintainer requires before merge

1. **Affected-version matrix, executed** — not just reasoned. The
   cross-version doc is good thinking, but every cell beyond 7.14/gfx1151
   is inference. Required: one more Windows wheel line (7.2.1 if
   installable — #3956's stack), and an explicit statement of the first
   release carrying #3803. ROCm 10.x: check whether the gate still exists
   in-tree; say so either way.
2. **Linux regression runs** — none exist. The patch changes RTC compile
   behavior on ALL platforms; MIOpen's Linux CI (`MIOPEN_USE_HIPRTC=1`
   test paths: batchnorm, reduction/CK, layernorm, softmax, kthvalue) must
   run on the patched tree, plus one manual Linux run demonstrating the
   shim path compiles+passes numerics. The package's own numerics harness
   (gate34) is a good template — port it.
3. **TheRock wheel-pipeline implications** — the wheel-side remedy
   (bundled freestanding STL + automatic `-I`) changes what every wheel
   consumer sees and interacts with `-I$ROCM_PATH/include` shadowing
   (proven to override MSVC discovery — which cuts both ways). That
   belongs in a TheRock issue with the poison-header experiment attached,
   not in the MIOpen PR; the MIOpen PR needs only a "see also" link.
4. **Direct validation of the actual patch text** through the real MIOpen
   path (patched source tree, `AMD_COMGR_SAVE_TEMPS`, cache-isolated),
   replacing today's content-level inference.
5. **Docs**: a PR-ready upstream report (markdown, self-contained, no
   "Gate" jargon) with the minimal repro, the DLL provenance, and the
   matrix — currently the material is spread across five internal-style
   gate documents.

---

## Blocking findings

1. **B1 — Candidate B patch never compiled; validation is content-level
   inference.** Both archived direct-validation runs failed for harness
   reasons (`standalone_compile_ab*.txt`, `compile: 6` in both arms;
   config static_assert; options not effective); no successful compile of
   the patched header exists in the package.
2. **B2 — Gate flip regresses HIP 6.x RTC and leaves `#if 1`
   scaffolding** (`< 7000000000ULL` → `> 7000000000ULL`); intended
   semantics (RTC-mode-only shim) not expressed; not a git patch; no
   commit message/sign-off.
3. **B3 — Incomplete scope + no cross-kernel trait audit.**
   `miopen_utility.hpp` carries the same HIP>=7 gate and is untouched;
   no enumeration of std usage across ALL RTC kernels vs the 11-trait
   shim (STD_INVENTORY shows `std::forward`, `std::numeric_limits`,
   `std::is_trivially_copyable_v`, `std::array`, `std::plus` in the
   embedded set); Linux HIP>=7 RTC kernels are at risk of new
   hard-fails.
4. **B4 — No Linux runs, no second version point, no ROCm-10 statement**
   (`docs/PHASE2_CROSS_VERSION.md` — all inference beyond 7.14/gfx1151,
   and the file is not even committed).
5. **B5 — Decisive experiments not reproducible from the repo**: DLL
   gate-flip and poisoned-header tests have no scripts; probes hardcode
   `gfx1151`/`hiprtc0714.dll`; no phase-2 orchestrator/CI entry point.
6. **B6 — Evidence-custody drift**: `gate36_fresh_shell.txt` SHA256 no
   longer matches `SHA256SUMS.txt`; `PHASE2_CROSS_VERSION.md` untracked.
7. **B7 — Narrative errors a maintainer will catch**: `miopen_utility.hpp`
   gate wrongly attributed to `ce14dab3` (contradicted by the package's
   own archived commit JSON); `STD_INVENTORY.txt` "closure" label
   contradicts the 13-file closure claim; `miopen_kernel: null` fields
   unexplained; "no-MSVC" runs actually executed on an MSVC-present
   machine (shadowing argument only).
8. **B8 — No artifact→repo routing plan** (MIOpen PR vs TheRock wheel
   issue vs ROCm docs); single-package submission would bounce.

## What would make it submittable

To **rocm-libraries/MIOpen** (fix PR):
- Rewrite candidate B as: revert the #3803 outer-gate hunk on
  `miopen_type_traits.hpp` **and** apply the equivalent change to
  `miopen_utility.hpp`; repair the rotted window (traits unconditional in
  RTC mode; proper `enable_if`, not `__hip_internal`); prefer a dedicated
  freestanding-traits header with `static_assert` self-tests; clean
  `git format-patch`, commit message citing #3956 and the Windows-wheel
  mechanism, sign-off.
- Validate the actual patched tree through real MIOpen (comgr temps,
  cache-isolated) on Windows; run the BN/numerics matrix on it.
- Static-audit script: all `src/kernels/**.cpp` (RTC set) x std-entity
  usage vs shim coverage; add as CI canary.
- Linux CI green (HIPRTC mode) + one manual Linux numerics run.
- Port the fix harness (`hiprtc_compile_bnsources.py`) to arch/version
  parameters and archive its outputs.

To **TheRock / wheel owners** (packaging issue, parallel):
- File separately: wheel ships msvc-triple clang+hiprtc with no C++ STL
  and no include-path configuration; propose bundled freestanding STL +
  automatic `-I`, or a documented MSVC prerequisite; attach the ctypes
  probe + poison-header experiment (scripted) and the Gate-25/26
  discovery evidence.

To **MIOpen #3956 / ROCm docs** (immediately submittable today, minor
edits): the RCA report as a comment, with the 5-line repro, the standalone
probe (parameterized), and the version-window reasoning; plus a
docs PR declaring MSVC Build Tools as a prerequisite for pip-wheel ROCm on
Windows.

Package hygiene (all destinations): re-generate
`evidence/phase2/SHA256SUMS.txt`/manifest after the Gate-36 re-run (or
revert the file); commit `PHASE2_CROSS_VERSION.md`; fix the
`miopen_utility.hpp` attribution and the STD_INVENTORY label; archive
closure-computation as a script; add one page mapping each artifact to its
destination repo.

---

## Verdict

**CONDITIONAL PASS.**

- As a **root-cause analysis / upstream issue report**: would be accepted
  (high-quality evidence chain; the maintainer-facing report itself still
  needs to be written — today it exists only as internal gate documents).
- As a **pre-PR for the candidate-B source fix**: **not submittable** —
  the patch has never been compiled, has the wrong gate semantics,
  incomplete scope, and no Linux/version-matrix coverage.

**Top 3 blockers:** (1) the candidate-B patch is unvalidated — its only
archived direct-compilation attempts failed in both arms for harness
reasons; (2) the gate flip regresses HIP 6.x RTC and the patch fixes only
`type_traits` while the same defect gate exists in `miopen_utility.hpp`,
with no RTC-kernel-wide trait audit behind the 11-trait shim; (3) zero
cross-platform/version evidence (no Linux run, no second ROCm version,
ROCm 10 unchecked) plus non-reproducible load-bearing experiments
(unscripted DLL-flip and poison tests, hardcoded gfx1151/hiprtc0714).
