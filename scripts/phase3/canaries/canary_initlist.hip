// G57-7: freestanding std::initializer_list viability under hiprtc.
// clang lowers braced-init-lists to field stores on the standard layout
// {const E*, size_t}; verify construction, begin()/size() iteration and
// value reads all work on the GPU with NO host STL.
#include "miopen_freestanding_initializer_list.hpp"

extern "C" __global__ void canary_initlist(int* out)
{
    std::initializer_list<unsigned long long> il = {3ULL, 1ULL, 4ULL, 1ULL, 5ULL};
    unsigned long long sum1 = 0, sum2 = 0, n = 0;
    for(unsigned long long i = 0; i < il.size(); ++i)
        sum1 += il.begin()[i];
    for(auto v : il)
    {
        sum2 += v;
        ++n;
    }
    out[0] = (int)(sum1 == 14ULL);  // 3+1+4+1+5
    out[1] = (int)(sum2 == 14ULL);
    out[2] = (int)(n == 5ULL);
    out[3] = (int)il.size();
}
// expect 1,1,1,5
