// Kthvalue runtime harness — Phase-3 Linux final closure (Gates F08-F13).
//
// Calls the public MIOpen C API miopenKthvalueForward through whichever
// source-built libMIOpen the wrapper LD_PRELOADed (unpatched or patched),
// with dlsym/dladdr provenance printed for the exact function pointers used.
// Deterministic permutation inputs (all values pairwise distinct per slice,
// exactly representable in FP32 and FP16); CPU reference mirrors the official
// driver reference mloKthvalueFwdRunHost (kthvalue_driver.hpp) with tie
// ambiguity eliminated by construction.
//
// Exit code 0 iff every case's values AND indices match the CPU reference.

#include <miopen/miopen.h>

#include <algorithm>
#include <cmath>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <dlfcn.h>

// ---------------------------------------------------------------------------
// All HIP runtime and MIOpen functions are resolved via dlsym(RTLD_DEFAULT)
// from the same wheel ROCm stack the source-built MIOpen loads — the harness
// has zero link-time ROCm dependencies. Pointer types use the header's
// hipError_t so the ABI is header-exact.
using fn_hipMalloc_t = hipError_t (*)(void**, size_t);
using fn_hipFree_t = hipError_t (*)(void*);
using fn_hipMemcpy_t = hipError_t (*)(void*, const void*, size_t, hipMemcpyKind);
using fn_hipDeviceSynchronize_t = hipError_t (*)(void);
using fn_hipGetErrorString_t = const char* (*)(hipError_t);
using hipStream_t_ = hipStream_t;

// MIOpen API types (function-pointer forms)
using fn_miopenCreate_t = miopenStatus_t (*)(miopenHandle_t*);
using fn_miopenDestroy_t = miopenStatus_t (*)(miopenHandle_t);
using fn_miopenGetStream_t = miopenStatus_t (*)(miopenHandle_t, hipStream_t*);
using fn_miopenCreateTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t*);
using fn_miopenDestroyTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t);
using fn_miopenSetTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t,
                                                          miopenDataType_t,
                                                          int,
                                                          const int*,
                                                          const int*);
using fn_miopenKthvalueForward_t = miopenStatus_t (*)(miopenHandle_t,
                                                      miopenTensorDescriptor_t,
                                                      const void*,
                                                      miopenTensorDescriptor_t,
                                                      void*,
                                                      miopenTensorDescriptor_t,
                                                      size_t*,
                                                      size_t,
                                                      int32_t,
                                                      bool);

static void* resolve(const char* name)
{
    void* p = dlsym(RTLD_DEFAULT, name);
    if(!p)
    {
        std::fprintf(stderr, "FATAL: dlsym(%s) returned NULL\n", name);
        std::exit(2);
    }
    return p;
}

static std::string provenance(const char* name, void* p)
{
    Dl_info info;
    std::memset(&info, 0, sizeof(info));
    const int ok = dladdr(p, &info);
    char buf[512];
    if(ok && info.dli_fname)
        std::snprintf(buf, sizeof(buf), "%s <- %s", name, info.dli_fname);
    else
        std::snprintf(buf, sizeof(buf), "%s <- UNKNOWN", name);
    return std::string(buf);
}

