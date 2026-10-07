// G57-4a: wrapper arm selection — RTC + HIP>=7 + NO reachable STL.
// The wrapper must route to miopen_freestanding_type_traits.hpp; kernel
// uses the BN-closure trait set and folds results (expect 0x7FFF = 1023 (all ten checks)
// over 10 checks).
#include "miopen_type_traits.hpp"

extern "C" __global__ void canary_wrapper_arms(int* out)
{
    int r = 0;
    r = (r << 1) | (int)std::is_same<std::remove_reference_t<int&>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_cv_t<const volatile int>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_const_t<const int>, int>::value;
    r = (r << 1) | (int)(std::true_type::value && !std::false_type::value);
    r = (r << 1) | (int)(std::integral_constant<int, 3>::value == 3);
    r = (r << 1) | (int)std::is_pointer<float*>::value;
    r = (r << 1) | (int)!std::is_pointer<float>::value;
    r = (r << 1) | (int)std::is_pointer<const float*>::value;
    r = (r << 1) | (int)(sizeof(std::conditional_t<true, char, double>) == 1);
    r = (r << 1)
       | (int)(sizeof(std::conditional_t<false, char, double>) == sizeof(double));
    *out = r;
}

// uses enable_if in a signature like bnorm_spatial_activation_functions.hpp
template <typename T, typename std::enable_if_t<std::is_pointer<T>::value, int> = 0>
__device__ int sig_if_pointer(T)
{
    return 1;
}
template <typename T,
          typename std::enable_if_t<!std::is_pointer<T>::value, int> = 0>
__device__ int sig_if_pointer(T)
{
    return 0;
}

extern "C" __global__ void canary_wrapper_enable_if(int* out)
{
    float f  = 0.f;
    float* p = &f;
    int r    = 0;
    r        = (r << 1) | sig_if_pointer(p);
    r        = (r << 1) | (1 - sig_if_pointer(f));
    r        = (r << 1) | 1; // padding so a single 5-bit result is expected
    *out     = r;            // expect 0b111 = 7
}
