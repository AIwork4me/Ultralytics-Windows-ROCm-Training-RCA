# Release-to-Upstream Closure — Phase Index

Branch: `work/windows-rocm-training-release-closure` · Started: 2026-11-14
Goal: prove and package the complete Windows-native ROCm Ultralytics YOLO training story
(provenance → primitives → lifecycle → AMP → quality/performance → upstream readiness),
with every claim tied to raw logs and machine-readable verdicts.

| Doc | Content |
|---|---|
| [PHASE0_REPOSITORY_AUDIT.md](PHASE0_REPOSITORY_AUDIT.md) | repo audit, historical-evidence re-verification (171-file manifest PASS, 10/10 ISA pairs PASS), baseline environment |
| [BASELINE_STATE.json](BASELINE_STATE.json) | machine-readable baseline (envs, binaries, upstream facts, discrepancies) |
| [HANDOFF.md](HANDOFF.md) | 交接文档（会话状态、发现、待办、复现命令、陷阱） |
| [EXECUTION_PLAN.md](EXECUTION_PLAN.md) | gate map P0–P8 with blocking rules |
| [CLAIMS_AND_EVIDENCE.md](CLAIMS_AND_EVIDENCE.md) | running claims ledger (updated per gate + audit corrections) |
| [FINAL_REPORT.md](FINAL_REPORT.md) | final delivery report (P0–P8, corrected per P8 audit) |
| [GO_NO_GO.md](GO_NO_GO.md) | final verdicts: GO-A/GO-B CONDITIONAL PASS · GO-C NO-GO (BLOCKED_RELEASE) |
| [P8_INDEPENDENT_AUDIT.md](P8_INDEPENDENT_AUDIT.md) | three-reviewer adversarial audit record: verdicts, findings ledger + dispositions, re-run evidence, pending items |

Gate verdicts: `release-provenance/G0_VERDICT.md` (**BLOCKED_RELEASE** — full source chain
proven; no official release package contains PR #13437 as of 2026-11-14) → G1/G2/G3 → G4 → G5 →
FINAL_REPORT.md / GO_NO_GO.md (final delivery).

Binding conventions: PASS/FAIL/EXPECTED_FAIL/SKIP/BLOCKED/NOT_RUN/INCONCLUSIVE statuses only;
every GPU result carries an in-process loaded-DLL probe (**two disclosed deviations**: the G4
runs and `g3_amp10_envA.json` predate the per-file probe convention — P8_INDEPENDENT_AUDIT.md
m6/M4); ENV A = pristine official wheel, ENV B = source-built patched MIOpen (never labeled
official), **third environment = miniconda base pre-fix 7.14.0 wheel (G4 only, audit-corrected)**;
frozen phase5_7/phase5_8 evidence untouched.
