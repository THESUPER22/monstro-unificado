@echo off
echo 🧹 LIMPANDO CACHE DO CURSOR (SEM MEXER NO MONSTRO)
echo.

REM Limpa cache do Python
echo Limpando __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Limpa logs antigos (mantém os últimos 3 dias)
echo Limpando logs antigos...
forfiles /m *.log /d -3 /c "cmd /c del @path" 2>nul

REM Limpa backups do modelo (mantém apenas o atual)
echo Limpando backups antigos do modelo...
del modelo_monstro.h5.backup* 2>nul
del modelo_monstro.h5.bak 2>nul

REM Limpa arquivos temporários
echo Limpando temporários...
del *.tmp 2>nul
del debug_*.json 2>nul

REM Reinicia serviços do Cursor
echo Parando processos do Cursor...
taskkill /f /im "Cursor.exe" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo ✅ Limpeza concluída! Pode reabrir o Cursor agora.
echo 📁 Arquivos do Monstro preservados intactos!
pause 