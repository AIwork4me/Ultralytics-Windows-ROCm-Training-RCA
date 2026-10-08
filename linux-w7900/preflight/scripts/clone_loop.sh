#!/usr/bin/env bash
# Persistent rocm-libraries blobless clone loop (network is flaky).
set -u
WS=/workspace/miopen-w7900-validation
LOG=$WS/logs/G04_rocm_libraries_clone.log
: > "$LOG"
for i in $(seq 1 400); do
  rm -rf /tmp/opencode/rl-clone-tmp
  if git clone --filter=blob:none https://github.com/ROCm/rocm-libraries.git /tmp/opencode/rl-clone-tmp >> "$LOG" 2>&1; then
    rm -rf "$WS/repos/rocm-libraries"
    mv /tmp/opencode/rl-clone-tmp "$WS/repos/rocm-libraries"
    echo "CLONE_OK_ATTEMPT_$i $(date -Is)" >> "$LOG"
    exit 0
  fi
  echo "clone attempt $i failed $(date -Is)" >> "$LOG"
  sleep 30
done
echo "CLONE_GAVE_UP $(date -Is)" >> "$LOG"
exit 1
