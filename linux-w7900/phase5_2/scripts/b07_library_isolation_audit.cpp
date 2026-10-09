// B07: dynamic-library contamination audit for the 7.14.1 validation env.
// Loads the source-built baseline libMIOpen exactly the way the final A/B
// legs will (LD_PRELOAD + LD_LIBRARY_PATH from run_validation_leg.sh),
// performs real MIOpen API calls (miopenCreate/TensorDescriptor/GetWorkspace
//Size), then scans /proc/self/maps for EVERY loaded ROCm-related object and
// asserts none resolves under /opt/rocm (7.2.1). dladdr provenance is
// printed for the key entry points.
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>

typedef struct miopenTensorDescriptor* miopenTensorDescriptor_t;

static int check(const char* label, void* handle, const char* sym)
{
    void* p = handle ? dlsym(handle, sym) : nullptr;
    if (!p) { printf("  %-28s %s: NOT FOUND\n", label, sym); return 0; }
    Dl_info i;
    if (dladdr(p, &i) && i.dli_fname)
        printf("  %-28s %s <- %s\n", label, sym, i.dli_fname);
    return 1;
}

static int maps_scan(int* n_rocm_objs, char* bad, size_t badsz)
{
    FILE* f = fopen("/proc/self/maps", "r");
    if (!f) { snprintf(bad, badsz, "cannot open /proc/self/maps"); return -1; }
    char line[1024];
    char objs[256][256];
    int n = 0;
    *n_rocm_objs = 0;
    bad[0] = 0;
    while (fgets(line, sizeof line, f)) {
        char* dash = strchr(line, '/');
        if (!dash) continue;
        char path[512];
        sscanf(dash, "%511s", path);
        // dedupe by basename
        const char* base = strrchr(path, '/');
        base = base ? base + 1 : path;
        int dup = 0;
        for (int i = 0; i < n; i++)
            if (strcmp(objs[i], base) == 0) { dup = 1; break; }
        if (dup) continue;
        if (strstr(path, "/opt/rocm")) {
            snprintf(bad + strlen(bad), badsz - strlen(bad),
                     "%s%s", bad[0] ? "; " : "", path);
            dup = 1;
        }
        if (!dup && (strstr(base, "libhip") || strstr(base, "libamd") ||
                     strstr(base, "librocm") || strstr(base, "libhsa") ||
                     strstr(base, "libroc") || strstr(base, "libMIOpen") ||
                     strstr(base, "libcomgr") || strstr(base, "rocr") ||
                     strstr(base, "librccl"))) {
            if (n < 256) { snprintf(objs[n], 256, "%s", base); n++; }
            (*n_rocm_objs)++;
        }
    }
    fclose(f);
    // print the deduped ROCm-related objects with full paths (second pass)
    f = fopen("/proc/self/maps", "r");
    printf("  loaded ROCm-related objects (dedup):\n");
    char seen[256][512]; int ns = 0;
    while (fgets(line, sizeof line, f)) {
        char* dash = strchr(line, '/');
        if (!dash) continue;
        char path[512];
        sscanf(dash, "%511s", path);
        const char* base = strrchr(path, '/');
        base = base ? base + 1 : path;
        if (!(strstr(base, "libhip") || strstr(base, "libamd") ||
              strstr(base, "librocm") || strstr(base, "libhsa") ||
              strstr(base, "libroc") || strstr(base, "libMIOpen") ||
              strstr(base, "libcomgr") || strstr(base, "rocr")))
            continue;
        int dup = 0;
        for (int i = 0; i < ns; i++) if (strcmp(seen[i], path) == 0) { dup = 1; break; }
        if (!dup && ns < 256) { snprintf(seen[ns], 512, "%s", path); ns++;
                                printf("    %s\n", path); }
    }
    fclose(f);
    return 0;
}

