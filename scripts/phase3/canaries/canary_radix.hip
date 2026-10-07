#include "radix.hpp"
extern "C" __global__ void radix_canary(int* out)
{
    // toFloatRounded runs only in non-RTC; just require the header parses.
    *out = 7;
}
