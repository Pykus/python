<#
.SYNOPSIS
    Create a small, privacy-conscious snapshot of selected workstation tooling.

.DESCRIPTION
    This script records two kinds of reproducibility information:

    1. Python packages from a chosen interpreter / virtual environment.
    2. A deliberately allow-listed subset of WinGet packages.

    It can also:
    - write a machine-neutral manifest describing what was captured;
    - compare the new snapshot with an older baseline and report drift;
    - generate a restore helper that defaults to DRY-RUN mode.

    The goal is not to clone an entire Windows computer. The goal is to keep a
    small, reviewable record of the tools that matter for a project, lab,
    automation workstation, or development environment.

    Privacy is intentional: the script does NOT export host names, user names,
    environment variables, network configuration, registry data, credentials,
    browser profiles, or a complete installed-software inventory.

.EXAMPLE
    .\Export-EnvironmentLocks.ps1

    Capture the default Python environment and three example WinGet packages.

.EXAMPLE
    .\Export-EnvironmentLocks.ps1 `
        -OutputDirectory .\known-good `
        -PythonExecutable .\.venv\Scripts\python.exe `
        -GenerateRestoreScript

    Capture a project virtual environment and create a dry-run restore helper.

.EXAMPLE
    .\Export-EnvironmentLocks.ps1 `
        -OutputDirectory .\after-update `
        -BaselineDirectory .\known-good

    Capture the current state and generate drift-report.txt showing what changed
    compared with the earlier snapshot.

.EXAMPLE
    .\Export-EnvironmentLocks.ps1 `
        -SkipPython `
        -WingetPackageIds @("Git.Git", "Microsoft.PowerShell")

    Track only selected WinGet packages.
#>

[CmdletBinding()]
param(
    # Directory that will receive lock files, manifest.json and optional reports.
    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = ".\environment-locks",

    # Only these package IDs are retained from WinGet's temporary export.
    # Keeping an allow-list avoids publishing a full workstation inventory.
    [Parameter(Mandatory = $false)]
    [string[]]$WingetPackageIds = @(
        "Git.Git",
        "Python.Python.3.12",
        "Microsoft.VisualStudioCode"
    ),

    # Can be "python", "py", or a full path such as .\.venv\Scripts\python.exe.
    [Parameter(Mandatory = $false)]
    [string]$PythonExecutable = "python",

    # Optional previous snapshot. If supplied, drift-report.txt is produced.
    [Parameter(Mandatory = $false)]
    [string]$BaselineDirectory,

    # Creates Restore-Environment.ps1 in the output folder.
    # The generated helper only prints actions unless run with -Execute.
    [Parameter(Mandatory = $false)]
    [switch]$GenerateRestoreScript,

    # Useful if Python is not relevant to the workstation being documented.
    [Parameter(Mandatory = $false)]
    [switch]$SkipPython,

    # Useful on systems without WinGet or when only Python state matters.
    [Parameter(Mandatory = $false)]
    [switch]$SkipWinget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptVersion = "2.0"

function Ensure-Directory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-JsonFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object]$InputObject,

        [Parameter(Mandatory)]
        [string]$Path
    )

    $InputObject |
        ConvertTo-Json -Depth 12 |
        Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-WingetPackageMap {
    <#
        Converts a WinGet lock JSON file into a simple hash table:

            Package.Id -> Version

        A hash table makes later comparisons much easier to read than repeatedly
        walking through WinGet's nested Sources / Packages structure.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $result = @{}

    if (-not (Test-Path -LiteralPath $Path)) {
        return $result
    }

    $document = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json

    foreach ($source in @($document.Sources)) {
        foreach ($package in @($source.Packages)) {
            $id = [string]$package.PackageIdentifier
            if ([string]::IsNullOrWhiteSpace($id)) {
                continue
            }

            $version = ""
            if ($null -ne $package.Version) {
                $version = [string]$package.Version
            }

            $result[$id] = $version
        }
    }

    return $result
}

function Write-DriftReport {
    <#
        Compare the just-created snapshot with an older snapshot.

        This is useful after:
        - updating a workstation;
        - rebuilding a PC;
        - changing a Python virtual environment;
        - preparing several similar classroom / lab computers;
        - investigating why "it works on machine A but not machine B".
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$CurrentDirectory,

        [Parameter(Mandatory)]
        [string]$ReferenceDirectory
    )

    $report = @()
    $report += "Environment drift report"
    $report += "========================"
    $report += "Generated (UTC): $((Get-Date).ToUniversalTime().ToString('o'))"
    $report += ""

    # ----- Python comparison -------------------------------------------------
    $report += "PYTHON PACKAGES"
    $report += "---------------"

    $currentPythonPath = Join-Path $CurrentDirectory "requirements.lock.txt"
    $baselinePythonPath = Join-Path $ReferenceDirectory "requirements.lock.txt"

    if ((Test-Path -LiteralPath $currentPythonPath) -and
        (Test-Path -LiteralPath $baselinePythonPath)) {

        $currentPython = @(Get-Content -LiteralPath $currentPythonPath | Where-Object { $_.Trim() })
        $baselinePython = @(Get-Content -LiteralPath $baselinePythonPath | Where-Object { $_.Trim() })
        $pythonDiff = @(Compare-Object -ReferenceObject $baselinePython -DifferenceObject $currentPython)

        if ($pythonDiff.Count -eq 0) {
            $report += "No changes detected."
        }
        else {
            foreach ($item in $pythonDiff) {
                if ($item.SideIndicator -eq "=>") {
                    $report += "+ CURRENT:  $($item.InputObject)"
                }
                elseif ($item.SideIndicator -eq "<=") {
                    $report += "- BASELINE: $($item.InputObject)"
                }
            }
        }
    }
    else {
        $report += "Comparison skipped: requirements.lock.txt is missing from one of the snapshots."
    }

    $report += ""
    $report += "WINGET PACKAGES"
    $report += "---------------"

    # ----- WinGet comparison -------------------------------------------------
    $currentWingetPath = Join-Path $CurrentDirectory "winget-packages.lock.json"
    $baselineWingetPath = Join-Path $ReferenceDirectory "winget-packages.lock.json"

    if ((Test-Path -LiteralPath $currentWingetPath) -and
        (Test-Path -LiteralPath $baselineWingetPath)) {

        $currentMap = Get-WingetPackageMap -Path $currentWingetPath
        $baselineMap = Get-WingetPackageMap -Path $baselineWingetPath

        $ids = @(@($baselineMap.Keys) + @($currentMap.Keys)) | Sort-Object -Unique
        $wingetChanges = 0

        foreach ($id in $ids) {
            $inCurrent = $currentMap.ContainsKey($id)
            $inBaseline = $baselineMap.ContainsKey($id)

            if (-not $inBaseline -and $inCurrent) {
                $report += "+ ADDED:   $id $($currentMap[$id])"
                $wingetChanges++
                continue
            }

            if ($inBaseline -and -not $inCurrent) {
                $report += "- REMOVED: $id $($baselineMap[$id])"
                $wingetChanges++
                continue
            }

            if ($baselineMap[$id] -ne $currentMap[$id]) {
                $report += "~ CHANGED: $id  $($baselineMap[$id]) -> $($currentMap[$id])"
                $wingetChanges++
            }
        }

        if ($wingetChanges -eq 0) {
            $report += "No changes detected."
        }
    }
    else {
        $report += "Comparison skipped: winget-packages.lock.json is missing from one of the snapshots."
    }

    $reportPath = Join-Path $CurrentDirectory "drift-report.txt"
    $report | Set-Content -LiteralPath $reportPath -Encoding UTF8
    return $reportPath
}

function New-RestoreHelper {
    <#
        Generate a separate recovery helper next to the lock files.

        Important safety behaviour:
        - default invocation is DRY-RUN;
        - packages are installed only when the operator explicitly adds -Execute;
        - only packages already present in the allow-listed lock file are used.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Directory
    )

    $restorePath = Join-Path $Directory "Restore-Environment.ps1"

    $restoreScript = @'
<#
.SYNOPSIS
    Re-create tooling recorded by Export-EnvironmentLocks.ps1.

.DESCRIPTION
    By default this script is a DRY-RUN: it prints what it would do.
    Add -Execute only after reviewing the lock files and displayed commands.

.EXAMPLE
    .\Restore-Environment.ps1

    Preview restoration actions without changing the machine.

.EXAMPLE
    .\Restore-Environment.ps1 -Execute

    Install the recorded Python requirements and allow-listed WinGet packages.
#>

[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$PythonExecutable = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requirementsPath = Join-Path $PSScriptRoot "requirements.lock.txt"
$wingetPath = Join-Path $PSScriptRoot "winget-packages.lock.json"

Write-Host "Mode: $(if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' })"
Write-Host "Snapshot directory: $PSScriptRoot"
Write-Host ""

if (Test-Path -LiteralPath $requirementsPath) {
    Write-Host "[Python]"
    Write-Host "  $PythonExecutable -m pip install -r `"$requirementsPath`""

    if ($Execute) {
        & $PythonExecutable -m pip install -r $requirementsPath
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed with exit code $LASTEXITCODE"
        }
    }
}
else {
    Write-Host "[Python] No requirements.lock.txt found; skipping."
}

