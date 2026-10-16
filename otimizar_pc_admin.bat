@echo off
chcp 65001 >nul
title Otimizacao do PC - Robo Monstro v22

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissoes de administrador...
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo ==================================================
echo    OTIMIZACAO DO PC PARA O ROBO MONSTRO V22
echo ==================================================
echo.

set BK=C:\AIOFEN\backup_otimizacao_pc
if not exist "%BK%" mkdir "%BK%"
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set D=%%d%%c%%b
reg export "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" "%BK%\HKLM_Run_admin_%D%.reg" /y >nul 2>&1

echo [1/5] Ajustando plano de energia...
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg /setacvalueindex SCHEME_CURRENT SUB_DISK DISKIDLE 0
powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
powercfg /setactive SCHEME_CURRENT
echo    OK - CPU no maximo e disco sempre ligado
echo.

echo [2/5] Desativando itens de inicializacao do sistema...
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "Avast Cleanup UI" /f >nul 2>&1
reg delete "HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" /v "IncrediBuild Agent Monitor" /f >nul 2>&1
echo    OK
echo.

echo [3/5] Limpando arquivos temporarios...
del /q /f /s "%TEMP%\*" >nul 2>&1
del /q /f /s "C:\Windows\Temp\*" >nul 2>&1
echo    OK
echo.

echo [4/5] Aplicando efeitos visuais (modo desempenho)...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" /v VisualFXSetting /t REG_DWORD /d 2 /f >nul 2>&1
echo    OK
echo.

echo [5/5] Reiniciando o Explorer...
taskkill /f /im explorer.exe >nul 2>&1
start "" explorer.exe
echo    OK
echo.

echo ==================================================
echo   CONCLUIDO! Reinicie o PC para efeito total.
echo ==================================================
echo.
echo Proximo passo MANUAL (Avast):
echo   Menu do Avast ^> Configuracoes ^> Geral ^> Excecoes
echo   Adicione a pasta: C:\AIOFEN
echo   E a pasta do MetaTrader 5.
echo.
pause
