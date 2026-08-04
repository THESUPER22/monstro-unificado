@echo off
title MONSTRO START (AUTONOMO)
cd /d C:\AIOFEN

REM Remove sinal de parada anterior
if exist parar.txt del /f /q parar.txt

REM Inicia o MetaTrader 5
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
timeout /t 10 /nobreak >nul

REM Inicia o Monstro V22 (WDO) em propria janela
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"
