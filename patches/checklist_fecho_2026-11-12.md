# Checklist de validação do fecho — 12/11/2026 (após 18:30)

**Objetivo:** aplicar C1–C4 na branch `robustez-fecho`, validar e, só se verde,
fazer merge na `main` para o pregão de sexta (13/11).
**Regra de ouro:** nada disso roda com pregão aberto ou posição real aberta.
**Não** iniciar `start_all.bat` (mataria o `terminal64`); se precisar reiniciar,
subir só o robô.

---

## 0. Pré-requisitos (18:05 → 18:30)

### 0.1 ORB paper fechou e gravou o CSV

```powershell
cd C:\AIOFEN
C:\AIOFEN\venv310\Scripts\python.exe rompimento_orb_wdo.py --resumo
Get-Content logs\rompimento_orb_wdo\state.json -Raw
Get-Content logs\rompimento_orb_wdo\trades_orb_wdo.csv -Tail 3
```

Esperado em 12/11:

- `state.json` com `"final": true` e a barra 17:55 (não o mark-to-market das 11h).
- 1 linha nova no CSV com `dia=2026-11-12`, `side=BUY`, `entry=5624.0`,
  `eff_manha=0.352`, `obs` contendo `BLOQUEIA4`.
- `--resumo` separando **liberados** (`eff >= 0.40`) e **bloqueados**.
- Nenhum processo do ORB depois de 18:20/18:30 (`TIME_STOP=18:30`).

### 0.2 Zero processos Python do robô/ORB

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Select-Object ProcessId, CreationDate, CommandLine | Format-List
```

- [ ] Nenhum processo com `monstro_unificado_v22.py`.
- [ ] Nenhum processo com `rompimento_orb_wdo.py`.
- [ ] Processos de editor/outras ferramentas podem ficar; **não matar às cegas**.

### 0.3 Flat de verdade (magics do robô)

Rodar o snapshot read-only abaixo (não abre, não fecha, não altera nada):

```python
# salvar como patches\snapshot_fecho.py e rodar:
# C:\AIOFEN\venv310\Scripts\python.exe patches\snapshot_fecho.py
import MetaTrader5 as mt5
from datetime import datetime, timedelta

MAGICS = {123456, 7008}   # Core + Faixa 1 (phantom 123457 fica de fora)
if not mt5.initialize():
    raise SystemExit("MT5 initialize falhou: %s" % (mt5.last_error(),))
try:
    pos = mt5.positions_get() or []
    print("posicoes abertas: %d" % len(pos))
    for p in pos:
        marca = "ROBO" if p.magic in MAGICS else "ignorada"
        print("  #%s %s %s vol=%s magic=%s [%s] lucro=%.2f"
              % (p.ticket, p.symbol, "BUY" if p.type == 0 else "SELL",
                 p.volume, p.magic, marca, p.profit))
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(hoje, datetime.now()) or []
    outs = [d for d in deals if d.magic in MAGICS and d.entry == mt5.DEAL_ENTRY_OUT]
    pnl = sum(d.profit + d.swap + d.commission for d in outs)
    print("deals OUT hoje (magics do robo): %d | PnL=R$ %.2f" % (len(outs), pnl))
finally:
    mt5.shutdown()
```

Critério: **`posicoes abertas` do robô = 0**. A posição fantasma `#2243200971`
WINV25 (magic 123457) é inerte e **não** entra no filtro; ignorar.

- [ ] `#2591384275` (Faixa 1, magic 7008) foi fechada pelo robô às 17:35.
- [ ] Se o fecho falhou com `10031`, usar o fechamento manual de fallback
      (como em 11/11) e registrar o deal/PnL no ROADMAP.
- [ ] **Não** seguir para a aplicação com posição do robô aberta.

### 0.4 Branch e arquivos limpos

```powershell
cd C:\AIOFEN
git status --short
git branch --show-current
git log --oneline -3
Test-Path patches\robustez_fecho_helpers.py
Test-Path tests\test_robustez_fecho.py
```

- [ ] Branch atual: `robustez-fecho` (criar/sincronizar com a `main` se preciso).
- [ ] `git status` limpo (ou só com os 3 materiais deste pacote já commitados).
- [ ] Helper e testes presentes.
- [ ] `main` e `robustez-fecho` no mesmo commit de partida.

---

## 1. Aplicação C1–C4 (18:30+)

### 1.1 Dry-run obrigatório

```powershell
C:\AIOFEN\venv310\Scripts\python.exe patches\aplicar_robustez_fecho.py
```

