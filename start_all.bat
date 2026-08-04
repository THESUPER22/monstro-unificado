@echo off
title MONSTRO START (AUTONOMO)
cd /d C:\AIOFEN

REM Remove sinal de parada anterior
if exist parar.txt del /f /q parar.txt

REM Protecao anti-duplicidade: se o robo (python ou EXE) ja esta rodando, nao sobe outro
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -and $_.CommandLine -like '*monstro_unificado_v22*') -or ($_.Name -eq 'MonstroDashboard.exe') }; if ($p) { exit 1 } else { exit 0 }"
if %errorlevel% equ 1 (
    echo [AVISO] Monstro ja esta rodando - start cancelado para evitar duplicidade (2 robos = conflito de porta 5001 e ordens duplicadas).
    exit /b 0
)

REM Inicia o MetaTrader 5
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
timeout /t 10 /nobreak >nul

REM Inicia o Monstro V22 (WDO) em propria janela
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"
