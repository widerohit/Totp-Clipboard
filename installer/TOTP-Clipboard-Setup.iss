; ===========================================================================
; TOTP Clipboard - Inno Setup installer script
; ===========================================================================
; Builds a Windows installer that:
;   - Installs TOTP-Clipboard.exe to Program Files (or a user-chosen folder)
;   - Creates Start Menu + optional Desktop shortcuts
;   - Optionally launches the app on Windows startup (user opt-in)
;   - Registers a proper entry in "Add or Remove Programs" with an uninstaller
;   - On uninstall, optionally offers to remove saved profiles from %AppData%
;
; Requires: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
; Build with the Inno Setup Compiler (ISCC.exe), or open this file in the
; Inno Setup IDE and press Build (Ctrl+F9).
;
; Expects TOTP-Clipboard.exe to already be built (via build_exe.ps1) and
; present at ..\dist_temp\TOTP-Clipboard.exe relative to this script.
; ===========================================================================

#define MyAppName "TOTP Clipboard"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Rohit"
#define MyAppExeName "TOTP-Clipboard.exe"
#define MyAppURL ""

[Setup]
; A fixed GUID identifies this app across versions for clean upgrades/uninstalls.
; Generate your own once via Tools > Generate GUID in the Inno Setup IDE,
; or leave this one - it only needs to be unique to this application.
AppId={{B7B6B6D4-9B3E-4C3E-9B7E-2C6B1C6B7B6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Installs to Program Files by default; falls back per-user automatically
; if the user doesn't have admin rights, via the dropdown below.
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Allow non-admin "install for me only" as well as admin "install for all users"
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=.\Output
OutputBaseFilename=TOTP-Clipboard-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
#ifexist "..\app.ico"
SetupIconFile=..\app.ico
#endif
UninstallDisplayIcon={app}\{#MyAppExeName}
; Closes a running instance automatically before install/uninstall so files
; aren't locked (mirrors the same fix used in build_exe.ps1).
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Start {#MyAppName} automatically when Windows starts (minimized to tray)"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist_temp\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Bundle the icon alongside the exe too, in case anything outside the exe
; payload wants to reference it (shortcuts use it directly from the exe below).
Source: "..\app.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Removes any stray temp files the app may have written next to the exe.
; Does NOT touch %AppData%\TOTP Clipboard - that is handled with a prompt
; below so user profiles are never deleted silently.
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataPath := ExpandConstant('{userappdata}\TOTP Clipboard');
    if DirExists(AppDataPath) then
    begin
      if MsgBox('Do you also want to delete your saved TOTP profiles and secrets?' + #13#10 + #13#10 +
                AppDataPath + #13#10 + #13#10 +
                'Choose No to keep your profiles in case you reinstall later.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(AppDataPath, True, True, True);
      end;
    end;
  end;
end;
