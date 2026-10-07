# Gate 26 reproduction: MSVC / Visual Studio discovery (read-only).
"=== where cl / vswhere ==="; where.exe cl 2>&1; where.exe vswhere 2>&1
"=== VS roots ==="
foreach ($d in @("C:\Program Files\Microsoft Visual Studio",
                 "C:\Program Files (x86)\Microsoft Visual Studio",
                 "C:\BuildTools")) {
  "{0} : {1}" -f $d, (Test-Path $d)
}
$vw = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vw) { & $vw -all -products * -format json } else { "vswhere NOT PRESENT" }
"=== type_traits search ==="
Get-ChildItem -Path "C:\Program Files*\Microsoft Visual Studio","C:\BuildTools" -Recurse -Filter type_traits -ErrorAction SilentlyContinue |
  Select-Object -First 5 -ExpandProperty FullName
