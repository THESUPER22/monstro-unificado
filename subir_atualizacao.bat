@echo off
chcp 65001 >nul
cd /d C:\AIOFEN

echo Subindo atualizacoes para o GitHub (robô NUNCA e afetado - so git)...

git add -A

git diff --cached --quiet
if %errorlevel%==0 (
    echo.
    echo Nada para subir - o repositorio ja esta atualizado.
    pause
    exit /b 0
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
git commit -m "atualizacao_%TS%"
if %errorlevel% neq 0 (
    echo.
    echo ERRO no commit. Verifique git config user.name / user.email.
    pause
    exit /b 1
)

git push origin main
if %errorlevel% neq 0 (
    echo.
    echo ERRO no push. Verifique conexao ou credenciais do GitHub.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  PRONTO! Codigo atualizado no GitHub.
echo ==========================================
pause
