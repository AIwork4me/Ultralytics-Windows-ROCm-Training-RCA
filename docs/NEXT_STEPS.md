# Next Steps (post-Phase-1)

Phase 1 (this repo, branch `rca/windows-gfx1151-rocm714`) established the
failure down to LEVEL 2. Phase 2 work, in dependency order:

1. **Decide H10 vs H11 (LEVEL 3).** Cheapest discriminators first (from the
   independent ROCm review):
   - Standalone HIPRTC reproducer: small C program linking
     `hiprtc0714.dll`, compiling a source that includes `<type_traits>` —
     decouples the finding from torch/MIOpen entirely.
   - `amdclang -E -v` probe of the wheel's clang include-search behavior
     (early review indicates: resource dir + legacy VS fallbacks only).
   - `INCLUDE`-redirect A/B in a child process (no installs needed).
   - TheRock-vs-rockrel wheel diff: #2169's Windows log (TheRock build,
     Oct 2025) compiled past the include chain — find what that build
     shipped/configured differently (bundled STL? extra include flags?).
   Then, on a machine with Visual Studio 2022 / Build Tools installed (or
   after installing on a *test* box), re-run `scripts/02_batchnorm_minimal.py`:
   - Passes in a VS developer shell but fails in a plain shell →
     include-discovery/environment-propagation issue (INCLUDE not picked up
     by HIPRTC).
   - Passes in both → MSVC STL presence is the missing prerequisite
     (H10); fix = document/declare prerequisite, or make wheels
     self-sufficient (H11).
   - Fails in both → strengthens wheel/HIPRTC include-path defect (H11);
     inspect `hiprtcCompileProgram` include construction.
   - Also investigate the MIOpen-side lever surfaced post-review: the
     embedded `miopen_type_traits.hpp` no-STL shim is gated
     `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL`; re-enabling a shim for
     Windows (or removing std-header includes from HIPRTC BN sources)
     would be an upstream MIOpen fix candidate.
2. **Check wheel diff across ROCm versions** (7.2.1 vs 7.14.0): did the
   Windows wheels ever ship a C++ STL or extra include flags for HIPRTC?
3. **Minimal C reproducer without PyTorch** (optional): call
   `hiprtcCreateProgram/hiprtcCompileProgram` from a small C program
   linking `hiprtc0714.dll`, compiling a source that includes
   `<type_traits>`, to decouple the finding from torch/MIOpen entirely.
4. **Upstream engagement (after internal review):**
   - Comment on / link evidence to MIOpen #3956 (open, unanswered).
   - If H10: propose doc fix to AMD's Windows PyTorch install page
     (declare MSVC prerequisite) via ROCm docs issue.
   - If H11: file a rocm-libraries / TheRock issue with this repo as
     reproduction (the #2169→#842 duplicate closure missed the HIPRTC
     path).
5. **Validation matrix for any candidate fix:** re-run
   `scripts/03_batchnorm_matrix.py` (all 8 cases) +
   `06_ultralytics_train_repro.ps1` (expect cases D/C/G and GPU train to
   flip to PASS with no regression in A/B/E/F/H).
6. Keep this repo as the canonical evidence trail; append new raw logs
   only (`evidence/raw/`), regenerate `manifest.json` / `SHA256SUMS.txt`.
