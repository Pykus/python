# Environment lock exporter (PowerShell)

A small PowerShell utility for recording reproducible workstation/tooling state without exporting the entire machine configuration.

It creates two optional lock files:

- `requirements.lock.txt` from `python -m pip freeze`
- `winget-packages.lock.json` containing only an explicit allow-list of WinGet packages

The script deliberately filters the WinGet export instead of publishing a full workstation inventory. This keeps the output focused and reduces accidental disclosure of unrelated installed software.

## Requirements

- Windows 10/11 with PowerShell 5.1+ or PowerShell 7
- WinGet for the package lock
- Python + pip for the Python lock

Either exporter may fail independently; the other one will still be attempted.

## Usage

```powershell
.\Export-EnvironmentLocks.ps1
```

Choose an output directory:

```powershell
.\Export-EnvironmentLocks.ps1 -OutputDirectory .\locks
```

Select the WinGet packages that should be retained:

```powershell
.\Export-EnvironmentLocks.ps1 `
  -WingetPackageIds @(
    "Git.Git",
    "Python.Python.3.12",
    "Microsoft.VisualStudioCode"
  )
```

Use a specific Python interpreter or virtual environment:

```powershell
.\Export-EnvironmentLocks.ps1 `
  -PythonExecutable ".\.venv\Scripts\python.exe"
```

## Notes

- Review generated lock files before committing them to a public repository.
- `pip freeze` can contain package names that reveal project choices, so publish it only when that is intended.
- The script does not export credentials, environment variables, network configuration, host names, or secrets.
- The WinGet export is created in the temporary directory and removed after filtering.
