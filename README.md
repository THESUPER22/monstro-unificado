# Monstro Unificado — WDO v22

Robô de trading automatizado para o **Mini Dólar (WDO)** na B3, operando via **MetaTrader 5**.
Rede neural Keras (22 features) + book nativo MT5 + trailing stop inteligente + integração DOL (Dólar Cheio).

## Arquivos — qual é qual

| Arquivo | Papel |
|---------|-------|
| **`monstro_unificado_v22.py`** | **PRODUÇÃO WDO** — é o robô que opera. **NÃO renomear** (referenciado por `iniciar_v22_wdo.bat`, `stop_all.bat` e pela própria rotina de encerramento). |
| `monstro_unificado_v2.py` | Legado WIN (Mini Índice) — pode rodar via `iniciar_monstro_win_v2.bat`. |
| `tests/testes_pos_fix.py` | Testes pós-fix (9 checagens, sem MT5). |
| `ROADMAP_WDO.md` | Histórico de sessões, decisões e checklist do robô WDO. |

## Requisitos

- Windows 10/11, Python **3.10**
- MetaTrader 5 em `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe`
- Git com Git Credential Manager (push sem senha)
- GitHub: repositório público `https://github.com/THESUPER22/monstro-unificado.git`

## Setup em um PC NOVO (checklist completo)

```cmd
git clone https://github.com/THESUPER22/monstro-unificado.git C:\AIOFEN
cd C:\AIOFEN
py -3.10 -m venv venv310
venv310\Scripts\activate
pip install -r requirements.txt
git config --global user.name "THESUPER22"
git config --global user.email "seu-email@exemplo.com"
```

Depois:
1. Primeiro `git push` vai pedir login do GitHub (Git Credential Manager grava e não pede mais).
2. Recriar a **tarefa agendada** (seção abaixo).
3. (Opcional) Recriar atalhos na área de trabalho.
4. Validar: `venv310\Scripts\python.exe tests\testes_pos_fix.py` → deve passar 9/9.

---

# AUTOMAÇÕES DO AMBIENTE

## 1) LIGAR o robô — `iniciar_v22_wdo.bat`

Sobe o MetaTrader 5, espera 10s e roda `python monstro_unificado_v22.py` na `venv310`.
Remove `parar.txt` antigo antes de iniciar (sistema liberado). Dashboard em `http://localhost:5001`.

```bat
@echo off
title TERMINAL DO MONSTRO V22 - WDO MINI DÓLAR
color 0A
cls
echo.
echo ========================================
echo    🚀 MONSTRO V22 - MINI DÓLAR WDO 🚀
echo ========================================
echo.

REM Remove arquivo de parada anterior se existir
if exist parar.txt (
    del parar.txt
    echo ✅ Arquivo parar.txt removido - Sistema liberado para iniciar
) else (
    echo ℹ️ Arquivo parar.txt não encontrado - Sistema já liberado
)

echo 🔄 Iniciando MetaTrader 5...
start "" "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"

REM Aguarda MT5 inicializar
echo ⏳ Aguardando MT5 inicializar (10 segundos)...
timeout /t 10 /nobreak >nul

echo 🤖 Iniciando Monstro V22 (WDO)...
start "Monstro V22 - WDO" cmd /k "cd /d C:\AIOFEN && call venv310\Scripts\activate && python monstro_unificado_v22.py"

echo.
echo ✅ SISTEMAS INICIADOS:
echo    🟢 MetaTrader 5
echo    🟢 Monstro V22 (WDO)
echo.
echo 💡 Para parar: stop_all.bat
echo 📊 Dashboard: http://localhost:5001
echo.

REM Mantém a janela principal aberta
pause
```

## 2) DESLIGAR o robô — `stop_all.bat`

Encerramento GRACIOSO: cria `parar.txt` (o robô fecha posições, salva modelo/experiências e faz flush de logs),
espera 45s, mata o processo cuja linha de comando contém `monstro_unificado_v22`, remove `parar.txt` e fecha o MT5.

```bat
@echo off
setlocal enabledelayedexpansion
title MONSTRO - ENCERRAMENTO GRACIOSO
color 0E
cls
echo.
echo ========================================
echo    MONSTRO - ENCERRAMENTO GRACIOSO
echo ========================================
echo.

cd /d C:\AIOFEN

REM Cria arquivo de sinalizacao para parada gracil
echo PARAR > parar.txt
echo [OK] Sinal de parada enviado ao Monstro...
echo.
echo Aguardando encerramento gracioso (45 segundos)...
timeout /t 45 /nobreak >nul

REM Verifica se o processo Python do Monstro ainda esta rodando
wmic process where "name='python.exe' and commandline like '%%monstro_unificado_v22%%'" get processid 2>nul | find /i "ProcessId" >nul
if %errorlevel% equ 0 (
    echo Processo ainda ativo, aguardando mais 20 segundos...
    timeout /t 20 /nobreak >nul
)

REM Mata o processo Python do Monstro especificamente
echo Encerrando processo Python do Monstro...
wmic process where "name='python.exe' and commandline like '%%monstro_unificado_v22%%'" delete >nul 2>&1

REM Fecha a janela CMD com titulo "Monstro V2 - WIN" (aberta pelo all.bat)
echo Fechando janela do Monstro...
taskkill /fi "windowtitle eq Monstro V2 - WIN" /f >nul 2>&1

REM Aguarda 3 segundos para garantir que fechou
timeout /t 3 /nobreak >nul

REM Remove o arquivo parar.txt
if exist parar.txt (
    del /f /q parar.txt
    echo [OK] parar.txt removido.
) else (
    echo [OK] parar.txt ja foi removido pelo robo.
)

REM Fecha o MetaTrader 5
echo Finalizando MetaTrader 5...
taskkill /f /im terminal64.exe >nul 2>&1

echo.
echo ========================================
echo    ENCERRAMENTO CONCLUIDO
echo ========================================
echo.
pause
```