int main()
{
    printf("B07_DYNAMIC_AUDIT pid=%d\n", getpid());
    printf("LD_LIBRARY_PATH=%s\n", getenv("LD_LIBRARY_PATH") ?: "");
    printf("LD_PRELOAD=%s\n", getenv("LD_PRELOAD") ?: "");
    printf("ROCM_PATH=%s HIP_PATH=%s\n", getenv("ROCM_PATH") ?: "",
           getenv("HIP_PATH") ?: "");

    void* h_miopen = dlopen("libMIOpen.so.1", RTLD_NOW | RTLD_GLOBAL);
    if (!h_miopen) { printf("FATAL: cannot dlopen libMIOpen.so.1: %s\n",
                            dlerror()); return 3; }
    printf("[dlopen] libMIOpen.so.1 OK\n");

    // Real API activity: create handle + tensor descriptor + workspace query
    // (loads hip/hsa eagerly; rocblas/comgr stay lazy until used — we also
    // explicitly dlopen the lazy set the way MIOpen resolves them).
    void* (*miopenCreate)(void**) = (void* (*)(void**))dlsym(h_miopen, "miopenCreate");
    void* handle = nullptr;
    if (miopenCreate) {
        int st = ((int(*)(void**))miopenCreate)(&handle);
        printf("[api] miopenCreate -> %d (%s)\n", st,
               st == 0 ? "aiSuccess" : "nonzero");
    }
    void* (*createTensor)(miopenTensorDescriptor_t*) =
        (void* (*)(miopenTensorDescriptor_t*))dlsym(h_miopen, "miopenCreateTensorDescriptor");
    miopenTensorDescriptor_t td = nullptr;
    if (createTensor && handle) {
        int st = ((int(*)(miopenTensorDescriptor_t*))createTensor)(&td);
        printf("[api] miopenCreateTensorDescriptor -> %d\n", st);
        int (*set4)(miopenTensorDescriptor_t, int, int, int, int, int) =
            (int (*)(miopenTensorDescriptor_t, int, int, int, int, int))
            dlsym(h_miopen, "miopenSet4dTensorDescriptor");
        if (set4 && td) {
            int st = set4(td, 1 /*fp32*/, 2, 8, 4, 16);
            printf("[api] miopenSet4dTensorDescriptor -> %d\n", st);
        }
    }

    printf("[provenance]\n");
    check("MIOpen", h_miopen, "miopenCreate");
    check("MIOpen", h_miopen, "miopenKthvalueForward");
    const char* lazy[] = {
        "libhiprtc.so.7", "libamdhip64.so.7", "libamd_comgr.so.3",
        "librocblas.so.5", "libhsa-runtime64.so.1", "libhipblaslt.so.1",
        "libroctx64.so.4",
    };
    for (auto s : lazy) {
        void* h = dlopen(s, RTLD_LAZY | RTLD_GLOBAL);
        if (!h) { printf("  %-28s dlopen FAILED: %s\n", s, dlerror()); continue; }
        Dl_info i;
        void* any = dlsym(h, s[3] == 'h' && strstr(s, "hiprtc") ? "hiprtcCompileProgram"
                       : strstr(s, "amdhip64") ? "hipMalloc"
                       : strstr(s, "comgr") ? "comgrVersion"
                       : strstr(s, "rocblas") ? "rocblas_create_handle"
                       : strstr(s, "hsa") ? "hsa_init"
                       : strstr(s, "hipblaslt") ? "hipblasLtCreate"
                                               : "roctxMark");
        if (any && dladdr(any, &i) && i.dli_fname)
            printf("  %-28s <- %s\n", s, i.dli_fname);
    }
    // also hsa via the runtime's lazy path (libamdhip64 dlopens hsa)
    printf("[maps scan]\n");
    int n = 0; char bad[2048] = {0};
    maps_scan(&n, bad, sizeof bad);
    printf("  ROCm-related loaded objects: %d\n", n);
    if (bad[0]) { printf("CONTAMINATION /opt/rocm paths: %s\n", bad); return 2; }
    printf("NO_/opt/rocm_IN_maps: PASS\n");
    return 0;
}
