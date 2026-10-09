// G05 STL-availability probe for the HIPRTC path on Linux/gfx1100.
// For each include-isolation mode, an RTC kernel reports (via __has_include)
// whether the four STL headers used by radix.hpp / tensor_view.hpp wrappers
// are visible to the RTC compiler. Nothing is included directly, so the probe
// never fails to compile; the flags ARE the measurement.
#include <hip/hiprtc.h>

#include <cinttypes>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <hip/hip_runtime_api.h>

static const char* probe_src = R"(
extern "C" __global__ void stl_probe(int* out)
{
#if __has_include(<type_traits>)
    out[0] = 1;
#else
    out[0] = 0;
#endif
#if __has_include(<utility>)
    out[1] = 1;
#else
    out[1] = 0;
#endif
#if __has_include(<limits>)
    out[2] = 1;
#else
    out[2] = 0;
#endif
#if __has_include(<initializer_list>)
    out[3] = 1;
#else
    out[3] = 0;
#endif
}
)";

int main(int argc, char** argv)
{
    const char* modes[][2] = {
        {"default",      nullptr},
        {"nostdincpp",   "-nostdinc++"},
        {"nostdinc",     "-nostdinc"},
    };
    const char* names[4] = {"type_traits", "utility", "limits", "initializer_list"};

    for (auto& mode : modes)
    {
        hiprtcProgram prog;
        if (hiprtcCreateProgram(&prog, probe_src, "stl_probe.cu", 0, nullptr, nullptr)
            != HIPRTC_SUCCESS) { std::printf("MODE %s: create FAILED\n", mode[0]); continue; }
        std::vector<const char*> opts;
        opts.push_back("-mcpu=gfx1100");
        if (mode[1]) opts.push_back(mode[1]);
        hiprtcResult r = hiprtcCompileProgram(prog, (int)opts.size(), opts.data());
        std::printf("MODE %-9s flags=[-mcpu=gfx1100%s] compile=%s", mode[0],
                    mode[1] ? std::string(std::string(",") + mode[1]).c_str() : "",
                    r == HIPRTC_SUCCESS ? "OK" : "FAIL");
        if (r != HIPRTC_SUCCESS) { std::printf("\n"); hiprtcDestroyProgram(&prog); continue; }

        std::size_t codesz = 0; hiprtcGetCodeSize(prog, &codesz);
        std::vector<char> code(codesz); hiprtcGetCode(prog, code.data());

        hipModule_t module;
        hipError_t he = hipModuleLoadDataEx(&module, code.data(), 0, nullptr, nullptr);
        if (he != hipSuccess) { std::printf(" load FAILED he=%d\n", he); hiprtcDestroyProgram(&prog); continue; }
        hipFunction_t fn;
        hipModuleGetFunction(&fn, module, "stl_probe");
        int* dout = nullptr; int hin[4] = {-1,-1,-1,-1};
        hipMalloc(&dout, sizeof(hin));
        void* args[] = {&dout};
        he = hipModuleLaunchKernel(fn, 1,1,1, 1,1,1, 0, 0, args, nullptr);
        hipDeviceSynchronize();
        hipMemcpy(hin, dout, sizeof(hin), hipMemcpyDeviceToHost);
        hipFree(dout);
        std::printf(" | ");
        for (int i = 0; i < 4; ++i)
            std::printf("<%s>=%d ", names[i], hin[i]);
        std::printf("| code_size=%zu\n", codesz);
        hiprtcDestroyProgram(&prog);
    }
    std::printf("G05_STL_PROBE_DONE\n");
    return 0;
}
