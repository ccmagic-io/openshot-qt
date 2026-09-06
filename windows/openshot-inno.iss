; -- Example1.iss --
; Demonstrates copying 3 files and creating an icon.

; SEE THE DOCUMENTATION FOR DETAILS ON CREATING .ISS SCRIPT FILES!

[Setup]
AppName=Openshot-CCMagic
AppVersion=v0.1
WizardStyle=modern dynamic
DefaultDirName={autopf}\Openshot-CCMagic
DefaultGroupName=Openshot-AI
UninstallDisplayIcon={app}\uninstall.exe
Compression=lzma2
SolidCompression=yes
OutputDir=userdocs:Inno Setup Examples Output
OutputBaseFilename=openshot_ccmagic_setup
AllowNoIcons=yes
SetupIconFile="C:\msys64\home\Edsel\openshot.github\openshot-qt\xdg\openshot-qt.ico


[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\msys64\home\Edsel\openshot.github\openshot-qt\build\exe.mingw_x86_64_msvcrt_gnu-3.14\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Openshot-CCMagic"; Filename: "{app}\launch.exe"
Name: "{autodesktop}\Openshot-CCMagic"; Filename: "{app}\launch.exe"; Tasks: desktopicon