Write-Host ""

if (Test-Path -LiteralPath $wingetPath) {
    Write-Host "[WinGet]"
    $document = Get-Content -LiteralPath $wingetPath -Raw | ConvertFrom-Json

    foreach ($source in @($document.Sources)) {
        foreach ($package in @($source.Packages)) {
            $id = [string]$package.PackageIdentifier
            if ([string]::IsNullOrWhiteSpace($id)) {
                continue
            }

            $arguments = @(
                "install",
                "--id", $id,
                "--exact",
                "--accept-package-agreements",
                "--accept-source-agreements"
            )

            if ($null -ne $package.Version -and -not [string]::IsNullOrWhiteSpace([string]$package.Version)) {
                $arguments += @("--version", [string]$package.Version)
            }

            Write-Host ("  winget " + ($arguments -join " "))

            if ($Execute) {
                & winget @arguments
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "WinGet failed for package '$id' with exit code $LASTEXITCODE. Continuing with the next package."
                }
            }
        }
    }
}
else {
    Write-Host "[WinGet] No winget-packages.lock.json found; skipping."
}
'@

    $restoreScript | Set-Content -LiteralPath $restorePath -Encoding UTF8
    return $restorePath
}

# -----------------------------------------------------------------------------
# Main workflow
# -----------------------------------------------------------------------------