Conferir no plano:

- [ ] `monstro_unificado_v22.py`: diff de ~230 linhas; `agente_monstro_core.py`:
      ~50 linhas.
- [ ] O diff mostra **C3 antes do `break`** e **C2 substituindo o log
      incondicional** das 17:35.
- [ ] O diff mostra o import dos helpers e `MAGICS_ROBO` antes de
      `def fechar_todas_posicoes`.
- [ ] O diff do agente mostra `contar_trades_reais_hoje` e a linha
      `Trades fechados (deals MT5)`.
- [ ] `sintaxe do buffer: OK`.
- [ ] **Nada foi gravado** (dry-run).

### 1.2 Aplicar

```powershell
C:\AIOFEN\venv310\Scripts\python.exe patches\aplicar_robustez_fecho.py --apply
```

Esperado:

- backup em `patches\backups\<timestamp>\` com os 2 arquivos + `manifest.json`
  + `diff.patch`;
- `py_compile` OK nos dois arquivos;
- hashes `sha256` impressos.

- [ ] Backup criado e conferido (`manifest.json` com `sha256_antes`).
- [ ] `git diff --stat` mostra só os 2 arquivos esperados.
- [ ] Nenhum outro arquivo alterado.

### 1.3 Se algo falhar

```powershell
C:\AIOFEN\venv310\Scripts\python.exe patches\aplicar_robustez_fecho.py --reverter
```

- [ ] Reversão restaura os hashes `sha256_antes` do manifest.
- [ ] `py_compile` OK após reverter.

---

## 2. Testes offline (obrigatórios)

```powershell
cd C:\AIOFEN
C:\AIOFEN\venv310\Scripts\python.exe -m py_compile `
  patches\robustez_fecho_helpers.py tests\test_robustez_fecho.py `
  monstro_unificado_v22.py agente_monstro_core.py
C:\AIOFEN\venv310\Scripts\python.exe tests\test_robustez_fecho.py
C:\AIOFEN\venv310\Scripts\python.exe -m pytest tests\test_robustez_fecho.py -q
```

Critério de aceite:

- [ ] `py_compile` OK nos 4 arquivos.
- [ ] `tests/test_robustez_fecho.py` → **TODOS OS TESTES PASSARAM**.
- [ ] `pytest ... -q` → **12 passed**.
- [ ] Nenhum teste toca no MT5 real (FakeMT5).

> Se o `pytest` do projeto inteiro for rodado, ignorar o
> `tests/test_gerenciador_bloqueio.py` legado (`assert False`), que **não**
> faz parte do CI e não foi alterado.

---

## 3. Teste de fecho real em demo (hoje, se possível)

O mercado WDO já fechou; para testar o **caminho real** do `order_send` sem
esperar sexta, usar um símbolo **24h disponível na demo** (ex.: BTCUSD) com
volume mínimo. Se a demo não tiver símbolo 24h, pular para 3.4 e fazer o teste
real na sexta, em janela controlada.

### 3.1 Fecho normal (C1 + C2)

1. Abrir 1 posição mínima no símbolo 24h, com magic de teste `999999`.
2. Rodar um harness standalone (não o robô) que chama o helper:

```python
# patches/teste_fecho_demo.py  (criar só na hora; não faz parte do pacote)
import MetaTrader5 as mt5
from patches.robustez_fecho_helpers import fechar_todas_robusto

MAGIC_TESTE = 999999
if not mt5.initialize():
    raise SystemExit("MT5 off")
try:
    fechadas, restantes = fechar_todas_robusto(
        mt5, {MAGIC_TESTE},
        reconnect=lambda: mt5.initialize(),
        log=__import__("logging"),
        deviation=50, tentativas=5, backoff_s=5.0)
    print("fechadas=%s restantes=%s" % (fechadas, restantes))
finally:
    mt5.shutdown()
```

Esperado:

- [ ] `fechadas=1`, `restantes=[]`.
- [ ] Log `FECHO CONFIRMADO` / `#ticket saiu após tentativa 1`.
- [ ] `positions_get()` volta vazio para o ticket.

### 3.2 Queda de rede simulada (C1)

Com uma posição de teste aberta, desligar o Wi-Fi/roteador por ~10 s **durante**
o fecho (ou rodar o harness e desligar quando aparecer a 1ª tentativa).

Esperado:

- [ ] log de `order_send None` ou `retcode 10031`;
- [ ] chamadas de reconexão + backoff de 5 s;
- [ ] fecho concluído quando a rede volta, dentro das 5 tentativas;
- [ ] `restantes=[]`.

