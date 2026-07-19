@echo off
title 🛡️ PROTEÇÃO DO MODELO MONSTRO
echo.
echo 🛡️ INICIANDO PROTEÇÃO DEFINITIVA DO MODELO MONSTRO
echo =====================================================
echo.
echo 🔒 Este sistema irá:
echo   - Monitorar o modelo a cada hora
echo   - Criar backups automáticos
echo   - Restaurar automaticamente se necessário
echo   - Manter múltiplas cópias de segurança
echo.
echo 📁 Backups serão salvos na pasta: modelo_protegido\
echo 📝 Logs em: protecao_modelo.log
echo.
pause

echo.
echo 🚀 Ativando ambiente virtual...
call venv310\Scripts\activate.bat

echo.
echo 🛡️ Iniciando sistema de proteção...
python proteger_modelo.py

echo.
echo 🛑 Sistema de proteção finalizado.
pause
