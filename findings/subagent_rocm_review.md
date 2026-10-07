# SUBAGENT B — ROCm/MIOpen Stack Review (GPU software-stack boundary claims)

Reviewer: subagent B (ROCm/MIOpen stack reviewer, challenge mode). Date: 2026-10-07.
Scope: stack-level claims 1–7 only. All independent checks below were run
read-only on the machine under test (nothing installed, nothing modified; the
only writes were this findings file).

---

## Per-claim verdict

### Claim 1 — MIOpen is definitively in the failing call path → **PROVEN**

- `evidence/raw/miopen/minimal_bn_miopen_logging.txt:29–46` logs entry into
  `miopenBatchNormForwardTrainingActivation_V2` with `bn_mode = 1`
  (miopenBNSpatial), x/yDesc `{8,16,64,64}` NCHW packed, expAvgFactor 0.1;
  line 50 logs the driver-equivalent command; lines 54–64 log the HIPRTC
  compile failure inside that same MIOpen call; the API trace is bracketed by
  `miopenDestroyTensorDescriptor` teardown (lines 65–70). The torch traceback
  (`evidence/raw/batchnorm/minimal.txt:38–48`) goes through
  `torch/nn/functional.py:2850 → torch.batch_norm(..., torch.backends.cudnn.enabled)`,
  and `docs/ENVIRONMENT.md` records `cudnn.enabled=True`,
  `cudnn.version()=3005002` (MIOpen 3.5.2 behind the cuDNN-compat API).
- Minor nuance (does not change the verdict): the log does not record the
  API's return status, and "in the call path" is correctly NOT equated by the
  RCA to "defect owned by MIOpen".

### Claim 2 — HIPRTC is definitively the failing compilation layer → **PROVEN**

- `HIPRTC_ERROR_COMPILATION (6)` from `hiprtcCompileProgram` appears in every
  failure log (e.g. `minimal.txt:9–10`, `matrix.txt` cases C/D/G signatures,
  `train_gpu.txt:50–51`).
- `evidence/raw/environment/dll_provenance.json:4–22` lists `hiprtc0714.dll`,
  `hiprtc-builtins0714.dll`, `amd_comgr.dll`, `MIOpen.dll`, `amdhip64_7.dll`
  among live-loaded modules in the failing torch process (SHA256s recorded).
- My independent addition (see checks): the wheel's own clang reproduces the
  exact `'type_traits' file not found` **standalone, with no MIOpen and no
  GPU**, and prints a search path containing only the clang resource dir plus
  hard-coded legacy VS 8/9/10 fallback dirs. So the failing layer is more
  precisely "the wheel's `x86_64-pc-windows-msvc` clang toolchain as invoked
  via hiprtc/comgr" — consistent with, and sharper than, the RCA's wording.
  Which sub-layer *owns* the fix (hiprtc defaults vs MIOpen options vs wheel
  packaging) remains open, as the RCA states.

### Claim 3 — `<type_traits>` is physically ABSENT (not merely undiscoverable) → **PROVEN** (my broader search confirms; the RCA's own probe was not exhaustive)

