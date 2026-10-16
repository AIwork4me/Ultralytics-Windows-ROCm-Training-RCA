// Read-only audit probe: includes frozen production headers without a host STL.
#define MIOPEN_HIP_RUNTIME_COMPILE 1
#include "miopen_type_traits.hpp"
#include "miopen_utility.hpp"
#include "miopen_initializer_list.hpp"

template<class...> using void_t = void;
template<class T, class = void> struct has_type : std::false_type {};
template<class T> struct has_type<T, void_t<typename T::type>> : std::true_type {};
static_assert(!has_type<std::enable_if<false, int>>::value);
static_assert(has_type<std::enable_if<true, int>>::value);
template<class T> T&& expr();
static_assert(std::is_same<decltype(std::forward<int&>(expr<int&>())), int&>::value);
static_assert(std::is_same<decltype(std::forward<const int&>(expr<const int&>())), const int&>::value);
static_assert(std::is_same<decltype(std::forward<int>(expr<int>())), int&&>::value);
constexpr std::initializer_list<int> values{3, 5};
static_assert(values.size() == 2 && values.begin()[0] == 3 && values.begin()[1] == 5);
static_assert(values.end() - values.begin() == 2);
static_assert(sizeof(std::initializer_list<int>) == sizeof(const int*) + sizeof(__SIZE_TYPE__));
