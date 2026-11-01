# Prepare ignored local dependencies. Does not install packages system-wide.
param(
    [string]$ModelSource = (Join-Path $env:USERPROFILE '.ollama/models'),
    [string]$Distribution = 'Ubuntu',
    [switch]$DownloadCompiler,
    [switch]$SkipModel
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskRoot = Join-Path $projectRoot '.work/m2'

function ConvertTo-TaskWSLPath([string]$WindowsPath) {
    $absolute = [IO.Path]::GetFullPath($WindowsPath)
    if ($absolute -notmatch '^([A-Za-z]):\\(.*)$') { throw 'Use a local drive path for the WSL compiler.' }
    return '/mnt/' + $Matches[1].ToLowerInvariant() + '/' + ($Matches[2] -replace '\\', '/')
}

function Assert-RecordedWSLHost {
    $osRelease = (& wsl.exe -d $Distribution --exec /bin/cat /etc/os-release 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect WSL distribution '$Distribution'." }
    if ($osRelease -notmatch '(?m)^ID=ubuntu\r?$' -or $osRelease -notmatch '(?m)^VERSION_ID="?24\.04"?\r?$' -or $osRelease -notmatch '(?m)^VERSION_CODENAME=noble\r?$') {
        throw 'The pinned Icarus package requires the recorded Ubuntu 24.04 WSL distribution.'
    }
    $architecture = ((& wsl.exe -d $Distribution --exec /usr/bin/dpkg --print-architecture 2>&1) -join ' ').Trim()
    if ($LASTEXITCODE -ne 0 -or $architecture -ne 'amd64') {
        throw 'The pinned Icarus package requires an amd64 WSL userspace.'
    }
    $linuxProjectRoot = ConvertTo-TaskWSLPath $projectRoot
    & wsl.exe -d $Distribution --exec /usr/bin/test -d $linuxProjectRoot
    if ($LASTEXITCODE -ne 0) { throw 'The checkout is not visible through the standard WSL /mnt/<drive> automount.' }
}

Assert-RecordedWSLHost
New-Item -ItemType Directory -Path $taskRoot -Force | Out-Null
if (-not $SkipModel) {
    $modelTarget = Join-Path $taskRoot 'ollama-models'
    $manifestRelative = 'manifests/registry.ollama.ai/library/qwen3/8b'
    $manifestSource = Join-Path $ModelSource $manifestRelative
    $expectedManifest = '500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'
    if ((Get-FileHash -LiteralPath $manifestSource -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedManifest) {
        throw 'qwen3:8b manifest differs from the recorded run. Preserve it and record a new model version.'
    }
    $manifest = Get-Content -LiteralPath $manifestSource -Raw | ConvertFrom-Json
    $records = @($manifest.config) + @($manifest.layers)
    foreach ($record in $records) {
        $digest = $record.digest -replace '^sha256:', ''
        if ($digest -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected model digest' }
        $relative = 'blobs/sha256-' + $digest
        $source = Join-Path $ModelSource $relative
        $target = Join-Path $modelTarget $relative
        if (-not (Test-Path -LiteralPath $target)) {
            $targetDirectory = Split-Path -Parent $target
            New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
            $partialTarget = Join-Path $targetDirectory ((Split-Path -Leaf $target) + '.copy.' + [guid]::NewGuid().ToString('N'))
            try {
                Copy-Item -LiteralPath $source -Destination $partialTarget
                if ((Get-FileHash -LiteralPath $partialTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) {
                    throw 'Copied model blob checksum mismatch. Original files were not changed.'
                }
                Move-Item -LiteralPath $partialTarget -Destination $target
            } finally {
                if (Test-Path -LiteralPath $partialTarget) { Remove-Item -LiteralPath $partialTarget -Force }
            }
        }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) {
            throw 'Model blob checksum mismatch. Original files were not changed.'
        }
    }
    $manifestTarget = Join-Path $modelTarget $manifestRelative
    New-Item -ItemType Directory -Path (Split-Path -Parent $manifestTarget) -Force | Out-Null
    if (Test-Path -LiteralPath $manifestTarget) {
        if ((Get-FileHash -LiteralPath $manifestTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedManifest) {
            throw 'Existing isolated manifest differs; refusing to replace it.'
        }
    } else {
        $partialManifest = $manifestTarget + '.copy.' + [guid]::NewGuid().ToString('N')
        try {
            Copy-Item -LiteralPath $manifestSource -Destination $partialManifest
            if ((Get-FileHash -LiteralPath $partialManifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedManifest) {
                throw 'Copied model manifest checksum mismatch. Original files were not changed.'
            }
            Move-Item -LiteralPath $partialManifest -Destination $manifestTarget
        } finally {
            if (Test-Path -LiteralPath $partialManifest) { Remove-Item -LiteralPath $partialManifest -Force }
        }
    }
}

$linuxTaskRoot = ConvertTo-TaskWSLPath $taskRoot
$packageName = 'iverilog_12.0-2build2_amd64.deb'
$packagePath = Join-Path $taskRoot $packageName
if (-not (Test-Path -LiteralPath $packagePath)) {
    if (-not $DownloadCompiler) { throw 'Compiler package missing. Re-run with -DownloadCompiler to fetch the pinned Ubuntu package.' }
    & wsl.exe -d $Distribution --cd $linuxTaskRoot --exec apt-get download 'iverilog=12.0-2build2'
    if ($LASTEXITCODE -ne 0) { throw 'Pinned compiler download failed; no system installation was performed.' }
}
if ((Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667') {
    throw 'Compiler package checksum differs from the recorded run.'
}
$linuxCompilerRoot = $linuxTaskRoot + '/iverilog'
& wsl.exe -d $Distribution --exec dpkg-deb -x ($linuxTaskRoot + '/' + $packageName) $linuxCompilerRoot
if ($LASTEXITCODE -ne 0) { throw 'Compiler extraction failed.' }
$compiler = @{
    kind = 'wsl'; distribution = $Distribution
    executable = $linuxCompilerRoot + '/usr/bin/iverilog'
    base_directory = $linuxCompilerRoot + '/usr/lib/x86_64-linux-gnu/ivl'
    working_directory = Join-Path $taskRoot 'syntax'
}
& wsl.exe -d $Distribution --exec $compiler.executable -B $compiler.base_directory -V
if ($LASTEXITCODE -ne 0) { throw 'Extracted compiler could not start.' }
$compiler | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'compiler.json') -Encoding utf8
if ($SkipModel) {
    Write-Output 'Verified isolated Icarus. Model preparation was skipped.'
} else {
    Write-Output 'Verified isolated model and Icarus. Start scripts/start_local_llm.ps1 in a separate terminal.'
}
