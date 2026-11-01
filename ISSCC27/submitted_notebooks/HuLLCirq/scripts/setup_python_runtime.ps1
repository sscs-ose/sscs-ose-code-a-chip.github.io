# Prepare the pinned embeddable Python used by the dependency-free GUI service.
# The archive is kept under ignored .work data; no system installation is performed.
param([switch]$DownloadPython)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimeRoot = Join-Path $projectRoot '.work/runtime'
$downloadRoot = Join-Path $runtimeRoot 'downloads'
$version = '3.12.10'
$archiveName = "python-$version-embed-amd64.zip"
$archiveUrl = "https://www.python.org/ftp/python/$version/$archiveName"
$archiveSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$target = Join-Path $runtimeRoot "python-$version-embed-amd64"
$executable = Join-Path $target 'python.exe'

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Description) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Description is missing: $Path" }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "$Description checksum differs. Expected $Expected but found $actual. Existing files were not replaced."
    }
}

New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
$archive = Join-Path $downloadRoot $archiveName
if (-not (Test-Path -LiteralPath $archive)) {
    if (-not $DownloadPython) {
        throw 'Pinned Python archive is missing. Re-run with -DownloadPython to fetch the recorded official release asset.'
    }
    $partialArchive = Join-Path $downloadRoot ($archiveName + '.download.' + [guid]::NewGuid().ToString('N'))
    try {
        Invoke-WebRequest -Uri $archiveUrl -OutFile $partialArchive
        Assert-Sha256 $partialArchive $archiveSha256 'Downloaded Python release archive'
        Move-Item -LiteralPath $partialArchive -Destination $archive
    } finally {
        if (Test-Path -LiteralPath $partialArchive) { Remove-Item -LiteralPath $partialArchive -Force }
    }
}
Assert-Sha256 $archive $archiveSha256 'Python release archive'

if (-not (Test-Path -LiteralPath $executable)) {
    if (Test-Path -LiteralPath $target) {
        throw "Python target exists but is incomplete; preserve it for diagnosis: $target"
    }
    $staging = Join-Path $runtimeRoot ("python-$version.extract." + [guid]::NewGuid().ToString('N'))
    $stagingFull = [IO.Path]::GetFullPath($staging)
    $runtimeFull = [IO.Path]::GetFullPath($runtimeRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $stagingFull.StartsWith($runtimeFull, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing a staging path outside the ignored HuLLCirq runtime directory.'
    }
    New-Item -ItemType Directory -Path $stagingFull | Out-Null
    try {
        Expand-Archive -LiteralPath $archive -DestinationPath $stagingFull
        Move-Item -LiteralPath $stagingFull -Destination $target
    } finally {
        if (Test-Path -LiteralPath $stagingFull) { Remove-Item -LiteralPath $stagingFull -Recurse -Force }
    }
}

$reported = (& $executable --version 2>&1) -join ' '
if ($LASTEXITCODE -ne 0 -or $reported -notmatch ('\bPython\s+' + [regex]::Escape($version) + '\b')) {
    throw "Prepared Python does not report $version. Output: $reported"
}
$configuration = [ordered]@{
    kind = 'windows_embeddable_python'
    version = $version
    executable = $executable
    archive_sha256 = $archiveSha256
    system_install = $false
}
$configurationPath = Join-Path $runtimeRoot 'python_runtime.json'
[IO.File]::WriteAllText($configurationPath, ($configuration | ConvertTo-Json -Depth 3), [Text.UTF8Encoding]::new($false))
Write-Output "Verified isolated Python $version at $executable"
Write-Output "Wrote Python runtime configuration: $configurationPath"
