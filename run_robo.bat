@echo off
echo Iniciando Robo Trader Monstro...
echo.

REM Verifica se o executável existe
if not exist "dist\monstro_unificado_v2_obf.exe" (
    echo ERRO: Executavel nao encontrado!
    echo Certifique-se de que o arquivo 'dist\monstro_unificado_v2_obf.exe' existe.
    pause
    exit /b 1
)

REM Executa o robô trader
echo Executando o robo trader...
cd dist
monstro_unificado_v2_obf.exe

REM Se chegou até aqui, o programa terminou
echo.
echo Robo trader finalizado.
pause

