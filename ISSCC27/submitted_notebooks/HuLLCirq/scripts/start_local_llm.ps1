# Foreground service: close with Ctrl+C. Only this process receives these settings.
param(
    [string]$OllamaPath = (Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'),
    [ValidateSet('qwen3:8b', 'qwen2.5-coder:7b')]
    [string]$Model = 'qwen3:8b',
    [ValidateRange(1024, 131072)]
    [int]$ContextLength = 16384
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$modelDirectory = Join-Path $projectRoot '.work/m2/ollama-models'
$modelPins = @{
    'qwen3:8b' = @{ path = 'manifests/registry.ollama.ai/library/qwen3/8b'; sha256 = '500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41' }
    'qwen2.5-coder:7b' = @{ path = 'manifests/registry.ollama.ai/library/qwen2.5-coder/7b'; sha256 = 'dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364' }
}
$manifest = Join-Path $modelDirectory $modelPins[$Model].path
if (-not (Test-Path -LiteralPath $manifest)) { throw "Prepare the pinned $Model model first." }
if ((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $modelPins[$Model].sha256) {
    throw "The isolated $Model manifest differs from its public pin."
}
if (Get-NetTCPConnection -LocalPort 11435 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 11435 is already in use; the existing process was not stopped.' }
$taskSettings = @{OLLAMA_HOST='127.0.0.1:11435'; OLLAMA_MODELS=$modelDirectory; OLLAMA_NO_CLOUD='1'; OLLAMA_CONTEXT_LENGTH=[string]$ContextLength; OLLAMA_NUM_PARALLEL='1'; OLLAMA_API_KEY=''}
$previousSettings = @{}
try {
    foreach ($name in $taskSettings.Keys) {
        $previousSettings[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $taskSettings[$name], 'Process')
    }
    $versionText = (& $OllamaPath --version 2>&1) -join ' '
    $versions = @([regex]::Matches($versionText, '\bversion(?: is|:)?\s+(\d+\.\d+\.\d+)\b') | ForEach-Object { $_.Groups[1].Value })
    if ($LASTEXITCODE -ne 0 -or $versions.Count -eq 0 -or @($versions | Where-Object { $_ -ne '0.32.15' }).Count) {
        throw "This recorded configuration requires Ollama 0.32.15. Output: $versionText"
    }
    & $OllamaPath serve
} finally {
    foreach ($name in $previousSettings.Keys) { [Environment]::SetEnvironmentVariable($name, $previousSettings[$name], 'Process') }
}
