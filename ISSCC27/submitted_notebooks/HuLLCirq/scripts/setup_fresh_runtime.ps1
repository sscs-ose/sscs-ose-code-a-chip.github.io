# First-ever PC setup. No private cache, restored project, system installation,
# model inference or design EDA is required. See docs/fresh_install.md.
[CmdletBinding()]
param(
    [switch]$Prepare,
    [switch]$Download,
    [switch]$AcceptModelLicense,
    [string]$Distribution = 'Ubuntu',
    [switch]$Plan
)
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Use PowerShell 7 (pwsh). No changes made.' }
if (-not $IsWindows -or [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'X64') {
    throw 'This setup targets Windows x86-64 with WSL2 Ubuntu 24.04 amd64. No changes made.'
}
if (($Download -or $AcceptModelLicense) -and -not $Prepare) {
    throw '-Download and -AcceptModelLicense require -Prepare; default mode is strictly read-only.'
}
if ($Plan -and ($Prepare -or $Download -or $AcceptModelLicense)) { throw '-Plan is read-only and cannot be combined with preparation switches.' }
if ($Plan) {
    [ordered]@{
        kind = 'plan_only_no_writes_or_processes'
        required_host = 'Windows x64; PowerShell 7; WSL2 Ubuntu 24.04 amd64; FUSE2 compatibility'
        versions = 'Python 3.12.10; Ollama 0.32.15; Qwen2.5-Coder 7b Q4_K_M; Icarus 12; Yosys 0.33; LibreLane 3.0.16; pinned SKY130A/HD'
        private_model_cache_required = $false
        restored_project_required = $false
        system_install = $false
    } | ConvertTo-Json
    return
}
$freshProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
# A moved/reparse-point .work could otherwise direct bootstrap writes outside
# the checkout. Refuse existing bootstrap ancestors that are reparse points.
foreach ($freshRelative in @('.work', '.work/runtime', '.work/runtime/downloads', '.work/runtime/python-3.12.10-embed-amd64')) {
    $freshAncestor = Join-Path $freshProjectRoot $freshRelative
    if (Test-Path -LiteralPath $freshAncestor) {
        if ((Get-Item -LiteralPath $freshAncestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'A bootstrap runtime ancestor is a reparse point. Preserve it and use an ordinary checkout-local runtime directory.'
        }
    }
}
$freshPython = Join-Path $freshProjectRoot '.work/runtime/python-3.12.10-embed-amd64/python.exe'
if (-not (Test-Path -LiteralPath $freshPython -PathType Leaf)) {
    if (-not ($Prepare -and $Download)) {
        throw 'Pinned Python is missing. Run this script with -Prepare -Download -AcceptModelLicense to acquire the fixed dependencies. No files written.'
    }
    & (Join-Path $PSScriptRoot 'setup_python_runtime.ps1') -DownloadPython
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Pinned Python bootstrap failed.' }
}
$freshArguments = @('-B', '-X', 'utf8', (Join-Path $PSScriptRoot 'fresh_runtime.py'), '--distribution', $Distribution)
if ($Prepare) {
    $freshArguments += '--prepare'
    if ($Download) { $freshArguments += '--download' }
    if ($AcceptModelLicense) { $freshArguments += '--accept-model-license' }
} else { $freshArguments += '--verify' }
& $freshPython @freshArguments
if ($LASTEXITCODE -ne 0) { throw 'Fresh runtime preparation/verification failed. Existing conflicting files and histories were preserved.' }
