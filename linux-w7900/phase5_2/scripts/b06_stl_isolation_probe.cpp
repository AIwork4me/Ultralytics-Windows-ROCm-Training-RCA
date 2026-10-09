// B06: HIPRTC STL-isolation investigation probe (gfx1100, ROCm 7.14.1 wheel).
//
// For each flag combination under test this probe:
//   1. compiles an RTC kernel whose four __has_include(<...>) results for
//      type_traits / utility / limits / initializer_list are read back from
//      GPU memory (the flags ARE the measurement);
//   2. compiles an include-SEARCH-PATH FINGERPRINT kernel (relative-path
//      probes that reveal WHICH directories are on the implicit search list);
//   3. compiles AND LAUNCHES an ordinary no-STL control kernel (axpy) under
//      the SAME flags to prove the toolchain remains usable;
//   4. prints dladdr provenance for the live libhiprtc.
//
// Nothing here modifies system/venv files. Failures of individual modes are
// data, not errors of the probe.
#include <hip/hiprtc.h>
#include <hip/hip_runtime_api.h>

#include <cinttypes>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <string>
#include <vector>

static const char* stl_src = R"(
extern "C" __global__ void stl_bits(int* out)
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

// Fingerprint probes: each path resolves only if its parent directory is on
// the RTC include search list. This reveals the implicit search structure
// without needing -v.
static const char* fp_names[] = {
    "hip/hip_runtime.h",            // HIP runtime include dir
    "v1/type_traits",               // some dir containing libc++ v1/
    "c++/v1/type_traits",           // llvm/include root
    "__cxx03/type_traits",          // the __cxx03 compatibility dir
    "stddef.h",                     // clang builtin resource dir
    "stdint.h",                     // system C headers
    "thrust/execution_policy.h",    // devel thrust dir
};
#define N_FP 7

static std::string make_fp_src()
{
    std::string s = "extern \"C\" __global__ void fp_bits(int* out)\n{\n";
    for (int i = 0; i < N_FP; i++)
        s += "#if __has_include(<" + std::string(fp_names[i]) + ">)\n"
             "    out[" + std::to_string(i) + "] = 1;\n#else\n"
             "    out[" + std::to_string(i) + "] = 0;\n#endif\n";
    s += "}\n";
    return s;
}

static const char* axpy_src = R"(
extern "C" __global__ void axpy_ctl(const float* x, float* y, float a, int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) y[i] = a * x[i] + y[i];
}
)";

static bool run_kernel_i1(const char* src, const std::vector<const char*>& opts,
                          int* out, int n, const char* name, std::string* log)
{
    hiprtcProgram prog;
    if (hiprtcCreateProgram(&prog, src, "probe.cu", 0, nullptr, nullptr)
        != HIPRTC_SUCCESS) { log->append("create FAILED;"); return false; }
    hiprtcResult r = hiprtcCompileProgram(prog, (int)opts.size(), opts.data());
    if (r != HIPRTC_SUCCESS) {
        size_t sz = 0;
        hiprtcGetProgramLogSize(prog, &sz);
        std::string l(std::max(sz, (size_t)1), '\0');
        hiprtcGetProgramLog(prog, &*l.begin());
        *log += " compile=" + std::string(hiprtcGetErrorString(r)) + " log={" +
                l.substr(0, 400) + "}";
        hiprtcDestroyProgram(&prog);
        return false;
    }
    size_t sz = 0;
    hiprtcGetCodeSize(prog, &sz);
    std::vector<char> code(sz);
    hiprtcGetCode(prog, code.data());
    hiprtcDestroyProgram(&prog);
    hipModule_t mod;
    if (hipModuleLoadDataEx(&mod, code.data(), 0, nullptr, nullptr)
        != hipSuccess) { log->append("load FAILED;"); return false; }
    hipFunction_t fn;
    if (hipModuleGetFunction(&fn, mod, name) != hipSuccess) {
        log->append("getfn FAILED;"); return false; }
    void* devOut = nullptr;
    hipMalloc(&devOut, n * sizeof(int));
    hipMemcpyHtoD(devOut, out, n * sizeof(int));
    if (strcmp(name, "axpy_ctl") == 0) {
        float *dx = nullptr, *dy = nullptr;
        hipMalloc(&dx, n * sizeof(float));
        hipMalloc(&dy, n * sizeof(float));
        std::vector<float> hx(n, 1.f), hy(n, 2.f);
        hipMemcpyHtoD(dx, hx.data(), n * sizeof(float));
        hipMemcpyHtoD(dy, hy.data(), n * sizeof(float));
        void* args[] = {&dx, &dy, new float(3.f), new int(n)};
        hipModuleLaunchKernel(fn, (n + 255) / 256, 1, 1, 256, 1, 1,
                              0, nullptr, args, nullptr);
        hipMemcpyDtoH(out, dy, 0);  // axpy check separately below
        std::vector<float> hr(n);
        hipMemcpyDtoH(hr.data(), dy, n * sizeof(float));
        bool ok = true;
        for (int i = 0; i < n; i++) if (hr[i] != 5.f) ok = false;
        out[0] = ok ? 1 : 0;
        hipFree(dx); hipFree(dy);
    } else {
        void* args[] = {&devOut};
        hipModuleLaunchKernel(fn, (n + 255) / 256, 1, 1, 256, 1, 1,
                              0, nullptr, args, nullptr);
        hipMemcpyDtoH(out, devOut, n * sizeof(int));
    }
    hipFree(devOut);
    hipModuleUnload(mod);
    return true;
}

