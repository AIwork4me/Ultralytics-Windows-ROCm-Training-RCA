# R22A Evidence Reconciliation Note (mission R22A.1 P1)

Reconciles the DERIVED dual-architecture comparison against the FROZEN primary
records it summarizes. No raw log was rewritten: every SHA256 below was
verified against the committed bytes on 2026-11-16, and both evidence manifests
(`evidence/raw/r22a-gfx1151/SHA256SUMS.txt`,
`evidence/raw/r22-dev-rerun/SHA256SUMS.txt`) still validate byte-for-byte.
Where a derived field was a `null` placeholder, the matrix
(`R22A_DUAL_ARCH_MATRIX.json`, updated in this same commit) now carries the
value quoted from the primary, with its source path and original SHA256.

## R1 — gfx1100 cold reliability 10/10

| | |
|---|---|
| Primary (frozen) | `evidence/raw/r22-dev-rerun/gpH_stability.json` |
| Original SHA256 | `d72b86fe5bd9950b0c1ec66134e428e703a0046707214616e227bb167897f0c3` |
| run_id | `GP-G-20261116-080547` — `python run_stability.py --runs 10 --cold --device -1` |
| Facts | 10/10 runs PASS, every run `cold(fresh-USERPROFILE)`, exit 0, anomalies `[]`, exit_code 0, `OFFICIAL_CANDIDATE`, gfx1100 / RX 7900 XTX |

Derived form: comparison MD row "G8 cold reliability 10/10 PASS" and matrix
`gfx1100.gates.G8_reliability == "PASS"`. The frozen matrix had left the
structured field `gfx1100.g8_cold` as `null` (summary existed only in the MD);
it is now filled from the primary above. No numeric claim changes.

## R2 — gfx1151 genuine resume-state evidence (G5)

| | |
|---|---|
| Primary (frozen) | `evidence/raw/r22a-gfx1151/gpF_resume.json` |
| Original SHA256 | `3d059addda2d60cf696c69752c6507120af9b4b7193849094c76b02ef37e8975` |
| run_id | `GP-F-20261116-093332` — `python verify_checkpoint_resume.py --epochs 8 --kill-after-epoch 2 --device -1` |

Genuine resume-state facts (not weights-only load; `resume_semantics` =
"resume=True (training state), not weights-only load"):

- `stages.rows_at_kill` = 3, `resume_exit` = 0, `resume_done_marker` = true
- **`resume_state_evidence_logged` = true** (optimizer/EMA/scheduler state
  actually restored, logged from the resumed process)
- `final_epoch_rows` = 9, **`epoch_continuity` = true** (no epoch reset)
- third process: `infer_exit` = 0, `infer_ok` = true (3-process lifecycle:
  `stage1` train, `stage3` resume, `stage4` infer)
- checkpoints hashed at kill: `last.pt` =
  `65e85d65cd3faeff530584e3058d442dcae969e7468395a7cc8c1c4c9d5ac5ad`,
  `best.pt` =
  `d8a8ddfb15af38c56b20280f8d8164b977d66386a70066bb9611d3591b08cb87`

