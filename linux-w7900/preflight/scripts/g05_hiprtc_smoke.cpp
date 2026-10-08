// G05 HIPRTC smoke test: compile + execute a small kernel for gfx1100 via
// the HIPRTC library API of the isolated 7.14.1 wheel stack.
// Proves: correct libhiprtc loaded (dladdr), -mcpu=gfx1100 accepted, code
// object nonempty, kernel executes, result verified. Full log to stdout.
#include <hip/hiprtc.h>

#include <cinttypes>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <string>
#include <vector>

#include <hip/hip_runtime_api.h>

static void die(const char* what, int rc)
{
    std::fprintf(stderr, "FATAL: %s rc=%d\n", what, rc);
    std::exit(1);
}

static std::string provenance(const char* name)
{
    void* p = dlsym(RTLD_DEFAULT, name);
    Dl_info info;
    std::memset(&info, 0, sizeof(info));
    if (p && dladdr(p, &info) && info.dli_fname)
        return std::string(name) + " <- " + info.dli_fname;
    return std::string(name) + " <- dlsym-failed";
}

static const char* src_rtc = R"(
extern "C" __global__ void axpy_smoke(const float* x, float* y, float a, int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) y[i] = a * x[i] + y[i];
}
)";

int main()
{
    std::printf("PROVENANCE: %s\n", provenance("hiprtcCreateProgram").c_str());
    std::printf("PROVENANCE: %s\n", provenance("hipModuleLaunchKernel").c_str());

    hiprtcProgram prog;
    hiprtcResult r = hiprtcCreateProgram(&prog, src_rtc, "axpy_smoke.cu", 0, nullptr, nullptr);
    if (r != HIPRTC_SUCCESS) die("hiprtcCreateProgram", r);

    const char* arch = "gfx1100";
    const char* opts[] = {"-mcpu=gfx1100"};
    r = hiprtcCompileProgram(prog, 1, opts);
    if (r != HIPRTC_SUCCESS)
    {
        std::size_t logsz = 0;
        hiprtcGetProgramLogSize(prog, &logsz);
        std::vector<char> log(logsz + 1, 0);
        hiprtcGetProgramLog(prog, log.data());
        std::fprintf(stderr, "COMPILE LOG:\n%s\n", log.data());
        die("hiprtcCompileProgram", r);
    }
    std::printf("hiprtcCompileProgram: OK (-mcpu=%s)\n", arch);

    std::size_t codesz = 0;
    hiprtcGetCodeSize(prog, &codesz);
    std::vector<char> code(codesz);
    hiprtcGetCode(prog, code.data());
    std::printf("code object size: %zu bytes%s\n", codesz, codesz > 0 ? " (NONEMPTY)" : " (EMPTY!)");
    if (codesz == 0) die("empty code object", 1);

    FILE* f = std::fopen(getenv("G05_CODEOUT") ? getenv("G05_CODEOUT") : "/tmp/opencode/g05_code.co", "wb");
    if (f) { std::fwrite(code.data(), 1, codesz, f); std::fclose(f); }

    // load + execute
    hipModule_t module;
    hipError_t he = hipModuleLoadDataEx(&module, code.data(), 0, nullptr, nullptr);
    if (he != hipSuccess) die("hipModuleLoadDataEx", he);
    hipFunction_t fn;
    he = hipModuleGetFunction(&fn, module, "axpy_smoke");
    if (he != hipSuccess) die("hipModuleGetFunction", he);

    const int N = 1024;
    float hx[N], hy[N];
    for (int i = 0; i < N; ++i) { hx[i] = float(i); hy[i] = 1.0f; }
    float *dx = nullptr, *dy = nullptr;
    hipMalloc(&dx, N * 4); hipMalloc(&dy, N * 4);
    hipMemcpy(dx, hx, N * 4, hipMemcpyHostToDevice);
    hipMemcpy(dy, hy, N * 4, hipMemcpyHostToDevice);

    float a_val = 2.5f; int n_val = N;
    void* args[] = {&dx, &dy, &a_val, &n_val};
    he = hipModuleLaunchKernel(fn, N / 64, 1, 1, 64, 1, 1, 0, 0, args, nullptr);
    if (he != hipSuccess) die("hipModuleLaunchKernel", he);
    hipDeviceSynchronize();

    float out[N];
    hipMemcpy(out, dy, N * 4, hipMemcpyDeviceToHost);
    int bad = 0;
    for (int i = 0; i < N; ++i)
        if (out[i] != 2.5f * float(i) + 1.0f) ++bad;
    std::printf("kernel result mismatches: %d / %d\n", bad, N);
    hipFree(dx); hipFree(dy);
    hiprtcDestroyProgram(&prog);
    if (bad != 0) die("numeric verification", 1);
    std::printf("G05_HIPRTC_SMOKE: PASS\n");
    return 0;
}
