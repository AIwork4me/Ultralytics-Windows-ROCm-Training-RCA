// G57-1: exercise every freestanding trait at RUNTIME (results folded to a
// checksum the host verifies). Compiled with -nostdinc + RTC defines so no
// host STL participates. Includes the freestanding header DIRECTLY (the
// wrapper's arm selection is tested separately in G57-4).
#include "miopen_freestanding_type_traits.hpp"

extern "C" __global__ void canary_traits(int* out)
{
    int r = 0;
    // remove_reference / _t (lvalue, rvalue, plain)
    r = (r << 1) | (int)std::is_same<std::remove_reference_t<int&>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_reference_t<int&&>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_reference<int>::type, int>::value;
    // remove_const / remove_volatile / remove_cv (+ _t)
    r = (r << 1) | (int)std::is_same<std::remove_const_t<const int>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_volatile_t<volatile int>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_cv_t<const volatile int>, int>::value;
    r = (r << 1) | (int)std::is_same<std::remove_cv<const int*>::type, const int*>::value;
    // integral_constant / true_type / false_type
    r = (r << 1) | (int)(std::true_type::value && !std::false_type::value);
    r = (r << 1) | (int)(std::integral_constant<int, 3>::value == 3);
    // is_same negative control
    r = (r << 1) | (int)!std::is_same<float, double>::value;
    // is_pointer family
    r = (r << 1) | (int)std::is_pointer<float*>::value;
    r = (r << 1) | (int)std::is_pointer<const float*>::value;
    r = (r << 1) | (int)!std::is_pointer<float>::value;
    // conditional_t runtime materialization
    r = (r << 1) | (int)(sizeof(std::conditional_t<true, char, double>) == 1);
    r = (r << 1) | (int)(sizeof(std::conditional_t<false, char, double>) == sizeof(double));
    *out = r;
}

// 15 checks, each expected 1 => r == 0x7FFF
