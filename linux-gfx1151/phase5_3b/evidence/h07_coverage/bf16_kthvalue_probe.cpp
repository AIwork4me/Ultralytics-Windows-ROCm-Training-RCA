// Gate H07 coverage probe — BF16 kthvalue applicability + runtime correctness.
//
// Public API miopenKthvalueForward with a miopenBFloat16 tensor through the
// LD_PRELOADed source-built libMIOpen (dlsym, dladdr provenance). Deterministic
// inputs: per-slice permutations of the integers 0..199 (all exactly
// integers (4*i and 1024+8*j) — unique k-th answer per slice).
// CPU reference: exact sort. Exit 0 only if values AND indices all match.
#include <miopen/miopen.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <dlfcn.h>

using fn_hipMalloc_t = int (*)(void**, size_t);
using fn_hipFree_t = int (*)(void*);
using fn_hipMemcpy_t = int (*)(void*, const void*, size_t, int);
using fn_hipDeviceSynchronize_t = int (*)(void);
using fn_miopenCreate_t = miopenStatus_t (*)(miopenHandle_t*);
using fn_miopenDestroy_t = miopenStatus_t (*)(miopenHandle_t);
using fn_miopenCreateTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t*);
using fn_miopenSetTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t, miopenDataType_t, int, const int*, const int*);
using fn_miopenDestroyTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t);
using fn_miopenKthvalueForward_t = miopenStatus_t (*)(miopenHandle_t, miopenTensorDescriptor_t, const void*,
                                                      miopenTensorDescriptor_t, void*, miopenTensorDescriptor_t,
                                                      size_t*, size_t, int32_t, bool);

static void* resolve(const char* n)
{
    void* p = dlsym(RTLD_DEFAULT, n);
    if(!p) { std::fprintf(stderr, "FATAL: cannot resolve %s\n", n); std::exit(3); }
    return p;
}

// 300 distinct exactly-BF16-representable integers: 4*i (i<256, <=1020, 8-bit
// mantissa exact) plus 1024+8*i (i<44) — all distinct, all exact in BF16.
static int exact_bf16_value(int j)
{
    return j < 256 ? 4 * j : 1024 + 8 * (j - 256);
}

static uint16_t f32_to_bf16_bits(float v)
{
    uint32_t u; std::memcpy(&u, &v, 4);
    return static_cast<uint16_t>(u >> 16); // inputs are exact -> truncation is exact
}

