@echo off
echo ============================================================
echo     ROBO TRADER MONSTRO - BUILD EXECUTAVEL
echo ============================================================
echo.

rem Ativa ambiente virtual se existir
if exist "..\venv\Scripts\activate.bat" (
    echo Ativando ambiente virtual...
    call ..\venv\Scripts\activate.bat
) else if exist "..\venv310\Scripts\activate.bat" (
    echo Ativando ambiente virtual...
    call ..\venv310\Scripts\activate.bat
) else (
    echo Ambiente virtual nao encontrado, usando Python global...
)

echo.
echo Executando build do executavel...
python build_exe_final.py

echo.
echo ============================================================
echo Build finalizado! Verifique a pasta dist_final/
echo ============================================================
pause
