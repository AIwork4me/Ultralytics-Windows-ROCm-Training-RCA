# Phase-2 Claims & Evidence Ledger (Gate 41)

P2-Cxxx IDs. Phase-1 C0xx IDs remain authoritative in
`docs/CLAIMS_AND_EVIDENCE.md` and are not restated here. Every row:
claim → raw file → command/result → confidence → counter-evidence
considered. All raw paths relative to `evidence/phase2/raw/` unless noted.

| ID | Claim | Evidence (raw file, command, result) | Confidence | Counter-evidence / notes |
|---|---|---|---|---|
| P2-C001 | `yolo_amd` conda env contains no Python (pre-Gate-22) | `environment/gate21_shell_state.txt` (+dir listing): only `conda-meta/`,`etc/`; `envs\yolo_amd\python.exe` absent | High | none |
| P2-C002 | With `(yolo_amd)` activated, `python` resolves to BASE; stack imports from base site-packages | `environment/gate21_activated_probe.txt`: CONDA_DEFAULT_ENV=yolo_amd yet sys.executable=`miniconda3\python.exe`, torch_location=base | High | none (ENV-B) |
| P2-C003 | Clean isolated env built: interpreter `envs\yolo_amd\python.exe`, 45-pkg closure, unrelated packages ABSENT | `environment/gate22_env_verify.txt`, `gate22_closure_manifest.json` (27,180 files, 4.89 GB); paddlex/paddle/etc ABSENT | High | onnxruntime leaks via user-site → neutralized by PYTHONNOUSERSITE=1 (documented) |
| P2-C004 | Clean env native stack is byte-identical to Phase-1 baseline | `environment/gate22_dll_provenance.json`: MIOpen.dll 74b4ee03…, hiprtc0714 c6159dd1…, amd_comgr 0a890dbd…, amdhip64_7 b4b4799f… | High | none (audit verified 10/10 DLLs) |
| P2-C005 | Clean env reproduces the Phase-1 failure field-for-field (P2-H1 falsified) | `clean_env/{A_gemm,B_conv,C_bn_minimal_train,C_bn_issue3956,C_bn_yololike,D_bn_eval,E_bn_cudnn_off,F_yolo_train}.txt`: A/B/E PASS; C/D/F FAIL identical 5-field signature | High | warm conv cache biases against, not toward, reproduction (audit) |
| P2-C006 | ROCm 7.14 Windows wheels built by "rockrel" CI from rocm-libraries | `clean_env/F_yolo_train.txt` embedded path `C:/home/runner/_work/rockrel/rockrel/rocm-libraries/...` | High | build-path string only; pipeline itself not audited |
| P2-C007 | Standalone HIPRTC (no torch/MIOpen) fails on ALL 5 std headers; no-include control compiles+executes (`out=42`) | `hiprtc/header_matrix.json` (probe `scripts/phase2/hiprtc_probe/hiprtc_probe.py`); `hiprtc/control_exec.txt` | High | control proves HIPRTC itself functional otherwise |
| P2-C008 | HIPRTC honors `-I`/`-isystem` options; rejects `--include-path=` | `hiprtc/include_option_probe.json`: fake header resolves via -I (code 3808B) and -isystem; nvrtc-style rejected | High | none |
| P2-C009 | Pre-MSVC: wheel clang C++ search = resource dir + legacy VS8/9/10 fallbacks only; all toolchain env vars unset | `hiprtc/gate25_include_discovery.txt`, `hiprtc/gate25_amdclang_verbose.txt` (PROXY labeling per protocol) | High | clang-driver proxy ≠ hiprtc internal, labeled as proxy; hiprtc behavior established directly in P2-C007/C012 |
| P2-C010 | MSVC/VS/BuildTools/WinSDK absent machine-wide (pre-Gate-27) | `msvc/gate26_msvc_discovery.txt`: no cl/vswhere/VS dirs/Windows Kits/type_traits | High | none |
| P2-C011 | VS Build Tools 2022 (VCTools workload) installed to C:\BuildTools: MSVC 14.44.35207 (cl 19.44.35229), WinSDK 10.0.26100.0 | `msvc/gate27_winget_install.txt` (exit 0), `gate27_post_install_record.txt` | High | machine state change documented; ROCm stack SHA256 re-verified unchanged |
| P2-C012 | With MSVC present, standalone HIPRTC compiles all std headers in a PLAIN shell (auto-discovery) | `msvc/gate27_armA_plain_shell.txt`: 6/6 HIPRTC_SUCCESS | High | none |
| P2-C013 | Minimal BN repro PASSES in plain shell with MSVC present (no env injection) | `msvc/gate27_armA_bn_repro.txt`: y mean=-0.000000, exit 0 | High | kernel-DB cache could mask — but scratch-DB forced-compile runs confirm fresh compiles pass (P2-C016) |
| P2-C014 | VS dev shell and INCLUDE-only injection also pass | `msvc/gate27_armB_devshell.txt`, `gate27_armC_include_only.txt` | High | none |
| P2-C015 | Wheel MIOpen honors `-I$ROCM_PATH/include`, shadowing MSVC discovery | `msvc/gate32_poison_header_test_v2.txt`: poisoned `type_traits` under ROCM_PATH → compile fails ON the poisoned file (cache-isolated, recompile confirmed) | High | v1 run cache-confounded, retained as confounder demo |
| P2-C016 | 48-line freestanding type_traits shim fixes ALL BN cases through real MIOpen, cache-isolated — does NOT rely on MSVC (MSVC was installed during these runs; the -I shadowing proof P2-C015 is what isolates the shim as the resolving header) | `candidateA/A_minimal|A_issue3956|A_yololike|A_eval|A_variants.txt` + `A_gemm/A_conv`: all PASS | High | wording corrected per Gate-45 review; MSVC-absence not claimed |
| P2-C017 | BN closure = 13 files; `<type_traits>` is the ONLY non-HIP std include; 5 std traits used | `miopen/extracted_kernel_tree/` + `STD_INVENTORY.txt` (closure computation archived in-session; AMD_COMGR_SAVE_TEMPS capture) | High | closure computed from actual wheel-extracted sources |
| P2-C018 | Upstream gate: `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` wraps the no-STL shim; HIP≥7.0 → real `<type_traits>` even in RTC | `upstream/miopen_type_traits.hpp` (develop fetch) == structure of extracted wheel header | High | raw artifact = preprocessor strings; branch semantics confirmed by C019 |
| P2-C019 | type_traits gate added by commit `ce14dab3` (PR #3803, 2025-06-16); utility gate added SEPARATELY by `b514736610` (PR #3147, 2025-12-18) — attribution split per Gate-45 review | `upstream/commit_ce14dab3.json` (file list: type_traits only) + `upstream/commit_b514736610.json` (utility only) | High | #3803 body terse ("Fixes for hip 7.0 breaking changes"); #3147 body cites #2617 |
| P2-C020 | hiprtc design context: 7.0 moved std traits out of builtin header to `__hip_internal`; `_WIN32` builds hardcode msvc target, no STL include path | `upstream/hiprtc_clr.cpp` (comment), `upstream/hiprtcInternal.cpp` (`#ifdef _WIN32` options block) | High | develop-branch sources; wheel binary behavior matches (C007/C012) |
| P2-C021 | Naive gate flip insufficient: historical shim version-rotted | `candidateB/dll_gate_flip_experiment.txt`: DLL patched `<7000000000ULL`→`<8000000000ULL` (2 sites) → fails at `miopen_type_traits.hpp:112` "expected class name" + `no template named 'enable_if'` | High | original DLL restored + SHA256-verified (`74b4ee03…`) |
| P2-C022 | Post-remedy regression: matrix 8/8 PASS (incl. previously-failing C/D/G) | `regression/gate33_matrix_rerun.txt` (exit 0), `gate33_matrix_results.json` | High | none |
| P2-C023 | Numerical correctness: GPU BN ≈ CPU reference (max_abs ≤ 7.2e-7; running stats ≤ 1.7e-10; grads finite) | `regression/gate34_numerics.txt` (NUMERICS: PASS, exit 0) | High | tolerance-based, not bit-exact (appropriate) |
| P2-C024 | YOLO26n GPU training closes end-to-end (amp=False AND default) | `yolo_closure/train_amp_off.txt`, `train_default_amp.txt`: epoch+val+weights+exit 0; mAP50=0.942 (functional closure only) | High | `EvaluateInvokers` non-fatal MIOpen tuning warnings present in logs (recorded, not blocking) |
| P2-C025 | Fresh-process re-validation (scrubbed env) passes BN + YOLO | `restart/gate36_fresh_shell.txt` | High | see file for arm details |
| P2-C026 | Cross-version: failure signature on ROCm 7.2.1/gfx1200/Py3.12 (MIOpen #3956) matches; TheRock builds declare MSVC prerequisite; #2169's build compiled past includes | Phase-1 external evidence (C022/C025/C028) + `upstream/therock_win_support.md` | Medium | external only; not locally tested on other ROCm/Python |

## Provenance note

Phase-2 raw artifacts are committed byte-exact (`.gitattributes` rule
`evidence/phase2/** -text`) and checksummed in
`evidence/phase2/SHA256SUMS.txt` (Gate 43). Phase-1 hashes untouched.
