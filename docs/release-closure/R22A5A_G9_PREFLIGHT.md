# R22A.5A G9 Preflight — clean-install contract & no-STL failure contract

- Generated: 2026-11-17 (mission R22A.5A Phase D, §7)
- Tooling: `scripts/r22a5a/g9_preflight.py` (CPU-only, no torch import,
  exit 3 = BLOCKED_RELEASE, exit 0 = PROCEED_CANDIDATE, exit 4 = violation)
- The historical `golden-path/` MODE A/MODE B behavior is untouched
  (R22A.4.1 freeze discipline).

## 1. Clean-install contract (the target)

**Official Windows driver + official compatible PyTorch/ROCm wheels +
published Ultralytics package → train, validate, save, resume — with NO
manual fixups.**

The G9 preflight statically blocks every hidden requirement from the
mission list. Scanner: `r22a5a_lib.scan_hidden_requirements` /
`scan_hidden_env`; audited files: `golden-path/README.md`,
`golden-path/WINDOWS_SETUP.md`, `windows-golden-path/README.md`,
`windows-golden-path/docs/release-checklist.md`.

Current audit result (2026-11-17): every hit in the committed user-facing
instructions is either (a) a NEGATION ("no editable fork") or (b) a
DISCLOSED pre-fix workaround clearly scoped to the known-issue section
(e.g. WINDOWS_SETUP.md §5 "install MSVC Build Tools as a temporary
workaround while the fixed wheel is pending"). Zero undisclosed reliance.
When a fixed stable wheel qualifies, the disclosed workarounds must be
REMOVED from the primary path (tracked as an R22A.5B acceptance step).

| Hidden requirement | Detection | Current state |
|---|---|---|
| Visual Studio Build Tools / host STL include paths | pattern + env `INCLUDE` | disclosed only (known-issue note) |
| `VCToolsInstallDir` | pattern + env | none in user instructions (appears only inside the no-STL test design, where REDIRECTING IT AWAY is the point) |
| `HIPRTC_COMPILE_OPTIONS_APPEND` / `HIPRTC_INCLUDE` | pattern + env | none in user instructions |
| custom `MIOPEN_*` overrides | pattern + env (except MIOPEN_LOG_LEVEL) | none |
| hardcoded developer paths (`C:\Users\…`, `C:\YOLO`, `/home/…`) | pattern | none |
| private package indexes | `--index-url` allowlist (5 AMD channels + pypi.org) | none |
| editable Ultralytics checkouts | pattern (negation-aware) | none (docs explicitly forbid) |
| local-only model files / undocumented datasets | golden-path uses `yolo26n.pt` auto-download + `coco8.yaml` (public) | OK |
| administrator privileges | not required by any step | OK |
| pre-existing kernel caches / patched DLLs | runtime concern → G9 runtime gate (R22A.5B) enforces fresh-cache identity | static OK |

## 2. Qualified-input gate (BLOCKED_RELEASE semantics)

`g9_preflight.py --plan <install_plan.json> --channel stable`:

- No fix-confirmed coherent candidate → **prints BLOCKED_RELEASE with the
  exact reason + re-scan instructions and exits 3. The golden path must
  NOT proceed with pre-fix wheels.** (On hosts WITH VS Build Tools a
  pre-fix wheel "works" — that masked success is exactly what this gate
  refuses to certify.)
- Qualified candidate → PROCEED_CANDIDATE + the emitted commands +
  next-step pointer (resolve_package_set → R22A.5B).
- Broken static contract (missing design element / broken golden-path
  suite) → exit 4 regardless of candidate state.

Verified this mission: stable → BLOCKED_RELEASE (exit 3); nightly →
PROCEED_CANDIDATE at OFFICIAL_DEV tier (exit 0).

## 3. No-STL failure contract (static design — execute in R22A.5B/G9 only)

Future runtime test = `windows-golden-path/scripts/verify_miopen_nostl.py`
(REUSED unchanged; statically verified now by
`g9_preflight.check_nostl_design`, 10/10 elements present in committed
bytes — see `release-provenance/r22a5a/g9_preflight_gfx1100_stable.json`).

Design elements (all statically pinned, CPU-verified):

1. **Loaded binary belongs to the candidate package**: R22A.5B runs
   `verify_provenance.py` in the target venv FIRST — loaded DLL SHA256 must
   match the wheel-audit DLL SHA256 (S2/S4 of the provenance contract).
2. **Host MSVC STL genuinely unreachable — NOT an unset variable**:
   `VCToolsInstallDir` is REDIRECTED to an empty scratch directory (the
   include tree cl.exe/HIPRTC would find is absent, not merely
   unconfigured) AND `INCLUDE=""` AND the child runs under a fresh
   `USERPROFILE`. Proving absence behaviorally: the pre-fix control leg
   MUST fail with the exact #3956 signature under this environment
   (`OFFICIAL_PRE_FIX_EXPECTED_FAIL`); an unexpected pass is reported as
   INCONCLUSIVE and investigated — it would indicate hidden STL
   reachability, never silently accepted.
3. **Fresh compilation & cache state controlled**: fresh USERPROFILE per
   leg = cold MIOpen cache identity (cache-role discipline inherited from
   the frozen R22A.2/3 harness contract).
4. **BatchNorm really executes on Radeon**: `nn.BatchNorm2d(100)` at the
   historically failing shape `(20,100,35,45)`, forward + loss + backward
   + `torch.cuda.synchronize()`.
5. **Finite outputs and gradients**: `isfinite` checks on output and both
   parameter grads; non-finite → exit non-zero.
6. **Original failure mode detectable**: `classify_nostl_failure` maps
   `HIPRTC_ERROR_COMPILATION` / `'type_traits' file not found` /
   `hipErrorInvalidKernelFile` / `miopenStatusUnknownError` to the mission
   failure vocabulary — the pre-fix signature is a RECOGNIZED, EXPECTED
   result on pre-fix bytes (that expectation IS the negative control).

**Execution boundary: design and static verification are complete NOW;
the GPU execution itself belongs to R22A.5B and is not run in this
CPU-only mission.**

## 4. User-facing scenario specifications (R22A.5B test plan)

Each step must record exact versions/identities (wheel SHA256s, DLL SHA256,
torch/ultralytics versions, driver, Windows build) in the acceptance
manifest:

| # | Scenario | Script (existing) | PASS condition |
|---|---|---|---|
| U1 | fresh installation | install commands from a qualified plan + `verify_environment.py` | real AMD GPU, `torch.version.hip` set, exit 0 |
| U2 | Radeon GPU selection | `train.py` (device=0 explicit) / CLI `device=-1` | genuine GPU in identity JSON, never silent CPU |
| U3 | real YOLO forward/backward | `train.py --smoke` | finite loss, ≥1 optimizer step |
| U4 | FP16 AMP verification | train AMP verdict + `audit_adamw_amp.py` facts | AMP_PASS taxonomy (see Stable acceptance contract §AMP) |
| U5 | valid optimizer updates | `audit_optimizer.py` | named_parameters delta > 1e-9, steps counted |
| U6 | model validation | `validate.py` | metrics produced from best.pt on GPU |
| U7 | save best.pt/last.pt | train run | both hashed into manifest |
| U8 | reload checkpoint | `verify_checkpoint.py` | weights load + delta vs pretrained proven |
| U9 | resume across a new process | `resume.py` in a second terminal | epoch continuity (see checkpoint integrity contract) |
| U10 | controlled failure diagnostics | pre-fix wheel leg / invalid ckpt / missing dataset | EXPECTED_FAIL/BLOCKED with classified reason — never a silent success |

## 5. What must wait for a repaired official wheel

- Any U-scenario on the STABLE channel (all currently blocked at the gate).
- The G9 CLEAN_WINDOWS_INSTALL class (fresh controlled image) — by design
  executed only once a stable candidate qualifies; on a development host
  the gate records HOST_REUSE_FRESH_VENV / BLOCKED_INFRASTRUCTURE honestly
  (acceptance-contract.json G9 semantics unchanged).
