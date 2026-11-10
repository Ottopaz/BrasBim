; SPDX-License-Identifier: GPL-3.0-or-later
; Instalador do BrasBim para Windows (spec/ui 49 §2), para o Inno Setup 6.
; Montado por instalador/construir.py, que passa a versão: ISCC /DVersao=0.0.1 brasbim.iss

#ifndef Versao
  #define Versao "0.0.0"
#endif
#define Raiz ".."

[Setup]
; Identificador fixo: instalar uma versão nova por cima atualiza
AppId={{6F1D3C2A-8B4E-4A7F-9C0D-B5A5B1B0A0BB}
AppName=BrasBim
AppVersion={#Versao}
AppVerName=BrasBim {#Versao}
AppPublisher=Contribuidores do BrasBim
AppPublisherURL=https://github.com/ootaviopaz/BrasBim
AppSupportURL=https://github.com/ootaviopaz/BrasBim/issues
DefaultDirName={localappdata}\Programs\BrasBim
DefaultGroupName=BrasBim
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#Raiz}\COPYING
SetupIconFile={#Raiz}\brasbim\ui\logo\brasbim.ico
UninstallDisplayIcon={app}\BrasBim.exe
UninstallDisplayName=BrasBim {#Versao}
OutputDir={#Raiz}\dist
OutputBaseFilename=BrasBim-{#Versao}-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "associar"; Description: "Abrir arquivos .ifc com o BrasBim"; GroupDescription: "Arquivos:"; Flags: unchecked

[Files]
Source: "{#Raiz}\dist\BrasBim\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Raiz}\COPYING"; DestDir: "{app}"; DestName: "COPYING.txt"; Flags: ignoreversion
Source: "{#Raiz}\COPYING.LESSER"; DestDir: "{app}"; DestName: "COPYING.LESSER.txt"; Flags: ignoreversion
Source: "{#Raiz}\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Raiz}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BrasBim"; Filename: "{app}\BrasBim.exe"
Name: "{group}\Desinstalar o BrasBim"; Filename: "{uninstallexe}"
Name: "{userdesktop}\BrasBim"; Filename: "{app}\BrasBim.exe"; Tasks: atalho

[Registry]
Root: HKCU; Subkey: "Software\Classes\.ifc\OpenWithProgids"; ValueType: string; ValueName: "BrasBim.ifc"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associar
Root: HKCU; Subkey: "Software\Classes\BrasBim.ifc"; ValueType: string; ValueName: ""; ValueData: "Projeto IFC"; Flags: uninsdeletekey; Tasks: associar
Root: HKCU; Subkey: "Software\Classes\BrasBim.ifc\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\BrasBim.exe,0"; Tasks: associar
Root: HKCU; Subkey: "Software\Classes\BrasBim.ifc\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\BrasBim.exe"" ""%1"""; Tasks: associar

[Run]
Filename: "{app}\BrasBim.exe"; Description: "Abrir o BrasBim agora"; Flags: nowait postinstall skipifsilent