struct Mode { const char* name; std::vector<const char*> extra; };

int main()
{
    Dl_info info;
    if (dladdr((void*)&hiprtcCompileProgram, &info) && info.dli_fname)
        std::printf("HIPRTC_LIB %s\n", info.dli_fname);
    if (dladdr((void*)&hipGetDeviceCount, &info) && info.dli_fname)
        std::printf("AMDHIP64_LIB %s\n", info.dli_fname);

    std::string fp_src = make_fp_src();
    std::vector<Mode> modes = {
        {"default",                {}},
        {"nostdincpp",             {"-nostdinc++"}},
        {"nostdinc",               {"-nostdinc"}},
        {"nostdincpp_nobuiltininc",{"-nostdinc++", "-nobuiltininc"}},
        {"nostdinc_nobuiltininc",  {"-nostdinc", "-nobuiltininc"}},
        {"nostdinc_nobuiltininc_isysroot", {"-nostdinc", "-nobuiltininc", "--sysroot=/nonexistent-b06"}},
    };

    for (auto& m : modes) {
        std::vector<const char*> opts;
        opts.push_back("-mcpu=gfx1100");
        for (auto e : m.extra) opts.push_back(e);
        std::string flags = "-mcpu=gfx1100";
        for (auto e : m.extra) flags += std::string(" ") + e;

        int bits[4] = {-1, -1, -1, -1};
        std::string log1;
        bool stl_ok = run_kernel_i1(stl_src, opts, bits, 4, "stl_bits", &log1);
        int fp[N_FP];
        for (auto& v : fp) v = -1;
        std::string log2;
        bool fp_ok = run_kernel_i1(fp_src.c_str(), opts, fp, N_FP,
                                   "fp_bits", &log2);
        int ctl = -1;
        std::string log3;
        bool ctl_ok = run_kernel_i1(axpy_src, opts, &ctl, 1024,
                                    "axpy_ctl", &log3);

        std::printf("MODE %s\n  flags: %s\n", m.name, flags.c_str());
        std::printf("  stl(type_traits,utility,limits,initializer_list)=%s "
                    "[%d %d %d %d]\n", stl_ok ? "ran" : "FAILED",
                    bits[0], bits[1], bits[2], bits[3]);
        if (!stl_ok) std::printf("  stl_log:%s\n", log1.c_str());
        std::printf("  fingerprint:");
        for (int i = 0; i < N_FP; i++)
            std::printf(" %s=%d", fp_names[i], fp_ok ? fp[i] : -1);
        std::printf("%s\n", fp_ok ? "" : ("  fp_log:" + log2).c_str());
        std::printf("  control_axpy=%s (result=%d)%s\n",
                    ctl_ok ? "COMPILED+RAN" : "FAILED", ctl,
                    ctl_ok ? "" : log3.c_str());
    }
    return 0;
}
