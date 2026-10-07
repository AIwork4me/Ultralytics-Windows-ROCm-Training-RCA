// G57-4c: wrapper arm selection — OFFLINE (no MIOPEN_HIP_RUNTIME_COMPILE).
// Wrapper must include the real <type_traits>; kernel uses
// is_trivially_copyable_v (real-STL-only entity). Expect 1.
#include "miopen_type_traits.hpp"

extern "C" __global__ void canary_wrapper_offline(int* out)
{
    *out = (int)std::is_trivially_copyable_v<int> & 1;
}
