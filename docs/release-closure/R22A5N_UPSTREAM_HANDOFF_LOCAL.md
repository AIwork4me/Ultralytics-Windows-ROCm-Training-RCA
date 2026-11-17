# Upstream handoff — R22A.5N nightly prequalification (LOCAL ONLY — not posted)

Prepared 2026-11-17. The owner reviews all evidence before deciding whether to
share anything upstream (rocm-libraries#15862). Do NOT auto-post.

---

Subject: Windows gfx1151 nightly prequalification of the #13437 MIOpen fix
(rocm-sdk-libraries 10.3.0a20261116) — no-host-STL regression resolved on
physical hardware

Summary for AMD Release Engineering:

- Environment: Windows 11 (10.0.26200), Radeon 8060S (gfx1151), Adrenalin
  driver 32.0.22032.6002, Python 3.13, official nightly index
  https://nightly.repo.amd.com/rocm/whl-next/, wheel set all 10.3.0a20261116
  (torch 2.16.0a0+, torchvision 0.30.0a0+, rocm-sdk-core/libraries/
  device-gfx1151, amd-torch/torchvision-device-gfx1151) + released
  ultralytics 8.4.214 from PyPI. All wheels SHA256-pinned; installed from
  verified local bytes only.
- MIOpen identity: build 3.6.3.25f28906; wheel SHA256 b11baad9…; embedded
  MIOpen.dll SHA256 f9312c3e…; source ancestry f0a5d266…25f28906
  (ahead_by=1074, behind_by=0). The DLL actually loaded in the GPU test
  process was verified equal to this wheel member (child-process evidence).
- Result 1 (the regression): BatchNorm2d(100) at the historically failing
  shape (20,100,35,45) — forward+loss+backward+sync, finite outputs and
  grads — PASSES with host MSVC STL unreachable (VCToolsInstallDir
  redirected to an empty dir, INCLUDE empty, cold MIOpen cache, no HIPRTC
  include shim). Paired negative control on the official pre-fix stack
  (torch 2.12.0+rocm7.14.1, MIOpen 3.5.2.cd957402, fix marker absent)
  fails with the exact original signature (HIPRTC_ERROR_COMPILATION,
  miopen_type_traits.hpp:151 'type_traits' file not found) under the same
  isolation. The fix is causally confirmed on physical Windows hardware
  with zero workarounds.
- Result 2 (training lifecycle): YOLO26n on COCO128, 3 epochs, batch 8:
  genuine FP16 autocast observed (96/96 stem-conv outputs), GradScaler
  65536→4096 with 4 backoffs, 7 effective AdamW updates / 11 attempts,
  finite grads on every confirmed update, decreasing loss, real metrics,
  best.pt/last.pt saved; controlled kill → NEW-process resume=True
  continues epochs without reset; third process reloads best.pt for GPU
  inference. workers=8 DataLoader exercise: 16 spawn children observed
  live, clean teardown.
- Packaging observations (nightly channel, 10.3.0a20261116):
  1) rocm-sdk-device-gfx1151 contains member paths up to 203 chars
     (hipdnn_plugins heuristics). On default Windows (LongPathsEnabled=0),
     installation fails with OSError when the site-packages prefix exceeds
     57 chars — typical short user venvs fit, nested project venvs do not.
  2) the `rocm` meta-package ships as sdist; offline/`--no-index`
     installs cannot build it (build isolation needs setuptools>=70.2.0
     from an index).
- Still blocked / not claimed: Stable channel (7.14.1 / 10.1.0) remains
  pre-fix (BLOCKED_RELEASE, issue #15862 unchanged); RC 10.2.0rc2
  pre-fix; no second-architecture, clean-install (G9), or Stable claims
  are made. This is a single-GPU nightly prequalification.

Artifacts: reports/r22a5n/R22A5N-GFX1151-20261117-A/ (29 files +
SHA256MANIFEST) in AIwork4me/Ultralytics-Windows-ROCm-Training-RCA,
branch validation/r22a5n-gfx1151-official-nightly → draft PR.
