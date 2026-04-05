# Setup PowerShell - Agente Financeiro (Windows)
# Execute: powershell -ExecutionPolicy Bypass -File setup.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  AGENTE FINANCEIRO - Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
$pythonCheck = & python --version 2>&1 | Select-String "Python"
if (-not $pythonCheck) {
    Write-Host "✗ Python não encontrado!" -ForegroundColor Red
    Write-Host "Instale o Python 3.10+ de: https://www.python.org"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host "✓ $pythonCheck" -ForegroundColor Green

# Executar setup.py
Write-Host ""
Write-Host "Iniciando instalação..." -ForegroundColor Cyan
Write-Host ""

& python setup.py

Write-Host ""
Write-Host "Setup concluído!" -ForegroundColor Green
