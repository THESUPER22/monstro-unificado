# ========================================
#    🤖 CONFIGURADOR DO MONSTRO - POWERSHELL
# ========================================

Write-Host ""
Write-Host "🤖 CONFIGURANDO MONSTRO NO POWERSHELL" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Cria função para iniciar o Monstro
$MonstroFunction = @"
function Start-Monstro {
    Write-Host ""
    Write-Host "🤖 INICIANDO MONSTRO DAS NEGOCIAÇÕES" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""

    Set-Location "C:\AIOFEN"
    Write-Host "📁 Diretório: " -NoNewline -ForegroundColor Yellow
    Write-Host (Get-Location) -ForegroundColor White
    Write-Host ""

    if (Test-Path "monstro_unificado.py") {
        Write-Host "✅ Arquivo encontrado - Iniciando..." -ForegroundColor Green
        Write-Host ""
        python monstro_unificado.py
    } else {
        Write-Host "❌ Arquivo monstro_unificado.py não encontrado!" -ForegroundColor Red
    }
}

# Alias para facilitar
Set-Alias -Name "monstro" -Value "Start-Monstro"
Set-Alias -Name "robo" -Value "Start-Monstro"
"@

# Verifica se existe profile do PowerShell
$ProfilePath = $PROFILE
$ProfileDir = Split-Path $ProfilePath -Parent

Write-Host "📁 Profile do PowerShell: $ProfilePath" -ForegroundColor Yellow

# Cria diretório se não existir
if (!(Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
    Write-Host "✅ Diretório do profile criado" -ForegroundColor Green
}

# Adiciona ou atualiza o profile
if (Test-Path $ProfilePath) {
    $CurrentProfile = Get-Content $ProfilePath -Raw
    if ($CurrentProfile -notmatch "Start-Monstro") {
        Add-Content -Path $ProfilePath -Value "`n# === MONSTRO DAS NEGOCIAÇÕES ===`n$MonstroFunction`n"
        Write-Host "✅ Função adicionada ao profile existente" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Função já existe no profile" -ForegroundColor Yellow
    }
} else {
    Set-Content -Path $ProfilePath -Value "# === MONSTRO DAS NEGOCIAÇÕES ===`n$MonstroFunction"
    Write-Host "✅ Profile criado com sucesso" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 CONFIGURAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 COMANDOS DISPONÍVEIS:" -ForegroundColor Cyan
Write-Host "   monstro     - Inicia o robô" -ForegroundColor White
Write-Host "   robo        - Inicia o robô" -ForegroundColor White
Write-Host "   Start-Monstro - Inicia o robô" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANTE: Feche e abra o PowerShell para aplicar as mudanças!" -ForegroundColor Yellow
Write-Host ""
Write-Host "🚀 TESTE: Digite 'monstro' no PowerShell para iniciar!" -ForegroundColor Green
Write-Host ""

Read-Host "Pressione Enter para continuar"
