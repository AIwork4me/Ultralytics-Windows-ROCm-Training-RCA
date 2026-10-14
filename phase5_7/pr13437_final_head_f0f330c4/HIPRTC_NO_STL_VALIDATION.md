# HIPRTC No-STL Regression Validation — final HEAD `f0f330c4` (leg B)

## Test identity
- Source: `projects/miopen/test/gtest/hiprtc_selfcontained.cpp` **at
  `f0f330c4`** (204 lines; the exact committed blob, built in `C:\bfin`)
- Registered gtest:
  `CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl`
- Executed binary: `C:\bfin\bin\test_hiprtc_selfcontained.exe`
  (SHA256 `5f0c3f13…`, `BINARY_SHA256.txt`)
- Command (working dir `C:\bfin`, `C:\bfin\bin` first on PATH):
  `MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.*`
- Raw log: `raw/hiprtc/B_final_gtest_run.log` — exit code **0**

## Provenance markers inside the log
- `GetLibPath: "C:\\bfin\\bin"` → the process runs the freshly built MIOpen
- User-kernel-cache directory: **`3.6.2.f0f330c4`** → binary was built from a
  clean tree at the final PR HEAD (a dirty tree yields a `-dirty` label)
- `Raw device name: gfx1151`; every RTC compile carries `-mcpu=gfx1151`

## Probe outcomes (from the log, nonce batch `116007495326500_*`)

| Probe | Kernel | Options | Outcome in log |
|---|---|---|---|
| P0 | `gtest_rtc_trivial` | `-nostdinc` | compiled + saved (isolation usable; `-nostdinc` selected) |
| P1 | `gtest_rtc_stl_probe.cpp` (kernel symbol `gtest_rtc_probe`; `#error` if any STL header reachable) | `-nostdinc` | compiled + saved → **host STL unreachable** |
| P2 | `gtest_rtc_stl_use` (`#include <type_traits>`) | none | compiled + saved → ambient STL usable |
| S1 | `gtest_rtc_selfcontained` | `-nostdinc` | compiled + saved + **launched** |
| S2 | `gtest_rtc_selfcontained` | none (with-STL control) | compiled + saved + **launched** |

All five compiles are genuinely executed, not served from cache: each kernel
name is looked up with a per-run unique nonce option
(`-DMIOPEN_GTEST_RTC_NONCE=<steady_clock>_<seq>`), and the log shows
`Unable to load binary` → `SaveBinary` for every entry.

## Launch and value verification
The inline self-contained kernel (uses `miopen_type_traits.hpp`,
`miopen_utility.hpp`, `tensor_layout_t` initializer-list construction,
`std::forward` on an lvalue and an rvalue, `conditional_t`,
`is_trivially_copyable_v`) is launched with `global_work_dim = {1,1,1}` and
the gtest asserts the four written values `{3, 5, 9, 11}` via `EXPECT_EQ`
(`out[0..3]`). The gtest reports `[ OK ]` (13790 ms) and
`[  PASSED  ] 1 test` — value equality included.

## Honest-semantics checks
- The skip path (comgr environments that inject the STL) exists in the test
  source; it was **not** taken here (P1 proved STL unreachable), so this PASS
  exercised the intended no-STL fallback path, not a skip.
- The paired with-STL control (S2) also ran and passed, so the same kernel
  content works with the ambient STL as well.

## Result

**PASS** — the self-contained inline kernel compiles under `-nostdinc`
on gfx1151, launches, and produces the expected values, with the host C++
standard library proven unreachable (P1) and cache isolation proven by
per-run nonces.
