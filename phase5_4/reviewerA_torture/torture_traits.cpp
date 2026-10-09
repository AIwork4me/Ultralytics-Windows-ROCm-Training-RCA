// Reviewer A (Gate P54-11) differential conformance torture for the
// freestanding RTC headers. Compiled TWICE through hipRTC:
//   leg A: -nostdinc  -> miopen_type_traits/miopen_utility/tensor_view select
//                        the freestanding definitions (the patched fallback arm)
//   leg B: ambient    -> the same headers select the real host STL headers
// Identical source, identical static_asserts -> differential conformance check.
#include "miopen_type_traits.hpp"
#include "miopen_utility.hpp"
#include "tensor_view.hpp"

// ---- edge cases NOT covered by the file's own self-tests ----
// A1-A3: function and array references through remove_reference
static_assert(std::is_same<std::remove_reference_t<void (&)()>, void()>::value, "A1");
static_assert(std::is_same<std::remove_reference_t<int (&)[5]>, int[5]>::value, "A2");
static_assert(std::is_same<std::remove_reference_t<int&&>, int>::value, "A3");
// A4-A6: remove_const/remove_cv see only top-level cv
static_assert(std::is_same<std::remove_const_t<const int*>, const int*>::value, "A4");
static_assert(std::is_same<std::remove_const_t<int* const>, int*>::value, "A5");
static_assert(std::is_same<std::remove_cv_t<int* const volatile>, int*>::value, "A6");
// A7-A9: is_pointer edge cases
using FP  = void (*)(int);
struct S;
using MP  = int S::*;
using MFP = void (S::*)() const;
static_assert(std::is_pointer<FP>::value, "A7 function pointer is a pointer");
static_assert(!std::is_pointer<MP>::value, "A8 member pointer is not is_pointer");
static_assert(!std::is_pointer<MFP>::value, "A9 member function pointer is not is_pointer");
// A10: function types
static_assert(std::is_same<void(), void()>::value, "A10");
// A11-A13: integral_constant conversions
constexpr std::integral_constant<int, 2> ic2{};
static_assert(ic2 == 2, "A11 implicit conversion");
static_assert(ic2() == 2, "A12 call operator");
static_assert(std::is_same<std::true_type, std::integral_constant<bool, true>>::value, "A13");
// A14: nested conditional
static_assert(std::is_same<std::conditional_t<sizeof(int) == 4,
                                              std::conditional_t<true, char, long>,
                                              double>,
                           char>::value,
              "A14");
// A15: enable_if SFINAE overloads
template <class T, std::enable_if_t<std::is_pointer<T>::value, int> = 0>
constexpr char classify(T)
{
    return 'p';
}
template <class T, std::enable_if_t<!std::is_pointer<T>::value, int> = 0>
constexpr char classify(T)
{
    return 'v';
}
static_assert(classify((int*)0) == 'p', "A15a");
static_assert(classify(1) == 'v', "A15b");
// A16-A18: std::forward semantics
void fwd_check()
{
    int l       = 0;
    const int c = 0;
    static_assert(std::is_same<decltype(std::forward<int&>(l)), int&>::value, "A16");
    static_assert(std::is_same<decltype(std::forward<int>(1)), int&&>::value, "A17");
    static_assert(std::is_same<decltype(std::forward<const int&>(c)), const int&>::value, "A18");
}
// A19-A21: initializer_list two-field layout + clang braced-init lowering
static_assert(sizeof(std::initializer_list<int>) == 2 * sizeof(void*), "A19 layout");
constexpr auto il3 = {1, 2, 3, 4};
static_assert(il3.size() == 4, "A20 constexpr size");
static_assert(*(il3.begin() + 3) == 4, "A21 constexpr element access through begin()");
// A22: is_trivially_copyable on additional shapes
static_assert(std::is_trivially_copyable<FP>::value, "A22a");
static_assert(std::is_trivially_copyable<S*>::value, "A22b");
static_assert(std::is_trivially_copyable_v<double[2][3]>, "A22c");
// keep the lowering live in device code (field stores are generated here)
__global__ void torture_kernel(int* out)
{
    auto il = {10, 20, 30, 40};
    out[0]  = static_cast<int>(il.end() - il.begin());
    out[1]  = static_cast<int>(il.size());
    out[2]  = *(il.begin() + 3);
}
