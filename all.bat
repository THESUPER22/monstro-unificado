@echo off
title MONSTRO V22 - WDO MINI DOLAR
color 0A
cls
echo ========================================
echo    MONSTRO V22 - MINI DOLAR WDO
echo ========================================
echo.

if exist parar.txt del parar.txt

echo Iniciando MetaTrader 5...
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
echo Aguardando MT5 (10s)...
timeout /t 10 /nobreak >nul

cd /d C:\AIOFEN
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"

echo.
echo SISTEMAS INICIADOS:
echo   - MetaTrader 5
echo   - Monstro V22 (WDO)
echo   - Dashboard: http://localhost:5001
echo.
echo Para parar: stop_all.bat
echo.
pause
