# Prepare the recorded generic synthesis runtime inside ignored workspace data.
# No system install; SKY130/LibreLane physical implementation remains separate.
param([string]$Distribution = 'Ubuntu', [switch]$DownloadSynthesizer)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskRoot = Join-Path $projectRoot '.work/m2b'
if ($taskRoot -notmatch '^([A-Za-z]):\\(.*)$') { throw 'Use a local drive path for WSL.' }
$linuxTaskRoot = '/mnt/' + $Matches[1].ToLowerInvariant() + '/' + ($Matches[2] -replace '\\', '/')
$osRelease = (& wsl.exe -d $Distribution --exec /bin/cat /etc/os-release 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Cannot inspect WSL distribution '$Distribution'." }
if ($osRelease -notmatch '(?m)^ID=ubuntu\r?$' -or $osRelease -notmatch '(?m)^VERSION_ID="?24\.04"?\r?$' -or $osRelease -notmatch '(?m)^VERSION_CODENAME=noble\r?$') {
    throw 'The pinned Yosys packages require the recorded Ubuntu 24.04 WSL distribution.'
}
$architecture = ((& wsl.exe -d $Distribution --exec /usr/bin/dpkg --print-architecture 2>&1) -join ' ').Trim()
if ($LASTEXITCODE -ne 0 -or $architecture -ne 'amd64') { throw 'The pinned Yosys packages require an amd64 WSL userspace.' }
$linuxProjectRoot = $linuxTaskRoot.Substring(0, $linuxTaskRoot.Length - '/.work/m2b'.Length)
& wsl.exe -d $Distribution --exec /usr/bin/test -d $linuxProjectRoot
if ($LASTEXITCODE -ne 0) { throw 'The checkout is not visible through the standard WSL /mnt/<drive> automount.' }
New-Item -ItemType Directory -Path $taskRoot -Force | Out-Null
$record = Get-Content -LiteralPath (Join-Path $projectRoot 'configs/runtime_m2b.json') -Raw | ConvertFrom-Json
foreach ($package in $record.synthesizer.packages) {
    $packagePath = Join-Path $taskRoot $package.filename
    if (-not (Test-Path -LiteralPath $packagePath)) {
        if (-not $DownloadSynthesizer) { throw 'Missing pinned package. Re-run with -DownloadSynthesizer.' }
        & wsl.exe -d $Distribution --cd $linuxTaskRoot --exec apt-get download ($package.name + '=' + $package.version)
        if ($LASTEXITCODE -ne 0) { throw 'Pinned package download failed.' }
    }
    if ((Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $package.sha256) { throw 'Pinned package checksum mismatch; refusing extraction.' }
    & wsl.exe -d $Distribution --exec dpkg-deb -x ($linuxTaskRoot + '/' + $package.filename) ($linuxTaskRoot + '/yosys')
    if ($LASTEXITCODE -ne 0) { throw 'Package extraction failed.' }
}
$configuration = @{
    kind = 'wsl'; distribution = $Distribution; executable = $linuxTaskRoot + '/yosys/usr/bin/yosys'
    working_directory = Join-Path $taskRoot 'synthesis'
    environment = @{ LD_LIBRARY_PATH = $linuxTaskRoot + '/yosys/usr/lib/x86_64-linux-gnu'; YOSYS_DATDIR = $linuxTaskRoot + '/yosys/usr/share/yosys' }
}
$version = & wsl.exe -d $Distribution --exec /usr/bin/env ('LD_LIBRARY_PATH=' + $configuration.environment.LD_LIBRARY_PATH) ('YOSYS_DATDIR=' + $configuration.environment.YOSYS_DATDIR) $configuration.executable -V
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne $record.synthesizer.version) { throw 'Yosys runtime version differs from the recorded version.' }
[IO.File]::WriteAllText((Join-Path $taskRoot 'synthesizer.json'), ($configuration | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
Write-Output 'Verified isolated generic Yosys runtime; no PDK mapping or physical verification is implied.'
