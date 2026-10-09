# REPRODUCTION GUIDE — Phase 5.3 Linux W7900 Final R2 A/B

Workspace layout used by this mission (recreate on a gfx1100 host with the ROCm 7.14.1
wheel SDK and the pinned evidence):

```
miopen-w7900-validation/
  repos/rca-evidence          @ c8417161125dc33275b7ac615298b449a81e7cf8 (pinned)
  repos/rocm-libraries        object store containing 7c586614 (frozen base)
  source/final-patched        git-am worktree, tree b983cadd  (Leg B source)
  build/recon/frozen-base-checkout  @ 7c586614               (Leg A source)
  build/legA-frozen-miopen, build/patched-miopen              (leg builds)
  install/legA-frozen-baseline, install/patched               (leg libs)
  scripts/                      published phase5.2.1 wrappers (WRAPPERS_MANIFEST hashes)
  tools/rocm7141-venv           ROCm 7.14.1 wheel SDK
```

## 0. Environment

```bash
source scripts/env_rocm7141.sh     # hipcc 7.14.60850 from venv; /opt/rocm-7.2.1 excluded
rocminfo | grep -A3 gfx1100        # W7900/W7900D
```

## 1. Evidence identity (L01)

```bash
git -C repos/rca-evidence checkout c8417161125dc33275b7ac615298b449a81e7cf8
python3 phase5_3/scripts/run_r2_verifiers_linux.py HEAD   # 66/66 (1 substituted)
sha256sum repos/rca-evidence/patches/phase5_1_r2/canonical/*.patch
cat repos/rca-evidence/patches/phase5_1_r2/canonical/000*.patch | sha256sum
```

## 2. Handoff consumer + adversarial matrix (L02)

```bash
python3 phase5_3/scripts/check_final_handoff_r2.py --check-only \
  repos/rca-evidence/findings/phase5_1_r2/FINAL_HANDOFF.json \
  --rca-root repos/rca-evidence --rca-evidence-sha c8417161125dc33275b7ac615298b449a81e7cf8
ENABLE_APPLY=1 python3 phase5_3/scripts/run_l02_adversarial_matrix.py   # 20/20
```

## 3. Source reconstruction (L03)

```bash
git -C repos/rocm-libraries worktree add --detach /tmp/wtA 7c5866144ac4b879be442563e2b49fa1c142ea36
cd /tmp/wtA && git am <pinned>/000{1,2,3}-*.patch && git rev-parse 'HEAD^{tree}'
# => b983caddf9f9f561e7d1b590deadb16267c2de15
```

## 4. Leg B build (L05) — wrapper identical to published manifest

```bash
MIOPEN_SOURCE=$PWD/source/final-patched/projects/miopen \
MIOPEN_BUILD=$PWD/build/patched-miopen MIOPEN_INSTALL=$PWD/install/patched \
MIOPEN_JOBS=64 bash scripts/build_leg_miopen.sh
# Leg A: reuse frozen install (7e045dc0…); do not rebuild
```

## 5. CTest portability (L07)

```bash
bash phase5_3/scripts/l07_ctest_build.sh          # no workaround flags
cd build/recon53-test && ctest -N -R '^test_hiprtc_selfcontained$' \
  && ctest --output-on-failure -R '^test_hiprtc_selfcontained$'   # Skipped, rc 0
```

## 6. Kthvalue A/B (L08)

```bash
mkdir -p /tmp/dA /tmp/dB
MIOPEN_LOG_LEVEL=6 KTHV_DUMP_DIR=/tmp/dA bash scripts/run_validation_leg.sh \
  legA-frozen <label-A> build/kthvalue-harness/kthvalue_runtime_harness_gfx1100
MIOPEN_LOG_LEVEL=6 KTHV_DUMP_DIR=/tmp/dB bash scripts/run_validation_leg.sh \
  patched <label-B> build/kthvalue-harness/kthvalue_runtime_harness_gfx1100
for f in /tmp/dA/*; do cmp "$f" "/tmp/dB/$(basename $f)"; done   # 15/15 identical
```

## 7. BatchNorm (L09)

```bash
# compile (see evidence for exact flags), then per leg:
MIOPEN_LOG_LEVEL=6 bash scripts/run_validation_leg.sh <leg> <label> \
  phase5_3/scripts/batchnorm_harness
```

## 8. Evidence integrity

```bash
python3 phase5_3/scripts/verify_final_evidence.py    # 26/26 PASS
```

Fresh-cache rule: every runtime invocation uses a NEW label; the wrapper refuses non-empty
cache directories (stale-cache guard, L11 A4).
