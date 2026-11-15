# R22 ACCEPTANCE RUNBOOK (portable gfx1100 + gfx1151)

Audience: the validation operator (either GPU machine). The harness is
byte-identical on both architectures; nothing below is machine-specific
except `-Gfx`.

## 0. Preconditions

- Windows 11, AMD Adreno/Radeon driver installed, no other GPU workload running
- Workspace: `C:\RadeonYOLO\` (auto-created by scripts)
- Base python for venv creation (any CPython 3.12/3.13 the stack supports)
- For **OfficialStable**: a lock resolved from the **stable** channel only

## 1. Resolve a candidate (metadata-driven; refuses to guess)

```powershell
cd <repo>/windows-golden-path
python scripts/discover_official_wheels.py --out-dir C:/RadeonYOLO/evidence/<run>/wheel-scan --gfx gfx1100
python scripts/resolve_package_set.py `
    --discovery C:/RadeonYOLO/evidence/<run>/wheel-scan/wheel_discovery.json `
    --channel rc --gfx gfx1100 --python cp312 `
    --python C:/RadeonYOLO/venvs/r21-engref/Scripts/python.exe `
    --out C:/RadeonYOLO/evidence/<run>/resolved_wheel_lock.json `
    --wheels-dir C:/RadeonYOLO/wheels
```

Exit 3 = `BLOCKED_OFFICIAL_ARTIFACT` (no qualifying candidate) → stop, record,
do NOT proceed to OfficialStable.

## 2. Mandatory binary audit BEFORE any gate (do not skip on a new version)

1. Wheel SHA256 vs discovery record; extract `_rocm_sdk_libraries/bin/MIOpen.dll`
2. Version string → build commit → GitHub compare `f0a5d266...<commit>` must be
   `behind_by: 0` (2026-11-15 data: rc2 `8faffed0f` FAILED here with behind_by=92
   despite a post-merge build date; nightly `9ea8cfc5`/dev `4e7d93e3` PASS)
3. `miopen_initializer_list` marker ≥1 (screening signal; never sufficient alone)

## 3. Run the gates

```powershell
# candidate channels (dev/nightly/rc) — ceiling *_CANDIDATE_PASS
.\run-golden-path.ps1 -Mode OfficialCandidate -LockJson <resolved_wheel_lock.json> -Gfx gfx1100 -StabilityRuns 10
# stable channel — the only path to OFFICIAL_STABLE_PASS
.\run-golden-path.ps1 -Mode OfficialStable   -LockJson <resolved_wheel_lock.json> -Gfx gfx1100 -StabilityRuns 10
```

Manual equivalents (what the modes run): install_official.ps1 →
verify_provenance → verify_torchvision_ops → verify_miopen_nostl(official leg,
--expect CANDIDATE|STABLE) → train_yolo.ps1 (exact CLI) → audit_optimizer →
verify_checkpoint_resume → run_stability (10×, `--cold` extra pass) →
generate_report full.

## 4. gfx1151 (Radeon 8060S) — same bytes, second machine

Repeat steps 1-3 with `-Gfx gfx1151`; device wheels:
`amd-torch-device-gfx1151` + `amd-torchvision-device-gfx1151`. Generate
evidence independently; never copy gfx1100 evidence.

## 5. Evidence classes

- `HOST_REUSE_FRESH_VENV` — earned on any dev host with a fresh venv
- `CLEAN_WINDOWS_INSTALL` — ONLY on a newly installed / controlled Windows
  image (no historical ROCm caches, no host STL dependency, no shims, no
  PYTHONPATH overrides). On a dev host record `G9 BLOCKED_INFRASTRUCTURE`.

## 6. GO/NO-GO

All of G0..G9 PASS on OFFICIAL_STABLE runtime class ⇒
`WINDOWS_RADEON_YOLO_GOLDEN_PATH_PASS`. Anything else ⇒ candidate-level
verdict at best, exact missing gate + owner recorded. See
`acceptance-contract.json` and `docs/release-checklist.md`.

## Known traps (verified this mission)

- rc wheels can be built AFTER the merge date yet still be pre-fix — only the
  compare API decides (rc2 case)
- PS 5.1: `WaitForExit(n)` is ms; `Start-Process -PassThru` + redirects loses
  `ExitCode`; pass JSON between PS and python via FILES
- a *completed* training's last.pt is not resumable (optimizer state stripped)
  — interrupt mid-run only; the harness verifies resumability pre-launch
- torchvision nms `hipErrorInvalidDeviceFunction` = missing torchvision device
  wheel (split-wheel), NOT a MIOpen regression
