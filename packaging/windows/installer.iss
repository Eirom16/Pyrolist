[Setup]
AppName=Pyrolist
AppVersion=VERSION_PLACEHOLDER
SourceDir=..\..
AppPublisher=Eirom16
AppPublisherURL=https://github.com/Eirom16/pyrolist
AppSupportURL=https://github.com/Eirom16/pyrolist/issues
AppUpdatesURL=https://github.com/Eirom16/pyrolist/releases
DefaultDirName={autopf}\Pyrolist
DefaultGroupName=Pyrolist
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist\installer
OutputBaseFilename=Pyrolist-VERSION_PLACEHOLDER-Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Crear acceso directo en el menú inicio"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Pyrolist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Pyrolist"; Filename: "{app}\Pyrolist.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\Desinstalar Pyrolist"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Pyrolist"; Filename: "{app}\Pyrolist.exe"; Tasks: desktopicon
Name: "{userstartmenu}\Pyrolist"; Filename: "{app}\Pyrolist.exe"; Tasks: startmenuicon

[Run]
Filename: "{app}\Pyrolist.exe"; Description: "{cm:LaunchProgram,Pyrolist}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Pyrolist"