// ---------------------------------------------------------------------------
// Deterministic PRNG (xorshift64*) — fixed seeds only; byte-identical inputs
// across processes and across unpatched/patched runs.
static uint64_t xs_state;
static inline uint64_t xs64()
{
    uint64_t x = xs_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    xs_state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

// Exact float<->half bit converters (inputs are exactly representable
// multiples of 0.25 well inside FP16 range, so conversion is lossless).
static inline uint16_t f32_to_f16_bits(float f)
{
    uint32_t x;
    std::memcpy(&x, &f, sizeof(x));
    const uint32_t sign = (x >> 16) & 0x8000U;
    int32_t exp         = static_cast<int32_t>((x >> 23) & 0xFF) - 127 + 15;
    uint32_t mant       = (x & 0x007FFFFFU) >> 13;
    if(exp <= 0) return static_cast<uint16_t>(sign); // no denormals in range used
    return static_cast<uint16_t>(sign | (static_cast<uint32_t>(exp) << 10) | mant);
}
static inline float f16_bits_to_f32(uint16_t h)
{
    uint32_t sign = static_cast<uint32_t>(h & 0x8000U) << 16;
    uint32_t exp  = (h >> 10) & 0x1FU;
    uint32_t mant = h & 0x03FFU;
    uint32_t out;
    if(exp == 0)
        out = sign; // zero (no denormals in range used)
    else
        out = sign | ((exp + 127 - 15) << 23) | (mant << 13);
    float f;
    std::memcpy(&f, &out, sizeof(f));
    return f;
}

// ---------------------------------------------------------------------------
struct TestCase
{
    const char* id;
    std::vector<int> in_dims;
    bool fp16;
    int32_t dim; // as passed to the API (negative allowed)
    size_t k;
    bool keepDim;
    uint64_t seed;
};

struct CaseResult
{
    bool values_ok = true;
    bool indices_ok = true;
    size_t n_slices = 0;
    size_t n_value_mismatch = 0;
    size_t n_index_mismatch = 0;
    double max_abs_err = 0.0;
    std::vector<float> exp_first, act_first;   // first slice, for the record
    std::vector<size_t> exp_idx_first, act_idx_first;
};

static int run_case(const TestCase& tc,
                    fn_miopenKthvalueForward_t miopenKthvalueForward,
                    fn_miopenCreateTensorDescriptor_t miopenCreateTensorDescriptor,
                    fn_miopenDestroyTensorDescriptor_t miopenDestroyTensorDescriptor,
                    fn_miopenSetTensorDescriptor_t miopenSetTensorDescriptor,
                    miopenHandle_t handle,
                    fn_hipMalloc_t hipMalloc,
                    fn_hipFree_t hipFree,
                    fn_hipMemcpy_t hipMemcpy,
                    fn_hipDeviceSynchronize_t hipDeviceSynchronize,
                    fn_hipGetErrorString_t hipGetErrorString,
                    CaseResult& res)
{
    const int rank = static_cast<int>(tc.in_dims.size());
    int32_t dim    = tc.dim;
    if(dim < 0) dim += rank;

    const size_t dim_size = static_cast<size_t>(tc.in_dims[dim]);
    size_t in_numel       = 1;
    for(int d : tc.in_dims) in_numel *= static_cast<size_t>(d);
    const size_t n_slices = in_numel / dim_size;

    std::vector<int> out_dims = tc.in_dims;
    if(!tc.keepDim)
    {
        out_dims.erase(out_dims.begin() + dim);
        if(out_dims.empty()) out_dims.push_back(1);
    }
    else
    {
        out_dims[dim] = 1;
    }
    const int out_rank      = static_cast<int>(out_dims.size());
    size_t out_numel        = 1;
    for(int d : out_dims) out_numel *= static_cast<size_t>(d);

    // contiguous strides
    auto strides_of = [](const std::vector<int>& dims) {
        std::vector<int> s(dims.size());
        int acc = 1;
        for(int i = static_cast<int>(dims.size()) - 1; i >= 0; --i)
        {
            s[i] = acc;
            acc *= dims[i];
        }
        return s;
    };
    const std::vector<int> in_strides = strides_of(tc.in_dims);
    const std::vector<int> out_strides = strides_of(out_dims);

    // --- deterministic input: per-slice permutation of {0..dim_size-1} ---
    const float base = -0.125f * static_cast<float>(dim_size);
    std::vector<float> input_f(in_numel);
    std::vector<size_t> ground_truth_idx(out_numel);
    std::vector<float> ground_truth_val(out_numel);

    for(size_t s = 0; s < n_slices; ++s)
    {
        xs_state = tc.seed ^ (0x9E3779B97F4A7C15ULL * (s + 1));
        std::vector<uint32_t> perm(dim_size);
        for(size_t i = 0; i < dim_size; ++i) perm[i] = static_cast<uint32_t>(i);
        for(size_t i = dim_size - 1; i > 0; --i)
        {
            const size_t j = static_cast<size_t>(xs64() % (i + 1));
            std::swap(perm[i], perm[j]);
        }
        float* slice = &input_f[s * dim_size];
        // slice values: all pairwise distinct, exact 0.25-multiples
        for(size_t i = 0; i < dim_size; ++i)
            slice[i] = base + 0.25f * static_cast<float>(perm[i]);

        // CPU reference (mirrors mloKthvalueFwdRunHost; ties impossible)
        std::vector<uint32_t> ids(dim_size);
        for(size_t i = 0; i < dim_size; ++i) ids[i] = static_cast<uint32_t>(i);
        std::sort(ids.begin(), ids.end(), [&](uint32_t a, uint32_t b) {
            return slice[a] < slice[b];
        });
        const uint32_t win    = ids[tc.k - 1];
        ground_truth_val[s]   = slice[win];
        ground_truth_idx[s]   = win;
    }

    // upload representation (fp16 or fp32); CPU ref uses the same values the
    // GPU kernel sees (after round-trip through the storage dtype)
    std::vector<uint16_t> input_h;
    std::vector<float> input_gpu_view; // values exactly as stored
    const void* input_dev_ptr_type = nullptr;
    (void)input_dev_ptr_type;
    miopenDataType_t dtype = tc.fp16 ? miopenHalf : miopenFloat;
    const size_t elem_size = tc.fp16 ? sizeof(uint16_t) : sizeof(float);

    std::vector<std::byte> input_bytes(in_numel * elem_size);
    std::vector<float> input_for_ref(in_numel);
    if(tc.fp16)
    {
        for(size_t i = 0; i < in_numel; ++i)
        {
            const uint16_t h = f32_to_f16_bits(input_f[i]);
            std::memcpy(&input_bytes[i * 2], &h, 2);
            input_for_ref[i] = f16_bits_to_f32(h);
        }
    }
    else
    {
        std::memcpy(input_bytes.data(), input_f.data(), in_numel * 4);
        input_for_ref = input_f;
    }

    // recompute ground truth on the storage-round-tripped values (identical
    // by construction for our value set; recomputed for rigor)
    for(size_t s = 0; s < n_slices; ++s)
    {
        const float* slice = &input_for_ref[s * dim_size];
        std::vector<uint32_t> ids(dim_size);
        for(size_t i = 0; i < dim_size; ++i) ids[i] = static_cast<uint32_t>(i);
        std::sort(ids.begin(), ids.end(), [&](uint32_t a, uint32_t b) {
            return slice[a] < slice[b];
        });
        ground_truth_val[s] = slice[ids[tc.k - 1]];
        ground_truth_idx[s] = ids[tc.k - 1];
    }

    // --- descriptors ---
    miopenTensorDescriptor_t inDesc = nullptr, outDesc = nullptr, idxDesc = nullptr;
    if(miopenCreateTensorDescriptor(&inDesc) != miopenStatusSuccess ||
       miopenCreateTensorDescriptor(&outDesc) != miopenStatusSuccess ||
       miopenCreateTensorDescriptor(&idxDesc) != miopenStatusSuccess)
    {
        std::printf("  DESC CREATE FAILED\n");
        return 3;
    }
    if(miopenSetTensorDescriptor(inDesc, dtype, rank, tc.in_dims.data(), in_strides.data()) !=
           miopenStatusSuccess ||
       miopenSetTensorDescriptor(outDesc, dtype, out_rank, out_dims.data(), out_strides.data()) !=
           miopenStatusSuccess ||
       miopenSetTensorDescriptor(idxDesc, miopenInt64, out_rank, out_dims.data(), out_strides.data()) !=
           miopenStatusSuccess)
    {
        std::printf("  DESC SET FAILED\n");
        return 3;
    }

    // --- GPU buffers ---
    void *d_in = nullptr, *d_out = nullptr, *d_idx = nullptr;
    hipError_t e;
    e = hipMalloc(&d_in, in_numel * elem_size);
    if(e) { std::printf("  hipMalloc(in) failed: %s\n", hipGetErrorString(e)); return 3; }
    e = hipMalloc(&d_out, out_numel * elem_size);
    if(e) { std::printf("  hipMalloc(out) failed: %s\n", hipGetErrorString(e)); return 3; }
    e = hipMalloc(&d_idx, out_numel * sizeof(size_t));
    if(e) { std::printf("  hipMalloc(idx) failed: %s\n", hipGetErrorString(e)); return 3; }

    e = hipMemcpy(d_in, input_bytes.data(), in_numel * elem_size, hipMemcpyHostToDevice);
    if(e) { std::printf("  hipMemcpy(in) failed: %s\n", hipGetErrorString(e)); return 3; }
    // zero-init outputs so stale memory cannot fake a pass
    std::vector<std::byte> zeros_out(out_numel * elem_size, std::byte{0});
    std::vector<size_t> zeros_idx(out_numel, 0);
    hipMemcpy(d_out, zeros_out.data(), out_numel * elem_size, hipMemcpyHostToDevice);
    hipMemcpy(d_idx, zeros_idx.data(), out_numel * sizeof(size_t), hipMemcpyHostToDevice);

    // --- the call under test ---
    const miopenStatus_t st = miopenKthvalueForward(
        handle, inDesc, d_in, outDesc, d_out, idxDesc, static_cast<size_t*>(d_idx),
        tc.k, tc.dim, tc.keepDim);
    if(st != miopenStatusSuccess)
    {
        std::printf("  miopenKthvalueForward returned %d\n", static_cast<int>(st));
        hipFree(d_in); hipFree(d_out); hipFree(d_idx);
        return 4;
    }
    e = hipDeviceSynchronize();
    if(e) { std::printf("  hipDeviceSynchronize failed: %s\n", hipGetErrorString(e)); return 3; }

    // --- read back ---
    std::vector<std::byte> out_bytes(out_numel * elem_size);
    std::vector<size_t> out_idx(out_numel);
    hipMemcpy(out_bytes.data(), d_out, out_numel * elem_size, hipMemcpyDeviceToHost);
    hipMemcpy(out_idx.data(), d_idx, out_numel * sizeof(size_t), hipMemcpyDeviceToHost);
    hipDeviceSynchronize();

    // --- verify values + indices exactly ---
    res.n_slices = n_slices;
    for(size_t s = 0; s < n_slices; ++s)
    {
        float actual;
        if(tc.fp16)
        {
            uint16_t h;
            std::memcpy(&h, &out_bytes[s * 2], 2);
            actual = f16_bits_to_f32(h);
        }
        else
        {
            std::memcpy(&actual, &out_bytes[s * 4], 4);
        }
        const double aerr = std::fabs(static_cast<double>(actual) -
                                      static_cast<double>(ground_truth_val[s]));
        if(aerr > res.max_abs_err) res.max_abs_err = aerr;
        const bool vok = (actual == ground_truth_val[s]);
        const bool iok = (out_idx[s] == ground_truth_idx[s]);
        if(!vok) { res.values_ok = false; ++res.n_value_mismatch; }
        if(!iok) { res.indices_ok = false; ++res.n_index_mismatch; }
        if(s == 0)
        {
            res.exp_first.push_back(ground_truth_val[s]);
            res.act_first.push_back(actual);
            res.exp_idx_first.push_back(ground_truth_idx[s]);
            res.act_idx_first.push_back(out_idx[s]);
        }
    }

    // optional full-array dump for byte-level A/B comparison (identical
    // binary used on both sides; dump dir supplied via env by the runner)
    if(const char* dump_dir = std::getenv("KTHV_DUMP_DIR"))
    {
        const std::string p = std::string(dump_dir) + "/" + tc.id;
        auto wr = [](const std::string& path, const void* d, size_t n) {
            FILE* f = std::fopen(path.c_str(), "wb");
            if(!f) { std::printf("  DUMP OPEN FAILED %s\n", path.c_str()); return; }
            std::fwrite(d, 1, n, f);
            std::fclose(f);
        };
        wr(p + "_input.bin", input_bytes.data(), input_bytes.size());
        wr(p + "_output.bin", out_bytes.data(), out_bytes.size());
        wr(p + "_indices.bin", out_idx.data(), out_idx.size() * sizeof(size_t));
        wr(p + "_expected_indices.bin", ground_truth_idx.data(),
           ground_truth_idx.size() * sizeof(size_t));
        FILE* f = std::fopen((p + "_expected_values.txt").c_str(), "w");
        if(f)
        {
            for(size_t s = 0; s < n_slices; ++s)
                std::fprintf(f, "%.9g\n", static_cast<double>(ground_truth_val[s]));
            std::fclose(f);
        }
        std::printf("  dumped arrays to %s_*\n", p.c_str());
    }

    hipFree(d_in); hipFree(d_out); hipFree(d_idx);
    miopenDestroyTensorDescriptor(inDesc);
    miopenDestroyTensorDescriptor(outDesc);
    miopenDestroyTensorDescriptor(idxDesc);
    return 0;
}

int main()
{
    std::printf("=== kthvalue runtime harness (W7900-LINUX-PREP-R1, gfx1100) ===\n");

    // resolve everything and PROVE which DSO services each symbol
    auto miopenCreate = reinterpret_cast<fn_miopenCreate_t>(resolve("miopenCreate"));
    auto miopenDestroy = reinterpret_cast<fn_miopenDestroy_t>(resolve("miopenDestroy"));
    auto miopenGetStream = reinterpret_cast<fn_miopenGetStream_t>(resolve("miopenGetStream"));
    auto miopenCreateTensorDescriptor =
        reinterpret_cast<fn_miopenCreateTensorDescriptor_t>(resolve("miopenCreateTensorDescriptor"));
    auto miopenDestroyTensorDescriptor =
        reinterpret_cast<fn_miopenDestroyTensorDescriptor_t>(resolve("miopenDestroyTensorDescriptor"));
    auto miopenSetTensorDescriptor =
        reinterpret_cast<fn_miopenSetTensorDescriptor_t>(resolve("miopenSetTensorDescriptor"));
    auto miopenKthvalueForward =
        reinterpret_cast<fn_miopenKthvalueForward_t>(resolve("miopenKthvalueForward"));
    auto hipMalloc = reinterpret_cast<fn_hipMalloc_t>(resolve("hipMalloc"));
    auto hipFree = reinterpret_cast<fn_hipFree_t>(resolve("hipFree"));
    auto hipMemcpy = reinterpret_cast<fn_hipMemcpy_t>(resolve("hipMemcpy"));
    auto hipDeviceSynchronize =
        reinterpret_cast<fn_hipDeviceSynchronize_t>(resolve("hipDeviceSynchronize"));
    auto hipGetErrorString =
        reinterpret_cast<fn_hipGetErrorString_t>(resolve("hipGetErrorString"));

    std::printf("PROVENANCE:\n");
    std::printf("  %s\n", provenance("miopenCreate", reinterpret_cast<void*>(miopenCreate)).c_str());
    std::printf("  %s\n",
                provenance("miopenKthvalueForward", reinterpret_cast<void*>(miopenKthvalueForward))
                    .c_str());
    std::printf("  %s\n", provenance("hipMalloc", reinterpret_cast<void*>(hipMalloc)).c_str());
    std::printf("  %s\n", provenance("hipMemcpy", reinterpret_cast<void*>(hipMemcpy)).c_str());

    miopenHandle_t handle = nullptr;
    if(miopenCreate(&handle) != miopenStatusSuccess)
    {
        std::printf("miopenCreate FAILED\n");
        return 2;
    }
    hipStream_t_ stream = nullptr;
    miopenGetStream(handle, &stream);
    std::printf("handle created, stream=%p\n", static_cast<void*>(stream));

    const std::vector<TestCase> cases = {
        {"FP32-2D-nokeep", {100, 500}, false, -1, 10, false, 0xC0FFEE123456789ULL},
        {"FP32-3D-keep-explicit-dim", {10, 20, 300}, false, 2, 137, true, 0xABCDEF9876543210ULL},
        {"FP16-4D-keep-kmax", {8, 3, 10, 2000}, true, -1, 2000, true, 0x13579BDF2468ACE0ULL},
    };

    int rc = 0;
    for(const auto& tc : cases)
    {
        CaseResult res;
        std::string dims;
        for(size_t i = 0; i < tc.in_dims.size(); ++i)
        {
            if(i) dims += "x";
            dims += std::to_string(tc.in_dims[i]);
        }
        std::printf("\nCASE %s shape={%s} dtype=%s dim=%" PRId32 " k=%zu keepDim=%d\n",
                    tc.id, dims.c_str(), tc.fp16 ? "FP16" : "FP32", tc.dim, tc.k,
                    tc.keepDim ? 1 : 0);
        const int c = run_case(tc, miopenKthvalueForward, miopenCreateTensorDescriptor,
                               miopenDestroyTensorDescriptor, miopenSetTensorDescriptor, handle,
                               hipMalloc, hipFree, hipMemcpy, hipDeviceSynchronize,
                               hipGetErrorString, res);
        if(c != 0)
        {
            std::printf("  STATUS: RUN_ERROR(%d)\n", c);
            rc = 1;
            continue;
        }
        const bool ok = res.values_ok && res.indices_ok;
        std::printf("  slices=%zu value_mismatches=%zu index_mismatches=%zu max_abs_err=%g\n",
                    res.n_slices, res.n_value_mismatch, res.n_index_mismatch, res.max_abs_err);
        std::printf("  slice0: exp_val=%.6g act_val=%.6g exp_idx=%zu act_idx=%zu\n",
                    res.exp_first[0], res.act_first[0], res.exp_idx_first[0], res.act_idx_first[0]);
        std::printf("  STATUS: %s\n", ok ? "PASS" : "FAIL");
        if(!ok) rc = 1;
    }

    miopenDestroy(handle);
    std::printf("\nHARNESS_RESULT: %s\n", rc == 0 ? "PASS" : "FAIL");
    return rc;
}
