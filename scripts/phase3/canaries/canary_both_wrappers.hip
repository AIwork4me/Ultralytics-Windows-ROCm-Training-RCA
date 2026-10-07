#include "miopen_type_traits.hpp"
#include "miopen_utility.hpp"
template <typename T>
__device__ int sink(T&& v)
{
    return std::is_same<T&, int&>::value ? 1 : 0;
}
extern "C" __global__ void bw_canary(int* out)
{
    int lv = 1;
    out[0] = sink(std::forward<int&>(lv));
}
