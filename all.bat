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
start "" /min "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
echo Aguardando MT5 (10s)...
timeout /t 10 /nobreak >nul

cd /d C:\AIOFEN
REM Frente 1 / 23.50: robo sem janela CMD (Dashboard 5001 abre em janela propria)
wscript.exe "C:\AIOFEN\run_robot_hidden.vbs"

echo.
echo SISTEMAS INICIADOS:
echo   - MetaTrader 5 (minimizado)
echo   - Monstro V22 (WDO, console oculto)
echo   - Dashboard: http://localhost:5001
echo.
echo Para parar: stop_all.bat
echo.
