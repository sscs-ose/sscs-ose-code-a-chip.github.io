# Prepare the pinned local Ollama runtime used by the current NPU project.
# Everything is kept under ignored .work data; no system installation or model download is performed.
param(
    [string]$ModelSource = (Join-Path $env:USERPROFILE '.ollama/models'),
    [ValidateSet('qwen2.5-coder:7b')]
    [string]$Model = 'qwen2.5-coder:7b',
    [string]$SourceModelTag = 'latest',
    [switch]$DownloadOllama,
    [switch]$SkipModel
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskRoot = Join-Path $projectRoot '.work/m2'
$downloadRoot = Join-Path $taskRoot 'downloads'
$modelTarget = Join-Path $taskRoot 'ollama-models'
$runtimeTarget = Join-Path $taskRoot 'ollama-0.32.15'

$modelPins = @{
    'qwen2.5-coder:7b' = @{
        family = 'qwen2.5-coder'
        target_tag = '7b'
        manifest_sha256 = 'dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364'
    }
}
$ollamaVersion = '0.32.15'
$ollamaArchiveName = 'ollama-windows-amd64-v0.32.15.zip'
$ollamaArchiveUrl = 'https://github.com/ollama/ollama/releases/download/v0.32.15/ollama-windows-amd64.zip'
$ollamaArchiveSha256 = 'a1d11d46a944f9c7521f5e9a3a5db51cd3365401da627d96c204698fc6914ff9'

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Description) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description is missing: $Path"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "$Description checksum differs. Expected $Expected but found $actual. Existing files were not replaced."
    }
}

function Copy-PinnedModel {
    $pin = $modelPins[$Model]
    $sourceManifest = Join-Path $ModelSource ("manifests/registry.ollama.ai/library/{0}/{1}" -f $pin.family, $SourceModelTag)
    Assert-Sha256 $sourceManifest $pin.manifest_sha256 "$Model source manifest"

    $manifest = Get-Content -LiteralPath $sourceManifest -Raw | ConvertFrom-Json
    $records = @($manifest.config) + @($manifest.layers)
    if ($records.Count -eq 0) { throw "$Model manifest contains no blobs." }
    foreach ($record in $records) {
        $digest = $record.digest -replace '^sha256:', ''
        if ($digest -notmatch '^[0-9a-f]{64}$' -or $record.size -lt 1) {
            throw "$Model manifest contains an invalid blob record."
        }
        $relative = 'blobs/sha256-' + $digest
        $source = Join-Path $ModelSource $relative
        if ((Get-Item -LiteralPath $source).Length -ne $record.size) {
            throw "$Model source blob size differs: $relative"
        }
        Assert-Sha256 $source $digest "$Model source blob"
        $target = Join-Path $modelTarget $relative
        if (-not (Test-Path -LiteralPath $target)) {
            $targetDirectory = Split-Path -Parent $target
            New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
            $partialTarget = Join-Path $targetDirectory ((Split-Path -Leaf $target) + '.copy.' + [guid]::NewGuid().ToString('N'))
            try {
                Copy-Item -LiteralPath $source -Destination $partialTarget
                if ((Get-Item -LiteralPath $partialTarget).Length -ne $record.size) {
                    throw "$Model copied blob size differs: $relative"
                }
                Assert-Sha256 $partialTarget $digest "$Model copied blob"
                Move-Item -LiteralPath $partialTarget -Destination $target
            } finally {
                if (Test-Path -LiteralPath $partialTarget) { Remove-Item -LiteralPath $partialTarget -Force }
            }
        }
        if ((Get-Item -LiteralPath $target).Length -ne $record.size) {
            throw "$Model target blob size differs: $relative"
        }
        Assert-Sha256 $target $digest "$Model target blob"
    }

    $targetManifest = Join-Path $modelTarget ("manifests/registry.ollama.ai/library/{0}/{1}" -f $pin.family, $pin.target_tag)
    New-Item -ItemType Directory -Path (Split-Path -Parent $targetManifest) -Force | Out-Null
    if (Test-Path -LiteralPath $targetManifest) {
        Assert-Sha256 $targetManifest $pin.manifest_sha256 "$Model target manifest"
    } else {
        $partialManifest = $targetManifest + '.copy.' + [guid]::NewGuid().ToString('N')
        try {
            Copy-Item -LiteralPath $sourceManifest -Destination $partialManifest
            Assert-Sha256 $partialManifest $pin.manifest_sha256 "$Model copied manifest"
            Move-Item -LiteralPath $partialManifest -Destination $targetManifest
        } finally {
            if (Test-Path -LiteralPath $partialManifest) { Remove-Item -LiteralPath $partialManifest -Force }
        }
    }
    Write-Host "Verified isolated $Model model without network download."
}

