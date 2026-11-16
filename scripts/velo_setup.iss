; Inno Setup script for Velo Downloader (owner-approved packaging).
; Build: & "C:\Users\moham\AppData\Local\Programs\Inno Setup 7\ISCC.exe" scripts\velo_setup.iss
; NOTE: keep AppVersion in sync with APP_VERSION in app/core/constants.py.

#define MyAppName "Velo Downloader"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Mohamed El-Damrawy (Individual)"
#define MyAppURL "https://github.com/MohamedEl-Damrawy/B7R-Downloader"
#define MyAppExeName "VeloDownloader.exe"

[Setup]
AppId={{3C4298C0-D6E3-47A7-AD11-DDDB2F631F71}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist_release
OutputBaseFilename=VeloDownloader-0.1.0-setup
SetupIconFile=..\resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Everything from the PyInstaller onedir dist: VeloDownloader.exe + _internal\
; runtime + bundled resources (styles/fonts/i18n/icons), vendor ffmpeg + its
; README, LICENSE and licenses/.
Source: "..\dist\VeloDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Runtime data lives in LOCALAPPDATA (outside the install dir) and is kept
; on uninstall by design (user downloads/database/logs are not touched).
