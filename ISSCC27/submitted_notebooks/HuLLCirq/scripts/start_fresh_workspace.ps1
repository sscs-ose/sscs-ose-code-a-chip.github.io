# Resolve and verify only the current checkout's fresh runtime, then serve on
# loopback. Starts no model, circuit job or network sharing automatically.
[CmdletBinding()]
param([string]$Distribution = 'Ubuntu', [ValidateRange(1,65535)][int]$Port = 8772)
$ErrorActionPreference = 'Stop'
$freshProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$freshPython = Join-Path $freshProjectRoot '.work/runtime/python-3.12.10-embed-amd64/python.exe'
if (-not (Test-Path -LiteralPath $freshPython -PathType Leaf)) {
    throw 'Run scripts/setup_fresh_runtime.ps1 -Prepare -Download -AcceptModelLicense first.'
}
& $freshPython -B -X utf8 (Join-Path $PSScriptRoot 'fresh_runtime.py') --distribution $Distribution --launch --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Fresh workspace launch failed; no unowned process was stopped.' }
