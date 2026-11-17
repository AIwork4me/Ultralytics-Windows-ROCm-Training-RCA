# R22A.4.1 Runtime Provenance Audit — gfx1151 additional sample R22A4-B-ADD1

- Generated: 2026-11-17 (mission R22A.4.1 §5, second mandatory P0 audit item)
- Audit subject: `evidence/raw/r22a3-gfx1151/R22A3_WORKERS8_WARM_ADDITIONAL.json`
  as committed at `b1babd8e` (IMMUTABLE_RAW_EVIDENCE — not modified by this
  mission; every check below reads committed bytes).

## 1. The classification problem

The additional warm sample's receipt records `runtime_class: INCONCLUSIVE`
verbatim, because the probe invocation did not pass `--channel dev` (the
classification argument). The run was NOT repeated to repair a classification
field — the frozen first result stands. Under the unified contract
(`physical_provenance_ok`), an INCONCLUSIVE record can never earn a physical
PASS by itself; acceptance for this sample flows ONLY from independently
verified package-lock provenance + runtime identity agreement.

## 2. Source observations (verbatim from the committed receipt — never rewritten)

| Field | Committed value |
|---|---|
| run_id | `R22A4-B-ADD1` (run R1 `R22A4-B-ADD1-R1`) |
| runtime_class | **INCONCLUSIVE** (original field, preserved) |
| gpu_name / gfx_target | AMD Radeon(TM) 8060S Graphics / gfx1151 |
| torch | `2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-ff5769655eeb1b91a46bce9edc16d87ca0efe7b6` |
| torchvision | `0.29.2+gitb2281111.devrocm10.3.0.dev0.ff5769655eeb1b91a46bce9edc16d87ca0efe7b6` |
| hip | 7.18.26441 |
| ultralytics | 8.4.214 |
| wheel_lock_sha256 | `97a2da636a8264887e2f9f89443e43673967e6d8b50acb2b5003a626fe089533` |
| loaded_miopen_dll_sha256 | `47a2e32c7401af2581860bc4a9e9fbb5b3f80be1e68c951b4ff3058f48683b91` (FULL hash — no prefix inference) |
| source_sha (harness) | `ed9014173d08b5b6d0d673773ed351f473b10d63` (committed R22A.4 revision on the PR #18 branch) |
| run facts | exit 0; duration 64.5 s (receipt 66.2 s); workers 8/8; 13 worker identities (PID+create_time+ppid); home_pre_existed=true on retained `warm-home-b` |

## 3. Independently verified (recomputed this mission from Git objects)

1. **Package-lock identity** — SHA256 of the committed blob
   `evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json` at `b1babd8e`
   = `97a2da63…8533` — **exactly equal** to the receipt's `wheel_lock_sha256`.
   The runner hashed the on-disk package lock at probe time; the committed
   Git blob hashes identically (the pack is `-text`, byte-exact). The lock's
   channel is `dev` (dev.repo.amd.com),gfx1151/python tags match.
2. **Runtime identity agreement with the frozen same-pack receipts**
   (reference = `R22A3_WORKERS8.json` frozen five + `R22A3_ADAMW_AMP.json`):
   torch string, ultralytics version, gfx_target, GPU name identical;
   loaded MIOpen DLL SHA256 identical (47a2e32c…83b91, also the expected DLL
   recorded for gfx1100's pack).
3. **Wheel-identity consistency inside the lock** — the lock's `torch` wheel
   is `2.15.0+gitf6cd88cb.devrocm10.3.0.dev0.ff5769655eeb…` (separator '.'
   before the TheRock revision; the receipt writes '-'): same wheel, and the
   lock's `rocm` package `10.3.0.dev0+ff5769655eeb…` carries the SAME TheRock
   revision `ff576965…` — one coherent DEV snapshot, no stable/DEV mixing
   (an official-stable torch `2.12.0+rocm7.14.1` parses to no TheRock
   revision and would be rejected).
4. **Historical CI/commit linkage** — harness `source_sha ed90141` is a real
   commit on the PR #18 branch (ancestor of `e7c93ea`), i.e. the sample was
   produced by the committed unified harness, not a worktree-only variant.

## 4. Derived conclusions — explicit four-field classification

Implemented as `runtime_provenance_gate()` in
`windows-golden-path/scripts/supplemental_acceptance.py` (fail-closed; wired
into the canonical `--dual` CLI so a tampered lock or receipt forces the
dual-arch verdict to NO-GO):

| Field | Value for R22A4-B-ADD1 |
|---|---|
| RECEIPT_RUNTIME_CLASS | `INCONCLUSIVE` (verbatim, unchanged) |
| AUTHORITATIVE_PACKAGE_PROVENANCE | `DEV_LOCK_VERIFIED` (committed lock hash == receipt claim; channel=dev) |
| RUNTIME_IDENTITY_MATCH | `MATCH` (torch / ultralytics / MIOpen DLL / gfx / GPU / wheel identity) |
| ACCEPTANCE_DISPOSITION | `PROVENANCE_ACCEPTED_DEV` (ceiling DEV_CANDIDATE) |

Policy (documented in code + pinned by tests): absent evidence →
INCONCLUSIVE (never accepted); conflicting or forged evidence (hash mismatch,
wrong wheel/DLL/gfx, mixed stable+DEV, non-dev lock, missing gpu_name) →
NO_GO.

## 5. Trust-boundary regression tests (mission §5.3)

`TestRuntimeProvenanceGate` (11 tests, all passing; suite total 194):

1. INCONCLUSIVE + verified DEV lock + full identity → PROVENANCE_ACCEPTED_DEV
2. INCONCLUSIVE + lock absent → INCONCLUSIVE
3. INCONCLUSIVE + lock hash mismatch → NO_GO
4. forged DEV label / wrong lock wheel revision → NO_GO
5. correct torch label but wrong MIOpen DLL → NO_GO
6. correct GPU name but wrong gfx_target → NO_GO
7. mixed stable+DEV identity → never accepted (NO_GO/INCONCLUSIVE)
   7b. stable-channel lock → NO_GO
8. missing mandatory identity component → INCONCLUSIVE; missing gpu_name → NO_GO
9. integration: gate over the REAL committed pack → DEV_LOCK_VERIFIED /
   PROVENANCE_ACCEPTED_DEV
10. dual-arch enforcement: additional sample + rejected gate → dual verdict
    NO-GO (fail-closed); gate=None preserves the historical pure-function
    behavior used by the other CPU tests

## 6. Verdict

The additional sample's DEV runtime identity is **independently established**
through the committed package lock (hash-verified against the Git blob) and
full runtime-identity agreement with the frozen receipts. The original
INCONCLUSIVE field remains disclosed verbatim; no INCONCLUSIVE→PASS
conversion happens inside any receipt — acceptance is derived, labeled, and
fail-closed.
