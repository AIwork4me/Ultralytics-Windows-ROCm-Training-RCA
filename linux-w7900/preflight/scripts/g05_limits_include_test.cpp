#include <hip/hiprtc.h>
#include <cstdio>
#include <vector>
static const char* src = R"(
#include <limits>
extern "C" __global__ void k(float* o){ o[0] = (float)__INT32_MAX__; }
)";
int main(){
  for (const char* extra : {(const char*)nullptr, "-nostdinc++", "-nostdinc"}) {
    hiprtcProgram p;
    hiprtcCreateProgram(&p, src, "t.cu", 0, nullptr, nullptr);
    std::vector<const char*> o{"-mcpu=gfx1100"};
    if (extra) o.push_back(extra);
    hiprtcResult r = hiprtcCompileProgram(p, o.size(), o.data());
    std::size_t n=0; hiprtcGetProgramLogSize(p,&n);
    std::vector<char> log(n+1,0); hiprtcGetProgramLog(p,log.data());
    std::printf("actual #include <limits> under %-11s -> compile=%s %s\n",
      extra?extra:"(default)", r==HIPRTC_SUCCESS?"OK":"FAIL",
      r!=HIPRTC_SUCCESS?"(log tail follows)":"");
    if(r!=HIPRTC_SUCCESS) std::printf("  log: %.200s\n", log.data());
    hiprtcDestroyProgram(&p);
  }
}
