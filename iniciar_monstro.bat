@echo off
title MONSTRO V22 - DASHBOARD WEB
cd /d C:\AIOFEN
echo Iniciando Monstro V22 (dashboard web em http://localhost:5001)...
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"
echo.
echo ✅ Monstro V22 iniciado.
echo 📊 Dashboard: http://localhost:5001
echo.
