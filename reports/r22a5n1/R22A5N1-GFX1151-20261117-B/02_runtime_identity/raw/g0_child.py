
import ctypes, hashlib, json, re, sys
from pathlib import Path
import torch
import torch.nn as nn

rec = {}
rec["torch"] = torch.__version__
rec["hip"] = torch.version.hip
rec["cuda_available"] = bool(torch.cuda.is_available())
rec["device_count"] = int(torch.cuda.device_count())
if rec["device_count"]:
    rec["gpu_name"] = torch.cuda.get_device_name(0)
    # a real GPU op in THIS process — the DLL identity observed below is the
    # one the GPU execution itself used
    torch.manual_seed(0)
    model = nn.BatchNorm2d(100).cuda()
    x = torch.randn(4, 100, 8, 8, device="cuda")
    y = model(x)
    (y * y).mean().backward()
    torch.cuda.synchronize()
    rec["op_finite"] = bool(torch.isfinite(y).all().item()) and \
        bool(torch.isfinite(model.weight.grad).all().item())
try:
    miopen = ctypes.CDLL("MIOpen.dll")
    gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
    gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    buf = ctypes.create_string_buffer(1024)
    gmfn(miopen._handle, buf, 1024)
    path = buf.value.decode(errors="replace")
    h = hashlib.sha256()
    blob = b""
    try:
        blob = Path(path).read_bytes()
        h = hashlib.sha256(blob)
    except OSError:
        pass
    versions = sorted(set(re.findall(rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", blob)))
    rec["miopen"] = {"loaded": True, "path": path, "sha256": h.hexdigest(),
                     "bytes": len(blob),
                     "embedded_version_strings": [v.decode() for v in versions],
                     "pr13437_marker_miopen_initializer_list":
                         blob.count(b"miopen_initializer_list")}
except OSError as e:
    rec["miopen"] = {"loaded": False, "error": str(e)}
print("G0_CHILD_IDENTITY " + json.dumps(rec))