- The RCA's probe (`evidence/raw/toolchain/toolchain_probe.txt`) covered PATH
  tools, VS roots, LLVM/Strawberry/conda/Git-msys/gcc roots, the two wheel
  trees, and env vars — but it did NOT cover: Windows SDK roots
  (`Program Files (x86)\Windows Kits`), Git-for-Windows' `mingw64` subtree
  (it checked only `usr\`), full-disk scans, or per-user toolchain installs.
- My independent checks closed those gaps:
  - Full C: drive scan (C: is the ONLY drive — `Get-PSDrive`): **0** files
    named `type_traits` anywhere, including a dedicated pass over
    `C:\Windows` (0 hits).
  - `C:\Program Files (x86)\Windows Kits` and `C:\Program Files\Windows Kits`
    do not exist (no Windows SDK installed at all).
  - `C:\Program Files\Git\mingw64\include\c++` and `mingw64\lib\gcc` absent;
    no `C:\msys64`, `C:\cygwin64`, `C:\Strawberry`, scoop, chocolatey.
  - `AppData\Local\Programs` (VS Code et al.), conda `envs\` and `pkgs\`:
    0 hits; the only conda toolchain-ish package is `vs2015_runtime`
    (VC++ runtime DLLs only — no headers, verified by listing).
  - pip cache holds only `rocm-7.14.0` (no older ROCm wheels to inspect).
- Residual caveats (do not falsify): (a) WSL `Ubuntu2204` exists (stopped,
  per `evidence/normalized/gate0_review.md`) with its STL inside an ext4.vhdx
  — invisible to file search AND unusable by a windows-msvc-target host
  compiler, so it could not plausibly serve; (b) "absent from disk" still
  does not prove "would be found if present" — that is the untested A/B.
  Verdict: the ABSENT statement is sound; the RCA should cite the fuller
  search space (or fold in this review's scan) rather than the narrow probe.

### Claim 4 — MIOpen.dll embeds the kernel sources → **PROVEN** (independently reproduced, plus new source-level detail)

- `grep -aoE 'MIOpenBatchNormFwd[A-Za-z]*\.cpp' MIOpen.dll | sort | uniq -c`
  → all four kernels, 1 occurrence each: `…FwdInferPerAct.cpp`,
  `…FwdInferSpatial.cpp`, `…FwdTrainPerAct.cpp`, `…FwdTrainSpatial.cpp`.
- `grep -aoE '#include <[a-z_]+>'` → `#include <utility>` ×3,
  `<type_traits>` ×2, `<limits>` ×2, `<initializer_list>` ×1, `<cstdint>` ×1.
- DLL inspected is the exact file hashed in `dll_provenance.json`
  (492,380,672 bytes).
- **New evidence the RCA lacks** (strengthens the mechanism to source level):
  I extracted the embedded `miopen_type_traits.hpp` text (byte offsets
  ≈481236415–481238960). Its structure is:
  ```cpp
  #if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL
  #ifdef MIOPEN_HIP_RUNTIME_COMPILE
  namespace std { /* inline shims: remove_reference, remove_cv, is_same,
                     is_pointer, conditional, … */ } // namespace std
  #else
  #include <type_traits> // std::remove_reference, std::remove_cv, is_pointer
  #endif
  #else
  #include <type_traits>      // <-- line 151, the failing include
  #endif
  ```
  On HIP ≥ 7.0 (local: 7.14.60850) the shim is compiled out and a real
  `<type_traits>` is unconditionally required. Similarly the embedded
  `miopen_cstdint.hpp` shims its typedefs under
  `#ifdef MIOPEN_HIP_RUNTIME_COMPILE` and only includes `<cstdint>` in the
  non-HIPRTC branch. This is the precise, source-level reason BN fails while
  other kernels compile (see claim 5), and it shows MIOpen upstream already
  possesses a no-STL fallback that is version-gated OFF for HIP ≥ 7.

### Claim 5 — Conv2d succeeds via MIOpen while BN fails because only BN kernels need C++ std headers → **PARTIALLY PROVEN** (now substantially stronger than the RCA left it; one part remains INFERRED)

What the RCA proved: cases F/P2 pass, i.e. conv executes on GPU (matrix F
16.76 s first call; `evidence/raw/conv/conv_control.txt` 0.05 s warm). No
MIOpen logging was captured during any conv run, so "conv goes through
MIOpen's runtime-compiled HIPRTC path" was previously unsupported — the RCA
itself flags this as unresolved (RCA.md "Remaining Hypotheses", last
paragraph).

My independent checks upgrade it:

1. **Direct evidence MIOpen runtime compilation succeeded for conv-support
   kernels on this exact stack**: `C:\Users\rocm\.miopen\cache\3.5.2.cd957402\
   gfx1151_20.ukdb` (current MIOpen 3.5.2, mtime 2026-10-07 11:36) contains
   successful compile records `MIOpenIm2d2Col.cpp.obj -DLOCAL_MEM_SIZE=…
   -DMIOPEN_USE_FP16…` (25 variants), `naive_conv.cpp.obj …`, and
   `Conv_Winograd_*.s.obj …`. These are MIOpen's own runtime-compiled (or
   runtime-assembled) conv kernels — proving the compile pipeline works for
   kernels that do not pull in std headers.
2. **Source-level asymmetry confirmed**: the embedded `MIOpenIm2d2Col.cpp`
   source's only `#include` line is `"miopen_cstdint.hpp"` (shimmed under
   HIPRTC; window ±12 KB/+4 KB around its text), whereas the BN chain
   (`.cpp:8 → batchnorm_functions.hpp:30 → configuration.hpp:34 →
   vector_types.hpp:8`) reaches `miopen_type_traits.hpp:151`, which on
   HIP ≥ 7 requires a real `<type_traits>`.
