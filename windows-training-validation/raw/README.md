# raw/ — file naming map (added 2026-11-14 audit, finding B-F4)

`g2_runner.py` writes **task-keyed** filenames only (`g2_{task}_{main,resume}.log`,
`g2_{task}_fp32.json`), so multiple legs of the same task overwrote each other during
the 2026-11-14 session. Forensic mapping of what each detect filename actually held at
audit time, and the clean-up performed:

## Scrambled logs (superseded originals, preserved verbatim in `scrambled_logs_20261114/`)

| File | Actual content (forensics: conda-path greps + AMP lines + summaries) |
|---|---|
| `g2_detect_main.log` | ENV-A amptrack **main attempt** (interrupt marker, `SUMMARY detect: 8/9 PASS`, exit=0; no pm13437 path reference) |
| `g2_detect_resume.log` | ENV-A amptrack **resume stage** (references `pm13437_official`, AMP checks passed, `SUMMARY detect: 13/14 PASS` exit=1, t08 FAIL) |
| `g2_detect_envA_amptrack_main.log` | ENV-A amptrack **main attempt** (aborted, `SUMMARY detect: 7/9 PASS` exit=1; **contains 1× `EvaluateInvokers` error line** — the sole official-wheel occurrence; in-process binary unproven for this aborted attempt) |
| `g2_detect_envA_amptrack_resume.log` | **ENV B** amptrack resume (references `pm13437_merged`, AMP **checks failed → FP32 fallback**, `SUMMARY detect: 14/14 PASS` exit=0) |

ENV-B detect fp32 (workers=0) main/resume logs and the ENV-B amptrack main log were
overwritten before any backup existed (lost; their records survive in the JSONs, the
detect-fp32 record restored from git `593160e`).

## Clean-up performed 2026-11-14

1. Originals of the four scrambled logs copied to `scrambled_logs_20261114/` (this table's source).
2. Canonical `g2_detect_fp32.json` (ENV B, 14/14, `ed7c67a9`) restored from git `593160e`.
3. **ENV-A amptrack leg re-run cleanly** (same command/args as original): artifacts now
   correctly named `g2_detect_envA_amptrack_rerun.{json,loaddll.json,main.log,resume.log}`
   — result: `13/14`, t08 FAIL **deterministically reproduced** (identical
   `max_param_abs_sum_delta=0.0`, `last_step_lr=4.0063e-05`), **0× EvaluateInvokers** in
   both fresh logs, post-hoc in-process probe = official `e97891df` (runner aborts at
   stage failure before its probe stage, same as the original run).
4. `g2_runner.py` naming limitation (task-keyed only, no amp/env dimension) is recorded
   in `G2_VERDICT.md`; renaming outputs post-run remains the convention for variant legs.

## Other new files from the 2026-11-14 audit session

- `g1_bn_estimator_probe.json` — persisted BN-estimator probe output (audit fix B-F3);
  reproduces the claimed `6.8e-08` (`rv_vs_unbiased_max_abs = 6.812e-08`, 45× closer to
  unbiased than biased reference), run on ENV B with patched DLL swapped in, fresh cache home.
