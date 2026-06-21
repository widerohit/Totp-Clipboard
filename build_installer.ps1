# build_installer.ps1
# Builds TOTP-Clipboard.exe (via build_exe.ps1) and then compiles the
# Windows installer (via Inno Setup) in one step.
#
# Requirements:
#   - Inno Setup 6.x installed (https://jrsoftware.org/isinfo.php)
#   - build_exe.ps1 and the installer\ folder present alongside this script
#
# Output: installer\Output\TOTP-Clipboard-Setup-<version>.exe

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Step 1: Build the exe (reuses the existing build_exe.ps1 pipeline)
# ---------------------------------------------------------------------------
Write-Host "==> Building TOTP-Clipboard.exe ..." -ForegroundColor Cyan
& .\build_exe.ps1

if (-not (Test-Path ".\dist_temp\TOTP-Clipboard.exe")) {
    throw "Build failed: dist_temp\TOTP-Clipboard.exe was not produced."
}

# ---------------------------------------------------------------------------
# Step 2: Locate the Inno Setup compiler (ISCC.exe)
# ---------------------------------------------------------------------------
$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    # Last resort: search the registry for Inno Setup's install location
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
    # Fall back to PATH, in case the user added Inno Setup to it
    $onPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($onPath) { $iscc = $onPath.Source }
}

if (-not $iscc) {
    Write-Host ""
    Write-Host "ISCC.exe (Inno Setup Compiler) was not found." -ForegroundColor Red
    Write-Host "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php and re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "==> Using Inno Setup compiler: $iscc" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Step 3: Compile the installer
# ---------------------------------------------------------------------------
Write-Host "==> Compiling installer ..." -ForegroundColor Cyan
& $iscc ".\installer\TOTP-Clipboard-Setup.iss"

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Installer built successfully:" -ForegroundColor Green
Get-ChildItem ".\installer\Output\*.exe" | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Green }