3. **GEMM control does not exercise HIPRTC at all**: the wheel ships
   precompiled code objects (`_rocm_sdk_libraries\bin\hipblaslt\library\
   gfx1151\*.co`, `*.hsaco`), so case A/P1 says nothing about the compile
   layer (the RCA never claimed it did — good).

Still INFERRED / unproven: (a) that the *specific* conv in case F used a
HIPRTC-compiled kernel rather than the precompiled CK path
(`MIOpenCKGroupedConv_gfx1151.dll`, 305 MB, present in the wheel) — no conv
MIOpen log exists; (b) the exact include set of `naive_conv.cpp` (its source
text was not located in my scan window). Marking guidance: "MIOpen runtime
compilation succeeds for some conv kernels on this stack" = PROVEN (ukdb);
"case F's specific algorithm compiled via HIPRTC" = INFERRED.

**Bonus archaeology**: the older
`C:\Users\rocm\.miopen\cache\3.5.1.98f923c854\gfx1151_20.ukdb` (Jul 23–Aug 2,
i.e. the machine's previous stack) contains
`MIOpenBatchNormFwdInferSpatial.cl.obj -DMIOPEN_USE_FP32=1 -DMIO_BN_GRP0=1 …`
records — BN previously compiled successfully on this machine **via the
OpenCL (.cl) path**. BN has never succeeded via the HIPRTC path locally. The
current 7.14 wheel stack was installed 2026-10-07 09:17 (dist-info mtimes),
so the previous stack ran for ~6 weeks before the RCA day. This is direct
local evidence that the BN compile path (or its STL requirement) changed
with the stack — a prime Level-3 lead the RCA does not mention.

### Claim 6 — What LEVEL 3 requires → **RCA's VS A/B is necessary but NOT sufficient; concrete additions below**

Gaps in the VS-installed A/B as proposed (RCA.md "Next Step",
HYPOTHESES.md H10/H11):

- It conflates three variables: (i) MSVC STL files being present,
  (ii) the *driver-level* clang MSVC detection (vswhere/registry) finding
  them, and (iii) hiprtc/comgr's embedded clang exercising that same
  detection. A negative result on a VS machine (BN still fails) would not
  distinguish "wheel/include-path defect" from "hiprtc never runs MSVC
  detection" without an explicit include-path experiment.
- My standalone clang probe (below) shows the wheel's clang falls back to
  hard-coded VS 8/9/10 era paths when detection finds nothing — i.e. the
  discovery machinery exists at driver level; whether hiprtc's embedded
  invocation shares it is untested.

Required additions (ordered by decisiveness per unit of effort):

1. **Standalone hiprtc reproducer** (no MIOpen, no torch): compile a 3-line
   `#include <type_traits>` HIP source through the wheel's `hiprtc0714.dll`
   (ctypes) on this machine (expect fail), then (a) with an explicit
   hiprtc include option pointing at a known-good STL, (b) on a VS-equipped
   machine. Decides STL-availability vs hiprtc-defaults vs caller-options in
   one axis. (I already produced the equivalent at the amdclang layer —
   same failure, fully standalone.)
2. **INCLUDE/CPATH redirection A/B** (no install): in a child process, set
   `INCLUDE` (honored by msvc-target clang) to any valid MSVC STL copy and
   rerun the minimal BN repro. If it compiles → availability is the sole
   missing piece (H10 reading); if not → discovery/include-path wiring
   defect in wheel/hiprtc (H11/HIPRTC reading). Sharper and cheaper than a
   full VS install A/B.
3. **Wheel-family diff**: TheRock nightly gfx1151 wheels (which per
   rocm-libraries #2169's Windows log compiled *past* all C++ headers on
   2025-10-16/17) vs this rockrel 7.14 wheel — diff `_rocm_sdk_core` for a
   bundled C++ STL and for hiprtc/comgr include defaults; repeat for #3956's
   7.2.1 lineage. Explains the external-report asymmetry and may identify
   the packaging regression directly.
4. **comgr/hiprtc option capture**: rerun the failing BN with
   `AMD_COMGR_SAVE_TEMPS=1` (+ `AMD_COMGR_REDIRECT_LOGGING=stdout`) to
   preserve the comgr temp dir and record the exact clang options MIOpen
   passes through hiprtc (which `-I`s, if any). Pins the owning layer.
5. **Upstream source check**: locate the rocm-libraries commit that added
   the `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` gate on the
   `miopen_type_traits.hpp` shim (found embedded in this DLL) — that commit
   is the MIOpen-side regression candidate that made HIP ≥ 7 require a host
   C++ STL, and extending the shim is a concrete smallest-fix candidate.
6. **ukdb lineage**: identify the previous local stack (MIOpen 3.5.1,
   pre-2026-10-07, BN compiled via `.cl`) — its wheel family/version dates
   the switch of BN to the HIPRTC path on Windows.

### Claim 7 — External-evidence reasoning re TheRock#842 / PR#1288 → **CONCLUSION PROVEN, but one supporting premise is factually WRONG (OVERREACH on the premise)**

- WRONG premise: `docs/EXTERNAL_EVIDENCE.md` (§ "Local failure vs
  rocm-libraries #2169 / TheRock #842", and its table row "Windows HIPRTC
  `type_traits` signature | Present") states #2169's Windows log fails in
  the HIPRTC path on `#include <type_traits>` "— the same mechanism we
  observe". The repo's own archived raw evidence contradicts this:
  `evidence/raw/external/rocm_libraries_2169_body.txt` contains **zero**
  occurrences of `type_traits` (verified `grep -c` = 0; my regex sweep found
  19 × "not a valid operand" and 4 × HIPRTC_ERROR_COMPILATION). The #2169
  Windows log (body lines 15–17 and 111–113) fails in the HIPRTC path with
  the **DPP inline-asm errors** (`reduction_functions.hpp:83`, "not a valid
  operand") — the same gfx1151 DPP defect as TheRock#842, just surfaced via
  the HIP source (`…SpatialHIP.cpp`) instead of the OpenCL source (`.cl`).
  Same for `docs/RCA.md` line ~152 ("#2169 … carried the same Windows
  signature") — inaccurate. `docs/CLAIMS_AND_EVIDENCE.md` C025 inherits the
  error.
- Consequence for the RCA's inference: the claim that #2169's duplicate
  closure "may have conflated the two paths" is unfounded — both of #2169's
  logs (Ubuntu and Windows) show the DPP defect, and the reporter confirmed
  the Oct-17 TheRock nightly (post-PR#1288) fixed his Windows case
  (`rocm_libraries_2169_comments.txt:7–19`). The closure was consistent.
- The BOTTOM-LINE conclusion still stands, on independent grounds: the
  local defect is NOT the PR#1288 defect — (i) local failure mode is header
  resolution (`'type_traits' file not found`), not invalid asm operands;
  (ii) PR#1288's stated change adds `MIO_BN_GFX115X` to **OpenCL** kernels
  (`rocm_libraries_pr1288.json`: "Added MIO_BN_GFX115X define to OpenCL
  kernels…"); (iii) PR#1288 merged 2025-10-08, long before ROCm 7.14 /
  MIOpen 3.5.2, so the DPP fix is in-tree here while the type_traits
  failure persists. Risk that the two defects are "actually the same":
  LOW — different error class, different compile path, and the DPP fix
  demonstrably present in the failing stack.
- Useful side-fact the RCA missed: #2169's Windows machine (TheRock 7.10
  nightly) resolved **all** C++ headers during the BN HIPRTC compile —
  either that machine had an STL or that wheel family shipped/discovered
  one. That is exactly the wheel-diff lead for Level 3 (see claim 6, item
  3).

---

## Independent checks performed (commands + results)

All commands run 2026-10-07 by this reviewer, read-only.

1. `grep -aoE 'MIOpenBatchNormFwd[A-Za-z]*\.cpp' …\_rocm_sdk_libraries\bin\MIOpen.dll | sort | uniq -c`
   → 4 kernel filenames, 1 each (claim 4 reproduced).
2. `grep -aoE '#include <[a-z_]+>' MIOpen.dll | sort | uniq -c`
   → utility×3, type_traits×2, limits×2, initializer_list×1, cstdint×1.
3. Python byte-offset analysis of MIOpen.dll (embedded-source region):
   - all 60 `MIOpen*.cpp` embedded kernel filenames enumerated;
   - raw dump of embedded `miopen_type_traits.hpp` (offsets ≈481236415–481238960)
     → HIP<7 shim + unconditional `#include <type_traits>` for HIP≥7 (see claim 4);
   - embedded `miopen_cstdint.hpp` dump → `#ifdef MIOPEN_HIP_RUNTIME_COMPILE`
     typedef shims, `#include <cstdint>` only otherwise;
   - embedded `MIOpenIm2d2Col.cpp` source: only include is
     `"miopen_cstdint.hpp"`;
   - quoted-include census of the embedded-source region (440–483.5 MB):
     `"miopen_type_traits.hpp"` included by 11 headers; angle-includes
     dominated by `<hip/hip_runtime.h>` (63) / `<hip/hip_fp16.h>` (51);
     std angle-includes only via the shim headers.
4. `find /c/ \( -path /c/Windows … \) -prune -o -type f -iname type_traits -print`
   (full C: excluding Windows) → **0 results**; separate
   `find /c/Windows -type f -iname 'type_traits'` → **0 results**.
   `Get-PSDrive -PSProvider FileSystem` → only `C:\` exists.
5. Existence probes: `C:\Program Files (x86)\Windows Kits` (absent),
   `C:\Program Files\Windows Kits` (absent), Git `mingw64\include\c++` /
   `mingw64\lib\gcc` (absent), `C:\msys64` / `C:\cygwin64` / `C:\Strawberry`
   / scoop / chocolatey (absent); targeted `type_traits` find over
   `AppData\Local\Programs`, conda `envs\`, `pkgs\`, `Temp` → 0;
   `pkgs\vs2015_runtime-*` → runtime DLLs only, no headers.
6. `amdclang.exe --version` / `--print-resource-dir` →
   `Target: x86_64-pc-windows-msvc`, resource dir
   `…\_rocm_sdk_core\lib\llvm\lib\clang\23` (verifies ENVIRONMENT.md claim).
7. `echo '#include <type_traits>' | amdclang.exe -x c++ -E -v -` →
   reproduces `fatal error: 'type_traits' file not found` standalone;
   search list = clang resource dir + legacy
   `C:/Program Files/Microsoft Visual Studio {10,9,8}.0/VC/include` fallbacks
   (all nonexistent); `-triple x86_64-pc-windows-msvc19.33.0`, `-std=c++14`.
   No wheel STL, no usable MSVC path.
8. `strings`-level inspection of `C:\Users\rocm\.miopen\cache\3.5.2.cd957402\gfx1151_20.ukdb`
   (mtime Oct 7 11:36) → 25 × `MIOpenIm2d2Col.cpp.obj -DLOCAL_MEM_SIZE=…`,
   `naive_conv.cpp.obj …`, `Conv_Winograd_*.s.obj …` (successful runtime
   compiles, current stack). Inspection of
   `.miopen\cache\3.5.1.98f923c854\gfx1151_20.ukdb` (Jul 23–Aug 2) →
   6 × `MIOpenBatchNormFwdInferSpatial.cl.obj -DMIOPEN_USE_FP32=1
   -DMIO_BN_GRP0=1 …` (BN compiled via OpenCL path under the previous
   stack).
9. `grep -c type_traits rocm_libraries_2169_body.txt
   rocm_libraries_2169_comments.txt` → 0 / 0; pattern sweep of the same
   file → 19 × "not a valid operand", 4 × HIPRTC_ERROR_COMPILATION,
   17 × MIOpenBatchNormFwdTrainSpatialHIP.cpp, 2 × ….cl (claim 7 premise
   check). #3956 JSON verified for Python 3.12.7 / torch 2.9.1+rocm7.2.1 /
   RX 9060 XT / gfx1200 / shape (20,100,35,45) / same
   `miopen_type_traits.hpp:151:10` include chain shape.
10. Wheel tree checks: `_rocm_sdk_libraries\bin` contains no
    `MIOpenDriver.exe` (matches RCA note); `_rocm_sdk_core\include\hip\`
    exists (hip headers resolvable — pinpointing that ONLY the C++ STL is
    missing from the compile's search path);
    `hipblaslt\library\gfx1151\*.co|*.hsaco` precompiled GEMM objects
    present; `grep` of `hiprtc0714.dll` → no hardcoded Windows include
    paths.

---

## Gaps & risks

1. **Factual error to correct in docs** (the only outright error found):
   `docs/EXTERNAL_EVIDENCE.md` §#2169 (and the inherited statements in
   `docs/RCA.md` §External Correlation and `docs/CLAIMS_AND_EVIDENCE.md`
   C025) assert the #2169 Windows log shows the `type_traits` failure. The
   archived raw log shows DPP inline-asm errors instead. The "different
   mechanism from PR#1288" conclusion survives on other grounds (see claim
   7) and should be re-based on those grounds. Also delete/adjust the
   "duplicate closure may have conflated paths" inference — the closure was
   sound.
2. **Un-mined local evidence**: `C:\Users\rocm\.miopen\` user kernel DBs
   (both 3.5.1 and 3.5.2) contain decisive pro/against facts (successful
   conv-path compiles now; successful BN `.cl` compiles before) that the
   RCA never inspected. The 3.5.1 `.cl` records also corroborate that BN's
   Windows backend previously used OpenCL — relevant to why TheRock#842-era
   issues all show `.cl` kernels while this stack fails in `.cpp`.
3. **Search-space citation**: the ABSENT (claim 3) conclusion is right, but
   the cited probe (`toolchain_probe.txt`) is narrower than the claim;
   either widen the probe script or cite this review's full-disk scan in
   the RCA (Windows Kits, mingw64, full C:, conda pkgs/envs, AppData).
4. **Conv-path logging absent**: no MIOPEN-enabled logging run exists for a
   conv workload, so "case F's conv went through MIOpen" is still inference
   (ukdb makes it a strong one). A 5-minute P8-style conv run with
   `MIOPEN_ENABLE_LOGGING=1` would close it.
5. **Version-gate discovery not yet upstreamed**: the `HIP < 7.0` gate on
   the `miopen_type_traits.hpp` HIPRTC shim (found embedded in the DLL) is
   the most likely MIOpen-side regression point and the smallest candidate
   fix; the RCA's H11 lists "MIOpen sources should avoid std headers" as a
   variant without knowing a shim already exists.
6. **Cannot exclude (low risk)**: hiprtc-side default-include-path defect —
   the standalone amdclang repro shows driver-level behavior, but hiprtc's
   embedded invocation may differ; only the hiprtc-level reproducer (Level
   3 item 1) closes this.
7. **Time-attribution risk (minor)**: EXPERIMENT_MATRIX P8 note "comgr temp
   dir auto-removed after failure" prevented source recovery — fine — but
   it also means the exact hiprtc option list was never captured
   (AMD_COMGR_SAVE_TEMPS would fix a rerun).

---

## What LEVEL 3 requires

LEVEL 3 = name the owning layer with a controlled experiment, i.e. decide
among: (a) user prerequisite (MSVC STL expected on Windows — H10),
(b) wheel packaging / include-path (H11a), (c) MIOpen source requirement
(H11b — now concretized as the HIP≥7 gate on the type_traits shim),
(d) hiprtc default-include defect. Minimum decisive set:

1. Standalone hiprtc reproducer via the wheel's `hiprtc0714.dll`
   (`#include <type_traits>` source): fails here; retest with explicit STL
   include option and on a VS machine → separates (d) from (a)/(b).
2. Child-process `INCLUDE`/`CPATH` → known-good MSVC STL, rerun minimal BN
   → if fixed, availability is sufficient (a); if not, wiring defect
   (b)/(d).
3. Wheel-family diff (TheRock gfx1151 nightly vs rockrel 7.14 vs 7.2.1):
   presence of any C++ STL and hiprtc/comgr include defaults → directly
   identifies packaging regressions; explains #2169-Windows vs #3956/local
   asymmetry.
4. `AMD_COMGR_SAVE_TEMPS=1` rerun to capture the exact compile options
   MIOpen→hiprtc passes (does MIOpen add any `-I` for an STL?) → decides
   MIOpen's share of responsibility.
5. Upstream `miopen_type_traits.hpp` history: the commit adding the
   `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` gate → names the regression
   and the candidate smallest fix (extend the shim / restore HIPRTC
   fallback for HIP≥7).
6. VS-installed machine A/B (the RCA's proposal) remains useful ONLY in
   combination with 1–2; alone it is confounded (STL presence vs driver
   detection vs hiprtc invocation).

The RCA's own boundary statement (LEVEL 2 reached, LEVEL 3 open) is
accurate; after this review, LEVEL 2 is *stronger* than the RCA claimed
(source-level shim gate, standalone clang repro, ukdb compile records), and
the cheapest LEVEL 3 steps are 1–3 above, not the VS A/B.
