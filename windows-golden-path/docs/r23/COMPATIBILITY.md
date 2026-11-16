# COMPATIBILITY.md (R23 draft, facts frozen 2026-11-15)

## Verified combinations (physical hardware)

| GPU | OS build | Driver | Python | torch | torchvision | device wheels | ultralytics | Result |
|---|---|---|---|---|---|---|---|---|
| RX 7900 XTX (gfx1100) | Win11 26300 | 32.0.21030.2001 | 3.12.16 | 2.12.0+rocm7.14.1 | 0.27.0+rocm7.14.1 | gfx1100 + gfx110x + tv-gfx1100 | 8.4.214 (PyPI) | FULL train/AMP/val/resume PASS (R21; requires VS Build Tools OR fixed wheel — see blocker) |
| RX 7900 XTX (gfx1100) | Win11 26300 | 32.0.21030.2001 | 3.12.16 | 2.15.0+gitf6cd88cb dev (10.3.0.dev0+ff576965) | 0.29.2+git… | amd-torch-device-gfx1100 + tv-gfx1100 | 8.4.214 | see evidence/r22-dev (dev-channel candidate; MIOpen fix PROVEN in source) |
| Radeon 8060S (gfx1151) | Win11 26200 | (P14) | 3.13 | 2.12.0+rocm7.14.1 | 0.27.0 | gfx1151 set | 8.4.182→8.4.214 | P14/P17/P19B historical PASS (engineering ref) |

## Rules that bite (each backed by a physical failure)

1. torch must come from the AMD index (`+rocm` local version). CPU wheels
   install silently from PyPI otherwise.
2. Both per-arch AND family device wheels (gfx1100 + gfx110x).
3. torchvision needs its OWN device wheel.
4. Never mix ROCm 7.x and 10.x components in one venv.
5. Python tag must match (cp312/cp313 wheels exist for the verified stacks).

## Channel status for the MIOpen fix (#13437)

See `../R22_CANDIDATE_WATCHLIST.md` — stable: absent; rc 10.2.0rc2: absent
(proven); nightly libraries: present (gfx1100 device wheels missing);
dev: present (full gfx1100 set installable).

## Not supported / not claimed

TensorRT; ONNX Runtime CUDAExecutionProvider on AMD; NVIDIA performance
parity; archs other than gfx1100/gfx1151; any MIOpen.dll replacement.
