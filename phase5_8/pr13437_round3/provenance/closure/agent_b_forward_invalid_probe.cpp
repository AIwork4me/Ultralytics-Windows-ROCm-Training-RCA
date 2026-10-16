// Existing fallback does not diagnose this invalid use required to fail by standard std::forward.
#define MIOPEN_HIP_RUNTIME_COMPILE 1
#include "miopen_utility.hpp"
int& invalid_use() { return std::forward<int&>(1); }