Ensure-Directory -Path $OutputDirectory

# The manifest intentionally contains only project/tooling metadata.
# It does not record machine identity or network information.
$manifest = [ordered]@{
    tool = "Export-EnvironmentLocks.ps1"
    toolVersion = $ScriptVersion
    createdAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Reproducible, privacy-conscious tooling snapshot"
    privacy = "No host name, user name, network configuration, credentials, environment variables, registry export, or full software inventory is recorded."
    python = [ordered]@{
        attempted = (-not $SkipPython.IsPresent)
        succeeded = $false
        executable = $PythonExecutable
        version = $null
        packageCount = 0
        output = $null
    }
    winget = [ordered]@{
        attempted = (-not $SkipWinget.IsPresent)
        succeeded = $false
        requestedPackageIds = @($WingetPackageIds)
        capturedPackageCount = 0
        output = $null
    }
}

# ----- Python snapshot --------------------------------------------------------
if (-not $SkipPython) {
    try {
        Write-Host "[1/4] Capturing Python package state..."

        $versionOutput = @(& $PythonExecutable --version 2>&1)
        if ($LASTEXITCODE -ne 0) {
            throw "'$PythonExecutable --version' failed with exit code $LASTEXITCODE."
        }

        $freezeOutput = @(& $PythonExecutable -m pip freeze 2>&1)
        if ($LASTEXITCODE -ne 0) {
            throw "'$PythonExecutable -m pip freeze' failed with exit code $LASTEXITCODE."
        }

        $requirementsPath = Join-Path $OutputDirectory "requirements.lock.txt"
        $freezeOutput | Set-Content -LiteralPath $requirementsPath -Encoding UTF8

        $manifest.python.succeeded = $true
        $manifest.python.version = ($versionOutput -join " ").Trim()
        $manifest.python.packageCount = @($freezeOutput | Where-Object { $_.Trim() }).Count
        $manifest.python.output = "requirements.lock.txt"

        Write-Host "      Saved $($manifest.python.packageCount) Python package entries."
    }
    catch {
        # Python failure is isolated: WinGet and all later stages still run.
        Write-Warning "Python snapshot skipped: $($_.Exception.Message)"
    }
}
else {
    Write-Host "[1/4] Python snapshot skipped by -SkipPython."
}

