@echo off
REM Robo WDO 100% oculto (Frente 1 / 23.50).
REM Chamado por run_robot_hidden.vbs; o console fica invisivel.
cd /d C:\AIOFEN
"C:\AIOFEN\venv310\Scripts\python.exe" "C:\AIOFEN\monstro_unificado_v22.py" >> "C:\AIOFEN\logs\monstro_console.log" 2>&1
