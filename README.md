# TOTP Clipboard

TOTP Clipboard is a lightweight offline Windows desktop utility for generating enterprise password values in this format:

```text
<BaseText><CurrentTOTP>
```

Example:

```text
TEST123456
```

It uses Python, Tkinter, PyOTP, and pystray. Profiles and secrets are stored only on the local machine.

## Features

- Multiple local profiles
- Add, edit, delete, and select active profile
- RFC6238 6-digit TOTP generation with 30-second intervals
- Base32 secret support
- One-click copy to the Windows clipboard
- Optional Auto Copy on Launch
- Live countdown timer
- Dark fixed-size Tkinter UI
- System tray menu: Open, Copy Current Value, Exit
- Import and export profiles as JSON
- Fully offline: no telemetry, analytics, cloud storage, external APIs, or internet access

## Project Structure

```text
totp-clipboard/
|-- installer/
|   `-- TOTP-Clipboard-Setup.iss
|-- main.py
|-- ui.py
|-- profile_manager.py
|-- otp_service.py
|-- tray.py
|-- build.ps1
|-- requirements.txt
|-- .gitignore
`-- README.md
```

## Profile Format

Profiles are securely stored in:

```text
%APPDATA%\TOTP Clipboard\profiles.dat
```

The data is encrypted at rest using Windows DPAPI. This keeps data safe across PyInstaller one-file app restarts. If an older plain text `profiles.json` exists beside the source files, beside the `.exe`, or in the AppData directory, the app migrates it into the new encrypted `.dat` format on first launch.



## Run From Source

Install Python 3.12 or newer, then run:

```bash
pip install -r requirements.txt
python main.py
```

## Build Windows EXE

Install dependencies:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

Create the executable:

```bash
pyinstaller --onefile --windowed --name TOTP-Clipboard main.py
```

For this project, simply run the included PowerShell script to compile everything into a permanent setup installer:

```powershell
.\build.ps1
```

Expected output:

```text
dist/
`-- TOTP-Clipboard-Setup-1.0.1.exe
```

## Installation

Once the setup executable is built, simply double-click the `TOTP-Clipboard-Setup-1.0.1.exe` in your `dist/` folder. It will guide you through installing the application permanently to your system and creating Start Menu or Desktop shortcuts.

## Import and Export

- Export writes profiles to a selected JSON file. The default filename is `profiles_export.json`.
- Import accepts either the exported object format or a plain array of profile objects.
- Imported profiles with matching names are updated. New names are added.

## Security Notes

- The application is offline only.
- It does not make network calls.
- It does not collect telemetry or analytics.
- It does not use cloud storage or external APIs.
- Secrets are encrypted using Windows DPAPI via `win32crypt` and stored in `%APPDATA%\TOTP Clipboard\profiles.dat`. They can only be decrypted by the Windows user account that encrypted them.

Protect exported profile files with normal OS file permissions and disk encryption where appropriate.
