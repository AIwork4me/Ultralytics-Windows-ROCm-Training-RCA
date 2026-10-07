# BLOCKED marker resolved

Resolved: 2026-10-07T22:06:00+08:00
Handoff found on origin/main (dc95c7a):
  SOURCE_SHA: b68f8944300f104875d953fc8e4510908c9aaf0b
  PATCH_ID:   P3-FINAL (0001+0002 series)
  0001 sha256: f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20
  0002 sha256: 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532
Original BLOCKED text preserved below.

# BLOCKED_ON_PATCH_HANDOFF — Linux Phase-3 Validator

Status date: 2026-10-07

```text
Linux baseline complete.
Patch validation not started.
Waiting for immutable:
SOURCE_SHA
PATCH_SHA256
PATCH_PATH
PATCH_ID
```

## What is complete (rerun-safe)

- Gates L00–L03: bootstrap, kernel gate (6.17.0-1032-oem ≥ 6.14 PASS), GPU permissions PASS
- Gates L04–L08: RCA repo cloned, branch rca/linux-gfx1151-phase3-regression,
  uv 0.12.3 + Python 3.13.15 venv, ROCm 7.14 wheel stack (rocm[devel,libraries,device-gfx1151]==7.14.0,
  torch 2.12.0+rocm7.14.0 line, ultralytics 8.4.174), build tools assessed
- Gates L09–L12: wheel layout discovery (TheRock layout, _rocm_sdk_* packages),
  gfx1151 verified (rocminfo + torch), GEMM control PASS, library provenance recorded
- Gates L13–L18: BatchNorm matrix 8/8 PASS on fresh isolated cache with direct
  HIPRTC-compile proof (MIOpenBatchNormFwdTrainSpatial INSERT INTO kern_db),
  wheel-MIOpen-load proof via /proc/self/maps, standalone HIPRTC header matrix
  6/6 PASS + GPU execution control, STL provider identified (system GCC 13
  libstdc++), YOLO predict + train PASS with recorded exit codes
- Gate L19: baseline conclusion PASS + independent adversarial subagent review
  (BASELINE_VALID_WITH_NOTES) with all findings remediated
- Build readiness: see docs/phase3/linux/BUILD_READINESS.md

## What resumes on rerun (once findings/phase3/PATCH_HANDOFF.json exists)

- Gate L20: verify PATCH_SHA256 == sha256sum(patch), fields valid
- Gates L22–L24: clone exact SOURCE_SHA, two trees, identity audit
- Gates L25–L30: unpatched source build + controls
- Gates L31–L39: patched build + full regression matrix
- Gates L40–L49: matrices, subagent attacks, manifest, final verdict

## Handoff expectation (from the Phase-3 plan)

```json
{
  "patch_id": "P3-Rx",
  "source_repo": "ROCm/rocm-libraries",
  "source_sha": "...",
  "patch_path": "patches/phase3/...",
  "patch_sha256": "...",
  "producer_platform": "windows"
}
```

The Linux validator consumes this file unmodified. No patch exists locally;
none was invented.