function Prepare-PinnedOllama {
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
    $archive = Join-Path $downloadRoot $ollamaArchiveName
    if (-not (Test-Path -LiteralPath $archive)) {
        if (-not $DownloadOllama) {
            throw "Pinned Ollama archive is missing. Re-run with -DownloadOllama to fetch the recorded official release asset."
        }
        $partialArchive = Join-Path $downloadRoot ($ollamaArchiveName + '.download.' + [guid]::NewGuid().ToString('N'))
        try {
            Invoke-WebRequest -Uri $ollamaArchiveUrl -OutFile $partialArchive
            Assert-Sha256 $partialArchive $ollamaArchiveSha256 'Downloaded Ollama release archive'
            Move-Item -LiteralPath $partialArchive -Destination $archive
        } finally {
            if (Test-Path -LiteralPath $partialArchive) { Remove-Item -LiteralPath $partialArchive -Force }
        }
    }
    Assert-Sha256 $archive $ollamaArchiveSha256 'Ollama release archive'

    $executable = Join-Path $runtimeTarget 'ollama.exe'
    if (-not (Test-Path -LiteralPath $executable)) {
        if (Test-Path -LiteralPath $runtimeTarget) {
            throw "Ollama target exists but is incomplete; preserve it for diagnosis: $runtimeTarget"
        }
        $staging = Join-Path $taskRoot ("ollama-0.32.15.extract." + [guid]::NewGuid().ToString('N'))
        $stagingFull = [IO.Path]::GetFullPath($staging)
        $taskFull = [IO.Path]::GetFullPath($taskRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        if (-not $stagingFull.StartsWith($taskFull, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Refusing a staging path outside the ignored HuLLCirq runtime directory.'
        }
        New-Item -ItemType Directory -Path $stagingFull | Out-Null
        try {
            Expand-Archive -LiteralPath $archive -DestinationPath $stagingFull
            $stagedExecutable = Get-ChildItem -LiteralPath $stagingFull -Filter 'ollama.exe' -File -Recurse | Select-Object -First 1
            if ($null -eq $stagedExecutable) { throw 'The verified Ollama archive contains no ollama.exe.' }
            $stagedRoot = $stagedExecutable.Directory.FullName
            Move-Item -LiteralPath $stagedRoot -Destination $runtimeTarget
        } finally {
            if (Test-Path -LiteralPath $stagingFull) { Remove-Item -LiteralPath $stagingFull -Recurse -Force }
        }
    }

    $previousHost = [Environment]::GetEnvironmentVariable('OLLAMA_HOST', 'Process')
    try {
        [Environment]::SetEnvironmentVariable('OLLAMA_HOST', '127.0.0.1:11435', 'Process')
        $versionText = (& $executable --version 2>&1) -join ' '
    } finally {
        [Environment]::SetEnvironmentVariable('OLLAMA_HOST', $previousHost, 'Process')
    }
    $versions = @([regex]::Matches($versionText, '\bversion(?: is|:)?\s+(\d+\.\d+\.\d+)\b') | ForEach-Object { $_.Groups[1].Value })
    if ($LASTEXITCODE -ne 0 -or $versions.Count -eq 0 -or @($versions | Where-Object { $_ -ne $ollamaVersion }).Count) {
        throw "Prepared Ollama does not report only version $ollamaVersion. Output: $versionText"
    }
    Write-Host "Verified isolated Ollama $ollamaVersion at $executable"
    return $executable
}

New-Item -ItemType Directory -Path $taskRoot -Force | Out-Null
if (-not $SkipModel) { Copy-PinnedModel }
$ollamaExecutable = Prepare-PinnedOllama

$configuration = [ordered]@{
    kind = 'local_ollama'
    version = $ollamaVersion
    executable = $ollamaExecutable
    model = $Model
    model_directory = $modelTarget
    endpoint = 'http://127.0.0.1:11435/v1'
}
$configurationPath = Join-Path $taskRoot 'local_runtime.json'
[IO.File]::WriteAllText($configurationPath, ($configuration | ConvertTo-Json -Depth 3), [Text.UTF8Encoding]::new($false))
Write-Output "Wrote local runtime configuration: $configurationPath"
