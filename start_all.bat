@echo off
title MONSTRO START (AUTONOMO)
cd /d C:\AIOFEN

REM Remove sinal de parada anterior
if exist parar.txt del /f /q parar.txt

REM Protecao anti-duplicidade: robo vivo x ZUMBI (parado.ok mais novo que o processo).
REM Zumbi = encerrou (parado.ok) mas o processo nao saiu; mata e segue.
REM Vivo de verdade = aborta e registra hora/PID/comparacao em logs\start_all.log.
REM Codigos: 0=liberado | 10=vivo | 11=erro interno | 12=psutil ausente.
set "PY=C:\AIOFEN\venv310\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "C:\AIOFEN\start_guard.py"
set "RC=%errorlevel%"
if not "%RC%"=="0" (
    if "%RC%"=="10" echo [AVISO] Robo vivo de verdade - start cancelado para evitar duplicidade ^(2 robos = conflito de porta 5001 e ordens duplicadas^).
    if "%RC%"=="11" echo [ERRO] start_guard falhou ^(erro interno^) - start cancelado por seguranca.
    if "%RC%"=="12" echo [ERRO] psutil ausente no venv - start cancelado ^(sem como distinguir robo vivo de zumbi^).
    echo Detalhes em logs\start_all.log.
    REM [AGENTE 18/11] propaga o codigo do guard: o Agendador mostra falha.
    exit /b %RC%
)
REM Start liberado: o parado.ok do encerramento anterior nao vale mais.
del /f /q parado.ok >nul 2>&1

REM RESET MT5 ANTES DO PREGAO - evita o coletor de dados congelado do terminal que "dormiu aberto" a noite.
REM Bug 11/09/2026: 2553x tick estagnado + Faixa 1 S/TRADE com feed ~180 min velho. Reinicio limpo resolve.
taskkill /f /im terminal64.exe >nul 2>&1
timeout /t 5 /nobreak >nul
REM Inicia o MetaTrader 5 com sessao nova (minimizado; nao rouba a tela do Dashboard)
start "" /min "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
timeout /t 15 /nobreak >nul

REM Inicia o Monstro V22 (WDO) 100% oculto: sem janela CMD.
REM O Dashboard (porta 5001) abre na janela PyWebView do proprio robo.
wscript.exe "C:\AIOFEN\run_robot_hidden.vbs"
