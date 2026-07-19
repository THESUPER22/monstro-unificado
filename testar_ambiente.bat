@echo off
echo ========================================
echo    🔧 TESTE DE AMBIENTE - DIAGNOSTICO
echo ========================================
echo.

echo 📁 Diretório atual:
echo    %CD%
echo.

echo 📂 Conteúdo da pasta:
dir /b *.py *.bat venv*
echo.

echo 🐍 Testando Python sem ambiente virtual:
python --version
echo    Código de saída Python: %ERRORLEVEL%
echo.

echo 🔍 Verificando ambiente virtual:
if exist "venv310\Scripts\activate.bat" (
    echo ✅ Arquivo activate.bat encontrado

    echo 🔧 Ativando ambiente virtual...
    call venv310\Scripts\activate

    echo 🐍 Testando Python no ambiente virtual:
    python --version
    echo    Código de saída: %ERRORLEVEL%

    echo 📦 Testando import do MetaTrader:
    python -c "import MetaTrader5 as mt5; print('✅ MT5 OK')"
    echo    Código de saída MT5: %ERRORLEVEL%

    echo 📦 Testando outros imports:
    python -c "import tensorflow as tf; print('✅ TensorFlow OK')"
    echo    Código de saída TF: %ERRORLEVEL%

) else (
    echo ❌ Arquivo activate.bat NÃO encontrado
    echo    Verificando estrutura venv310:
    if exist "venv310" (
        dir venv310
        echo.
        dir venv310\Scripts
    ) else (
        echo    Pasta venv310 não existe!
    )
)

echo.
echo ========================================
echo    🏁 DIAGNÓSTICO CONCLUÍDO
echo ========================================
pause
