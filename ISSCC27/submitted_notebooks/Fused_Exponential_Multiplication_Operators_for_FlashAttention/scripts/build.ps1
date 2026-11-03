# Build the C++ reference models with MSVC (local Windows box).
#   powershell -ExecutionPolicy Bypass -File scripts/build.ps1 [-Clean]
param([switch]$Clean)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$vc   = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vc)) { throw "vcvars64.bat not found: $vc" }

$build = Join-Path $root "build"
New-Item -ItemType Directory -Force $build | Out-Null
if ($Clean) { Get-ChildItem $build -Recurse -File | Remove-Item -Force }

$src = Join-Path $root "src"
$vcf = "`"$vc`" >nul && cd /d `"$root`" && "
$cflags = "/nologo /std:c++17 /O2 /EHsc /W3 /fp:precise /I`"$src`""

# expmul.exe : operator-level error study (phase 1)
$cmd1 = $vcf + "cl $cflags `"$src\expmul.cpp`" /Fe:`"$build\\expmul.exe`" /Fo:`"$build\\`""
cmd /c $cmd1
if ($LASTEXITCODE -ne 0) { throw "cl (expmul) failed with $LASTEXITCODE" }

# tb.exe : shared testbench for baseline + ExpMul kernels (phase 2)
$cmd2 = $vcf + "cl $cflags `"$src\tb.cpp`" `"$src\flash_attn_baseline.cpp`" " +
        "`"$src\flash_attn_expmul.cpp`" /Fe:`"$build\\tb.exe`" /Fo:`"$build\\`""
cmd /c $cmd2
if ($LASTEXITCODE -ne 0) { throw "cl (tb) failed with $LASTEXITCODE" }

Write-Host "built $build\expmul.exe, $build\tb.exe"
