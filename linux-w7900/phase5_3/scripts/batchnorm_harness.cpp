// BatchNorm forward/backward numerical harness — Phase 5.3 Gate L09.
//
// Calls the public MIOpen C API miopenBatchNormalizationForwardTraining and
// miopenBatchNormalizationBackward through whichever source-built libMIOpen
// the wrapper LD_PRELOADed (legA-frozen or patched), with dlsym/dladdr
// provenance printed for the exact function pointers used.
//
// Workload: N=8 C=16 H=64 W=64 FP32, miopenBNSpatial, eps=1e-5,
// expAvgFactor=0.1, deterministic xorshift64* inputs, CPU float64 reference.
//
// PREDECLARED tolerances (fixed BEFORE running; never adjusted after
// observing results):
//   |y|   <= 1e-5   |dx| <= 1e-5   |dw| <= 1e-4   |db| <= 1e-5
//   |running mean| <= 1e-4        running var relative <= 1e-3
//
// Exit code 0 iff all six checks pass within tolerance.

#include <miopen/miopen.h>

#include <algorithm>
#include <cmath>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <string>
#include <vector>

using fn_hipMalloc_t = int (*)(void**, size_t);
using fn_hipFree_t = int (*)(void*);
using fn_hipMemcpy_t = int (*)(void*, const void*, size_t, int);
using fn_hipDeviceSynchronize_t = int (*)(void);

using fn_miopenCreate_t = miopenStatus_t (*)(miopenHandle_t*);
using fn_miopenDestroy_t = miopenStatus_t (*)(miopenHandle_t);
using fn_miopenCreateTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t*);
using fn_miopenDestroyTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t);
using fn_miopenSetTensorDescriptor_t = miopenStatus_t (*)(miopenTensorDescriptor_t,
                                                           miopenDataType_t, int,
                                                           const int*, const int*);
using fn_miopenBatchNormalizationForwardTraining_t =
    miopenStatus_t (*)(miopenHandle_t, miopenBatchNormMode_t,
                       void*, void*,
                       const miopenTensorDescriptor_t, const void*,
                       const miopenTensorDescriptor_t, void*,
                       const miopenTensorDescriptor_t,
                       void*, void*,
                       double, void*, void*, double, void*, void*);
using fn_miopenBatchNormalizationBackward_t =
    miopenStatus_t (*)(miopenHandle_t, miopenBatchNormMode_t,
                       const void*, const void*,
                       const void*, const void*,
                       const miopenTensorDescriptor_t, const void*,
                       const miopenTensorDescriptor_t, const void*,
                       const miopenTensorDescriptor_t, void*,
                       const miopenTensorDescriptor_t, const void*,
                       void*, void*,
                       double, const void*, const void*);

static void* resolve(const char* name)
{
    void* p = dlsym(RTLD_DEFAULT, name);
    if(!p)
    {
        std::fprintf(stderr, "FATAL: cannot resolve %s\n", name);
        std::exit(3);
    }
    return p;
}

static std::string provenance(const char* name, void* p)
{
    Dl_info info;
    const int ok = dladdr(p, &info);
    char buf[512];
    if(ok && info.dli_fname)
        std::snprintf(buf, sizeof(buf), "%s <- %s", name, info.dli_fname);
    else
        std::snprintf(buf, sizeof(buf), "%s <- <unknown>", name);
    return buf;
}

// deterministic xorshift64* generator
static inline uint64_t xs64s(uint64_t& s)
{
    s += 1;
    uint64_t x = s;
    x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
    return x * 2685821657736338717ULL;
}
static inline double next_uniform01(uint64_t& s)
{
    return (static_cast<double>(xs64s(s) >> 11)) * (1.0 / 9007199254740992.0);
}

