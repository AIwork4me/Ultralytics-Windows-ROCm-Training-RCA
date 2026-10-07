// G57-4b: wrapper arm selection — RTC + HIP>=7 + STL REACHABLE (default
// env with MSVC auto-discovery). The wrapper must route to the REAL
// <type_traits>; the kernel uses is_trivially_copyable_v, which exists
// ONLY in the real STL (not in the freestanding header) — proving the
// real arm was taken. Expect 1.
#include "miopen_type_traits.hpp"

extern "C" __global__ void canary_wrapper_real(int* out)
{
    *out = (int)std::is_trivially_copyable_v<float> & 1;
}
