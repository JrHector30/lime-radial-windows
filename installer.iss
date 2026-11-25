; Script de Inno Setup para Lime Radial Windows
; Genera el instalador oficial LimeRadial-Setup.exe

#define MyAppName "Lime Radial"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Lime Radial Open Source"
#define MyAppURL "https://github.com/JrHector30/tangerine-windows"
#define MyAppExeName "LimeRadial.exe"

[Setup]
AppId={{9B7E34D8-6C7A-4D78-9B2F-9E7D8A1C4E2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\LimeRadial
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=LimeRadial-Setup
SetupIconFile=lime.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Iniciar Lime Radial automáticamente al encender Windows"; GroupDescription: "Configuración de inicio:"; Flags: checkedonce

[Files]
Source: "dist\LimeRadial\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\lime.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\lime.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LimeRadial"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Lime Radial ahora en segundo plano (barra de iconos)"; Flags: nowait postinstall skipifsilent
