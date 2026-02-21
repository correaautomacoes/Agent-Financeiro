$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = "$([Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop))\Agente Financeiro.lnk"
$Target = "$PSScriptRoot\run_app.bat"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"$Target`""
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.IconLocation = "shell32.dll, 174"
$Shortcut.Description = "Agente Financeiro Inteligente"
$Shortcut.Save()

Write-Host "Atalho criado na área de trabalho com sucesso!" -ForegroundColor Green
