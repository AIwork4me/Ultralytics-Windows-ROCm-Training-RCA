# Evidence retention audit — PR #13437 Round 3

Agent C independent audit, 2026-10-17 (Asia/Shanghai). Baseline evidence commit:
`b0a52dd14e58af39aecd5c67bd080aeeba43de45`; implementation under test:
`d4b574ac8a039f39976c5f9f4e18adcb074dc237`.

## Disposition

**C acceptance: PASS for retention with all original artifacts retained. No artifact deletion
is recommended.** Agent D must independently accept the security/publication gate. The
baseline package is 135 tracked files / 2,950,273 bytes. Its size does not justify weakening
the archive. The closure adds audits, missing CI logs and reproducible inspection tools.

| Category | Purpose and dependency | Disposition / reproducibility |
|---|---|---|
| 24 `.elf` files | Three kthvalue A/B pairs, seven BatchNorm A/B pairs, and two representative BatchNorm A/B pairs; independent machine-code checks | Retain all. `scripts/verify_isa_pairs.py` reads ten primary pairs and checks nonempty `.text` and `.note` byte equality. Representative pairs preserve original extraction history. |
| 2 `.co` files | Compressed FP32 kthvalue objects | Retain; standard-library bz2 decoding permits independent comparison to ELF without ROCm. |
| 18 `.isa` and six additional kthvalue disassembly `.txt` files, plus `isa_A.txt` / `isa_B.txt` | Original wheel-objdump views; readable ISA review | Retain; seven `bnx` ISA A/B bodies are byte-identical. ELF `.text` equality is the independent check, not an empty text diff. |
| Four SQLite databases, four SHM sidecars, four zero-byte WAL files | Two copied cache layouts per A/B label; preserve exact snapshot state and original driver behavior | Retain all; total snapshot size is 229,376 bytes. Byte-identical duplicate layouts are small. The validator copies entire cache trees to a temporary directory before SQLite opens them, preventing recovery/checkpoint changes to evidence. WALs are currently empty; no claim relies on deleting them. |
| Empty `raw/perf/isa_A.body` and `isa_B.body` | Abandoned/failed text extraction | Retain and label as unusable for ISA validation. Two empty files can trivially compare equal, so they are never accepted as proof. |
| Empty `raw/kthvalue/E_r3_kthvalue_cold.log` and sibling `.time` | Failed `/usr/bin/time` invocation | Retain the failed attempt. The successful first fresh-cache execution is confusingly named `E_r3_kthvalue_warm.log`; its 27/27 result, not the empty file, supports functionality. |
| Earlier benchmark outputs, swap transcripts and interleaved logs | Expose failed attempts, DLL restoration and measurement history | Retain all; final timing data are the distinct `perf2_A_1`, `perf2_B_2`, `perf2_B_3`, `perf2_A_4` logs. Earlier overwritten/aborted legs cannot increase sample count. |
| Functional logs, build logs, scripts and binary hashes | Positive/negative controls, numerical checks, build/runtime identities and reproduction | Retain all. Historical scripts remain unchanged rather than being edited to pretend stronger results. `REPRODUCE.md` discloses machine-specific paths and required dependencies. |

No removed categories exist. Nothing is removed merely to reduce the PR size. SHA256SUMS
must be regenerated only after final additions/edits and must cover every tracked payload
except itself.

## What the retained ISA artifacts actually establish

The standard-library validator independently extracted ELF sections for all ten paired
variants and found `.text` and `.note` byte-identical. Text sizes in bytes:

- kth FP32 5376, FP16 5504, BF16 5376;
- bnx0–6: 8832, 3840, 5888, 2304, 5504, 4864, 4352.

Dynamic symbols identify bnx0–2 as backward spatial BatchNorm, bnx3–5 as forward training
spatial BatchNorm, and bnx6 as a multi-entrypoint forward training spatial object. The
archived `.isa` body counts are respectively 1289, 663, 974, 453, 941, 820, 747 lines.

Each archived SQLite snapshot contains **three kthvalue rows only**. bz2-decompressing
those rows exactly reproduces the matching FP32/FP16/BF16 retained ELF files for its label.
Both retained layouts give the same rows. **No BatchNorm cache rows are archived**, so
historical BatchNorm option-set/cache extraction is not independently reconstructed from
this package. A/B filenames and historical run narrative associate those standalone ELF
pairs with Round 2 and Round 3; these are weaker provenance than a retained complete
source-to-cache chain. The scoped claim is ten paired retained code-object variants with
identical machine code. It is not proof about every MIOpen kernel, source attestation or
whole-program timing.

## Measurement limitations that retention must preserve

Independent recalculation of the four final PERF_JSON objects reproduces all reported
median-of-leg-median deltas. Those are **not pooled medians of 400 retained samples**:
individual 200-event samples were not archived. Four aggregate minima are impossible
negative event durations:

| Final raw log | Workload | Minimum ms |
|---|---|---:|
| `raw/perf/perf2_A_1.log` | fwd 20×100×35×45 | -0.29501 |
| `raw/perf/perf2_A_4.log` | fwd 20×100×35×45 | -0.05075 |
| `raw/perf/perf2_B_2.log` | fwd 20×100×35×45 | -0.40767 |
| `raw/perf/perf2_B_3.log` | bwd 32×256×56×56 | -3.21978 |

The anomaly reaches a GPU-bound case. No individual samples exist to independently bound
its effect on medians. Retain the data and disclose timing as INCONCLUSIVE; the observed
GPU-bound median deltas (-1.13%, -3.91%, -3.35%, +0.73%) show no confirmed material
regression, but do not establish a timing non-regression PASS. Cold compile results and
sub-ms timing are also INCONCLUSIVE; no complete YOLO paired A/B exists.

The gfx942 job log repeats the captured failed-test output because ctest ran with `-V`
and `--output-on-failure`. Repeated GPU Hang text at lines 3921 and 4302 is **not evidence
of a second execution**. One failed invocation is established; no matched develop run or
causal exclusion exists. The correction belongs in the RCA rather than deleting the log.

## Privacy and integrity

Every current payload file was read bytewise and all text files decoded for inspection;
ELFs were parsed and caches opened in disposable copies. No GitHub-token/private-key/URL-
credential pattern was detected by the independent narrow pattern scan. This is combined
with Agent D's manual publication scan, not a general proof that any scanner finds every
secret. Generic `C:\Users\rocm` and build-root paths are necessary environment context.

An unnecessary private hostname in two YOLO log lines is redacted with equal-length text;
`provenance/LOG_REDACTION.md` records the before/after hashes and scope. No numerical
result, timestamp, exit classification or diagnostic is changed. Independently compared
against the original local `r3_mission` archive, all other existing raw evidence bytes
match. Final manifest verification and a fresh-clone check remain required after all edits.

## Acceptance boundaries

Retention does not make original missing measurements exist. It preserves the limited
historical observations, makes ten retained ELF comparisons independently executable,
and keeps failed-attempt disclosures. No new GPU/AMP/Linux run is claimed. Current-head
Linux CI and gfx942 residual risk remain separate upstream acceptance conditions.
