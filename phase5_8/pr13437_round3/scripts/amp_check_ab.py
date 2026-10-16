"""Standalone Ultralytics AMP check under whichever MIOpen.dll is swapped in.
Reports check_amp verdict + in-process DLL path."""
import ctypes
import sys

import torch

print("torch", torch.__version__, "| hip", torch.version.hip)
miopen = ctypes.CDLL("MIOpen.dll")
gmfn = ctypes.WinDLL("kernel32").GetModuleFileNameA
gmfn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
path = ctypes.create_string_buffer(512)
gmfn(miopen._handle, path, 512)
print("MIOpen.dll loaded from:", path.value.decode(errors="replace"))

from ultralytics import YOLO
from ultralytics.utils.checks import check_amp

model = YOLO("yolo26n.pt")
ok = check_amp(model)
print("AMP_CHECK_RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
