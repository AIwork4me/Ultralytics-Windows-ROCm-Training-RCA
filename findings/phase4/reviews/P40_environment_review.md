# Gate P40 Independent Review — Environment Verification (Phase 4)

- Reviewer: independent (ZCode agent), review by direct observation
- Date: 2026-10-08
- Artifact under review: `evidence/phase4/environment/environment.json` (schema `phase4_environment_v1`)
- Machine: native Windows 11 (10.0.26200 x64), Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151)

## VERDICT: CONDITIONAL PASS

The environment substance is fully verified: the yolo_amd conda env is real and functional, the repo is on `main` and byte-identical with the live `origin/main` (fresh fetch), and the wheel MIOpen.dll hash matches the pristine Phase-3 value exactly. The conditions are documentation defects in the executor's own record, not environment defects: one factually inaccurate field (`working_tree: "clean"`), one non-verifiable truncated hash, and an undisclosed base/env duplication caveat.

## Findings

### BLOCKER
None.

### MAJOR
None.

### MINOR
1. **`"working_tree": "clean"` is inaccurate.** `git status` shows untracked `evidence/phase4/` (which contains the record itself, so the tree was already non-clean when the field was written). The *tracked* tree is clean and there are no staged/modified files, so the misstatement is semantic, not substantive — but an evidence record must not contain a false field.
2. **Conda base duplicates the entire ROCm stack, undisclosed.** `C:\Users\rocm\miniconda3\python.exe` (base) also has torch 2.12.0+rocm7.14.0, an MIOpen.dll with the *identical* SHA256, and an identical hipcc/clang. Bare `python` and bare `hipcc` on a default PATH resolve to **base** (`/c/Users/rocm/miniconda3/python.exe`, `/c/Users/rocm/miniconda3/Scripts/hipcc`). Consequence: version strings alone cannot discriminate env vs base; the only discriminator is `sys.executable`/`sys.prefix`, which the record does capture and which I independently reproduced. Residual leakage risk is low *only because* the two stacks are currently version-identical — if base drifts, bare-command runs would silently report base values.

### NIT
3. **Truncated hash in the record.** `"phase3_patched_dll_sha256": "9fa28af5..."` is not verifiable as written. The full value `9fa28af5d3b99ab7f099c5b9647bd30a9ed759d9a95d2cba29710228ce139f71` exists in committed Phase-3 evidence (`evidence/phase3/raw/regression/g78_v3_kernels.json`, `findings/phase3/phase3_conclusion.json`) and matches; the record should carry it in full or an explicit pointer.

## Evidence (commands run + key output)

1. Env identity (reviewer-executed, full path):
   `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe 2.12.0+rocm7.14.0 7.14.60850 True AMD Radeon(TM) 8060S Graphics`
   → matches record fields `python_executable`, `pytorch_version`, `hip_version`, `cuda_api_available`, `device_name`.
2. Git state: `git status` → `On branch main`, untracked `evidence/phase4/` only; `git fetch origin` exit 0; `rev-parse HEAD origin/main` → both `cb5e8cac615afff38bb8c78634a7cf130fc97a06`; `log --oneline -2` → `cb5e8ca phase3: add final upstream readiness audit`, `f553c49`. Commit `e43321f` exists ("publish immutable patch handoff"), consistent with the record's note `origin/main advanced e43321f -> cb5e8ca`. Sync verified against the **live remote**, not stale refs.
3. MIOpen.dll (reviewer-computed via env python hashlib):
   `74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a` — exact match; size 492380672 bytes — matches `size_bytes`. Machine confirmed at pristine wheel state.
4. Toolchain, all at the exact recorded paths: `git 2.55.0.windows.5`; `cmake version 4.4.4` (`phase3_buildtools\...\cmake.exe`); `ninja 1.13.2.git.kitware.jobserver-pipe-1` (`phase3_buildtools\Scripts\ninja.exe`); env hipcc → `HIP version: 7.14.60850-2b22ab01`, `AMD clang version 23.0.0git (...46fcb339fb61119b337f973c7ca9e710a319fdd0+PATCHED:1efe4605317a40d2170d33617075bd5675d0d558)`, `Target: x86_64-pc-windows-msvc`; `C:\BuildTools\VC\Tools\MSVC\14.44.35207` present; both hiprtc DLLs exist; `rocm_sdk_core-7.14.0.dist-info` present; all four phase3 artifact directories exist.
5. Ambiguity probes: base python torch → `2.12.0+rocm7.14.0` at `miniconda3\Lib\site-packages`; base MIOpen.dll SHA256 → identical `74b4ee...`; base hipcc → identical version strings; `which python` → `/c/Users/rocm/miniconda3/python` (base).

## Standard questions

**(a) Was the correct source/environment used?** Yes. The pinned interpreter `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe` resolves `sys.executable` inside `envs\yolo_amd` (not base), reports the exact recorded torch/HIP/device values, and the wheel MIOpen.dll matches the pristine Phase-3 hash. The repo is the real RCA repo at the recorded path, on `main`, byte-identical with the live `origin/main` after a fresh fetch.

**(b) Is the evidence sufficient?** Substantively yes — every checkable field reproduced under independent execution, including hash and live-remote sync. Insufficient in three particulars: the false `working_tree: "clean"` field, the truncated patched-DLL hash, and the absence of any note that conda base carries an identical duplicate stack (which is what makes the env-vs-base discriminator load-bearing).

**(c) Could any claim be explained by a wrong environment?** Partly, and only hypothetically. Because base duplicates the stack bit-for-bit (same torch version, same MIOpen hash, same hipcc/clang), an accidental bare-`python` run would have produced identical outputs — so version strings prove nothing about *which* env ran. However, the record's own discriminator (`sys.executable` inside `envs/yolo_amd`) was re-executed by this reviewer with the full path and holds, and since the stacks are currently identical, even a historical base leak could not have altered any recorded value. Stale PATH is a live hazard going forward (bare `python`/`hipcc` → base) but did not corrupt P40's recorded facts.

## Required actions (conditions for PASS)

1. Correct `rca_repo.working_tree` in `evidence/phase4/environment/environment.json` to reflect reality, e.g. `"no modified/staged tracked files; untracked evidence/phase4/ pending commit"`, or commit the evidence and re-record. (owner: executor)
2. Replace `"9fa28af5..."` with the full SHA256 `9fa28af5d3b99ab7f099c5b9647bd30a9ed759d9a95d2cba29710228ce139f71` or an explicit pointer to the committed Phase-3 evidence file. (owner: executor)
3. Add a caveat field to the record noting conda base duplicates the ROCm stack, and require all subsequent Phase-4 gates to invoke tooling via the absolute env path (or an activated `yolo_amd`) and to log `sys.prefix` — version strings must never be used as the env discriminator. (owner: executor, applies to P41+)
