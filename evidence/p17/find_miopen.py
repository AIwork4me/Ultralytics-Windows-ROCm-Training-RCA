import ctypes, ctypes.wintypes as wt, torch, sys
psapi = ctypes.WinDLL('Psapi.dll'); k32 = ctypes.WinDLL('kernel32.dll')
x = torch.randn(8, 8, device='cuda'); y = x @ x; torch.cuda.synchronize()
import torch.nn as nn
c = nn.Conv2d(3, 8, 3).cuda(); z = c(torch.randn(1,3,16,16,device='cuda')); torch.cuda.synchronize()
h = k32.GetCurrentProcess()
arr = (wt.HMODULE * 2048)(); needed = wt.DWORD()
psapi.EnumProcessModulesEx(h, ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(needed), 3)
n = needed.value // ctypes.sizeof(wt.HMODULE)
buf = ctypes.create_unicode_buffer(1024)
out = open(sys.argv[1], 'w', encoding='utf-8')
for i in range(n):
    psapi.GetModuleFileNameExW(h, arr[i], buf, 1024)
    p = buf.value
    low = p.lower()
    if 'miopen' in low or 'rocm' in low or 'hip' in low:
        out.write(p + '\n')
out.close()
