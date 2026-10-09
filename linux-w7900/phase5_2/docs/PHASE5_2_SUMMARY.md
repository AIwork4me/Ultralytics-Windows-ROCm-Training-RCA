# PHASE 5.2 SUMMARY — Linux W7900 Handoff Bridge (W7900-PHASE52-BRIDGE-R1)

**FINAL VERDICT: `PHASE5_2_BRIDGE_READY_WITH_STL_LIMITATION`**

The Linux W7900 validation environment is now bridged to the EXACT Windows
Phase-5.1 frozen candidate P5.1-CANDIDATE-R1. Every source, hash, schema,
and build-isolation gate passed with independent audits. The single
remaining limitation — Linux cannot reproduce a complete no-STL HIPRTC
environment on ROCm 7.14.1 — is honestly recorded as INCONCLUSIVE (never
as PASS) and is scoped into the next mission.

## What this mission did

1. **Pinned the immutable Windows evidence** (B01): RCA commit
   `494907699f3b57095663f0a70b42278001a8efb7` verified via git transport
   AND GitHub API into a local pinned checkout (`repos/rca-evidence`).
2. **Fixed the real schema mismatch** (B02): the Linux consumer now
   validates the ACTUAL frozen schema (`base_sha`, `ordered_commits`,
   `ordered_patches`, `series_hash{sha256_file_concat_v1}`,
   `source_tree_identity.head_tree_sha1`, DCO/copyright interpretation)
   and rejects the provisional schema with no fallback. The Windows
   manifest was never touched.
3. **Made the patch directory safe** (B03): README.md accepted as the
   documented support file (never hashed); 22-attack adversarial matrix +
   two independent audit passes — byte flips, reordering, injected
   0004-malicious.patch, symlinks, traversal, absolute paths, executable
   bits, nested dirs, wrong pins, wrong evidence commit, missing files,
   empty object stores, unauthorized apply — every attack fails for its
   intended reason; TOCTOU re-check fails on dirty checkout.
4. **Acquired the exact frozen upstream source** (B04): through an
   unstable egress proxy, via local-tree-proven b68f894 extraction +
   641 hash-verified API-fetched delta blobs: object store complete
   (0/47,771 missing), pin ref `refs/phase52/frozen-base`.
5. **Reconstructed the candidate EXACTLY** (B05): two independent methods
   (git am; git apply --cached + write-tree) both produce tree
   `605d0d214acdbc06086fdb27c61fec970c0f2798`; 10 changed files' blob
   SHAs match the manifest 10/10; 4 copyright attributions present; no
   placeholders; disposable worktrees cleaned.
6. **Characterized HIPRTC STL behavior honestly** (B06): default =
   full-STL; `-nostdinc++`/`-nostdinc` = partial-STL (utility gone,
   type_traits/limits/initializer_list remain via EMBEDDED headers in
   libhiprtc-builtins.so.7 — immune to every flag combination tested by
   us AND by the adversarial auditor, including overlays and env passthru).
   Full no-STL on Linux 7.14.1 = INCONCLUSIVE. Spoof vector
   (`-D__has_include(x)=0`) demonstrated and banned from the runbook.
7. **Re-proved library isolation** (B07): live process maps contain ZERO
   /opt/rocm objects across startup + lazy loads; ldconfig and
   wheel-shadowing attack surfaces documented with mandatory guards.
8. **Built the frozen unpatched Leg A** (B08): from 7c586614 (NOT the
   historical b68f894), config-identical discipline,
   `install/legA-frozen-baseline/lib/libMIOpen.so.1.0` sha256
   `7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d`,
   driver-bound 3.6.2, Kthvalue sanity PASS on gfx1100 with fresh cache.
   Leg B directories remain EMPTY (mission boundary).
9. **Handed off the direct Kthvalue harness** (B09): API byte-identical
   between bases; harness binary invariant `b830b37a...`; wrapper
   hardened (legA-frozen leg name, override warnings, sha printing);
   complete next-mission invocation plan written.
10. **Re-validated everything end-to-end** (B10) and passed the
    **three-reviewer panel** (B11): integrity / toolchain / maintainer —
    all PASS, zero blockers/majors, every justified minor resolved.

## Mission boundaries respected

The MIOpen patch was not changed; Windows artifacts untouched; historical
evidence preserved; system ROCm 7.2.1 never mixed in; NO final patched
workload built or run; NO Linux A/B PASS claimed; NO upstream PR/issue/
comment; NO DCO sign-offs; no binaries/caches committed.

## Next mission (Phase 5.3)

Follow `docs/FINAL_AB_VALIDATION_RUNBOOK.md` exactly: build Leg B via the
tree-identity-checked apply path, run the same harness on both frozen
legs, compare dumps, run the patched regression test with the documented
Linux negative-mode expectation (isolation-insufficient diagnostic is the
honest outcome; Windows retains the no-STL evidence).
