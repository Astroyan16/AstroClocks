; Inno Setup script for AstroClocks v3.0.

#define MyAppName "AstroClocks"
#define MyAppVersion "3.0"
#define MyAppPublisher "Yannis Benazza"
#define MyAppExeName "AstroClocks-v3.0.exe"
#define MyAppSourceDir "output\AstroClocks-v3.0"

[Setup]
; Keep the AppId stable so v3.0 upgrades the same AstroClocks application.
AppId={{FB044594-264E-48D7-9B18-96531C01515F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AstroClocks
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=Install_AstroClocks3.0
SetupIconFile=AppIcon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
english.StartupTasks=Startup options
english.AutoStartTask=Launch AstroClocks when Windows starts
french.StartupTasks=Options de démarrage
french.AutoStartTask=Lancer AstroClocks au démarrage de Windows

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "{cm:AutoStartTask}"; GroupDescription: "{cm:StartupTasks}"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall shellexec skipifsilent
