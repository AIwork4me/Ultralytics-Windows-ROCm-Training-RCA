# FINAL GATE — Phase 5.2 (W7900-PHASE52-BRIDGE-R1)

```
PHASE 5.2 — LINUX W7900 HANDOFF BRIDGE
======================================

ENVIRONMENT
GPU:              AMD Radeon PRO W7900 (gfx1100, PCI 1002:744b; ROCm name "W7900D")
LLVM target:      gfx1100
OS:               Ubuntu 24.04.4 LTS
ROCm version:     7.14.1 isolated wheel SDK (validation) / 7.2.1 system (untouched)
PyTorch:          2.12.0+rocm7.14.1 (venv)
HIPRTC:           libhiprtc.so.7 7.14.60850 (venv, dladdr-proven)
System ROCm contamination: NONE (live maps: 0 /opt/rocm objects)

WINDOWS FREEZE
Candidate ID:               P5.1-CANDIDATE-R1
RCA evidence SHA:           494907699f3b57095663f0a70b42278001a8efb7 (git+API verified, pinned)
Frozen upstream base:       7c5866144ac4b879be442563e2b49fa1c142ea36 (tree 8b0bf035)
Ordered candidate commits:  d4003de1a7cabc3715f73e48d3fd414f312a40de
                            3b18a0655b991890b63587ee18cb0950234a47f0
                            e7ff6d75fac3e7b683e81e671555ada99af13b74
Expected source tree SHA:   605d0d214acdbc06086fdb27c61fec970c0f2798

PATCH INTEGRITY
Patch 0001 SHA256:  14719b8b4ae7b4370afa42249b56c130d7d42b9447701e57a702570eb12ed7e2 (15546 B)
Patch 0002 SHA256:  7d40c314dcac87085178ba9d0c84bb2eced8f33ba8e9bd3a6151903d6ee4751e (7444 B)
Patch 0003 SHA256:  3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4 (27631 B)
Series SHA256:      797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d (sha256_file_concat_v1)
Patch order:        unique contiguous 1..3 enforced; wrong order FAILS
README handling:    allowed as documented support file; NEVER in series hash; symlinked README FAILS
Source reconstruction: EXACT — two methods (git am; apply --cached+write-tree) -> 605d0d21...; 10/10 blob SHAs match manifest

HANDOFF COMPATIBILITY
Actual Windows schema:   base_sha/ordered_commits/ordered_patches/series_hash/head_tree_sha1
Linux consumer compatible: YES (rewritten in B02; provisional schema rejected, no fallback)
Manifest check-only:     PASS (exit 0; manifest sha256 pinned 58a6f9ce...)
Adversarial matrix:      22/22 attacks behave as intended + 2 independent audit passes; no false-PASS achievable
Wrong candidate rejection: FAIL-CLOSED (pins + stale denylist)
Wrong tree rejection:     FAIL-CLOSED (manifest pin + apply-time write-tree comparison)

HIPRTC STL INVESTIGATION
Default header availability:     type_traits/utility/limits/initializer_list ALL reachable (1111)
-nostdinc++ header availability: utility=0, others=1 (PARTIAL isolation; 1011)
-nostdinc header availability:   identical to -nostdinc++ (1011)
Verified complete no-STL isolation: INCONCLUSIVE on Linux ROCm 7.14.1
  (libhiprtc-builtins.so.7 embeds type_traits/limits/initializer_list;
   immune to -nostdinc/-nostdinc++/-nobuiltininc/--sysroot/overlays/env passthru;
   system 7.2.1 shows 0000 but is excluded from the validation environment)
Partial-STL controls:       exercised (exactly the patch's inconsistent-availability guard scenario)
False-PASS risks:           -D__has_include spoof vector demonstrated + disproved + banned in runbook;
                           patch 0003's own isolation probe self-detects leaks
Remaining limitations:     Windows retains the no-STL regression evidence; Linux negative mode
                           expected to report isolation-insufficient (honest diagnostic)

MIOPEN VALIDATION READINESS
Frozen upstream base acquired:    YES (object store complete 0/47771 missing; refs/phase52/frozen-base)
Frozen unpatched baseline build:  YES — install/legA-frozen-baseline/lib/libMIOpen.so.1.0
                                  sha256 7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d
Patched operational leg built:    NO (dirs EMPTY by design)
Actual final patched A/B executed: NO
Source-built MIOpen provenance:   dladdr-proven in-stream on every run; wrapper prints lib+harness sha256
Direct Kthvalue harness ready:    YES (binary invariant b830b37a...; API identical between bases;
                                  KthvalueFwd dispatch + RTC compile proven on the frozen leg)
Fresh cache controls:             per-leg per-label dirs; stale reuse refused (FORCE downgrades + warns)
Disk available:                   ~36 GB free at mission end (predisk 41 GB recorded before leg build)

INDEPENDENT AUDITS
Gate audit coverage:  B00-B10 each audited by fresh-context subagents (see reviews/)
Reviewer A:           PASS (source & supply-chain integrity)
Reviewer B:           PASS (ROCm/HIPRTC toolchain)
Reviewer C:           PASS (upstream maintainer; runbook minors resolved)
Unresolved BLOCKER:   NONE
Unresolved MAJOR:     NONE

GITHUB
Evidence branch:      linux-w7900/phase5.2-handoff-bridge
Remote commit SHA:    (recorded in evidence_manifest.json / github_publication.json)
Remote artifacts verified: YES (post-push fetch + file checks)

UPSTREAM SAFETY
Upstream PR created:      NO
Upstream issue created:   NO
Upstream comment posted:  NO
Final Linux A/B executed: NO

FINAL VERDICT: PHASE5_2_BRIDGE_READY_WITH_STL_LIMITATION
```

Basis: all source/hash/schema/build-isolation gates PASS with independent
audits; exact tree reconstruction reproduced; frozen unpatched Leg A built
and sanity-proven; the ONLY unresolved limitation is the inability to
reproduce full no-STL HIPRTC behavior on Linux — recorded INCONCLUSIVE
(never PASS), scoped into the next mission per the runbook.
