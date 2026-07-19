@echo off
title TESTE - ENCERRAMENTO SEGURO
color 0B
echo.
echo ========================================
echo    TESTE - ENCERRAMENTO SEGURO
echo ========================================
echo.
echo 🧪 Este script testa o encerramento seguro dos sistemas
echo.

REM Cria arquivo de sinal
echo 🚦 Criando sinal de encerramento...
echo SHUTDOWN > shutdown_signal.txt

echo ✅ Sinal criado! Os sistemas devem detectar e encerrar graciosamente.
echo.
echo 📋 O que deve acontecer:
echo    1. Sistemas detectam o sinal
echo    2. Fecham posições abertas
echo    3. Salvam modelos e experiências
echo    4. Criam backups de segurança
echo    5. Encerram graciosamente
echo.
echo ⏳ Aguarde até 45 segundos para encerramento completo...
echo.
pause
