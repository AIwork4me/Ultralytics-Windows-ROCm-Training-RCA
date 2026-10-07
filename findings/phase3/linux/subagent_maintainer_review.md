# Subagent Maintainer Review — Gate L45

Date: 2026-10-08. Independent maintainer-simulation reviewer (fresh context).
Verbatim text below; validator remediation noted at top.

## Verdict (reviewer)

ADEQUATE_WITH_CONDITIONS

## Validator remediation of reviewer conditions (GATE L46)

- BLOCKER-1 (stale conclusions/manifest): fixed — run-2 conclusion/summary/
  final_gate rewritten, BLOCKED marker superseded, manifest regenerated
  (this commit series).
- MAJOR-1 (build parity + 690/800): fixed — configure/build logs + both
  CMakeCaches archived under build_*/; parity_note.txt explains the
  incremental-vs-full target count and the contained first-configure
  contamination.
- MAJOR-2 (no-STL narrative vs data): fixed — corrected to the measured
  PARTIAL-STL reality; extended-canary E1 (unpatched fails 'utility' not
  found through real comgr RTC) + E2 (patched guard fires by design).
- MAJOR-3 (0002 paths uncompiled on Linux): fixed — extended-canary E3/E4
  (tensor_view RTC, radix value-equivalence static_asserts, freestanding
  initializer_list chain zero-STL, Kthvalue TU both trees).
- MAJOR-4 (radix not probe-gated; Kthvalue runtime): value equivalence
  asserted + compile coverage added; RUNTIME kthvalue remains an open
  condition (documented in summary; MIOpenDriver was OFF in both legs,
  mirroring the Windows configuration).
- MAJOR-5 (CK/PReLU coverage claims): fixed in RTC_KERNEL_SELECTION.md
  (torch-native PReLU, CK plugin failure symmetric both builds).
- MAJOR-6 (single arch/line): accepted as documented condition for CI.
- MINORs: YOLO wheel-vs-source labeled; amp-default self-disable labeled;
  sqlite provenance recorded in manifest notes; docstring NIT fixed.

## Full verbatim review

(The reviewer's complete output follows, verbatim.)

---

# Maintainer Review — Linux cross-platform validation of the MIOpen HIPRTC self-containment patch (P3-FINAL)

VERDICT: **ADEQUATE_WITH_CONDITIONS**

The core no-regression mechanism for Linux HIP>=7 **when an STL resolves** is well evidenced: same source SHA `b68f8944` on both legs with a hash-verified, mutation-audited patch delta; per-run `dladdr(miopenCreate)` binding proof for the source-built libraries; token-identical preprocessed wrapper output in the with-STL arm (2,903,968 canonical bytes both trees); bit-identical BN numerics (37 tensors, overall `max_abs = 0.0`, seeded, CPU-referenced); and an honest, re-verified STL-provider root cause (`-H` trace inside `hiprtcCompileProgram`).

[Reviewer BLOCKER-1]: submission's structured conclusion contradicts claimed result (stale run-1 files: linux_conclusion.json BLOCKED/null, final_gate NOT_STARTED, BLOCKED marker never lifted, SUMMARY header BLOCKED); run-2 evidence outside the integrity manifest; l47_final scan untracked stray.

[Reviewer MAJOR-1]: build-config parity asserted not archived; 690 vs 800 target asymmetry unexplained; ambient ldd (no LD_LIBRARY_PATH) in build_unpatched/provenance.txt resolves ROCm deps to /opt/rocm-7.2.1; the controlled-env ldd proof attached only to the FAILED probe v1.

[Reviewer MAJOR-2]: no-STL coverage argument contradicts its own data — arm B records rtc_compile=6 'utility' file not found while the narrative claims comgr always bundles libc++; fallback exercised only via host -fsyntax-only (no device codegen); freestanding headers never device-compiled on Linux; selection logic never observed in a real RTC TU.

[Reviewer MAJOR-3]: none of patch 0002's changed paths (radix.hpp, tensor_view.hpp, miopen_freestanding_initializer_list.hpp) compiled on Linux, even at host syntax level; RTC_KERNEL_SELECTION's claim they are "covered by Gate L33" incorrect.

[Reviewer MAJOR-4]: radix.hpp not probe-gated — changes the WITH-STL Linux path too; "provable no-op when an STL resolves" overstated; sole consumer MIOpenKthvalue has zero runtime coverage anywhere.

[Reviewer MAJOR-5]: static-CK wrappers (the only <utility>/std::forward RTC users, 14 TUs) never executed — CK grouped conv symbol resolution fails in every log; conv cases routed through Gemm* solvers; PReLU row attribution contradicted by torch-native dispatch (Windows Gate 68 observation).

[Reviewer MAJOR-6]: scope — one GPU arch (gfx1151), one ROCm line (7.14 wheels), no 10.x runtime, no second arch; non-BN matrix finiteness-only outside 6 BN cases.

[Reviewer MINORs]: YOLO PASS->PASS not clean A/B (wheel 3.5.2 vs patched source 3.6.2); patched-leg fresh-cache RTC-compile proof indirect; amp-default self-disabled (both legs effectively fp32); g57_results.jsonl lacks per-arm rc fields; stale artifacts; provenance ldd block unlabeled environment.

[Reviewer NITs]: arm-D docstring says 3 vs code checks 2; raw trace file with .json extension; patch DCO/author placeholders, double blank lines, duplicate new-file-mode lines; RTC_KERNEL_SELECTION should mark pooling/softmax limits coverage as control coverage.

Reviewer conditions before PR acceptance: (1) reconcile record + regenerate manifest; (2) prove build parity, archive caches/logs, explain 690/800; (3) close no-STL gap honestly (fix narrative or use failing comgr path to device-compile freestanding through hiprtc; extend canary to 0002 files); (4) runtime-execute a Kthvalue-class op under both source builds; (5) fix coverage claims; (6) broaden platform matrix in CI; (7) fill DCO identity.

Reviewer bottom line: scientific core sound; for gfx1151/ROCm 7.14 supports "no Linux regression"; package could not be submitted as-is (its own conclusion denied the work; manifest excluded decisive evidence; radix/no-STL fallback asserted rather than tested on this platform).

(End of reviewer output. Remediation of conditions 1,2,3,5 + partial 4 recorded at the top of this file; conditions 4-runtime, 6, 7 are producer/CI-side.)
