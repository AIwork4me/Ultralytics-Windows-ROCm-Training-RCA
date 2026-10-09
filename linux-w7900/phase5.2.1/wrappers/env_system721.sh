#!/usr/bin/env bash
# Isolated environment for the pre-existing SYSTEM ROCm 7.2.1 stack.
# Usage: source scripts/env_system721.sh
# Used only for machine-baseline tests (G02). Never mixed with 7.14.1 venv.
set -euo pipefail

# Strip any 7.14.1 venv entries
VENV_TAG="miopen-w7900-validation/tools/rocm7141-venv"
PATH="$(echo "$PATH" | tr ':' '\n' | grep -v "$VENV_TAG" | paste -sd:)"
LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v "$VENV_TAG" | paste -sd:)"

export ROCM_PATH="/opt/rocm"
export HIP_PATH="/opt/rocm"
export PATH="/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH"
export LD_LIBRARY_PATH="/opt/rocm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH=""   # drop /opt/amd-oneclick-runtime helper modules for determinism
unset HSA_OVERRIDE_GFX_VERSION || true
hash -r
echo "[env_system721] ROCM_PATH=$ROCM_PATH"
echo "[env_system721] hipcc=$(command -v hipcc)"
echo "[env_system721] python=$(command -v python)"
