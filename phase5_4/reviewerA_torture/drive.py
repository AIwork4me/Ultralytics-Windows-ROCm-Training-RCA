import ctypes
import pathlib
import sys

SDK   = r"C:\Users\rocm\miniconda3\Lib\site-packages\_rocm_sdk_core\bin\hiprtc0714.dll"
KDIR  = r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5.4-develop-replay\projects\miopen\src\kernels"
SRC   = pathlib.Path(__file__).with_name("torture_traits.cpp").read_text()

h = ctypes.CDLL(SDK)
prog = ctypes.c_void_p()

def compile_leg(label, isolate):
    opts = [
        b"-D__HIP_PLATFORM_AMD__=1",
        b"-DHIP_PACKAGE_VERSION_FLAT=7014000000",
        b"-DMIOPEN_HIP_RUNTIME_COMPILE",
        b"-std=c++17",
        b"--gpu-architecture=gfx1151",
        ("-I" + KDIR).encode(),
    ]
    if isolate:
        opts.append(b"-nostdinc")
    arr = (ctypes.c_char_p * len(opts))(*opts)
    rc = h.hiprtcCompileProgram(prog, len(opts), arr)
    n = ctypes.c_size_t()
    h.hiprtcGetProgramLogSize(prog, ctypes.byref(n))
    buf = ctypes.create_string_buffer(max(n.value, 1))
    h.hiprtcGetProgramLog(prog, buf)
    log = buf.value.decode(errors="replace")
    print(f"=== {label}: hiprtcCompileProgram rc={rc}")
    tail = [l for l in log.splitlines() if l.strip()]
    for l in tail[-25:]:
        print("   " + l)
    return rc

rc = h.hiprtcCreateProgram(ctypes.byref(prog), SRC.encode(), b"torture_traits.cpp", 0, None, None)
print("create rc =", rc)
if rc != 0:
    sys.exit(2)
a = compile_leg("LEG A freestanding (-nostdinc, MIOPEN_HIP_RUNTIME_COMPILE)", isolate=True)
h.hiprtcDestroyProgram(ctypes.byref(prog))
prog = ctypes.c_void_p()
rc = h.hiprtcCreateProgram(ctypes.byref(prog), SRC.encode(), b"torture_traits.cpp", 0, None, None)
b = compile_leg("LEG B real host STL (ambient include env, MIOPEN_HIP_RUNTIME_COMPILE)", isolate=False)
h.hiprtcDestroyProgram(ctypes.byref(prog))
print("RESULT:", "BOTH LEGS COMPILE (differential conformance holds)" if a == 0 and b == 0
      else f"DIFFERENTIAL OUTCOME legA={a} legB={b}")
