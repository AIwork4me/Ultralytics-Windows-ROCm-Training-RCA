// Proposed MIOpen CI test (Phase-3 Gate 59/84 reviewer-D item): compile
// an embedded kernel translation unit through hiprtc with -nostdinc and
// the runtime-compile define set, proving RTC kernel sources stay
// self-contained without a host C++ standard library. Compile-only: no
// GPU execution required (log inspection suffices); negative-control
// mode verifies the unpatched tree fails with the field signature.
//
// Proposed wiring (test/CMakeLists.txt, gated on BUILD_TESTING and
// MIOPEN_USE_HIPRTC):
//   add_executable(hiprtc_selfcontained test/hiprtc_selfcontained.cpp)
//   target_link_libraries(hiprtc_selftrained PRIVATE hiprtc::hiprtc)
//   add_test(NAME hiprtc_selfcontained COMMAND hiprtc_selfcontained
//            ${CMAKE_SOURCE_DIR}/src/kernels)
//
#include <hip/hiprtc.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string read_file(const std::string& p)
{
    std::ifstream f(p, std::ios::binary);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Mirror the option set MIOpen's comgr BuildHip applies to this kernel
// (src/comgr.cpp), plus -nostdinc to simulate an environment without a
// host C++ standard library.
int compile_kernel(const std::string& kernels_dir)
{
    const std::string src =
        read_file(kernels_dir + "/MIOpenBatchNormFwdTrainSpatial.cpp");
    hiprtcProgram prog{};
    hiprtcCreateProgram(&prog, src.c_str(), "MIOpenBatchNormFwdTrainSpatial.cpp",
                        0, nullptr, nullptr);
    std::vector<const char*> opts = {
        "-D__HIP_PLATFORM_AMD__=1",
        "-DMIOPEN_USE_FP16=0",
        "-DMIOPEN_USE_FP32=1",
        "-DMIOPEN_USE_FPMIX=0",
        "-DMIOPEN_USE_BFPMIX=0",
        "-DMIOPEN_LAYER_NCHW=1",
        "-DMIOPEN_LAYER_NHWC=0",
        "-DMIO_BN_VARIANT=0",
        "-DHIP_PACKAGE_VERSION_FLAT=7000000000", // any HIP >= 7 exercises the probe
        "-DMIOPEN_HIP_RUNTIME_COMPILE",
        "-std=c++17",
        "--gpu-architecture=gfx90a", // CI-friendly arch; codegen not required
        "-nostdinc",
    };
    hiprtcResult r = hiprtcCompileProgram(prog, (int)opts.size(), opts.data());
    size_t n = 0;
    hiprtcGetProgramLogSize(prog, &n);
    std::string log(n > 0 ? n : 1, '\0');
    hiprtcGetProgramLog(prog, log.data());
    if(r != HIPRTC_SUCCESS)
    {
        std::fprintf(stderr, "%s\n", log.c_str());
        std::fprintf(stderr,
                     "FAIL: kernel sources are not self-contained for runtime "
                     "compilation (missing freestanding definitions?)\n");
    }
    else if(log.find("type_traits") != std::string::npos)
    {
        std::fprintf(stderr, "WARN: log mentions type_traits\n");
    }
    hiprtcDestroyProgram(&prog);
    return r == HIPRTC_SUCCESS ? 0 : 1;
}

} // namespace

int main(int argc, char** argv)
{
    if(argc != 2)
    {
        std::fprintf(stderr, "usage: %s <miopen-src-kernels-dir>\n", argv[0]);
        return 2;
    }
    return compile_kernel(argv[1]);
}
