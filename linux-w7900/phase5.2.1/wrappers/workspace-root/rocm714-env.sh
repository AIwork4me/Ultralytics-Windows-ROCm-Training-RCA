#!/bin/bash
# Sanitized ROCm 7.14 build/test environment for the fresh image (mission §11).
# Source this in every vLLM build/test shell.
VENV=/workspace/venv-qwen-gdn-rca
PYVER=python3.12
DEV="$VENV/lib/$PYVER/site-packages/_rocm_sdk_devel"

source "$VENV/bin/activate"

export PATH="$DEV/bin:$VENV/bin:$HOME/.cargo/bin:/usr/bin:/bin"
export ROCM_PATH="$DEV"
export HIP_PATH="$DEV"
export HIP_CLANG_PATH="$DEV/lib/llvm/bin"
export LD_LIBRARY_PATH="$DEV/lib"
export CMAKE_PREFIX_PATH="$DEV"

export VLLM_TARGET_DEVICE=rocm
export PYTORCH_ROCM_ARCH=gfx1100

export PYTHONPATH=""
unset CUDA_HOME CUDA_PATH
