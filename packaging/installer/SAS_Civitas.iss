#define MyAppName "SAS Civitas"
#define MyAppExeName "SAS Civitas.exe"
#define MyAppVersion "1.2.0"
[Setup]
AppId={{E3E0F3E0-3D47-4B4E-A9B7-5C0D5E2B4D5A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\SAS Civitas\App
DefaultGroupName={#MyAppName}
OutputDir=..\..\artifacts\inno-output
OutputBaseFilename=SAS Civitas - Instalador
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
DisableDirPage=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\..\assets\icon.ico
WizardStyle=modern
[Tasks]
Name: "desktopicon"; Description: "Criar atalho no Desktop"; GroupDescription: "Atalhos:"; Flags: unchecked
[Files]
Source: "..\..\artifacts\pyinstaller-dist\SAS Civitas\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
