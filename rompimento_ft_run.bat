@echo off
REM Rompimento da Primeira Hora - PAPER TRADE (forward test, READ-ONLY).
REM Chamado pela tarefa agendada "Rompimento-FT" (seg-sex 09:00).
cd /d C:\AIOFEN
"C:\AIOFEN\venv310\Scripts\python.exe" "C:\AIOFEN\rompimento_ft.py" %*
exit /b %ERRORLEVEL%
