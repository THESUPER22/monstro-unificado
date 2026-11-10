@echo off
REM ORB WDO - PAPER TRADE (forward test, READ-ONLY, sem order_send).
REM Chamado pela tarefa agendada "ORB-WDO-FT" (seg-sex 10:20).
cd /d C:\AIOFEN
"C:\AIOFEN\venv310\Scripts\python.exe" "C:\AIOFEN\rompimento_orb_wdo.py" %*
exit /b %ERRORLEVEL%
