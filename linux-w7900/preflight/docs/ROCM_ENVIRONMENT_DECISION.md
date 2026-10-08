# ROCm Environment Decision — W7900 Linux Validation Prep (W7900-LINUX-PREP-R1)

Date: 2026-10-08 | Gate: G01

## Decision

**Strategy B: New isolated ROCm 7.14.1 Python SDK environment** for the final
validation legs (A = unpatched, B = patched), while **retaining the system
ROCm 7.2.1 stack untouched** for machine-baseline measurements only.

## Why

1. The machine has a single pre-existing ROCm userspace: **7.2.1** at
   `/opt/rocm -> /etc/alternatives/rocm -> /opt/rocm-7.2.1` (HIP 7.2.53211,
   MIOpen 1.0.70201, comgr 3.0.0, rocBLAS 5.2.70201). It is healthy:
   `pip check` clean; `torch 2.9.1+gitff65f5b` (HIP 7.2.53211) resolves every
   ROCm library to `/opt/rocm/lib` (verified via `ldd libtorch_hip.so`) —
   no bundled/foreign ROCm libraries inside torch.
2. The machine has **no functional 7.14.x environment** (mission requirement).
3. The upcoming Phase-5.1 freeze originates from a 7.14.1-era toolchain
   (mission reference: `torch==2.12.0+rocm7.14.1`). Building both validation
   legs against one 7.14.1 SDK keeps the **MIOpen source patch as the single
   independent variable**.
4. AMD's official wheel index (https://repo.amd.com/rocm/whl-multi-arch/,
   HTTP 200) provides `rocm[libraries,devel,device-gfx1100]==7.14.1`,
   `torch[device-gfx1100]==2.12.0+rocm7.14.1` and
   `torchvision[device-gfx1100]==0.27.0+rocm7.14.1` for cp312/Linux.

## What was installed (nothing system-level was modified)

- Location: `tools/rocm7141-venv` (workspace-local, independent
  `/usr/bin/python3` 3.12.3 venv; NOT `/opt/venv`).
- `rocm-sdk-core/devel/libraries/device-gfx1100` 7.14.1
  (HIP 7.14.60850, hiprtc 7.14.60850, devel tree expanded via `rocm-sdk init`).
- `torch 2.12.0+rocm7.14.1`, `torchvision 0.27.0+rocm7.14.1`.
- Self-test: `rocm-sdk test` **27/27 OK** under isolation.

## Contamination control (critical finding)

The shell exports a global `ROCM_PATH=/opt/rocm` and `/opt/rocm` entries in
`PATH`/`LD_LIBRARY_PATH`. Without countermeasures the 7.14.1 venv SDK
resolves headers/cmake to 7.2.1 (proven: initial `rocm-sdk test` failed
`testCLIUsesDevelRootPath`, hipconfig reported `/opt/rocm`).

Mitigation (mandatory for every 7.14.1 session):

    source scripts/env_rocm7141.sh

This script scrubs all `/opt/rocm*` entries from `PATH`/`LD_LIBRARY_PATH`,
sets `ROCM_PATH`/`HIP_PATH` to the venv devel tree, and prepends venv bins.
After sourcing, `rocm-sdk test` = 27/27 OK. Conversely,
`scripts/env_system721.sh` isolates the 7.2.1 baseline stack. The two
environments must never be active in the same process.

Note: the 7.14.1 SDK wheel itself bundles `libMIOpen.so.1` (wheel build).
That binary is NOT used for validation — validation always links the
source-built MIOpen explicitly; provenance checks (G06/G07) enforce this.

## Rule compliance

- No GPU driver change, no kernel upgrade, no system ROCm uninstall/overwrite.
- No 7.2.1/7.14.1 mixing inside a single runtime process (isolation scripts).
- System MIOpen never silently used for validation (explicit linkage +
  `dladdr`/`LD_DEBUG` provenance evidence required by G06/G07).
