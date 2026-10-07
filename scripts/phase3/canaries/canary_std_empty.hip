// G57-3: prove namespace std starts EMPTY for std-traits purposes in an
// HIP>=7 RTC translation unit (hiprtc 7 moved builtin traits to
// __hip_internal). Compiles -nostdinc and defines the full freestanding
// trait set; any hiprtc-provided duplicate would be a redefinition error
// at compile time. Kernel folds runtime results; host verifies checksum.
#include "miopen_freestanding_type_traits.hpp"

// Additional canary-only definitions proving the names were NOT already
// taken: extend a trait the shim owns via explicit specialization.
namespace std {
template <class A, class B>
struct canary_pair_integral : integral_constant<bool, is_same<A, B>::value>
{
};
} // namespace std

extern "C" __global__ void canary_std_empty(int* out)
{
    int r = 0;
    r = (r << 1) | (int)std::canary_pair_integral<int, int>::value;
    r = (r << 1) | (int)!std::canary_pair_integral<int, float>::value;
    r = (r << 1) | (int)std::is_same<std::true_type, std::integral_constant<bool, true>>::value;
    *out = r; // 3 bits -> 0b111 = 7
}
