$ErrorActionPreference = "Stop"

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

& $pythonCommand @pythonArgs -m PyInstaller `
    --onefile `
    --windowed `
    --name TOTP-Clipboard `
    --clean `
    -y `
    --additional-hooks-dir .\pyinstaller_hooks `
    --collect-submodules tkinter `
    --add-data "$tclRoot\tcl8.6;_tcl_data" `
    --add-data "$tclRoot\tk8.6;_tk_data" `
    --add-data "$tclRoot\tcl8;_tcl_data\tcl8" `
    --add-binary "$dllRoot\tcl86t.dll;." `
    --add-binary "$dllRoot\tk86t.dll;." `
    main.py
