; ChatList — инсталлятор (Inno Setup 6)
; Версия подставляется из version.py через installer\version.iss при сборке.

#include "version.iss"

#define MyAppName "ChatList"
#define MyAppExeName "ChatList.exe"
#define MyAppPublisher "ChatList"
#define MyAppURL "https://github.com/chatlist"

[Setup]
AppId={{8F3C2A1B-4D5E-6F70-8910-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename={#MyAppName}-{#AppVersion}-setup
SetupIconFile=..\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#AppVersion}
CreateUninstallRegKey=yes
Uninstallable=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppName}-{#AppVersion}.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\chatlist.db"
Type: files; Name: "{app}\.env"
Type: files; Name: "{app}\.env.example"
Type: dirifempty; Name: "{app}"

[Code]
function InitializeUninstall(): Boolean;
var
  ErrorCode: Integer;
  Answer: Integer;
begin
  Exec('taskkill.exe', '/IM {#MyAppExeName} /F /T', '', SW_HIDE,
    ewWaitUntilTerminated, ErrorCode);

  Answer := MsgBox(
    'Удалить ChatList и пользовательские данные (база, логи, .env)?',
    mbConfirmation, MB_YESNO);

  Result := Answer = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    MsgBox('ChatList успешно удалён.', mbInformation, MB_OK);
end;
