<#
.SYNOPSIS
    Test SCPC locally, optionally against installed native SolidCraft 0.30.1.
.EXAMPLE
    .\scripts\test.ps1
.EXAMPLE
    .\scripts\test.ps1 -Native
#>
[CmdletBinding()]
param([switch]$Native)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw 'Python is not on PATH. Activate your Conda/Python environment first.'
    }

    Write-Host 'SCPC Python API and fake-SolidCraft control protocol tests'
    & python -m unittest discover -s tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }

    # The native test is opt-in, because it requires the actual SolidCraft
    # CLI and intentionally evaluates a real CAD model.
    if ($Native) {
        if (-not (Get-Command solidcraft-cli -ErrorAction SilentlyContinue)) {
            throw 'solidcraft-cli was not found on PATH (tested version: 0.30.1).'
        }
        Write-Host 'SCPC actual SolidCraft 0.30.1 native smoke test'
        & python tests/native_smoke.py --output-dir output/native-smoke
        if ($LASTEXITCODE -ne 0) { throw 'Native SolidCraft tests failed.' }
        Write-Host 'Native output: output/native-smoke/'
    }
} finally {
    Pop-Location
}
