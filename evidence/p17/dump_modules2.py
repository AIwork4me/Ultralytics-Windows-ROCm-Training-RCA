import ctypes, ctypes.wintypes as wt, torch, sys
k32 = ctypes.WinDLL('kernel32.dll')
x = torch.randn(8, 8, device='cuda'); y = x @ x; torch.cuda.synchronize()
TH32CS_SNAPMODULE = 0x8 | 0x10
class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", wt.WCHAR*256),
                ("szExePath", wt.WCHAR*260)]
snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, k32.GetCurrentProcessId())
me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(MODULEENTRY32W)
with open(sys.argv[1], 'w', encoding='utf-8') as out:
    if k32.Module32FirstW(snap, ctypes.byref(me)):
        while True:
            out.write(f"{me.szModule}\t{me.szExePath}\n")
            if not k32.Module32NextW(snap, ctypes.byref(me)):
                break
    else:
        out.write(f"Module32First failed err={k32.GetLastError()}\n")
k32.CloseHandle(snap)
