#!/usr/bin/env bash
# Strictly isolated environment for the ROCm 7.14.1 Python SDK venv.
# Usage: source scripts/env_rocm7141.sh
# Removes ALL /opt/rocm (7.2.1) entries from PATH / LD_LIBRARY_PATH and
# points ROCM_PATH/HIP_PATH at the venv devel tree so no 7.2.1/7.14.1
# mixing can occur in a single process.
set -euo pipefail

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$WS_ROOT/tools/rocm7141-venv"
SP="$VENV/lib/python3.12/site-packages"
SDK_CORE="$SP/_rocm_sdk_core"
SDK_LIBS="$SP/_rocm_sdk_libraries"
SDK_DEVEL="$SP/_rocm_sdk_devel"

# Strip any /opt/rocm* and previous venv entries from PATH and LD_LIBRARY_PATH
PATH="$(echo "$PATH" | tr ':' '\n' | grep -v '^/opt/rocm' | grep -v "^$VENV" | paste -sd:)"
LD_LIBRARY_PATH="$(echo "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -v '^/opt/rocm' | grep -v "^$VENV" | grep -v "^$SP" | paste -sd:)"

export PATH="$SDK_DEVEL/bin:$SDK_DEVEL/llvm/bin:$VENV/bin:$PATH"
export LD_LIBRARY_PATH="$SDK_CORE/lib:$SDK_LIBS/lib:$SDK_DEVEL/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ROCM_PATH="$SDK_DEVEL"
export HIP_PATH="$SDK_DEVEL"
export ROCM_HOME="$SDK_DEVEL"
unset HSA_OVERRIDE_GFX_VERSION || true

# Python access to the venv (not system /opt/venv)
hash -r
echo "[env_rocm7141] ROCM_PATH=$ROCM_PATH"
echo "[env_rocm7141] hipcc=$(command -v hipcc)"
echo "[env_rocm7141] python=$(command -v python)"
