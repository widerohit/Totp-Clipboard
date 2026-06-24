$ErrorActionPreference = "Stop"

# Use unique build/dist temp directories
$guid = [guid]::NewGuid().Guid.Substring(0,8)
$buildDir = "build_$guid"
$distDir = "dist_temp_$guid"

Write-Host "==> Compiling Portable Python Executable..." -ForegroundColor Cyan

# Determine Python executable
$pythonCommand = "python"
$pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = "py"
    $pythonArgs = @("-3")
}
$pythonExe = & $pythonCommand @pythonArgs -c "import sys; print(sys.executable)"
$pythonHome = Split-Path $pythonExe -Parent
$tclRoot = Join-Path $pythonHome "tcl"
$dllRoot = Join-Path $pythonHome "DLLs"
$iconPath = ".\app.ico"

# Construct PyInstaller arguments
$pyInstallerArgs = @(
    "--onefile",
    "--windowed",
    "--name",
    "TOTP-Clipboard",
    "-y",
    "--additional-hooks-dir",
    ".\pyinstaller_hooks",
    "--collect-submodules",
    "tkinter",
    "--add-data",
    "$tclRoot\tcl8.6;_tcl_data",
    "--add-data",
    "$tclRoot\tk8.6;_tk_data",
    "--add-data",
    "$tclRoot\tcl8;_tcl_data\tcl8",
    "--add-binary",
    "$dllRoot\tcl86t.dll;.",
    "--add-binary",
    "$dllRoot\tk86t.dll;.",
    "--workpath",
    $buildDir,
    "--distpath",
    $distDir,
    "main.py"
)

if (Test-Path $iconPath) {
    $pyInstallerArgs = @("--icon", $iconPath) + $pyInstallerArgs
    $pyInstallerArgs += @("--add-data", "$iconPath;.")
}

& $pythonCommand @pythonArgs -m PyInstaller @pyInstallerArgs

if (-not (Test-Path ".\$distDir\TOTP-Clipboard.exe")) {
    throw "Build failed: Portable executable was not produced in temporary folder."
}

Write-Host "`n==> Locating Inno Setup compiler..." -ForegroundColor Cyan

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    $regPath = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
    if (Test-Path $regPath) {
        $installLoc = (Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue).InstallLocation
        if ($installLoc) {
            $candidate = Join-Path $installLoc "ISCC.exe"
            if (Test-Path $candidate) { $iscc = $candidate }
        }
    }
}
if (-not $iscc) {
    $onPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($onPath) { $iscc = $onPath.Source }
}
if (-not $iscc) {
    Write-Host "`nISCC.exe (Inno Setup Compiler) was not found." -ForegroundColor Red
    Write-Host "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php and re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "==> Compiling Permanent Installer..." -ForegroundColor Cyan

# Ensure final dist folder exists
if (-not (Test-Path "dist")) { New-Item -ItemType Directory -Force "dist" | Out-Null }

# Run Inno Setup and pass the temporary directory as ExeDir
& $iscc "/DExeDir=..\$distDir" ".\installer\TOTP-Clipboard-Setup.iss"

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

Write-Host "`n==> Cleaning up temporary build files..." -ForegroundColor Cyan
if (Test-Path $buildDir) { cmd.exe /c "rmdir /s /q $buildDir" }
if (Test-Path $distDir) { cmd.exe /c "rmdir /s /q $distDir" }

Write-Host "`nAll done! The installer is ready:" -ForegroundColor Green
Get-ChildItem ".\dist\*.exe" | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Green }