## 3) SUBIR o código (backup GitHub)

- **Manual** — `subir_atualizacao.bat` (atalho na área de trabalho "Subir atualizacoes GitHub"): `git add -A` → commit → push, mostra o resultado.
- **Automático** — `subir_atualizacao_auto.bat` + `backup_auto.vbs` (sem janela, log em `backup_auto.log`), agendado **todos os dias 08:50**.

```bat
@echo off
chcp 65001 >nul
cd /d C:\AIOFEN

echo Subindo atualizacoes para o GitHub (robô NUNCA e afetado - so git)...

git add -A

git diff --cached --quiet
if %errorlevel%==0 (
    echo.
    echo Nada para subir - o repositorio ja esta atualizado.
    pause
    exit /b 0
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
git commit -m "atualizacao_%TS%"
if %errorlevel% neq 0 (
    echo.
    echo ERRO no commit. Verifique git config user.name / user.email.
    pause
    exit /b 1
)

git push origin main
if %errorlevel% neq 0 (
    echo.
    echo ERRO no push. Verifique conexao ou credenciais do GitHub.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  PRONTO! Codigo atualizado no GitHub.
echo ==========================================
pause
```

`subir_atualizacao_auto.bat` é igual ao manual **sem o `pause`** (para o agendador não travar) e com `backup_automatico_%TS%` como mensagem. `backup_auto.vbs`:

```vbs
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c ""C:\AIOFEN\subir_atualizacao_auto.bat"" >> ""C:\AIOFEN\backup_auto.log"" 2>&1", 0, False
```

## Tarefa agendada Windows (a recriar no PC novo)

| Item | Valor |
|------|-------|
| Nome | `Monstro Backup GitHub` |
| Gatilho | Diário, 08:50 |
| Ação | `wscript.exe C:\AIOFEN\backup_auto.vbs` |
| Opção | `/IT` (roda só com usuário logado; PC sempre na tomada) |

Comando de recriação:

```cmd
schtasks /Create /F /TN "Monstro Backup GitHub" /TR "wscript.exe C:\AIOFEN\backup_auto.vbs" /SC DAILY /ST 08:50 /IT
```

## PROMPT DE RECRIAÇÃO (cole em qualquer IA num PC novo)

> Reconfigure o robô de trading "Monstro Unificado" (Mini Dólar/WDO) neste PC a partir do repositório público https://github.com/THESUPER22/monstro-unificado.git
> 1) Clone para C:\AIOFEN. **Importante:** todos os scripts de automação já vêm no repositório (iniciar_v22_wdo.bat, stop_all.bat, subir_atualizacao.bat, subir_atualizacao_auto.bat, backup_auto.vbs). Não recrie nem renomeie `monstro_unificado_v22.py` — ele é o robô de produção e é referenciado por nome em stop_all.bat e na rotina de encerramento.
> 2) Crie o venv Python 3.10 em C:\AIOFEN\venv310 e instale requirements.txt.
> 3) Configure git config user.name/user.email e o Git Credential Manager (push sem senha).
> 4) Registre a tarefa agendada "Monstro Backup GitHub": diária 08:50, ação `wscript.exe C:\AIOFEN\backup_auto.vbs` (roda escondida, log em backup_auto.log). Comando: schtasks /Create /F /TN "Monstro Backup GitHub" /TR "wscript.exe C:\AIOFEN\backup_auto.vbs" /SC DAILY /ST 08:50 /IT
> 5) Crie atalhos na área de trabalho: iniciar_v22_wdo.bat (Ligar robô), stop_all.bat (Desligar robô), subir_atualizacao.bat (Subir código).
> 6) Valide com: venv310\Scripts\python.exe tests\testes_pos_fix.py (deve passar 9/9).

## Rotina de backup (proteção contra perda)

- **Regra:** sempre que editar código → clicar em "Subir atualizacoes GitHub". E a cópia da manhã (08:50) cobre o dia anterior automaticamente.
- Arquivos de dados (modelos `.keras`, CSVs, experiências, logs) ficam **fora** do git de propósito (`.gitignore`) — só código, config e docs são versionados.
- O repositório é **público**: nunca commitar senha/token/credencial.
