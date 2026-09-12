@echo off
title TERMINAL DO MONSTRO V22 - WDO MINI DÓLAR
color 0A
cls
echo.
echo ========================================
echo    🚀 MONSTRO V22 - MINI DÓLAR WDO 🚀
echo ========================================
echo.

REM Remove arquivo de parada anterior se existir
if exist parar.txt (
    del parar.txt
    echo ✅ Arquivo parar.txt removido - Sistema liberado para iniciar
) else (
    echo ℹ️ Arquivo parar.txt não encontrado - Sistema já liberado
)

echo 🔄 Reiniciando MetaTrader 5 (reset do coletor de dados - evita feed congelado do terminal "dormiu aberto")...
taskkill /f /im terminal64.exe >nul 2>&1
timeout /t 5 /nobreak >nul
REM Inicia o MetaTrader 5
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"

REM Aguarda MT5 inicializar
echo ⏳ Aguardando MT5 inicializar (15 segundos)...
timeout /t 15 /nobreak >nul

echo 🤖 Iniciando Monstro V22 (WDO)...
REM Inicia apenas o Monstro V22 em sua própria janela
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"

echo.
echo ✅ SISTEMAS INICIADOS:
echo    🟢 MetaTrader 5
echo    🟢 Monstro V22 (WDO)
echo.
echo 💡 Para parar: stop_all.bat
echo 📊 Dashboard: http://localhost:5001
echo.

REM Mantém a janela principal aberta
pause
