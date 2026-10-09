#!/usr/bin/env bash
# reproduce_final_ab.sh — end-to-end reproduction of the Phase 5.3 Linux W7900
# final R2 A/B validation (identity -> build -> runtime -> integrity).
# Assumes the workspace layout in docs/REPRODUCTION_GUIDE.md and the pinned
# RCA evidence commit c8417161125dc33275b7ac615298b449a81e7cf8.
set -euo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # miopen-w7900-validation
P53="$WS/phase5_3"
PIN=c8417161125dc33275b7ac615298b449a81e7cf8
LABEL="repro-$(date +%s)"

echo "== [1/7] Evidence identity =="
git -C "$WS/repos/rca-evidence" rev-parse HEAD | grep -q "^$PIN$" \
  || { echo "rca-evidence not pinned at $PIN"; exit 1; }
python3 "$P53/scripts/run_r2_verifiers_linux.py" HEAD

echo "== [2/7] Handoff consumer =="
python3 "$P53/scripts/check_final_handoff_r2.py" --check-only \
  "$WS/repos/rca-evidence/findings/phase5_1_r2/FINAL_HANDOFF.json" \
  --rca-root "$WS/repos/rca-evidence" --rca-evidence-sha "$PIN"

echo "== [3/7] Leg binaries =="
sha256sum "$WS"/install/legA-frozen-baseline/lib/libMIOpen.so.1.0 \
          "$WS"/install/patched/lib/libMIOpen.so.1.0

echo "== [4/7] Kthvalue A/B (fresh caches) =="
mkdir -p /tmp/p53r-dA-"$LABEL" /tmp/p53r-dB-"$LABEL"
MIOPEN_LOG_LEVEL=6 KTHV_DUMP_DIR=/tmp/p53r-dA-"$LABEL" \
  bash "$WS/scripts/run_validation_leg.sh" legA-frozen "kthv-$LABEL-A" \
  "$WS/build/kthvalue-harness/kthvalue_runtime_harness_gfx1100"
MIOPEN_LOG_LEVEL=6 KTHV_DUMP_DIR=/tmp/p53r-dB-"$LABEL" \
  bash "$WS/scripts/run_validation_leg.sh" patched "kthv-$LABEL-B" \
  "$WS/build/kthvalue-harness/kthvalue_runtime_harness_gfx1100"
n=0; for f in /tmp/p53r-dA-"$LABEL"/*; do cmp "$f" "/tmp/p53r-dB-$LABEL/$(basename "$f")"; n=$((n+1)); done
echo "byte-identical dump pairs: $n (expect 15)"

echo "== [5/7] BatchNorm both legs =="
MIOPEN_LOG_LEVEL=6 bash "$WS/scripts/run_validation_leg.sh" legA-frozen "bn-$LABEL-A" \
  "$P53/scripts/batchnorm_harness"
MIOPEN_LOG_LEVEL=6 bash "$WS/scripts/run_validation_leg.sh" patched "bn-$LABEL-B" \
  "$P53/scripts/batchnorm_harness"

echo "== [6/7] CTest portability =="
( cd "$WS/build/recon53-test" && ctest -N -R '^test_hiprtc_selfcontained$' \
  && ctest --output-on-failure -R '^test_hiprtc_selfcontained$' )

echo "== [7/7] Evidence integrity =="
python3 "$P53/scripts/verify_final_evidence.py"

echo "REPRODUCTION_COMPLETE (expect: 66/66 verifiers; consumer PASS; 15 dump pairs;"
echo "batchnorm 6/6 PASS x2; ctest Skipped rc 0; checker ALL CHECKS PASSED)"
