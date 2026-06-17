; keel.iss — Inno Setup script for the Keel desktop GUI (Windows).
;
; Wraps the PyInstaller onefile dist\Keel.exe in a proper installer:
;   * installs to Program Files (or per-user if non-admin),
;   * Start Menu shortcut (+ optional desktop shortcut),
;   * a real uninstaller (Add/Remove Programs entry).
;
; This does NOT code-sign anything — the "unknown publisher" SmartScreen
; warning persists until the .exe and this installer are signed with an
; Authenticode certificate. The installer's value here is UX, not trust.
;
; Build (run from the repo root, after `pyinstaller Keel.spec --noconfirm`):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\keel.iss
; Override the version from CI/CLI with:  ISCC /DMyAppVersion=0.1.0 installer\keel.iss
; Output: dist\KeelSetup-<version>.exe

#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"   ; keep in sync with keel.py __version__
#endif

#define MyAppName "Keel"
#define MyAppPublisher "Felipe Carvajal Brown"
#define MyAppURL "https://github.com/fcarvajalbrown/Keel"
#define MyAppExeName "Keel.exe"

[Setup]
; AppId uniquely identifies the app for upgrades/uninstall — DO NOT change it.
AppId={{78353783-BC5F-4340-B48D-802F4F065D49}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Keel hull mark for the installer .exe and the Add/Remove Programs entry.
SetupIconFile=..\assets\keel.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Allow per-user install when not running elevated, so no UAC prompt is forced.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; The installer ships the GUI app, so it shows the GUI license (PolyForm
; Noncommercial + the free-use grant). The engine remains AGPL (..\LICENSE);
; business use needs the commercial license (..\COMMERCIAL-LICENSE.md).
LicenseFile=..\LICENSE-NONCOMMERCIAL.md
OutputDir=..\dist
OutputBaseFilename=KeelSetup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
