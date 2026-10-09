// Gate L06: in-process dynamic-library provenance probe.
// dlopen's the leg's libMIOpen.so (absolute path), resolves miopenCreate,
// then calls it to force full dependency resolution; walks /proc/self/maps
// for every loaded ROCm-relevant library, records absolute paths + SHA256
// (via stat + read of mapped file) for libMIOpen/libhiprtc/libamdhip64/
// libamd_comgr/librocblas/libhsa-runtime64, and asserts zero /opt/rocm-7.2.1.
// Exit 0 only if the loaded libMIOpen matches the expected absolute path and
// no 7.2.1 library is mapped.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int file_sha256(const char* path, char out[65]) {
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "sha256sum '%s' 2>/dev/null", path);
    FILE* p = popen(cmd, "r");
    if (!p) return -1;
    char buf[512];
    out[0] = 0;
    if (fgets(buf, sizeof(buf), p)) {
        char* sp = strchr(buf, ' ');
        if (sp) { *sp = 0; strncpy(out, buf, 64); out[64] = 0; }
    }
    int rc = pclose(p);
    return (rc == 0 && out[0]) ? 0 : -1;
}

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s <abs-path-libMIOpen.so>\n", argv[0]); return 2; }
    const char* want = argv[1];
    void* h = dlopen(want, RTLD_NOW);
    if (!h) { fprintf(stderr, "dlopen failed: %s\n", dlerror()); return 3; }
    void* sym = dlsym(h, "miopenCreate");
    if (!sym) { fprintf(stderr, "miopenCreate missing\n"); return 4; }
    Dl_info info;
    if (dladdr(sym, &info) && info.dli_fname) {
        printf("miopenCreate resolved from: %s\n", info.dli_fname);
    } else { fprintf(stderr, "dladdr failed\n"); return 5; }
    // call miopenCreate with NULL handle ptr is invalid; instead just resolve
    // miopenKthvalueForward symbol to confirm the API surface is present.
    void* kth = dlsym(h, "miopenKthvalueForward");
    printf("miopenKthvalueForward resolved: %s\n", kth ? "yes" : "NO");
    if (!kth) return 6;

    // Force real initialization (HIP context creation -> lazy loads) so the
    // maps walk observes post-GPU-init state, not merely startup linkage.
    typedef int (*create_fn)(void**);
    typedef int (*destroy_fn)(void*);
    create_fn create = (create_fn)sym;
    destroy_fn destroy = (destroy_fn)dlsym(h, "miopenDestroy");
    void* handle = NULL;
    if (create && destroy) {
        int rc = create(&handle);
        printf("miopenCreate rc=%d handle=%p\n", rc, handle);
        if (rc == 0 && handle) {
            int rc2 = destroy(handle);
            printf("miopenDestroy rc=%d\n", rc2);
        }
    } else {
        printf("create/destroy not resolvable (unexpected)\n");
    }

    // walk /proc/self/maps
    FILE* maps = fopen("/proc/self/maps", "r");
    if (!maps) { perror("maps"); return 7; }
    char line[4096];
    const char* watch[] = {"libMIOpen.so", "libhiprtc.so", "libamdhip64.so",
                           "libamd_comgr.so", "librocblas.so", "libhsa-runtime64.so",
                           "libhipblaslt.so", "libroctx64.so", NULL};
    int contamination = 0;
    char seen[16][4096]; int nseen = 0;
    while (fgets(line, sizeof(line), maps)) {
        char* path = strchr(line, '/');
        if (!path) continue;
        char* nl = strchr(path, '\n'); if (nl) *nl = 0;
        if (strstr(path, "rocm-7.2.1")) { printf("CONTAMINATION: %s\n", path); contamination = 1; }
        for (int i = 0; watch[i]; i++) {
            const char* base = strrchr(path, '/');
            base = base ? base + 1 : path;
            if (strncmp(base, watch[i], strlen(watch[i])) == 0) {
                int dup = 0;
                for (int j = 0; j < nseen; j++) if (!strcmp(seen[j], path)) dup = 1;
                if (!dup && nseen < 16) {
                    strncpy(seen[nseen], path, 4095); seen[nseen][4095] = 0; nseen++;
                    char sha[65];
                    if (file_sha256(path, sha) == 0)
                        printf("LOADED %s sha256=%s\n", path, sha);
                    else
                        printf("LOADED %s sha256=<unavailable>\n", path);
                }
            }
        }
    }
    fclose(maps);
    int right_lib = 0;
    if (info.dli_fname && strcmp(info.dli_fname, want) == 0) right_lib = 1;
    printf("dladdr_path_matches_expected=%d contamination=%d\n", right_lib, contamination);
    dlclose(h);
    return (right_lib && !contamination) ? 0 : 10;
}
