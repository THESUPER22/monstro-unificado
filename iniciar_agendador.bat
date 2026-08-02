@echo off
cd /d C:\AIOFEN
if exist parar.txt del parar.txt
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
timeout /t 10 /nobreak >nul
start "" /d "C:\AIOFEN" "dist\MonstroDashboard\MonstroDashboard.exe"
