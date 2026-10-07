// G57-5 (debug form): forward-sink results written separately to
// out[0..2] so any single mismatch is attributable.
#include "miopen_freestanding_utility.hpp"

template <typename T>
__device__ int forward_sink(T&& v)
{
    return std::is_pointer<decltype(v)>::value
               ? 0
               : (std::is_same<decltype(v), int&>::value ? 1 : 2);
}

extern "C" __global__ void canary_forward(int* out)
{
    int lval = 0;
    out[0]   = forward_sink(lval);                     // expect 1 (lvalue)
    out[1]   = forward_sink(int(0));                   // expect 2 (rvalue)
    out[2]   = forward_sink(static_cast<int&&>(lval)); // expect 2 (xvalue)
}