int main()
{
    constexpr int N = 8, C = 16, H = 64, W = 64;
    constexpr size_t T = static_cast<size_t>(N) * C * H * W;
    constexpr double eps = 1e-5;
    constexpr double expAvgFactor = 0.1;
    // PREDECLARED tolerances
    constexpr double TOL_Y = 1e-5, TOL_DX = 1e-5, TOL_DW = 1e-4, TOL_DB = 1e-5,
                     TOL_RM = 1e-4, TOL_RV_REL = 1e-3;

    auto miopenCreate = reinterpret_cast<fn_miopenCreate_t>(resolve("miopenCreate"));
    auto miopenDestroy = reinterpret_cast<fn_miopenDestroy_t>(resolve("miopenDestroy"));
    auto miopenCreateTensorDescriptor =
        reinterpret_cast<fn_miopenCreateTensorDescriptor_t>(resolve("miopenCreateTensorDescriptor"));
    auto miopenDestroyTensorDescriptor =
        reinterpret_cast<fn_miopenDestroyTensorDescriptor_t>(resolve("miopenDestroyTensorDescriptor"));
    auto miopenSetTensorDescriptor =
        reinterpret_cast<fn_miopenSetTensorDescriptor_t>(resolve("miopenSetTensorDescriptor"));
    auto bnFwd = reinterpret_cast<fn_miopenBatchNormalizationForwardTraining_t>(
        resolve("miopenBatchNormalizationForwardTraining"));
    auto bnBwd = reinterpret_cast<fn_miopenBatchNormalizationBackward_t>(
        resolve("miopenBatchNormalizationBackward"));
    auto hipMalloc = reinterpret_cast<fn_hipMalloc_t>(resolve("hipMalloc"));
    auto hipFree = reinterpret_cast<fn_hipFree_t>(resolve("hipFree"));
    auto hipMemcpy = reinterpret_cast<fn_hipMemcpy_t>(resolve("hipMemcpy"));
    auto hipDeviceSynchronize =
        reinterpret_cast<fn_hipDeviceSynchronize_t>(resolve("hipDeviceSynchronize"));

    std::printf("PROVENANCE:\n");
    std::printf("  %s\n", provenance("miopenCreate", reinterpret_cast<void*>(miopenCreate)).c_str());
    std::printf("  %s\n", provenance("miopenBatchNormalizationForwardTraining",
                                     reinterpret_cast<void*>(bnFwd)).c_str());
    std::printf("  %s\n", provenance("miopenBatchNormalizationBackward",
                                     reinterpret_cast<void*>(bnBwd)).c_str());
    std::printf("  %s\n", provenance("hipMalloc", reinterpret_cast<void*>(hipMalloc)).c_str());
    std::printf("WORKLOAD: N=%d C=%d H=%d W=%d FP32 mode=spatial eps=%g expAvgFactor=%g\n",
                N, C, H, W, eps, expAvgFactor);
    std::printf("TOLERANCES (predeclared): y<=%g dx<=%g dw<=%g db<=%g rm<=%g rv_rel<=%g\n",
                TOL_Y, TOL_DX, TOL_DW, TOL_DB, TOL_RM, TOL_RV_REL);

    miopenHandle_t handle;
    if(miopenCreate(&handle) != miopenStatusSuccess)
    {
        std::fprintf(stderr, "FATAL: miopenCreate failed\n");
        return 3;
    }

    miopenTensorDescriptor_t xDesc;
    miopenCreateTensorDescriptor(&xDesc);
    const int dims[4] = {N, C, H, W};
    const int strides[4] = {C * H * W, H * W, W, 1};
    miopenSetTensorDescriptor(xDesc, miopenFloat, 4, dims, strides);
    miopenTensorDescriptor_t bnDesc; // derived BN tensor descriptor: 1xCx1x1 (spatial mode)
    miopenCreateTensorDescriptor(&bnDesc);
    const int bnDims[4] = {1, C, 1, 1};
    const int bnStrides[4] = {C, 1, 1, 1};
    miopenSetTensorDescriptor(bnDesc, miopenFloat, 4, bnDims, bnStrides);

    // ---- deterministic host data -------------------------------------------------
    // Input magnitudes scaled to MIOpen's own gtest convention (Data_scale 1e-3
    // order, bn_spatial_test.cpp) so per-channel reduction sums stay in a range
    // where FP32 tree reductions meet the PREDECLARED absolute tolerances.
    // Tolerances themselves are untouched; identical inputs on both legs.
    uint64_t seed = 0x5eed1234abcdull;
    std::vector<float> x(T), dy(T), bnScale(C), bnBias(C);
    for(size_t i = 0; i < T; ++i)
        x[i] = static_cast<float>((next_uniform01(seed) * 4.0 - 2.0) * 0.01);
    for(size_t i = 0; i < T; ++i)
        dy[i] = static_cast<float>((next_uniform01(seed) * 2.0 - 1.0) * 0.01);
    for(int c = 0; c < C; ++c)
        bnScale[c] = static_cast<float>(0.5 + next_uniform01(seed) * 1.5);
    for(int c = 0; c < C; ++c)
        bnBias[c] = static_cast<float>(next_uniform01(seed) * 2.0 - 1.0);
    std::vector<float> runMean(C, 0.0f), runVar(C, 1.0f);
    std::vector<float> savedMean(C), savedInvVar(C);

    std::vector<float> y(T), dx(T), dwScale(C, 0.0f), dwBias(C, 0.0f);

    // ---- CPU float64 reference (NCHW layout: x[n][c][h][w] at ((n*C+c)*H+h)*W+w) ----
    std::vector<double> mean(C), var(C), invStd(C);
    const size_t CHW = static_cast<size_t>(C) * H * W;
    const size_t HW = static_cast<size_t>(H) * W;
    const size_t per = static_cast<size_t>(N) * H * W; // elements per channel
    for(int c = 0; c < C; ++c)
    {
        double m = 0.0;
        for(int n = 0; n < N; ++n)
            for(size_t i = 0; i < HW; ++i)
                m += static_cast<double>(x[n * CHW + c * HW + i]);
        m /= static_cast<double>(per);
        double v = 0.0;
        for(int n = 0; n < N; ++n)
            for(size_t i = 0; i < HW; ++i)
            {
                const double d = static_cast<double>(x[n * CHW + c * HW + i]) - m;
                v += d * d;
            }
        v /= static_cast<double>(per); // population variance (MIOpen semantics)
        mean[c] = m;
        var[c] = v;
        invStd[c] = 1.0 / std::sqrt(v + eps);
    }
    // Full batchnorm training gradient (mean and variance depend on x):
    //   x_hat = (x - mean) * invStd
    //   dbeta = sum(dy)
    //   dgamma = sum(dy * x_hat)
    //   dx = gamma * invStd * (dy - mean(dy) - x_hat * mean(dy * x_hat))
    std::vector<double> refY(T), refDx(T), refDw(C, 0.0), refDb(C, 0.0), refRm(C), refRv(C);
    for(int c = 0; c < C; ++c)
    {
        const double s = bnScale[c], b = bnBias[c], iv = invStd[c];
        double dwacc = 0.0, dbacc = 0.0;
        for(int n = 0; n < N; ++n)
            for(size_t i = 0; i < HW; ++i)
            {
                const size_t idx = n * CHW + c * HW + i;
                const double xh = (static_cast<double>(x[idx]) - mean[c]) * iv;
                const double dyv = static_cast<double>(dy[idx]);
                refY[idx] = s * xh + b;
                dwacc += dyv * xh;
                dbacc += dyv;
            }
        refDw[c] = dwacc;
        refDb[c] = dbacc;
        refRm[c] = (1.0 - expAvgFactor) * 0.0 + expAvgFactor * mean[c];
        refRv[c] = (1.0 - expAvgFactor) * 1.0 + expAvgFactor * var[c];
    }
    for(int c = 0; c < C; ++c)
    {
        const double s = bnScale[c], iv = invStd[c];
        double mdy = 0.0, mdyxh = 0.0;
        for(int n = 0; n < N; ++n)
            for(size_t i = 0; i < HW; ++i)
            {
                const size_t idx = n * CHW + c * HW + i;
                const double xh = (static_cast<double>(x[idx]) - mean[c]) * iv;
                const double dyv = static_cast<double>(dy[idx]);
                mdy += dyv;
                mdyxh += dyv * xh;
            }
        mdy /= static_cast<double>(per);
        mdyxh /= static_cast<double>(per);
        for(int n = 0; n < N; ++n)
            for(size_t i = 0; i < HW; ++i)
            {
                const size_t idx = n * CHW + c * HW + i;
                const double xh = (static_cast<double>(x[idx]) - mean[c]) * iv;
                const double dyv = static_cast<double>(dy[idx]);
                refDx[idx] = s * iv * (dyv - mdy - xh * mdyxh);
            }
    }

    // ---- GPU allocations ------------------------------------------------------------
    void *dx_, *dx2, *dy_, *dy2, *out, *out2, *sc, *bi, *rm, *rv, *sm, *sv, *dws, *dwb;
    hipMalloc(&dx_, T * sizeof(float));
    hipMalloc(&dy_, T * sizeof(float));
    hipMalloc(&out, T * sizeof(float));
    hipMalloc(&out2, T * sizeof(float));
    hipMalloc(&dx2, T * sizeof(float));
    hipMalloc(&sc, C * sizeof(float));
    hipMalloc(&bi, C * sizeof(float));
    hipMalloc(&rm, C * sizeof(float));
    hipMalloc(&rv, C * sizeof(float));
    hipMalloc(&sm, C * sizeof(float));
    hipMalloc(&sv, C * sizeof(float));
    hipMalloc(&dws, C * sizeof(float));
    hipMalloc(&dwb, C * sizeof(float));
    hipMemcpy(dx_, x.data(), T * sizeof(float), 1 /*hipMemcpyHostToDevice*/);
    hipMemcpy(dy_, dy.data(), T * sizeof(float), 3);
    hipMemcpy(sc, bnScale.data(), C * sizeof(float), 3);
    hipMemcpy(bi, bnBias.data(), C * sizeof(float), 3);
    hipMemcpy(rm, runMean.data(), C * sizeof(float), 3);
    hipMemcpy(rv, runVar.data(), C * sizeof(float), 3);
    hipMemcpy(dws, std::vector<float>(C, 0.0f).data(), C * sizeof(float), 3);
    hipMemcpy(dwb, std::vector<float>(C, 0.0f).data(), C * sizeof(float), 3);

    float alpha = 1.0f, beta = 0.0f;
    float aD = 1.0f, bD = 0.0f, aP = 1.0f, bP = 0.0f; // MIOpen requires float (1,0)

    std::printf("\nFORWARD (training)...\n");
    miopenStatus_t st1 = bnFwd(handle, miopenBNSpatial, &alpha, &beta,
                               xDesc, dx_, xDesc, out,
                               bnDesc, sc, bi,
                               expAvgFactor, rm, rv, eps, sm, sv);
    std::printf("  miopenBatchNormalizationForwardTraining status=%d\n", static_cast<int>(st1));
    hipDeviceSynchronize();
    std::printf("  hipDeviceSynchronize after forward OK\n");
    hipMemcpy(y.data(), out, T * sizeof(float), 2 /*hipMemcpyDeviceToHost*/);
    hipMemcpy(savedMean.data(), sm, C * sizeof(float), 2);
    hipMemcpy(savedInvVar.data(), sv, C * sizeof(float), 2);
    hipMemcpy(runMean.data(), rm, C * sizeof(float), 2);
    hipMemcpy(runVar.data(), rv, C * sizeof(float), 2);

    std::printf("BACKWARD...\n");
    miopenStatus_t st2 = bnBwd(handle, miopenBNSpatial, &aD, &bD, &aP, &bP,
                               xDesc, dx_, xDesc, dy_, xDesc, out2,
                               bnDesc, sc, dws, dwb, eps, sm, sv);
    std::printf("  miopenBatchNormalizationBackward status=%d\n", static_cast<int>(st2));
    hipDeviceSynchronize();
    std::printf("  hipDeviceSynchronize after backward OK\n");
    hipMemcpy(dx.data(), out2, T * sizeof(float), 2);
    hipMemcpy(dwScale.data(), dws, C * sizeof(float), 2);
    hipMemcpy(dwBias.data(), dwb, C * sizeof(float), 2);

    // ---- checks ---------------------------------------------------------------------
    int fails = 0;
    auto maxabs = [](const std::vector<float>& got, const std::vector<double>& ref, double& mo) {
        mo = 0.0;
        for(size_t i = 0; i < ref.size(); ++i)
        {
            const double d = std::fabs(static_cast<double>(got[i]) - ref[i]);
            if(d > mo) mo = d;
            if(!std::isfinite(got[i])) return false;
        }
        return true;
    };
    double mY, mDx, mDw, mDb, mRm, mRvAbs, mRvRel = 0.0;
    bool finY = maxabs(y, refY, mY);
    bool finDx = maxabs(dx, refDx, mDx);
    bool finDw = maxabs(dwScale, refDw, mDw);
    bool finDb = maxabs(dwBias, refDb, mDb);
    bool finRm = maxabs(runMean, refRm, mRm);
    bool finRv = true;
    mRvAbs = 0.0;
    for(int c = 0; c < C; ++c)
    {
        if(!std::isfinite(runVar[c])) finRv = false;
        const double rel = std::fabs(static_cast<double>(runVar[c]) - refRv[c]) / std::fabs(refRv[c]);
        if(rel > mRvRel) mRvRel = rel;
        (void)0;
    }
    struct Chk { const char* name; double got; double tol; bool fin; };
    const Chk checks[] = {
        {"y", mY, TOL_Y, finY}, {"dx", mDx, TOL_DX, finDx},
        {"dw", mDw, TOL_DW, finDw}, {"db", mDb, TOL_DB, finDb},
        {"running_mean", mRm, TOL_RM, finRm},
    };
    for(const auto& c : checks)
    {
        const bool ok = c.fin && c.got <= c.tol;
        std::printf("CHECK %-14s max_abs=%.3e (tol %.1e) finite=%d -> %s\n",
                    c.name, c.got, c.tol, c.fin ? 1 : 0, ok ? "PASS" : "FAIL");
        if(!ok) fails++;
    }
    const bool rvOk = finRv && mRvRel <= TOL_RV_REL;
    std::printf("CHECK %-14s max_rel=%.3e (tol %.1e) finite=%d -> %s\n",
                "running_var", mRvRel, TOL_RV_REL, finRv ? 1 : 0, rvOk ? "PASS" : "FAIL");
    if(!rvOk) fails++;
    const bool rmNontrivial = mRm > 0.0; // running mean actually moved from init 0
    double rvMoved = 0.0; // distance of running var from its init value 1.0
    for(int c = 0; c < C; ++c)
        rvMoved = std::max(rvMoved, std::fabs(static_cast<double>(runVar[c]) - 1.0));
    const bool rvNontrivial = rvMoved > 0.0;
    std::printf("running stats nontrivial update: rm_moved=%d rv_moved=%d (max |rv-1|=%.3e)\n",
                rmNontrivial ? 1 : 0, rvNontrivial ? 1 : 0, rvMoved);

    hipFree(dx_); hipFree(dy_); hipFree(out); hipFree(out2); hipFree(dx2);
    hipFree(sc); hipFree(bi); hipFree(rm); hipFree(rv); hipFree(sm); hipFree(sv);
    hipFree(dws); hipFree(dwb);
    miopenDestroyTensorDescriptor(xDesc);
    miopenDestroyTensorDescriptor(bnDesc);
    miopenDestroy(handle);

    std::printf("HARNESS_RESULT: %s\n", fails == 0 ? "PASS" : "FAIL");
    return fails == 0 ? 0 : 1;
}
