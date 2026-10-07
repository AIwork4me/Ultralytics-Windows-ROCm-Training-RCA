# Linux Validation Summary — Phase 3 (run 1: 2026-10-07)

```text
STATUS: BLOCKED_ON_PATCH_HANDOFF
```

The Windows Phase-3 patch producer has not yet published
`findings/phase3/PATCH_HANDOFF.json` (verified against local branch state and
a fresh `git fetch --all --prune` of all remote branches). Per the re-entrant
execution rules, the Linux validator completed every stage that does not
depend on the patch, published the evidence, and stopped without error.

## What this run established

1. **Controlled environment**: Ubuntu 24.04.4 / kernel 6.17.0-1032-oem,
   uv 0.12.3, Python 3.13.15 venv, ROCm 7.14.0 wheel stack (devel + libraries
   + device-gfx1151), torch 2.12.0+rocm7.14.0 / torchvision 0.27.0 /
   torchaudio 2.11.0, ultralytics 8.4.174. Exact frozen line, no
   substitutions.
2. **Hardware identity**: gfx1151 / Radeon 8060S confirmed by rocminfo AND
   torch device properties (never inferred from product name alone).
3. **Linux baseline PASS** (the counterfactual leg): the exact 5-line
   Windows-failing BatchNorm2d repro passes; 8/8 BN/GN cases pass on a FRESH
   isolated cache with direct proof that the same kernel that fails on
   Windows — `MIOpenBatchNormFwdTrainSpatial` for gfx1151 — is
   runtime-compiled by HIPRTC on Linux (cache-miss SELECT → compile → INSERT
   INTO kern_db, plus comgr llvmcache artifacts in the isolated cache dir).
4. **Standalone HIPRTC matrix 6/6 PASS** (none/type_traits/utility/limits/
   cstdint/initializer_list) with std-facility-exercising bodies, plus an
   on-GPU execution control (module load → launch → memcpy → result 1).
5. **STL root-cause counterpart**: Linux HIPRTC resolves `<type_traits>` to
   system GCC 13 libstdc++ via clang's automatic GCC-install detection
   (proven by a `-H` include trace inside hiprtcCompileProgram). Windows has
   no such provider — consistent with the Phase-2 RCA.
6. **YOLO controls PASS**: predict (bus.jpg, 4 persons + 1 bus) and train
   (coco8, 1 epoch, validation, best/last.pt) with recorded exit codes.
7. **Independent adversarial review** of the baseline: verdict
   BASELINE_VALID_WITH_NOTES; every accepted finding (incl. two mechanism-
   narrative errors and a system-ROCm disclosure error) remediated and
   re-proven the same day. Review preserved verbatim.
8. **Build readiness** for the post-handoff source builds: dependency
   inventory complete; wheel stack covers all ROCm-side deps; missing host
   deps (sqlite3, nlohmann_json, CK…) installable via the tree's own
   cget-based installer into a local prefix without sudo; /opt/rocm-7.2.1
   contamination vector identified with a mandatory cache-pin mitigation.

## Nothing to regress yet

No patch exists on this machine; none was invented; nothing upstream was
created, commented, or pushed except this Linux evidence branch.

## Resuming

Rerun the same validator prompt after the Windows producer commits
`findings/phase3/PATCH_HANDOFF.json`. Gates L20+ resume from the handoff
verification; all baseline gates L00–L19 are complete and re-verified cheaply
on rerun.
