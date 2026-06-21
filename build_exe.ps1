$ErrorActionPreference = "Stop"

# Kill any running instance so dist files aren't locked
Get-Process TOTP-Clipboard -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

$pythonCommand = "python"
$pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = "py"
    $pythonArgs = @("-3")
}

# Determine Python executable path for PyInstaller data collection
$pythonExe = & $pythonCommand @pythonArgs -c "import sys; print(sys.executable)"
$pythonHome = Split-Path $pythonExe -Parent
$tclRoot = Join-Path $pythonHome "tcl"
$dllRoot = Join-Path $pythonHome "DLLs"

# Path to the app icon (place app.ico in the project root)
$iconPath = ".\app.ico"

# Use alternative build and distribution directories to avoid locked files
$buildDir = "build_temp"
$distDir = "dist_temp"

# Clean previous build/dist directories if they exist
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }

# Construct PyInstaller arguments
$pyInstallerArgs = @(
    "--onefile",
    "--windowed",
    "--name",
    "TOTP-Clipboard",
    "--clean",
    "-y",
    "--additional-hooks-dir",
    ".\\pyinstaller_hooks",
    "--collect-submodules",
    "tkinter",
    "--add-data",
    "$tclRoot\\tcl8.6;_tcl_data",
    "--add-data",
    "$tclRoot\\tk8.6;_tk_data",
    "--add-data",
    "$tclRoot\\tcl8;_tcl_data\\tcl8",
    "--add-binary",
    "$dllRoot\\tcl86t.dll;.",
    "--add-binary",
    "$dllRoot\\tk86t.dll;.",
    "--workpath",
    $buildDir,
    "--distpath",
    $distDir,
    "main.py"
)

# Only pass the icon flags if app.ico actually exists, so the build doesn't
# fail outright for anyone who hasn't added an icon yet.
if (Test-Path $iconPath) {
    $pyInstallerArgs = @("--icon", $iconPath) + $pyInstallerArgs
    # Bundle app.ico into the exe payload too, so ui.py can load it at runtime
    # for the title-bar/taskbar icon via resource_path("app.ico")
    $pyInstallerArgs += @("--add-data", "$iconPath;.")
} else {
    Write-Host "Note: app.ico not found in project root - building without a custom icon." -ForegroundColor Yellow
}

# Run PyInstaller with argument array
& $pythonCommand @pythonArgs -m PyInstaller @pyInstallerArgs

Write-Host "Build completed. Executable is in $distDir"
