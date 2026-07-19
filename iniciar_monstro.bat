@echo off
echo ========================================
echo    🤖 INICIANDO MONSTRO DAS NEGOCIACOES
echo ========================================
echo.

REM Navega para o diretório do projeto
echo 📁 Navegando para C:\AIOFEN...
cd /d C:\AIOFEN
echo    Diretório atual: %CD%
echo.

REM Verifica se o ambiente virtual existe
echo 🔍 Verificando ambiente virtual...
if not exist "venv310\Scripts\activate.bat" (
    echo ❌ ERRO: Arquivo venv310\Scripts\activate.bat não encontrado!
    echo    Diretório atual: %CD%
    echo    Verificando se existe venv310...
    if exist "venv310" (
        echo    ✅ Pasta venv310 existe
        dir venv310
    ) else (
        echo    ❌ Pasta venv310 não existe!
    )
    echo.
    echo    Pressione qualquer tecla para continuar mesmo assim...
    pause
    goto :skip_venv
)

echo ✅ Ambiente virtual encontrado!
echo 🔧 Ativando ambiente virtual Python 3.10...
call venv310\Scripts\activate
if errorlevel 1 (
    echo ❌ ERRO ao ativar ambiente virtual!
    pause
    goto :skip_venv
)

echo ✅ Ambiente virtual ativado!

:skip_venv
echo.
echo 🐍 Testando Python...
python --version
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo    Tentando usar python3...
    python3 --version
    if errorlevel 1 (
        echo ❌ ERRO: python3 também não encontrado!
        echo    Verifique se Python está instalado e no PATH
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

echo ✅ Python funcionando: %PYTHON_CMD%
echo.

REM Verifica se o arquivo do monstro existe
echo 📄 Verificando arquivo monstro_unificado.py...
if not exist "monstro_unificado.py" (
    echo ❌ ERRO: monstro_unificado.py não encontrado!
    echo    Arquivos Python disponíveis:
    dir *.py
    echo.
    pause
    exit /b 1
)

echo ✅ Arquivo monstro_unificado.py encontrado!
echo.

REM Inicia o MetaTrader 5 (se não estiver rodando)
echo 🚀 Verificando MetaTrader 5...
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if errorlevel 1 (
    echo 📈 MetaTrader 5 não está rodando. Tentando iniciar...
    if exist "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe" (
        start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
        echo ⏳ Aguardando MT5 inicializar (10 segundos)...
        timeout /t 10 /nobreak >nul
        echo ✅ MT5 deve estar iniciando...
    ) else (
        echo ⚠️ AVISO: MT5 não encontrado em C:\Program Files\MetaTrader 5 Terminal\
        echo    Verifique se está instalado no local correto
        echo    Continuando mesmo assim...
    )
) else (
    echo ✅ MetaTrader 5 já está rodando!
)

echo.
echo 🤖 Iniciando Monstro das Negociações...
echo ========================================
echo    Comando: %PYTHON_CMD% monstro_unificado.py
echo    Diretório: %CD%
echo    Pressione CTRL+C para parar o robô
echo ========================================
echo.

REM Inicia o robô Python
%PYTHON_CMD% monstro_unificado.py

REM Se chegou aqui, o robô parou
echo.
echo ========================================
echo    🔴 MONSTRO FINALIZADO
echo ========================================
echo    Código de saída: %ERRORLEVEL%
echo.

REM Sempre mantém o terminal aberto para debug
echo    Pressione qualquer tecla para fechar...
pause >nul
