@echo off
title Monstro WIN v2 - Mini Indice
color 0A

echo.
echo ========================================
echo    MONSTRO WIN V2 - MINI INDICE
echo ========================================
echo.
echo 🎯 Configuracao: WIN (Mini Indice)
echo 📊 Volume: 5 contratos
echo 🛡️ SL: 90 pontos / TP: 35 pontos
echo 💰 Risk: -R$ 1000 diario
echo 📚 Filtro: 200cc+ (APRENDIZADO)
echo 🔗 Port: 5002 (Dashboard)
echo.

cd /d C:\AIOFEN

echo 🔄 Ativando ambiente Python...
call venv310\Scripts\activate

echo.
echo 📋 Verificando arquivos essenciais...
if not exist "config_win_v2.json" (
    echo ❌ ERRO: config_win_v2.json nao encontrado!
    pause
    exit /b 1
)

rem if not exist "EA_BookData_WIN.mq5" (
rem     echo ❌ ERRO: EA_BookData_WIN.mq5 nao encontrado!
rem     echo 📝 Certifique-se de que o EA WIN esta compilado no MT5
rem     pause
rem     exit /b 1
rem )

echo ✅ Arquivos OK
echo.

echo 🚀 Iniciando Monstro WIN v2...
echo 📡 Dashboard disponivel em: http://localhost:5002
echo 📊 Logs em: monstro_v2.log
echo.
echo ⚠️  IMPORTANTE: Certifique-se de que:
echo    1. MT5 esta aberto e logado
echo    2. EA_BookData_WIN esta ativo no grafico WIN
echo    3. Arquivo book_data_win.csv sendo gerado
echo    4. EA funcionara independente da tela ativa
echo.

python monstro_unificado_v2.py

echo.
echo 🔴 Monstro WIN v2 finalizado.
pause
