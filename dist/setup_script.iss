; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!
; install command /silent /norestart /RESTARTEXITCODE=101 /ini="%INIFILE%
; TODO: Add Installer UI for selecting custom INI
; TODO: Add Installer UI for setting custom INI

;#define MySourceDir "D:\PY\WPKG-GP-Client\dist\"
;#define MyAppName "WPKG-GP Client"
;#define MyAppVersion "0.9.X"
;#define MyAppPublisher "Nils Thiele"
#define MyAppURL "https://github.com/sonicnkt/wpkg-gp-client"
#define MyAppExeName "WPKG-GP-Client.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{22866224-045A-46B6-B652-A7D7194D553A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
UninstallDisplayName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MySourceDir}
OutputBaseFilename={#MyOutput}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
CloseApplications=no
UninstallDisplayIcon={app}\WPKG-GP-Client.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[INI]
;Filename: "{app}\wpkg-gp_client.ini"; Section: "General"; Key: "check last update"; String: "False"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "General"; Key: "last update interval"; String: "14"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "General"; Key: "allow quit"; String: "True"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "General"; Key: "check boot log"; String: "False"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "General"; Key: "check vpn"; String: "False"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "Update Check"; Key: "start up"; String: "False"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "Update Check"; Key: "interval"; String: "0"
;Filename: "{app}\wpkg-gp_client.ini"; Section: "Update Check"; Key: "update url"; String: "https://YOUR_WEB.SERVER/packages.xml"

[Files]
Source: "{#MySourceDir}\WPKG-GP-Client\WPKG-GP-Client.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace
Source: "{#MySourceDir}\WPKG-GP-Client\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
;Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: "HKLM64"; Subkey: "Software\Wpkg-Gp-Client"; Flags: createvalueifdoesntexist uninsdeletekey; Permissions: users-full; Check: IsWin64
Root: "HKLM"; Subkey: "Software\Wpkg-Gp-Client"; Flags: createvalueifdoesntexist uninsdeletekey; Permissions: users-full; Check: not IsWin64
Root: "HKLM64"; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: expandsz; ValueName: "WPKG-GP Client"; ValueData: "{app}\WPKG-GP-Client.exe"; Flags: uninsdeletevalue; Check: IsWin64
Root: "HKLM"; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: expandsz; ValueName: "WPKG-GP Client"; ValueData: "{app}\WPKG-GP-Client.exe"; Flags: uninsdeletevalue; Check: not IsWin64

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if FileExists(ExpandConstant('{param:ini|None}')) then begin
      // delete installed ini file first
      DeleteFile(ExpandConstant('{app}\wpkg-gp_client.ini'));
      // copy supplied ini file
      FileCopy(ExpandConstant('{param:ini|None}'),ExpandConstant('{app}\wpkg-gp_client.ini'),True);
      // MsgBox('Custom ini installed: ' + ExpandConstant('{param:ini|None}'), mbInformation, MB_OK);
    end;
    // if no default ini exists copy the example ini to the default
    if not FileExists(ExpandConstant('{app}\wpkg-gp_client.ini')) then begin
      //MsgBox('No default ini supplied', mbInformation, MB_OK);
      //copy example ini to default ini
      FileCopy(ExpandConstant('{app}\wpkg-gp_client_example.ini'),ExpandConstant('{app}\wpkg-gp_client.ini'),True)
    end;
  end;
end;