Derived form: comparison MD row "G5 … PASS (resume=True semantics, 3
processes)". The frozen matrix carried `gfx1151.g5.{epochs_continuity,
resume_process,inference_third_process}` as `null` placeholders; they are now
filled from this primary. gfx1100's frozen G5 primary
(`evidence/raw/r22-dev-rerun/gpF_resume.json`, SHA256
`964b3002093d89f003a24a95ca75e264e0b008bf904721b85e7d8f975e9579c6`) shows the
identical stage pattern (rows_at_kill 3 → final_epoch_rows 9, epoch_continuity
true, infer_ok true) on the same 8-epoch/kill-at-2 contract.

## R3 — gfx1151 loaded MIOpen identity

| | |
|---|---|
| Primary (frozen) | `evidence/raw/r22a-gfx1151/gpA_provenance.json` |
| Original SHA256 | `dde5d258a37e9434e811ebe710f830c20a51f5203cd453fe468e707a6fed3da9` |
| run_id | `GP-A-20261116-093332` — `verify_provenance.py` inside the candidate venv |

- Actually-loaded DLL (in-process, after a CUDA op forced MIOpen init):
  `C:\RadeonYOLO\R22A\venvs\r22-candidate\Lib\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll`
- loaded SHA256 = `47a2e32c7401af2581860bc4a9e9fbb5b3f80be1e68c951b4ff3058f48683b91`
  — byte-identical to the wheel-embedded copy (same SHA256), i.e. no DLL
  redirection was in play
- embedded version string `3.6.3.4e7d93e3`, #13437 fix marker count = 2
- `runtime_class` = `OFFICIAL_CANDIDATE` (dev channel + verified ancestry),
  `lock_audit.ok` = true

Derived form: comparison MD "embedded MIOpen.dll `3.6.3.4e7d93e3` identical";
the matrix now records the loaded-DLL SHA256 explicitly.

## R4 — original G3 output vs parser-derived G3 result

Two attempts exist; both raw archives are preserved byte-for-byte.

**Attempt 1 — G3 FAIL (env-prep defect, disclosed incident):**

| | |
|---|---|
| Raw stdout | `evidence/raw/r22a-gfx1151/attempt1_g3_first_failure/gpD_train_stdout.log` — SHA256 `b75252114c04197ad18c374c9d76ba0faf84806d3e8c5f4e47e89e22527c5d86` |
| Gate status | `…/attempt1_g3_first_failure/gate_status.json` — SHA256 `90e2a12e79d0a28d0dab74e614d0dbf21c82d20abdf920d2b685c0c6b96f051f` — `overall: NO_GO`, G3 `FAIL/exit 1` |
| Parsed record | `…/attempt1_g3_first_failure/gpD_train_cli.json` — SHA256 `89fbe869598e1b4b5fdb0a0e9ed252f1f8c989fa00de260cb65a185259659e77` |

Training itself exited 0 (checkpoints saved, mAP50 0.941), but the env-prep
`settings.json` `runs_dir` override displaced the checkpoints out of the gate's
workdir scan, so the gate correctly fail-closed. Classification at the time:
harness/stack defect **NONE**; env-prep corrected (`runs_dir` removed) before
attempt 2. Full disclosure in `R22A_GATES.json`
(SHA256 `add665f3ade847470496c07ec9514f66088772d7b900458243614c8cc1b32187`).

**Attempt 2 — G3 PASS (accepted):**

| | |
|---|---|
| Original raw stdout | `evidence/raw/r22a-gfx1151/gpD_train_stdout.log` — SHA256 `b52f4c39b9e443e39d0cea9fb86b7b1643d65f42e66a99bc48ba0f49d7c1aeab` |
| Parser-derived record | `evidence/raw/r22a-gfx1151/gpD_train_cli.json` — SHA256 `3a20a266bcfc77981b1d8f18ac1e1d4a8405b3649e388798b2d39359004425f3` |
| Gate status | `evidence/raw/r22a-gfx1151/gate_status.json` — SHA256 `79603cab077c83e8bf7ba2a5e556c6b9ff92f767d1a04d6c43960f94c6c46e17` — G3 `PASS`, `overall: GO` |

Reconciliation: every parser-derived fact in the attempt-2 record
(`device CUDA:0` / `AMD Radeon(TM) 8060S Graphics`, `amp_check PASSED`,
`epoch_completed`, `losses_finite`, 2 hashed checkpoints) is traceable to the
attempt-2 raw stdout above; nothing was carried over from attempt 1, and the
attempt-1 archive remains the honest record of the first fail-closed stop.

## R5 — frozen locks vs corrected package-origin policy (R22A.1 P0)

Both frozen 46-artifact DEV locks (45 wheels + 1 official ROCm source
distribution `rocm-10.3.0.dev0+ff576965….tar.gz`) recorded
`gpu_stack_origin_official_channel.ok = false`,
`violations = ["rocm-bootstrap"]` under the old NAME-PREFIX rule.

| Lock (frozen, unmodified) | SHA256 |
|---|---|
| `evidence/raw/r22-dev-rerun/resolved_wheel_lock.json` (gfx1100) | `f99b78d504b673888e9b4862cea91b176596906aa134032515f08005e6899f7e` |
| `evidence/raw/r22a-gfx1151/R22A_PACKAGE_LOCK.json` (gfx1151; `R22A_GFX1151_PACKAGE_LOCK.json` byte-identical) | `97a2da636a8264887e2f9f89443e43673967e6d8b50acb2b5003a626fe089533` |

The historical `rules_checked` blocks are kept as-is (they are what the
resolver computed that day). The corrected policy classifies per artifact from
URL + metadata: `rocm-bootstrap==0.3.0` is the AMD-authored pure-Python
bootstrap component whose exact verified PyPI artifact (SHA256
`62d0160ecdd86f7132dbab9aec257cb2c96327df2592b0633aa6bb56399cc095`,
byte-identical in both locks) is explicitly allowlisted; native stack
artifacts (torch/torchvision/rocm*/amd-torch*, incl. the ROCm sdist) all
resolve from the exact `dev.repo.amd.com` channel; PyPI remains forbidden for
torch, torchvision, rocm-sdk-libraries and AMD device wheels. Both locks PASS
the recomputed audit (8 native + 1 approved bootstrap + 37 third-party = 46;
single ROCm family 10) — enforced by CPU regression test
`TestPackageOriginPolicy::test_frozen_dev_locks_pass_corrected_validation`.

## Integrity statement

- No file under `evidence/raw/` was modified by R22A.1; the derived artifacts
  updated are `R22A_DUAL_ARCH_MATRIX.json`, `R22A_DUAL_ARCH_COMPARISON.md` and
  this note, all under `windows-golden-path/reports/r22a-gfx1151/`.
- Manifest re-validation: `sha256sum -c evidence/raw/r22a-gfx1151/SHA256SUMS.txt`
  from the repo root (its paths are posix repo-relative); the r22-dev-rerun
  manifest lists names relative to its own directory — validate it as
  `sha256sum -c SHA256SUMS.txt` from inside `evidence/raw/r22-dev-rerun/`
  (a CRLF working tree needs the committed LF blobs via `git cat-file`, as
  10c8234 documented). Both were verified against the committed bytes on
  2026-11-16: 46/46 and 18/18 OK.
