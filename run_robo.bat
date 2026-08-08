@echo off
echo Iniciando Robo Trader Monstro (v22 - sniper %%R)...
echo.

cd /d C:\AIOFEN
if exist parar.txt del parar.txt

REM Executa o robo trader v22
echo Executando o robo trader...
call venv310\Scripts\activate
python monstro_unificado_v22.py

REM Se chegou até aqui, o programa terminou
echo.
echo Robo trader finalizado.
pause
