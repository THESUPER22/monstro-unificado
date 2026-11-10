@echo off
REM Monitor de saude dos coletores do Monstro (read-only).
REM Chamado pela tarefa agendada "Monstro-Monitor-Coletores".
cd /d C:\AIOFEN
"C:\AIOFEN\venv310\Scripts\python.exe" "C:\AIOFEN\monitor_saude_coletores.py" %*
exit /b %ERRORLEVEL%
