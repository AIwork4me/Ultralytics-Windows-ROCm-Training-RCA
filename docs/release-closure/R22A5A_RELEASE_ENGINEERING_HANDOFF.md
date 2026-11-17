# R22A.5A Release-Engineering Handoff (internal draft — NOT posted)

- Generated: 2026-11-17 (mission R22A.5A Phase F, §9.1)
- Recipient (when routed): AMD ROCm / TheRock Windows package release owner
  (routing issue: ROCm/rocm-libraries#15862 — still open, no assignee as of
  2026-11-17; NOT duplicated or commented by this mission)
- Boundary: this is an INTERNAL DRAFT. No email, no comment, no issue is
  posted automatically. The already-filed #15862 remains the single thread.

## 1. One-paragraph summary

The MIOpen Windows HIPRTC host-STL fix (rocm-libraries PR #13437, merged
2026-10-19 as `f0a5d2664cf3334161f7b82c02dfcd2213988a8a`, carried by
TheRock PR #9359) is **merged in source but absent from every obtainable
official Windows binary channel**. As of the 2026-11-17 five-channel scan
(plus TheRock release tags and download.pytorch.org), the newest
stable/GA artifacts (multi-arch 7.14.1, whl-next stable 10.1.0, rc
10.2.0rc2) are all proven PRE-FIX by binary audit + source ancestry; only
the nightly/dev channels carry the fix (fresh nightly audit 2026-11-17:
build `25f28906`, marker present, behind_by=0). Windows users without
MSVC Build Tools therefore still hit `HIPRTC_ERROR_COMPILATION:
'type_traits' file not found` → `miopenStatusUnknownError` on first
BatchNorm training.

## 2. Fixed facts the release owner can verify in minutes

| Fact | Evidence |
|---|---|
| merged fix commit | `f0a5d2664cf3334161f7b82c02dfcd2213988a8a` (squash merge, gh api state=MERGED 2026-10-19T09:27:09Z) |
| TheRock integration | PR #9359 merge `b0958085`; submodule bump `d875648` contains the fix (compare ahead_by=2/behind_by=0); TheRock main submodule `9ea8cfc5` also contains it (behind_by=0) |
| stable whl-next 10.1.0 pre-fix | wheel `0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159`, embedded MIOpen.dll `266d716bab4aaf4ec3bb7492d35f6b65473982bc38f22b14235863a15c1429b4` = `3.6.1.39d8d603`, marker 0 (P14/P15/P16 byte-identical) |
| rc 10.2.0rc2 pre-fix DESPITE post-merge build date | DLL `2a3a026c…` build `8faffed0f`, marker 0, compare `diverged` behind_by=92 — branch cut before the merge |
| nightly carries the fix | 10.3.0a20261116 wheel `b11baad9…`, DLL `f9312c3e…` build `25f28906`, marker 2, behind_by=0 (audit 2026-11-17, method in-repo) |
| no TheRock release tag contains the fix | latest release still `therock-10.1` (2026-10-05); all 5 newest tags' submodule pointers behind (compare-based) |

## 3. Required wheel identity (what "done" looks like)

1. A TheRock release (or post-release) whose rocm-libraries submodule
   pointer passes `merge-base --is-ancestor f0a5d266` — we verify via the
   GitHub compare API, never dates.
2. Built Windows wheels landing on `repo.amd.com/rocm/whl-multi-arch/`
   and/or `stable.repo.amd.com/rocm/whl-next/` with the full device-wheel
   set for gfx1100 (`rocm-sdk-device-gfx1100` or
   `amd-torch-device-gfx1100(+gfx110x)`) and gfx1151.
3. Artifact URL + version + SHA256 + publication channel published (or
   reachable on the index) so the audit chain
   (wheel-SHA → DLL-SHA → build-commit → ancestry) can close.

## 4. Release acceptance tests we will run immediately on publication

Already implemented and CPU-verified in this repository (no AMD action
needed — listed so the release owner knows what will be reported back):

1. `scripts/r22a5a/scan_official_releases.py` — five-channel + TheRock +
   PyTorch-index classification (fail-closed vocabulary).
2. `scripts/r22a5a/audit_wheel_provenance.py` — bounded wheel download,
   ZIP-only inspection, DLL hash/marker/build-commit, live ancestry.
3. `windows-golden-path/scripts/resolve_package_set.py` — hash-pinned lock.
4. `windows-golden-path/scripts/verify_miopen_nostl.py --leg official` —
   the no-host-STL BatchNorm regression at the failing shape, cold cache.
5. Full R22A.5B dual-architecture gate matrix (G0..G9) on RX 7900 XTX and
   Radeon 8060S, plus a clean-Windows G9 leg and an independent developer
   acceptance package (issue #14 invitation).

## 5. Hardware available for independent validation

| Machine | GPU | gfx | OS | Python | Role |
|---|---|---|---|---|---|
| RCA validation host A | Radeon RX 7900 XTX (dGPU) | gfx1100 | Windows 11 26200 | 3.12/3.13 | dual-arch matrix leg 1 |
| RCA validation host B | Radeon 8060S (iGPU) | gfx1151 | Windows 11 26200 | 3.13 | dual-arch matrix leg 2 |

## 6. Minimum information needed from release engineering

1. Owner + planned cut (branch/snapshot) whose lineage contains `f0a5d266`.
2. First installable artifact identity: URL, version, SHA256, channel.
3. Release mechanism: SDK cut vs ABI-compatible `rocm_sdk_libraries`
   `.postN` of 10.1.0 (the R20 question — feasibility of a post-release
   against the existing 10.1.0 torch/device-wheel dependency set).
4. Publication ETA + whether gfx1100 AND gfx1151 device wheels ship in the
   same cut.
5. Confirmation that #15862 is the tracking issue for this rollout.

## 7. What this repository will NOT do

- No pressure tactics, no duplicate issues, no edits to AMD repositories.
- No claim of vendor support beyond what AMD's own matrices state.
- No publication of "official Stable PASS" until the physical gates close
  on both architectures from a qualified stable artifact.
