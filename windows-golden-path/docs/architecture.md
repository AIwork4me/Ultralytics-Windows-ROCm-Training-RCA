# Windows Golden Path Harness — Architecture (R21)

## Purpose

One toolkit that can honestly answer: **"Can an ordinary Windows Radeon user
train YOLO with official packages, with no AMD internals knowledge?"** It
validates whatever stack you point it at and refuses to over-claim — runtime
classification is enforced in code (`gp_lib.classify_runtime`), not in prose.

## Layout

```
run-golden-path.ps1          single entry point; 5 explicit modes
acceptance-contract.json     machine-checkable G0..G9 gate definitions
compatibility-matrix.yaml    channel/stack facts + mixing rules (scan-sourced)
requirements-lock/           hash-pinned wheel sets
scripts/
  gp_lib.py                  shared: provenance, evidence schema, classification
  check_environment.py       host baseline (no install, no GPU)
  discover_official_wheels.py 5-channel scan; NEVER synthesizes URLs
  resolve_package_set.py     pip-metadata resolution + hash pinning
  install_official.ps1       isolated venv; SHA256 verified before install
  verify_provenance.py       G0: wheel/DLL/binary lineage + workaround detector
  verify_miopen_nostl.py     G1: the actual #13437 regression (BN2d(100) @ 20,100,35,45)
  verify_torchvision_ops.py  G2: 9 GPU gates, no CPU fallback, nms split-wheel classifier
  train_yolo.ps1             G3: EXACT standard user command, exit code, ckpt hashes
  audit_optimizer.py         G4: real updates (named_parameters delta + per-step scaler)
  verify_checkpoint_resume.py G5: interrupt → NEW-process resume=True → reload+infer
  run_stability.py           G8: N independent runs; cold≠warm cache; anomaly tally
  generate_report.py         false-PASS rejection; SHA256SUMS; synthetic≠physical
tests/test_harness_cpu.py    CPU-only contract tests (no GPU needed)
reports/  evidence/          per-run outputs (gitignored except curated copies)
```

## Modes

| Mode | Installs? | GPU? | Max verdict |
|---|---|---|---|
| `-Preflight` (default) | never | never | baseline facts |
| `-EngineeringReference` | isolated venv from lock | yes | ENGINEERING_REFERENCE_PASS |
| `-OfficialCandidate <lock>` | isolated venv from lock | yes | DEV/NIGHTLY/RC_CANDIDATE_PASS |
| `-OfficialStable <lock>` | isolated venv from lock | yes | OFFICIAL_STABLE_PASS (also needs G7/G9) |
| `-PrepareRelease` | never | never | scan + artifact regeneration |

## Core invariants

1. **Fail-closed classification.** Any detected workaround (HIPRTC shim,
   MIOPEN_* override, DLL path redirection) forces `ENGINEERING_REFERENCE`
   regardless of test outcomes — an official verdict can never be issued on a
   shimmed process (`gp_lib.classify_runtime`).
2. **Evidence schema.** Every phase writes one strict-JSON record with the
   18 required keys (mission §11); booleans are real JSON booleans;
   `exit_code` is an int. `write_evidence` rejects violations.
3. **False-PASS rejection.** `generate_report.py full` re-derives verdicts:
   PASS + nonzero exit ⇒ violation; PASS without GPU provenance ⇒ violation;
   records tagged `harness_fixture` can never count as PHYSICAL_GPU_PASS.
4. **Marker ≠ proof.** `miopen_initializer_list` is a screening signal. A
   positive official verdict needs runtime no-STL behavior (G1) plus build
   lineage (G0). Conversely the decisive ancestry fact for the 2026-11-15
   rc/nightly/dev audits came from the GitHub compare API, not dates.
5. **Cold ≠ warm.** A fresh Python process is not a cold MIOpen cache; cold
   legs redirect USERPROFILE per run and never touch the user's global cache.
6. **Isolation.** Everything lives under `C:\RadeonYOLO\`; P17/P18/P19
   environments are read-only references; global PATH/HIP/driver untouched.

## Failure vocabulary

`gp_lib.FAILURE_CLASSES` (mission §11). Notable mappings:
`hipErrorInvalidDeviceFunction` in `torchvision.ops.nms` →
`TORCHVISION_DEVICE_WHEEL_MISSING` (the P18/P19 split-wheel dependency), so it
is never misfiled as a MIOpen source regression.

## Portability notes learned on this host (PS 5.1.26100)

- `Process.WaitForExit(n)` takes MILLISECONDS.
- `Start-Process -PassThru` + output redirection loses `ExitCode` — use
  `cmd /c ... > log 2>&1` + `$LASTEXITCODE`.
- Native-arg passing mangles embedded quotes — pass JSON via FILES.
- `Get-ChildItem -Include` needs a `\*` in the path.
- Subprocess text capture needs explicit `encoding="utf-8"` (host locale is
  cp936; yolo logs contain UTF-8/ANSI).