### 3.3 Falha persistente (C2, o teste que evita mentira)

Manter a rede off durante todas as tentativas.

Esperado:

- [ ] `restantes=[ticket]`;
- [ ] log `critical` com o ticket;
- [ ] **nunca** a mensagem `POSICOES FECHADAS` / `FECHO CONFIRMADO`.

### 3.4 Trava de shutdown (C3)

Teste estático obrigatório hoje; teste dinâmico na sexta, se necessário:

- [ ] Revisar no diff que o bloco C3 está **antes** do
      `logging.info("...ENCERRAMENTO GRACIL CONCLU...")` e do `break`.
- [ ] Confirmar que `continue` volta ao loop e **não** executa o `break`.
- [ ] Confirmar o escape `MONSTRO_FORCE_SHUTDOWN=1`.
- [ ] (Sexta, opcional) com posição aberta, criar `parar.txt` e iniciar o robô
      fora da janela de trade: esperar `SHUTDOWN BLOQUEADO` e processo vivo;
      com `MONSTRO_FORCE_SHUTDOWN=1`, encerra.

### 3.5 Relatório por deals (C4)

- [ ] Fechar manualmente uma posição demo após as 17:35 (se houver).
- [ ] Rodar `agente_monstro_core.py dryrun` ou a função
      `contar_trades_reais_hoje()` e conferir que o deal manual aparece.
- [ ] Comparar com `history_deals_get`: `n` e `PnL` batem (inclui swap/comissão).

---

## 4. Merge para a `main` (somente se tudo verde)

Critérios **todos** obrigatórios:

- [ ] `pytest tests/test_robustez_fecho.py -q` → 12 passed.
- [ ] `py_compile` OK nos 2 arquivos alterados.
- [ ] Fecho real em demo OK (3.1) **ou** aceite explícito de testar na sexta
      antes das 09:00.
- [ ] Nenhuma posição do robô aberta.
- [ ] `git diff` revisado (só C1–C4).

```powershell
cd C:\AIOFEN
git add monstro_unificado_v22.py agente_monstro_core.py patches/aplicar_robustez_fecho.py `
  patches/robustez_fecho_helpers.py patches/robustez_fecho_2026-11-11.md `
  patches/proposta_ml_23.29.md patches/checklist_fecho_2026-11-12.md
git commit -m "robustez fecho C1-C4: reconexao 10031, confirmacao positions_get, trava shutdown, relatorio por deals"
git checkout main
git merge --no-ff robustez-fecho
git push origin main
```

- [ ] Merge concluído, `main` limpa (`git status`).
- [ ] `git rev-list --left-right --count origin/main...HEAD` → `0 0`.
- [ ] Branch `robustez-fecho` mantida (não apagar) para auditoria.

---

## 5. Rollback

- **Antes do commit:** `python patches\aplicar_robustez_fecho.py --reverter`.
- **Depois do commit:** `git revert <commit-do-merge>` (ou restaurar os 2
  arquivos do commit anterior).
- Helpers e testes são **aditivos** e podem permanecer.
- Não há migração de estado/banco.

---

## 6. Pós-merge — sexta (13/11)

- [ ] 09:00: robô sobe e importa `patches.robustez_fecho_helpers` sem erro.
- [ ] 09:00–17:35: monitorar logs; o warning de clipping deve estar **throttled**
      (se T1 for aplicado depois) e o fecho deve usar o caminho novo.
- [ ] 17:35: conferir `FECHO CONFIRMADO` **somente** com `positions_get()` vazio.
- [ ] Se aparecer `10031`: esperar as 5 tentativas × 5 s; se persistir,
      `FECHO INCOMPLETO` + fechamento manual de fallback.
- [ ] 18:05: relatório diário deve mostrar `Trades fechados (deals MT5)`.
- [ ] Registrar o resultado no ROADMAP (seção 23.31 ou nova).

---

## 7. Definição de "verde"

O patch só vai para a `main` se **todas** forem verdadeiras:

1. 12/12 testes offline.
2. `py_compile` OK nos arquivos reais.
3. Nenhuma posição do robô aberta no momento da aplicação.
4. Diff restrito a C1–C4 (nenhuma regra de trade tocada).
5. Pelo menos um fecho real em demo confirmado por `positions_get()`
   **ou** teste real agendado para sexta antes das 09:00, com rollback pronto.

Caso contrário: manter na branch, registrar o bloqueio no ROADMAP e **não**
fazer merge.
