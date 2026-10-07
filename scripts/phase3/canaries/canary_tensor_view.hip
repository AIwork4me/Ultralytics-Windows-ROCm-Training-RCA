#include "tensor_view.hpp"
extern "C" __global__ void tv_canary(int* out)
{
    // exercise the initializer_list-consuming constructor path
    tensor_layout_t<3> l{1ULL, 2ULL, 3ULL};
    *out = (int)(l.layout[0] + l.layout[1] + l.layout[2]);
}
