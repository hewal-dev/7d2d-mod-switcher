; Inno-Setup-Skript für die Windows-Fassung des 7D2D Mod Switchers.
;
; Bauen (im Repo-Wurzelverzeichnis, nach dem PyInstaller-Lauf):
;   iscc packaging\win\installer.iss
; Ergebnis: dist\7D2D-Mod-Switcher-Setup-<Version>.exe
;
; Installation pro Benutzer (%LOCALAPPDATA%\Programs) — keine Administratorrechte
; nötig, passend dazu, dass die App unter Windows nur Junctions anlegt.
; Anlegen von Startmenü-Eintrag, optionalem Desktopsymbol und einem Eintrag
; unter „Apps & Features" zum Deinstallieren.

#define AppName "7D2D Mod Switcher"
#define AppVersion "1.2.1"
#define AppExe "7D2D-Mod-Switcher.exe"
#define AppPublisher "Hewal-dev"
#define AppUrl "https://github.com/hewal-dev/7d2d-mod-switcher"

[Setup]
SourceDir=..\..
AppId={{8E4F2C1A-5B7D-4A3E-9C2F-7D1B6A0E5C31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\7D2D Mod Switcher
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=dist
OutputBaseFilename=7D2D-Mod-Switcher-Setup-{#AppVersion}
SetupIconFile=assets\mod-switcher-logo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes
VersionInfoVersion=1.2.1.0
VersionInfoDescription=7D2D Mod Switcher Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Mod-Ordner von 7 Days to Die umschalten"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
