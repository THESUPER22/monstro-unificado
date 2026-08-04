@echo off
setlocal enabledelayedexpansion
title MONSTRO - ENCERRAMENTO GRACIOSO
color 0E
cls
echo.
echo ========================================
echo    MONSTRO - ENCERRAMENTO GRACIOSO
echo ========================================
echo.

cd /d C:\AIOFEN

REM Cria arquivo de sinalizacao para parada gracil
echo PARAR > parar.txt
echo [OK] Sinal de parada enviado ao Monstro...
echo.
echo Aguardando encerramento gracioso (45 segundos)...
timeout /t 45 /nobreak >nul

REM Mata o processo Python do Monstro especificamente (PowerShell/CIM - compativel com Win10/11)
echo Encerrando processo Python do Monstro...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*monstro_unificado_v22*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM Mata o EXE do Monstro se estiver rodando (dashboards manuais)
echo Encerrando MonstroDashboard.exe se ativo...
powershell -NoProfile -Command "Get-Process MonstroDashboard -ErrorAction SilentlyContinue | Stop-Process -Force"

REM Fecha a janela CMD do Monstro (titulo atual: Monstro V22 - WDO)
echo Fechando janela do Monstro...
taskkill /fi "windowtitle eq Monstro V22 - WDO" /f >nul 2>&1
taskkill /fi "windowtitle eq MONSTRO START (AUTONOMO)" /f >nul 2>&1

REM Aguarda 3 segundos para garantir que fechou
timeout /t 3 /nobreak >nul

REM Remove o arquivo parar.txt
if exist parar.txt (
    del /f /q parar.txt
    echo [OK] parar.txt removido.
) else (
    echo [OK] parar.txt ja foi removido pelo robo.
)

REM Fecha o MetaTrader 5
echo Finalizando MetaTrader 5...
taskkill /f /im terminal64.exe >nul 2>&1

echo.
echo ========================================
echo    ENCERRAMENTO CONCLUIDO
echo ========================================
timeout /t 3 /nobreak >nul
