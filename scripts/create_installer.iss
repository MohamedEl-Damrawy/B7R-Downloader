; Velo Downloader - Inno Setup script (prepared for approved packaging)
; Owner approval recorded: Setup + ZIP with Desktop and Start Menu shortcuts, and clean-machine test.
; Build performed with PyInstaller in this environment (pyside6-deploy/Nuitka blocked: no working C compiler toolchain).
; Requires: built standalone output at dist\VeloDownloader\ and Inno Setup 6 (ISCC.exe).
; IMPORTANT: Review bundled third-party license/compliance obligations (Qt/PySide6, FFmpeg GPLv3 build, yt-dlp) before distribution.
; NOTE (QUAL-05): keep MyAppVersion in sync with APP_VERSION in app/core/constants.py (single source of truth).

#define MyAppName "Velo Downloader"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Mohamed El-Damrawy (Individual)"
#define MyAppCopyright "Copyright (c) 2026 Mohamed El-Damrawy"
#define MyAppExeName "VeloDownloader.exe"
#define MyDistDir "..\dist\VeloDownloader"

[Setup]
AppId={{B7D4E7D1-9D4E-4B8E-9B2D-VELODOWNLOADER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright={#MyAppCopyright}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_release
OutputBaseFilename=VeloDownloader-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; FEAT-14: keep in sync with scripts/make_icon.py
SetupIconFile=..\resources\icons\app.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}\licenses_docs"; Flags: ignoreversion
Source: "..\licenses\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}\licenses_docs"; Flags: ignoreversion
Source: "..\licenses\third_party\*"; DestDir: "{app}\licenses_docs\third_party"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\resources\legal\*"; DestDir: "{app}\licenses_docs\legal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
