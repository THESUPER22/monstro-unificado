@echo off
title MONSTRO - Dashboard P&L Tempo Real
color 0A
cd /d C:\AIOFEN

echo.
echo ===============================================
echo   🤖 MONSTRO DAS NEGOCIAÇÕES - DASHBOARD P&L  
echo ===============================================
echo.
echo 📊 Iniciando monitoramento de lucro em tempo real...
echo.

REM Instalar colorama se necessário
pip install colorama >nul 2>&1

REM Ativar ambiente virtual se existir
if exist venv310\Scripts\activate (
    call venv310\Scripts\activate
    echo ✅ Ambiente virtual ativado
) else (
    echo ⚠️  Ambiente virtual não encontrado - usando Python global
)

echo.
echo 🚀 Executando dashboard...
echo.
python dashboard_tempo_real.py

pause 