# ----- WinGet snapshot --------------------------------------------------------
if (-not $SkipWinget) {
    $temporaryExport = $null

    try {
        Write-Host "[2/4] Capturing allow-listed WinGet package state..."

        $temporaryExport = Join-Path $env:TEMP ("winget-export-{0}.json" -f [guid]::NewGuid().ToString("N"))

        & winget export `
            --output $temporaryExport `
            --include-versions `
            --accept-source-agreements | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "winget export failed with exit code $LASTEXITCODE."
        }

        $export = Get-Content -LiteralPath $temporaryExport -Raw | ConvertFrom-Json

        foreach ($source in @($export.Sources)) {
            # This is the privacy boundary: retain only explicitly requested IDs.
            $source.Packages = @(
                $source.Packages | Where-Object {
                    $WingetPackageIds -contains [string]$_.PackageIdentifier
                }
            )
        }

        # Remove empty sources to keep the resulting JSON compact and readable.
        $export.Sources = @(
            $export.Sources | Where-Object { @($_.Packages).Count -gt 0 }
        )

        $wingetPath = Join-Path $OutputDirectory "winget-packages.lock.json"
        Write-JsonFile -InputObject $export -Path $wingetPath

        $capturedCount = 0
        foreach ($source in @($export.Sources)) {
            $capturedCount += @($source.Packages).Count
        }

        $manifest.winget.succeeded = $true
        $manifest.winget.capturedPackageCount = $capturedCount
        $manifest.winget.output = "winget-packages.lock.json"

        Write-Host "      Saved $capturedCount allow-listed WinGet package entries."
    }
    catch {
        # WinGet failure is isolated: manifest, comparison and restore generation continue.
        Write-Warning "WinGet snapshot skipped: $($_.Exception.Message)"
    }
    finally {
        if ($temporaryExport -and (Test-Path -LiteralPath $temporaryExport)) {
            Remove-Item -LiteralPath $temporaryExport -Force -ErrorAction SilentlyContinue
        }
    }
}
else {
    Write-Host "[2/4] WinGet snapshot skipped by -SkipWinget."
}

# ----- Manifest ---------------------------------------------------------------
Write-Host "[3/4] Writing machine-neutral manifest..."
$manifestPath = Join-Path $OutputDirectory "manifest.json"
Write-JsonFile -InputObject $manifest -Path $manifestPath

# ----- Optional comparison and restore helper --------------------------------
Write-Host "[4/4] Running optional post-processing..."

if (-not [string]::IsNullOrWhiteSpace($BaselineDirectory)) {
    try {
        if (-not (Test-Path -LiteralPath $BaselineDirectory)) {
            throw "Baseline directory '$BaselineDirectory' does not exist."
        }

        $driftPath = Write-DriftReport `
            -CurrentDirectory $OutputDirectory `
            -ReferenceDirectory $BaselineDirectory

        Write-Host "      Drift report: $driftPath"
    }
    catch {
        Write-Warning "Baseline comparison skipped: $($_.Exception.Message)"
    }
}

if ($GenerateRestoreScript) {
    try {
        $restorePath = New-RestoreHelper -Directory $OutputDirectory
        Write-Host "      Restore helper: $restorePath"
        Write-Host "      It defaults to DRY-RUN; use -Execute only after review."
    }
    catch {
        Write-Warning "Restore helper generation failed: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Environment snapshot complete."
Write-Host "Output directory: $OutputDirectory"
Write-Host "Review the generated files before publishing or using them for restoration."
