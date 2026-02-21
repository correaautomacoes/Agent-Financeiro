[Setup]
AppId={{2B3D4E5F-6G7H-8I9J-0K1L-M2N3O4P5Q6R7}
AppName=Agente Financeiro Inteligente
AppVersion=1.3
AppPublisher=Mateus Correa
DefaultDirName=C:\Agente Financeiro
DefaultGroupName=Agente Financeiro
DisableDirPage=no
OutputDir=.
OutputBaseFilename=Instalador_Agente_Financeiro
WizardStyle=modern

[Files]
Source: "c:\Users\Mateus Correa\Documents\Agent-Financeiro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "venv, .git, .env, __pycache__, .artifacts, .gemini, *.iss, *.pyc"

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\Agente Financeiro"; Filename: "{app}\run_app.bat"; IconFilename: "shell32.dll"; IconIndex: 174
; Atalho na Area de Trabalho (Forcado)
Name: "{userdesktop}\Agente Financeiro"; Filename: "{app}\run_app.bat"; IconFilename: "shell32.dll"; IconIndex: 174

[Run]
; Removi o 'nowait' para garantir que voce veja e complete a instalacao no terminal
Filename: "cmd.exe"; Parameters: "/c ""{app}\instalar_windows.bat"""; Description: "Configurar Agente Financeiro"; Flags: postinstall runascurrentuser
