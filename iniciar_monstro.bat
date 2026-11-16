@echo off
title MONSTRO V22 - DASHBOARD WEB
cd /d C:\AIOFEN
echo Iniciando Monstro V22 (dashboard web em http://localhost:5001)...
REM Frente 1 / 23.50: robo sem janela CMD (Dashboard 5001 abre em janela propria)
wscript.exe "C:\AIOFEN\run_robot_hidden.vbs"
echo.
echo ✅ Monstro V22 iniciado.
echo 📊 Dashboard: http://localhost:5001
echo.
