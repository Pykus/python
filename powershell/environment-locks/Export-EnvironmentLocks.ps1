[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = ".\environment-locks",

    [Parameter(Mandatory = $false)]
    [string[]]$WingetPackageIds = @(
        "Git.Git",
        "Python.Python.3.12",
        "Microsoft.VisualStudioCode"
    ),

    [Parameter(Mandatory = $false)]
    [string]$PythonExecutable = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

Ensure-Directory -Path $OutputDirectory

# Export the Python environment if the requested interpreter is available.
try {
    & $PythonExecutable --version | Out-Null
    & $PythonExecutable -m pip freeze |
        Set-Content -LiteralPath (Join-Path $OutputDirectory "requirements.lock.txt") -Encoding UTF8
}
catch {
    Write-Warning "Python lock export skipped: $($_.Exception.Message)"
}

# Export WinGet metadata, then retain only explicitly allowed package IDs.
try {
    $temporaryExport = Join-Path $env:TEMP ("winget-export-{0}.json" -f [guid]::NewGuid().ToString("N"))

    winget export `
        --output $temporaryExport `
        --include-versions `
        --accept-source-agreements | Out-Null

    $export = Get-Content -LiteralPath $temporaryExport -Raw | ConvertFrom-Json

    foreach ($source in @($export.Sources)) {
        $source.Packages = @(
            $source.Packages | Where-Object {
                $WingetPackageIds -contains [string]$_.PackageIdentifier
            }
        )
    }

    $export.Sources = @(
        $export.Sources | Where-Object { @($_.Packages).Count -gt 0 }
    )

    $export | ConvertTo-Json -Depth 12 |
        Set-Content -LiteralPath (Join-Path $OutputDirectory "winget-packages.lock.json") -Encoding UTF8

    Remove-Item -LiteralPath $temporaryExport -Force -ErrorAction SilentlyContinue
}
catch {
    Write-Warning "WinGet lock export skipped: $($_.Exception.Message)"
}

Write-Host "Environment lock files written to: $OutputDirectory"
