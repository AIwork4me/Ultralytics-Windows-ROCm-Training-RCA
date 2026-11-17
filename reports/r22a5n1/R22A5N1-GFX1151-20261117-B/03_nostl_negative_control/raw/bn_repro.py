
import ctypes, hashlib, json, sys
from pathlib import Path
import torch
import torch.nn as nn


def miopen_identity():
    """In-process loaded MIOpen.dll identity. Captured PRE-OP as well: a
    pre-fix child dies inside the BatchNorm HIPRTC compile, so a post-op-only
    capture would never run on exactly the legs that must prove their DLL."""
    try:
        miopen = ctypes.CDLL("MIOpen.dll")
        gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
        gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        buf = ctypes.create_string_buffer(1024)
        gmfn(miopen._handle, buf, 1024)
        path = buf.value.decode(errors="replace")
        blob = Path(path).read_bytes()
        return {"loaded": True, "path": path,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
                "pr13437_marker_miopen_initializer_list":
                    blob.count(b"miopen_initializer_list")}
    except OSError as e:
        return {"loaded": False, "error": str(e)}


miopen_pre = miopen_identity()
print("BN_NOSTL_CHILD_MIOPEN_PRE " + json.dumps(miopen_pre))
try:
    torch.manual_seed(0)
    model = nn.BatchNorm2d(100).cuda()
    x = torch.randn(20, 100, 35, 45, device="cuda")
    y = model(x)
    loss = (y * y).mean()
    loss.backward()
    torch.cuda.synchronize()
except Exception:
    # the pre-fix legs die INSIDE the BatchNorm HIPRTC compile; capture the
    # loaded MIOpen identity at the moment of failure (torch has loaded it by
    # then — ctypes resolves the already-loaded module by name) BEFORE the
    # traceback unwinds, then let the failure propagate honestly
    miopen_fail = miopen_identity()
    print("BN_NOSTL_CHILD_MIOPEN_ATFAIL " + json.dumps(miopen_fail))
    raise
out_finite = bool(torch.isfinite(y).all().item())
grad_finite = bool(torch.isfinite(model.weight.grad).all().item()) and \
              bool(torch.isfinite(model.bias.grad).all().item())
miopen_post = miopen_identity()
print("BN_NOSTL_REPRO out_finite=%s grad_finite=%s loss=%.6f" %
      (out_finite, grad_finite, float(loss)))
print("BN_NOSTL_CHILD_MIOPEN " + json.dumps(
    {"pre_op": miopen_pre, "post_op": miopen_post}))
sys.exit(0 if (out_finite and grad_finite) else 1)
