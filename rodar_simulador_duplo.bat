@echo off
title ECOSSISTEMA DUPLO - MONSTRO DAS NEGOCIACOES (WDO + WIN)
color 0E

echo ========================================================
echo    INICIANDO ECOSSISTEMA DUPLO - MONSTRO DAS NEGOCIACOES
echo    WDO (v22, magic 7007) + WIN (v2, magic 2002)
echo    MODO: CONTA SIMULADOR / DEMO MT5
echo ========================================================
echo.

cd /d C:\AIOFEN

echo [0/3] Verificando MT5 aberto...
tasklist | find /i "terminal64.exe" >nul
if errorlevel 1 (
    echo   [!] MT5 NAO parece estar aberto. Abra e logue o MT5 em conta Simulador.
    echo       Pressione ENTER para tentar mesmo assim ou CTRL+C para cancelar.
    pause
)

echo [0/3] Validando unidade do simbolo WIN (GATE 6.2a)...
call venv310\Scripts\activate
python scripts\validar_simbolo_win.py
if errorlevel 1 (
    echo.
    echo   [ERRO] GATE 6.2a FALHOU: unidade WIN divergente. NAO subir o WIN.
    echo   Corrija config_win_v2.json (check tick_size / value por ponto).
    echo.
    set /p go="Deseja subir APENAS o WDO? [s/N]: "
    if /i not "%go%"=="s" exit /b 1
    echo   Subindo somente WDO...
    start "MONSTRO - WDO (v22)" cmd /k "cd /d C:\AIOFEN && venv310\Scripts\python.exe monstro_unificado_v22.py"
    exit /b 0
)

echo.
echo [1/3] IniciandoOperacao WDO (Unificado v22)...
echo       window: MONSTRO - WDO
start "MONSTRO - WDO (v22)" cmd /k "cd /d C:\AIOFEN && venv310\Scripts\python.exe monstro_unificado_v22.py"

echo.
timeout /t 5 /nobreak >nul

echo [2/3] IniciandoOperacao WIN (Indice v2 / Simulado)...
echo       window: MONSTRO - WIN
start "MONSTRO - WIN (v2)" cmd /k "cd /d C:\AIOFEN && venv310\Scripts\python.exe monstro_unificado_v2.py"

echo.
echo [3/3] Up ecossistema duplo iniciado.
echo ========================================================
echo   AMBOS OS ROBS RODANDO NA MESMA CONTA SIMULADOR MT5!
echo   WDO  : python monstro_unificado_v22.py  (magic 7007)
echo   WIN  : python monstro_unificado_v2.py   (magic 2002)
echo   Logs : monstro_wdo.log / monstro_v2.log
echo ========================================================
echo.

pause
