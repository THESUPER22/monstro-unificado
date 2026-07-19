@echo off
title TERMINAL DO MONSTRO V2 - WIN MINI ÍNDICE
color 0A
cls
echo.
echo ========================================
echo    🚀 MONSTRO V2 - MINI ÍNDICE WIN 🚀
echo ========================================
echo.

REM Remove arquivo de parada anterior se existir
if exist parar.txt (
    del parar.txt
    echo ✅ Arquivo parar.txt removido - Sistema liberado para iniciar
) else (
    echo ℹ️ Arquivo parar.txt não encontrado - Sistema já liberado
)

echo 🔄 Iniciando MetaTrader 5...
REM Inicia o MetaTrader 5
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"

REM Aguarda MT5 inicializar
echo ⏳ Aguardando MT5 inicializar (10 segundos)...
timeout /t 10 /nobreak >nul

echo 🤖 Iniciando Monstro V2 (WIN)...
REM Inicia apenas o Monstro V2 em sua própria janela
start "Monstro V2 - WIN" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v2.py"

echo.
echo ✅ SISTEMAS INICIADOS:
echo    🟢 MetaTrader 5
echo    🟢 Monstro V2 (WIN)
echo.
echo 💡 Para parar: stop_all.bat
echo 📊 Dashboard: http://localhost:5002
echo.

REM Mantém a janela principal aberta
pause
