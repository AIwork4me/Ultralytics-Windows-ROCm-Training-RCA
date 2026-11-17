# R22A.5N.1 Lock Provenance Reconciliation — the DEV-lock misbinding (P0-A)

- Generated: 2026-11-17 (mission R22A.5N.1 PHASE 1 §4)
- Scope: why three R22A.5N training receipts record the WRONG wheel-lock SHA,
  what was and was not affected, the fail-closed fix, and its negative tests.

## 1. The defect

`windows-golden-path/scripts/audit_adamw_amp.py` (R22A.5N revision) defined:

```python
WHEEL_LOCK = REPO_ROOT / "evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json"  # DEV lock
...
"wheel_lock_sha256": gp_lib.sha256_file(WHEEL_LOCK) ...   # unconditional
```

`--channel` only fed `classify_runtime`; the lock hash was always the
historical **DEV** set. Consequence — three Nightly receipts recorded:

| Receipt (pack A) | recorded `wheel_lock_sha256` | actual runtime |
|---|---|---|
| `05_yolo_training_amp/adamw_amp.json` | `97a2da63…` (DEV) | nightly venv |
| `07_reliability/workers8_amp.json` | `97a2da63…` (DEV) | nightly venv |
| `07_reliability/workers8_amp_v2.json` | `97a2da63…` (DEV) | nightly venv |

Correct Nightly lock identity (git blob of
`resolved_wheel_lock_nightly_gfx1151.json`, 46 records):
`cf147540a166a623bcf4f7961e07540980af5e117c7a0cc1f2cf38c2b013a7ac`
DEV lock blob SHA (`evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json`):
`97a2da636a8264887e2f9f89443e43673967e6d8b50acb2b5003a626fe089533`

## 2. Attribution corruption, NOT a wrong runtime

The same receipts independently prove the runtime was the Nightly candidate:

- `torch = 2.16.0a0+rocm10.3.0a20261116` (DEV lock carries different torch
  builds; this version exists only in the nightly lock)
- `loaded_miopen_dll_sha256 = f9312c3e…` = the frozen nightly candidate DLL
  (`rocm_sdk_libraries-10.3.0a20261116` wheel, byte-audit `b11baad9…`)
- `installed_manifest.json` (pack A) lists exactly the 46-record nightly set

So the misbinding is confined to the **receipt attribution field**. No package
that was installed or loaded during the physical runs came from the DEV set.
Per mission §4.6 this reconciliation is stated explicitly rather than inferred
either way.

## 3. The fix (fail-closed, backward-compatible)

`audit_adamw_amp.py` now carries `r22a5n1-wheel-lock-gate-v1`:

- `--wheel-lock <path>` — explicit experiment lock; bytes hashed, parsed, and
  BOUND to the run: lock channel == `--channel`, lock `gfx_target` == observed
  GPU, runtime versions (torch/torchvision/ultralytics) == lock records.
  ANY violation ⇒ `SystemExit(2)` BEFORE any GPU work.
- non-dev channel WITHOUT `--wheel-lock` ⇒ refuse (never silently default a
  Nightly run to the DEV lock).
- `channel=dev` without `--wheel-lock` ⇒ historical behavior preserved
  (R22A.2/R22A.3/R22A.4 receipts remain exactly reproducible).
- New receipt fields: `wheel_lock_path`, `wheel_lock_sha256` (correct value),
  `wheel_lock_channel`, `wheel_lock_gfx`, `wheel_lock_package_count`,
  `runtime_package_versions`, `provenance_gate_version`, full
  `wheel_lock_binding` block. No optimizer/model math touched.

## 4. Independent verification (engine side)

The hardened acceptance engine (`scripts/r22a5n1/nightly_acceptance.py`) adds
gate **LK**: it re-hashes the committed lock bytes and re-verifies EVERY
training receipt's binding via the same `verify_lock_binding` (a copied hash
string is not enough). Feeding pack A's actual field values to LK yields
`SHA_MISMATCH` — demonstrated as a pinned test
(`test_historical_pack_a_lock_defect_detected_by_lk`).

## 5. Negative tests (all executed, all rejected)

| Tampering | Result |
|---|---|
| DEV lock SHA substituted into a nightly receipt | LK `SHA_MISMATCH` → FAIL |
| receipt channel `dev` on nightly lock bytes | LK `BINDING_VIOLATION` → FAIL |
| lock bytes mutated after the receipt | LK `SHA_MISMATCH` → FAIL |
| internally-consistent lock+receipt from gfx1100 | LK `MISSION_IDENTITY_MISMATCH` → FAIL |
| runtime torch version ≠ lock record | `verify_lock_binding` violations → exit 2 |
| missing lock file | exit 2 before training |
| nightly channel without `--wheel-lock` | exit 2 before training |
| wheel version label changed (lock vs installed diff) | PKG FAIL |
| wheel SHA changed | PKG FAIL (sdk SHA ≠ frozen audit) |

## 6. New physical evidence (Stage C/E of this mission)

`reports/r22a5n1/R22A5N1-GFX1151-20261117-B/05_yolo_training_amp/adamw_amp.json`
and `07_reliability/workers8_amp_v2.json` are produced by the fixed instrument
with `--channel nightly --wheel-lock <committed lock>`: the receipts carry the
correct `cf147540…` binding, and the LK gate re-derives it from bytes.

The original three pack-A receipts are preserved byte-for-byte; their misbound
field remains visible as the defect record (never rewritten, never re-issued).
