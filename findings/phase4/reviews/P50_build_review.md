# Gate P50 Review — Canonical MIOpen.dll Build Provenance (Phase 4)

- **Reviewer method**: direct observation via Git Bash + `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe`. No reliance on gate self-reporting except where independently cross-checked.
- **Review date**: 2026-10-08
- **Object under review**:
  - DLL: `C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\miopen\bin\MIOpen.dll`
  - Source: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical` (git worktree of `rocm-libraries-phase3`, HEAD `4084759`, 2 commits after `b68f894`)
  - Build script: `Ultralytics-Windows-ROCm-Training-RCA\scripts\phase4\build_canonical_miopen.py`
  - Evidence: `Ultralytics-Windows-ROCm-Training-RCA\evidence\phase4\build\{configure.log, build.log, build_provenance.json}`

## VERDICT: **PASS**

All seven verification points pass by direct observation. One MINOR evidence-quality finding (build.log does not capture the compile; the build is proven instead by ninja's own journal, timestamps, and hash chain) with a required follow-up action. No conda-base contamination. The DLL's identity, source provenance, and build-window provenance are independently confirmed.

## Findings

| ID | Severity | Finding |
|----|----------|---------|
| F-1 | **MINOR** | `build.log` (4 lines, 251 bytes) records only `[0/2] Re-checking globbed directories...` + `ninja: no work to do.` — the byte-exact signature of a **no-op** `cmake --build` (empirically demonstrated, see E-8). It therefore documents no compilation. The build itself is nonetheless proven to have run inside the script's build step by ninja's append-only journal `.ninja_log` (1030 edges, DLL linked at 11:31:48.267 exactly matching the DLL's on-disk mtime, session bracketed by configure.log 11:24:35.944 and build.log write 11:31:49.487 / provenance 11:31:50.046). Cause is benign (Windows ninja re-exec after the `CONFIGURE_DEPENDS` glob recheck regenerated `build.ninja` — two ninja processes are visible in the journal, one at 11:24:35.97 and one at 11:31:49.35, matching the two captured stdout lines), but the evidence set alone would not prove a build. **Required action** in Required Actions below. |
| F-2 | NIT | `build_provenance.json` records `worktree_state_deviation.restored: true` as a hardcoded literal; the script runs `git checkout -- .` but never verifies or records the resulting status. Reviewer independently confirms restoration succeeded (556/556 removed long-path files present again; see E-3). |
| F-3 | NIT | `git status --short`/`git diff --stat HEAD` are weak integrity signals in this repo: 46,396 of 54,443 tracked files carry skip-worktree bits, to which status/diff are blind. Reviewer compensated with direct blob-vs-HEAD content comparison of all files touched by the two reconstruction commits plus the toolchain file: 10/10 byte-identical (E-4). Future gates should not rely on "status clean" alone. |
| F-4 | NIT | The documented deviation ("556 over-260-char files temporarily removed") is one facet of a larger shape: 1177 tracked files have ≥260-char absolute paths in this worktree; 621 were **never materialized** (phase3-equivalent state, skip-worktree'd), 556 existed, were removed for the build, and were restored after. Arithmetic fully consistent (E-3). `core.longpaths=true` is set on the repo. |

No BLOCKER or MAJOR findings. **No conda BASE path leakage anywhere** (the specific MAJOR risk this gate was asked to exclude).

## Evidence

All commands run 2026-10-08 by reviewer.

### E-1. DLL identity (check 1, 7)

```
$ sha256sum C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\miopen\bin\MIOpen.dll
b32d6310817a225ff81cfe8de3dfe2a0d5c525caa845bad1f4d2304abc6aa721 *...MIOpen.dll
```
Matches `build_provenance.json` `dll_sha256` = `b32d6310...c6aa721` exactly. Size 465,298,432 bytes == provenance `dll_size` (RelWithDebInfo, ~465 MB, with 407 MB `.rdata` of embedded kernels/DBs and 201 MB PDB alongside).

PE structure (reviewer-parsed headers): `MZ`, `PE\0\0` at e_lfanew=0x78, machine `0x8664` (AMD64), optional-header magic `0x020B` (PE32+), 9 sections including `.hipFatBin`/`.hip_fat` (HIP code objects embedded) and `.reloc`. Import table (22 DLLs) resolves to exactly the expected dependency set:

```
libbz2.dll, sqlite3.dll, amdhip64_7.dll, hiprtc0714.dll, amd_comgr.dll, rocblas.dll,
KERNEL32.dll, MSVCP140.dll, WS2_32.dll, ntdll.dll, VCRUNTIME140.dll, VCRUNTIME140_1.dll,
api-ms-win-crt-{time,locale,stdio,runtime,filesystem,convert,heap,environment,string,math}-l1-1-0.dll
```

The `hiprtc0714.dll` import is consistent with the RTC-relevant two-commit change under review. `pefile` is not installed in the env; import parsing done manually (static names only — runtime load resolution is out of P50 scope).

### E-2. Source provenance (check 2)

```
$ git -C ...rocm-libraries-phase4-canonical rev-parse HEAD
4084759f3804748b7935d882db2d0445a3e0c380
$ git -C ... status --short        -> (empty, exit 0)
$ git -C ... diff --stat HEAD      -> (empty)
$ git -C ... rev-parse --git-dir
C:/Users/rocm/Desktop/YOLO_AMD/rocm-libraries-phase3/.git/worktrees/rocm-libraries-phase4-canonical
$ git -C ...rocm-libraries-phase3 worktree list
.../rocm-libraries-phase3               b68f894 [develop]
.../rocm-libraries-phase4-canonical     4084759 [prepare/miopen-hiprtc-selfcontained]
```

HEAD is exactly 2 commits after b68f894 (`c86d1b9` "MIOpen: keep RTC type traits self-contained...", `4084759` "MIOpen: make remaining RTC kernel std includes self-contained"), both touching only `projects/miopen/src/kernels/*` + `src/CMakeLists.txt` — consistent with the "two-commit reconstruction" characterization.

### E-3. Long-path restoration arithmetic (checks 2, F-4)

Reviewer recomputed with the script's own logic (`len(abs path) >= 260` over `git ls-files`):

```
>=260-char tracked files: 1177 | existing on disk now: 556
```

The 556 that existed at build time (script removed exactly `count: 556` per provenance) are all present again; the other 621 were never materialized (46,396 files repo-wide carry skip-worktree bits, so `git status` stays clean). `git config core.longpaths` = `true`.

### E-4. Content integrity of the distinguishing files (compensating for F-3)

Reviewer compared on-disk bytes to `git show HEAD:<path>` (SHA256) for every file touched by the two commits plus the build-defining files:

```
10/10 MATCH: src/CMakeLists.txt, miopen_freestanding_type_traits.hpp,
miopen_freestanding_utility.hpp, miopen_type_traits.hpp, miopen_utility.hpp,
miopen_freestanding_initializer_list.hpp, radix.hpp, tensor_view.hpp,
projects/miopen/CMakeLists.txt, cmake/ClangToolChain.cmake
```

### E-5. Configure command cross-check (check 3)

`build_provenance.json:configure_command` joined == `configure.log` line 1 (after `$ ` prefix), **byte-identical, 2431 chars**. Key flags present in both and in `CMakeCache.txt`:

- `-DCMAKE_HIP_ARCHITECTURES=gfx1151` (cache: `CMAKE_HIP_ARCHITECTURES:UNINITIALIZED=gfx1151`)
- toolchain `-DCMAKE_TOOLCHAIN_FILE=...\rocm-libraries-phase4-canonical\projects\miopen\cmake\ClangToolChain.cmake` (also in cache)
- `-DROCM_PATH=C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core` (cache match)
- `-DBUILD_TESTING=OFF` (cache `BUILD_TESTING:BOOL=OFF`)
- `-DCMAKE_BUILD_TYPE=RelWithDebInfo`, `-G Ninja`, `MIOPEN_BUILD_CK/DRIVER=OFF`, `MIOPEN_ENABLE_FIN=OFF`, compilers/linker all under `_rocm_sdk_core\lib\llvm\bin` (cache match)

### E-6. Unexpected-dependency review (check 4)

Fixed-string scan (both slash styles) for conda BASE markers `C:\Users\rocm\miniconda3\Lib\site-packages`, `...\miniconda3\Library`, `...\miniconda3\Scripts` in:

```
configure.log:        0 hits
build.log:            0 hits
CMakeCache.txt:       0 hits
compile_commands.json:0 hits
build.ninja:          0 hits
```

Full root audit of all 6007 path tokens across the 577 entries of `compile_commands.json` (the commands actually used to compile):

```
2069  canonical source (rocm-libraries-phase4-canonical)
1702  phase3 deps/shims (phase3_deps)
1579  yolo_amd env (_rocm_sdk_core)
 657  phase4 build dir (phase4_build)
   0  anything else (no conda base, no other roots)
```

MSVC/WinSDK headers enter via the `INCLUDE`/`LIB` env vars set by the script (verified in `build_canonical_miopen.py::env()`, which deliberately does not inherit PATH), hence their absence from `-I` flags is expected.

### E-7. Wheel-side staging cleanup (check 5)

```
$ ls C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\lib\cmake
ls: cannot access '...': No such file or directory   (exit 2)
$ ls ...\_rocm_sdk_core\lib
amd_comgr.lib amdhip64.lib amdocl64.lib cltrace.lib hiprtc-builtins.lib hiprtc.lib llvm
```

Temporary `hip-lang` staging dir is gone; wheel restored to pristine state.

### E-8. build.log content vs. reality (check 6, F-1)

`build.log` full content:

```
$ cmake.exe --build ...phase4_build\miopen --target MIOpen -- -k 0
exit=0
[0/2] Re-checking globbed directories...
ninja: no work to do.
```

Zero FAILED/error entries (check 6 pass; `configure.log` likewise has only warnings plus one benign try-compile result line `Performing Test CMAKE_HAVE_LIBC_PTHREAD - Failed`).

Reviewer empirically established, using a throwaway CMake+Ninja+clang project with the exact same cmake 4.4.4 / phase3_buildtools ninja / `_rocm_sdk_core` clang++ that a **piped** build does print `[N/M]` edge lines, and that a no-op build prints exactly `[0/2] Re-checking globbed directories...\nninja: no work to do.` — byte-identical to `build.log`'s captured output. So `build.log` alone evidences no compilation.

The actual build is proven by `.ninja_log` (ninja's own journal; 1030 edges):

```
edge 1:   verify_globs completed 11:24:36.027   (ninja proc #1, started 11:24:35.97)
...      1028 compile/link edges               (DLL edge end -> output mtime 11:31:48.2677836)
edge 1030: verify_globs completed 11:31:49.403  (ninja proc #2, started 11:31:49.35)
```

Timeline coherence (all from file mtimes at second/sub-second precision):

```
11:24:34.010  CMakeCache.txt written (configure finishing)
11:24:35.837  build.ninja written ("Generating done")
11:24:35.944  configure.log written (script's configure step returned)
11:24:36.027  first ninja edge (build step began ~30 ms after configure returned)
11:31:47.854  .ninja_deps last update
11:31:48.236  lib/MIOpen.lib
11:31:48.267  bin/MIOpen.dll   (mtime == .ninja_log DLL-edge recorded mtime, to the 100 ns)
11:31:48.949  bin/MIOpen.pdb
11:31:49.403  last ninja edge (proc #2 glob recheck)
11:31:49.446  .ninja_log last write
11:31:49.487  build.log written  (build subprocess exited)
11:31:50.046  build_provenance.json written (internal timestamp 11:31:50.008789)
```

The full build ran inside the script's single `cmake --build` subprocess window; a second script invocation is excluded because it would have rewritten `configure.log` after 11:31 (its mtime is 11:24:35.944). The two captured stdout lines correspond to the two glob-recheck ninja processes; the middle (full-build) process's `[N/M]` stream did not reach the capture pipe, consistent with Windows ninja re-exec behavior after the `CONFIGURE_DEPENDS` glob recheck regenerated `build.ninja`.

Also confirmed: `install/` prefix absent (only `--target MIOpen` was built, as recorded); `bin/`, `lib/` artifact mtimes all within the 11:24–11:31 window; no stale/pre-existing DLL (DLL mtime is in-window and equals the journal-recorded link mtime).

## Required Actions

1. **(From F-1, required before evidence archival)** Copy `phase4_build\miopen\.ninja_log` (and optionally a SHA256 of `.ninja_deps`) into `evidence\phase4\build\` as supplementary build evidence, and add a one-line annotation to `build.log` (or the gate record) noting that the captured no-op-style output is a ninja glob-recheck/re-exec capture artifact and that the compile is evidenced by `.ninja_log`.
2. (From F-2) Change `build_canonical_miopen.py` to verify post-build `git status --short` and record its (empty) output in the provenance JSON instead of the hardcoded `restored: true`.
3. (From F-3) In future gates, do not cite "git status clean" as worktree-integrity evidence for this repo (skip-worktree blind); use blob-vs-HEAD comparison for build-input files as done in E-4.

## Pre-verified facts for downstream gates (P51+)

- Canonical DLL SHA256: `b32d6310817a225ff81cfe8de3dfe2a0d5c525caa845bad1f4d2304abc6aa721` (465,298,432 bytes, PE32+ x64, imports `amdhip64_7.dll`/`hiprtc0714.dll`/`amd_comgr.dll`/`rocblas.dll`/`libbz2.dll`/`sqlite3.dll` + CRT).
- Build dir `phase4_build\miopen` is internally coherent (single 11:24–11:31 session) and `build_phase3` was not touched.
- Wheel `_rocm_sdk_core` is pristine (no staged `lib\cmake`).
