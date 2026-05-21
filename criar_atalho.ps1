$ErrorActionPreference = "Stop"

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$shortcutPath = Join-Path $desktop "Agente Financeiro.lnk"
$target = Join-Path $PSScriptRoot "run_app.bat"

if (-not (Test-Path $target)) {
    throw "Nao encontrei o arquivo de inicializacao: $target"
}

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:ComSpec"
$shortcut.Arguments = "/k `"$target`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "shell32.dll, 174"
$shortcut.Description = "Iniciar Agente Financeiro"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Atalho criado na Area de Trabalho: $shortcutPath" -ForegroundColor Green
