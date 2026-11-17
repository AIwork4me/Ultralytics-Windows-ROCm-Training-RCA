# P16 OFFICIAL WHEEL BINARY AUDIT (2026-11-15)

Per mission §5.2: no historical P14/P15 finding was reused without re-checking. Both known official channels were re-scanned live and the MIOpen.dll carrier was re-downloaded and re-audited byte-for-byte today.

## 1. Channel re-scan (2026-11-15)

### `https://repo.amd.com/rocm/whl-multi-arch/torch/`

Newest cp313 Windows wheel: `torch-2.12.0+rocm7.14.1-cp313-cp313-win_amd64.whl` — unchanged since the P15 scan (no 7.14.2 / 7.15.x).

### `https://stable.repo.amd.com/rocm/whl-next/` (TheRock-style layout)

Root lists per-arch `amd-torch-device-gfx*`, `rocm-sdk-core`, `rocm-sdk-libraries`, `rocm-sdk-device-*`, plus deps. Newest Windows set:

| Package | Newest version |
|---------|----------------|
| `rocm_sdk_core` (win_amd64) | 10.1.0 |
| `rocm_sdk_libraries` (win_amd64) | 10.1.0 |
| `torch` (cp313 win_amd64) | 2.14.0+rocm10.1.0 |
| `amd_torch_device_gfx1151` (cp313 win_amd64) | 2.14.0+rocm10.1.0 |

**No rocm 10.2.0 artifact exists; no new version published since the P15 audit.**

## 2. Binary re-audit of the currently published artifact

`rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl` re-downloaded from `stable.repo.amd.com/rocm/whl-next/rocm-sdk-libraries/` on 2026-11-15 (Last-Modified 2026-10-05, i.e. predates P14/P15):

- **Wheel SHA256: `0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159`** — byte-identical to the P14/P15 audited copy (`p14_wheel_audit/wheels/`). Same S3 object; no rebuild.
- Embedded `_rocm_sdk_libraries/bin/MIOpen.dll` re-extracted and re-audited today:

| Property | Value | P14/P15 record | Match |
|----------|-------|----------------|-------|
| Size | 496,074,240 B | 496,074,240 B | ✓ |
| SHA256 | `266d716bab4aaf4ec3bb7492d35f6b65473982bc38f22b14235863a15c1429b4` | same | ✓ |
| Version string | `3.6.1.39d8d603` | same | ✓ |
| Build commit date | `39d8d603` = 2026-09-16 (< merge `f0a5d266` 2026-10-19) | same | ✓ |
| `miopen_initializer_list` marker | **0** (pre-fix; post-fix reference = 2) | 0 | ✓ |
| `miopen_type_traits` | 12 (non-discriminator) | 12 | ✓ |

## 3. Verdict

- **BLOCKED_RELEASE stands.** Every known official Windows ROCm channel currently ships only pre-#13437 MIOpen binaries. The missing cut point remains **a post-2026-10-19 MIOpen → Windows SDK/wheel build → publish cycle** (owner: AMD/TheRock release chain, tracked in [rocm-libraries#15862](https://github.com/ROCm/rocm-libraries/issues/15862)).
- No new comment was posted on #15862 today: the re-audit found no material new fact (byte-identical artifact); P15's handoff evidence stands unchanged.
- Runtime three-leg evidence (LEG A official-7.14.1 FAIL / LEG B whl-next-10.1.0 FAIL / LEG C merged-source PASS, no-STL method) is preserved from P14/P15 and remains valid for these exact byte-identical artifacts.
- Positive readiness fact retained: the whl-next torch 2.13.0/2.14.0+rocm10.1.0 stack installs and performs real GPU compute on gfx1151 (P14) — it becomes the ordinary user path the moment a fixed `rocm_sdk_libraries` ships.
