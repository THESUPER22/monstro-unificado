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

REM Verifica se o processo Python do Monstro ainda esta rodando
wmic process where "name='python.exe' and commandline like '%%monstro_unificado_v2%%'" get processid 2>nul | find /i "ProcessId" >nul
if %errorlevel% equ 0 (
    echo Processo ainda ativo, aguardando mais 20 segundos...
    timeout /t 20 /nobreak >nul
)

REM Mata o processo Python do Monstro especificamente
echo Encerrando processo Python do Monstro...
wmic process where "name='python.exe' and commandline like '%%monstro_unificado_v2%%'" delete >nul 2>&1

REM Fecha a janela CMD com titulo "Monstro V2 - WIN" (aberta pelo all.bat)
echo Fechando janela do Monstro...
taskkill /fi "windowtitle eq Monstro V2 - WIN" /f >nul 2>&1

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
echo.
pause
