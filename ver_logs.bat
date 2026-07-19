@echo off
title MONITOR DE LOGS DO MONSTRO
cd /d C:\AIOFEN
call venv310\Scripts\activate
echo.
echo ========================================
echo    MONITOR DE LOGS DO MONSTRO
echo ========================================
echo.
echo [1] Monitorar logs em tempo real
echo [2] Ver ultimas 20 linhas
echo [3] Ver arquivo completo
echo.
set /p opcao="Escolha uma opcao (1-3): "

if "%opcao%"=="1" (
    echo.
    echo Iniciando monitoramento em tempo real...
    python monitorar_logs.py
) else if "%opcao%"=="2" (
    echo.
    echo Mostrando ultimas 20 linhas...
    python monitorar_logs.py tail
    pause
) else if "%opcao%"=="3" (
    echo.
    echo Abrindo arquivo completo...
    type monstro.log
    pause
) else (
    echo Opcao invalida!
    pause
)

cmd 