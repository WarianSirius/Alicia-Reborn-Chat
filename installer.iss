#define MyAppName "Alicia Voice Chat"
#define MyAppVersion "1.2.0"
#define MyAppExeName "AliciaVoiceChat.exe"
[Setup]
AppId={{BCBFAAD4-1D8D-478E-8BE7-5C1423EA1E30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\AliciaVoiceChat
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=AliciaVoiceChat_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
[Files]
Source: "dist\AliciaVoiceChat\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Weitere Optionen:"; Flags: unchecked
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Alicia Voice Chat starten"; Flags: nowait postinstall skipifsilent