int main()
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    auto hipMalloc = (fn_hipMalloc_t)resolve("hipMalloc");
    auto hipFree = (fn_hipFree_t)resolve("hipFree");
    auto hipMemcpy = (fn_hipMemcpy_t)resolve("hipMemcpy");
    auto hipDeviceSynchronize = (fn_hipDeviceSynchronize_t)resolve("hipDeviceSynchronize");
    auto miopenCreate = (fn_miopenCreate_t)resolve("miopenCreate");
    auto miopenDestroy = (fn_miopenDestroy_t)resolve("miopenDestroy");
    auto miopenCreateTensorDescriptor = (fn_miopenCreateTensorDescriptor_t)resolve("miopenCreateTensorDescriptor");
    auto miopenSetTensorDescriptor = (fn_miopenSetTensorDescriptor_t)resolve("miopenSetTensorDescriptor");
    auto miopenKthvalueForward = (fn_miopenKthvalueForward_t)resolve("miopenKthvalueForward");

    { Dl_info i; if(dladdr((void*)miopenKthvalueForward, &i) && i.dli_fname)
        std::printf("PROVENANCE: miopenKthvalueForward <- %s\n", i.dli_fname); }

    constexpr int N = 100, L = 300, K = 10;
    // deterministic permutation per slice (LCG), values 0..199
    std::vector<uint16_t> host(N * L);
    for(int s = 0; s < N; ++s)
    {
        uint64_t st = 0x9E3779B97F4A7C15ULL ^ (uint64_t(s) * 0xBF58476D1CE4E5B9ULL);
        std::vector<int> perm(L);
        for(int j = 0; j < L; ++j) perm[j] = exact_bf16_value(j);
        for(int j = L - 1; j > 0; --j)
        {
            st = st * 6364136223846793005ULL + 1442695040888963407ULL;
            const int r = (int)((st >> 33) % (uint64_t)(j + 1));
            std::swap(perm[j], perm[r]);
        }
        for(int j = 0; j < L; ++j)
            host[(size_t)s * L + j] = f32_to_bf16_bits((float)perm[j]);
    }

    miopenHandle_t h;
    miopenStatus_t stc = miopenCreate(&h);
    std::printf("miopenCreate=%d\n", (int)stc);
    std::printf("step: descriptors create\n");

    miopenTensorDescriptor_t din, dout, didx;
    miopenStatus_t c1 = miopenCreateTensorDescriptor(&din);
    miopenStatus_t c2 = miopenCreateTensorDescriptor(&dout);
    miopenStatus_t c3 = miopenCreateTensorDescriptor(&didx);
    std::printf("creates: %d %d %d ptrs=%p %p %p\n", (int)c1,(int)c2,(int)c3, (void*)din,(void*)dout,(void*)didx);
    const int dims[2] = {N, L};
    const int in_strides[2] = {L, 1};
    const int outdims_nok[1] = {N};      // keepDim=false -> [N]
    const int out_strides[1] = {1};
    miopenSetTensorDescriptor(din, miopenBFloat16, 2, dims, in_strides);
    miopenSetTensorDescriptor(dout, miopenBFloat16, 1, outdims_nok, out_strides);
    miopenSetTensorDescriptor(didx, miopenInt64, 1, outdims_nok, out_strides);
    std::printf("step: descriptors set\n");

    void *d_in = nullptr, *d_out = nullptr; void* d_idx = nullptr;
    std::printf("step: mallocs\n");
    hipMalloc(&d_in, host.size() * 2);
    hipMalloc(&d_out, (size_t)N * 2);
    hipMalloc(&d_idx, (size_t)N * 8);
    hipMemcpy(d_in, host.data(), host.size() * 2, 1 /*host->device*/);
    std::printf("step: memcpy in\n");

    std::printf("calling miopenKthvalueForward(BF16 [100x300], k=10, dim=-1)...\n");
    miopenStatus_t st = miopenKthvalueForward(h, din, d_in, dout, d_out, didx,
                                              (size_t*)d_idx, (size_t)K, -1, false);
    std::printf("miopenKthvalueForward status=%d (%s)\n", (int)st,
                st == 0 ? "miopenStatusSuccess" : "nonzero");
    if(st != 0)
    {
        std::printf("BF16_RESULT: NOT_SUPPORTED_BY_RUNTIME status=%d\n", (int)st);
        return 4;
    }
    hipDeviceSynchronize();
    std::vector<uint16_t> out(N);
    std::vector<int64_t> idx(N);
    hipMemcpy(out.data(), d_out, (size_t)N * 2, 2 /*device->host*/);
    hipMemcpy(idx.data(), d_idx, (size_t)N * 8, 2);

    // CPU reference from the same bf16 inputs (values = exact integers)
    int vmis = 0, imis = 0;
    for(int s = 0; s < N; ++s)
    {
        std::vector<std::pair<int,int>> v(L); // (value, index)
        for(int j = 0; j < L; ++j)
            v[j] = {(int)host[(size_t)s * L + j], j};
        std::sort(v.begin(), v.end());
        const int exp_val = v[K - 1].first, exp_idx = v[K - 1].second;
        const int act_val = (int)out[s];
        if(act_val != exp_val) ++vmis;
        if((int)idx[s] != exp_idx) ++imis;
        if(s == 0)
            std::printf("slice0: exp_val=%d act_val=%d exp_idx=%d act_idx=%lld\n",
                        exp_val, act_val, exp_idx, (long long)idx[s]);
    }
    hipFree(d_in); hipFree(d_out); hipFree(d_idx);
    miopenDestroy(h);
    std::printf("value_mismatches=%d index_mismatches=%d\n", vmis, imis);
    const bool pass = (vmis == 0 && imis == 0);
    std::printf("BF16_RESULT: %s\n", pass ? "PASS" : "FAIL");
    return pass ? 0 : 1;
}
