@echo off
cd /d C:\AIOFEN
echo [%date% %time%] Backup automatico iniciado
git add -A
git diff --cached --quiet
if %errorlevel%==0 (
    echo [%date% %time%] Nada para subir - repositorio ja atualizado.
    exit /b 0
)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
git commit -m "backup_automatico_%TS%"
if %errorlevel% neq 0 (
    echo [%date% %time%] ERRO no commit.
    exit /b 1
)
git push origin main
if %errorlevel% neq 0 (
    echo [%date% %time%] ERRO no push.
    exit /b 1
)
echo [%date% %time%] PRONTO - backup enviado ao GitHub.
