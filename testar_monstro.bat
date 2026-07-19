@echo off
echo ========================================
echo    TESTANDO MONSTRO CORRIGIDO
echo ========================================

cd /d C:\AIOFEN
call venv310\Scripts\activate

echo Iniciando teste do Monstro...
python monstro_unificado_v2.py

echo.
echo Teste finalizado. Pressione qualquer tecla...
pause
