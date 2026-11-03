$ErrorActionPreference = 'Stop'
# Optional wrapper for hosts that permit local PowerShell scripts.
# The documented direct Node entry point does not change execution policy.
& node (Join-Path $PSScriptRoot 'setup.mjs')
if ($LASTEXITCODE -ne 0) {
    throw "Comparator Atlas setup failed with exit $LASTEXITCODE"
}
