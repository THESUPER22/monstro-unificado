# ========================================
#    🤖 INICIANDO MONSTRO - POWERSHELL
# ========================================

Write-Host ""
Write-Host "🤖 INICIANDO MONSTRO DAS NEGOCIAÇÕES" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navega para o diretório do projeto
Set-Location "C:\AIOFEN"
Write-Host "📁 Diretório atual: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Verifica se o arquivo existe
if (Test-Path "monstro_unificado.py") {
    Write-Host "✅ Arquivo monstro_unificado.py encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ Arquivo monstro_unificado.py NÃO encontrado!" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host ""
Write-Host "🐍 Verificando Python..." -ForegroundColor Cyan
python --version

Write-Host ""
Write-Host "🚀 Iniciando o Monstro..." -ForegroundColor Green
Write-Host "   Para parar: Ctrl+C" -ForegroundColor Yellow
Write-Host "   Dashboard: http://127.0.0.1:5001" -ForegroundColor Magenta
Write-Host ""

# Executa o Monstro
try {
    python monstro_unificado.py
}
catch {
    Write-Host ""
    Write-Host "❌ Erro ao executar o Monstro: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "🏁 Monstro encerrado." -ForegroundColor Yellow
    Read-Host "Pressione Enter para fechar"
}
