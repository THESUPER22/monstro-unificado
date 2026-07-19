@echo off
REM Execute como ADMINISTRADOR
echo Configurando tarefas para rodar como SYSTEM (sem senha)...

schtasks /change /tn "cleanup_monstro_final.bat" /ru "SYSTEM"
schtasks /change /tn "start_all.bat" /ru "SYSTEM"

echo.
echo Verificando resultado...
schtasks /query /tn "cleanup_monstro_final.bat" /fo LIST | find "Modo de Logon"
schtasks /query /tn "start_all.bat" /fo LIST | find "Modo de Logon"
echo.
pause
