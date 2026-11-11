# Patch de robustez do fecho — proposta para revisão (11/11/2026)

**Status:** PROPOSTA — nada aplicado ao robô em produção.
**Origem:** ROADMAP seção **23.27** (incidente do fechamento das 17:35).
**Commit de referência das âncoras:** `9cd5c1b` (main).
**Arquivos aditivos desta proposta:**

- `patches/robustez_fecho_helpers.py` — helpers injetáveis (testados).
- `tests/test_robustez_fecho.py` — 12 testes com `FakeMT5`, sem terminal.
- este documento.

> `monstro_unificado_v22.py` e `agente_monstro_core.py` **não foram alterados**.
> O fonte do robô tem strings com encoding legado (mojibake); a aplicação deve
> ser feita por script/editor UTF-8 e validada com `py_compile`.

---

## 1. O que aconteceu (evidência)

| Hora | Evento |
|---|---|
| 17:35:02 | `FECHANDO TODAS AS POSIÇÕES` → `mt5.order_send` retorna `None` para `#2590873006` |
| 17:35:02 | agenda re-checagem 15 s/30 s |
| 17:35:13 | log imprime **“POSIÇÕES FECHADAS”** — falso, nada foi fechado |
| 17:35:18 | shutdown gracioso tenta de novo → **retcode 10031** (filling 0 e 1) |
| 17:35:18 | `parar.txt` encerra o processo **com a SELL aberta** |
| 17:36–17:37 | `WATCHDOG-DLL: Tick estagnado >10s` confirma a queda de rede |
| 18:05:47 | fecho manual a 5586,0 → **−R$ 50,00** (deal `1878867890`) |

Resultado do dia: **−R$ 35,00 bruto** (≈ −R$ 37,40 com R$ 1,20/operação).
O relatório das 17:35 dizia “Trades executados: 1”; o real eram **2**
(o fecho manual não aparece na contagem por log).

### Bugs → correções

| # | Bug | Correção |
|---|---|---|
| B1 | sem retry/reconexão em `10031` | **C1** reconexão com backoff |
| B2 | mensagem de sucesso incondicional | **C2** confirmar via `positions_get()` |
| B3 | shutdown não garante flat | **C3** trava de shutdown |
| B4 | relatório conta linhas de log, não deals | **C4** deals reais do MT5 |

---

## 2. C1 — Reconexão com backoff em `10031`

**Âncora:** `monstro_unificado_v22.py`, função `fechar_todas_posicoes`
(`def` em **L10608**, corpo até **L10723**).
Pontos críticos: envio em **L10663**, tratamento `None` em **L10666**,
retcode em **L10703**.
Hoje usa **filling fixo `ORDER_FILLING_IOC`** (L10659) e **sem retry**.

**Proposta:** delegar o corpo para `fechar_todas_robusto`
(`patches/robustez_fecho_helpers.py`), que:

- tenta **todos os fillings** aceitos pelo símbolo (FOK/IOC/RETURN);
- em `10031` (ou `order_send is None`) chama `reconectar_mt5()` e espera
  **backoff** antes de repetir (padrão: 5 tentativas × 5 s);
- só retorna `True` quando `positions_get()` confirma que o ticket saiu;
- usa `pos.magic` (hoje o request grava `MAGIC_NUMBER` fixo em L10656 —
  isso também corrige o fecho de posições da Faixa 1/magic 7008).

**Integração sugerida:**

```python
# topo do monstro_unificado_v22.py
from patches.robustez_fecho_helpers import (
    fechar_todas_robusto, posicoes_restantes, contar_deals_reais_hoje,
)

MAGICS_ROBO = tuple(
    {MAGIC_NUMBER} | ({MAGIC_ROMPIMENTO} if ROMPIMENTO_ATIVO else set())
)


def fechar_todas_posicoes(motivo: str = "Encerramento automático") -> int:
    fechadas, restantes = fechar_todas_robusto(
        mt5, MAGICS_ROBO,
        reconnect=reconectar_mt5,
        log=logging,
        deviation=20,
        tentativas=5,
        backoff_s=5.0,
    )
    if restantes:
        logging.critical(
            "FECHO INCOMPLETO (%s): %d posição(ões) ainda aberta(s): %s",
            motivo, len(restantes), restantes)
    else:
        logging.info(
            "FECHO CONFIRMADO (%s): %d fechada(s), flat.", motivo, fechadas)
    return fechadas
```

> O retorno continua `int`, então os chamadores atuais
> (`encerramento_seguro_completo` em L10813 e o bloco das 17:35 em L7007)
> não quebram.

---

## 3. C2 — Confirmação inegociável antes de logar sucesso

**Âncora:** bloco `# === ENCERRAMENTO AUTOMÁTICO ÀS 17:35 ===`
em **L6998–L7027**. A mensagem incondicional está em **L7026–L7027**.

**Antes (resumo):**

```python
posicoes_fechadas = fechar_todas_posicoes("Encerramento automático 17:35")
...
logging.info(f"POSIÇÕES FECHADAS ÀS {HORARIO_ENCERRAMENTO} - AGUARDANDO AFTER MARKET")
```

**Depois:**

```python
posicoes_fechadas = fechar_todas_posicoes("Encerramento automático 17:35")
_restantes = posicoes_restantes(mt5, MAGICS_ROBO)
if _restantes:
    logging.critical(
        "POSIÇÕES AINDA ABERTAS ÀS %s: %s — fecho NÃO confirmado",
        HORARIO_ENCERRAMENTO, _restantes)
else:
    logging.info(
        "POSIÇÕES FECHADAS ÀS %s — flat confirmado (%d)",
        HORARIO_ENCERRAMENTO, posicoes_fechadas)
```

**Regra:** o texto “POSIÇÕES FECHADAS” só pode aparecer se
`posicoes_restantes(mt5, MAGICS_ROBO) == []`. Retcode nunca é prova de fecho.

---

## 4. C3 — Trava de segurança no shutdown

**Âncora:** bloco `# ===== VERIFICAÇÃO DE PARADA GRACIL =====`
em **L6918–L6959**. O `break` que encerra o loop está em **L6958–L6959**,
depois do log “ENCERRAMENTO GRACIL CONCLUÍDO” (L6956–L6957).

**Proposta:** antes do log final e do `break`, garantir flat. Se ainda houver
posição, tentar fechar de novo; se continuar aberta, **não encerrar** e
manter o processo vivo (com escape hatch explícito).

```python
# ... depois de salvar modelo/experiências ...
_restantes = posicoes_restantes(mt5, MAGICS_ROBO)
if _restantes:
    logging.critical(
        "SHUTDOWN BLOQUEADO: posições abertas %s — tentando fechar", _restantes)
    fechar_todas_posicoes("Trava de shutdown")
    _restantes = posicoes_restantes(mt5, MAGICS_ROBO)

if _restantes and not os.environ.get("MONSTRO_FORCE_SHUTDOWN"):
    logging.critical(
        "SHUTDOWN BLOQUEADO: %d posição(ões) seguem abertas. "
        "Processo permanece vivo. Use MONSTRO_FORCE_SHUTDOWN=1 para forçar.",
        len(_restantes))
    time.sleep(30)
    continue  # volta ao loop; NÃO executa o break

logging.info("ENCERRAMENTO GRACIL CONCLUÍDO — flat confirmado")
thread_ativo = False
break
```

> `continue` já é usado no loop (L6968, L6971). `time` e `os` já são
> importados no módulo. O `parar.txt` é consumido antes (L6924); para tentar
> de novo, o operador recria o arquivo ou usa `MONSTRO_FORCE_SHUTDOWN=1`.

---

## 5. C4 — Relatório diário por deals reais

**Âncora:** `agente_monstro_core.py`, `gerar_relatorio_diario`
(`def` em **L800**), linha de trades em **L809–L812**.
A contagem atual (`contar_executados_hoje`, ~L409–L419) lê o log do robô
(“processada e resetada”) e o CSV do rompimento — **não** os deals do MT5.
Foi por isso que o fecho manual das 18:05 não entrou no relatório.

**Proposta:** adicionar uma contagem paralela, read-only, por deals:

```python
from patches.robustez_fecho_helpers import contar_deals_reais_hoje

def contar_trades_reais_hoje():
    """(n_fechados, pnl_realizado) lendo deals reais. Degrada para (None, 0)."""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None, 0.0
        try:
            hoje = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0)
            magics = {MAGIC_NUMBER, MAGIC_ROMPIMENTO}
            return contar_deals_reais_hoje(mt5, magics, hoje, datetime.now())
        finally:
            mt5.shutdown()
    except Exception:
        return None, 0.0
```

No relatório, manter os contadores de log **rotulados como tal** e incluir a
linha nova:

```python
n_real, pnl_real = contar_trades_reais_hoje()
if n_real is None:
    linhas.append("Trades fechados (deals MT5): indisponível (MT5 off)")
else:
    linhas.append(
        f"Trades fechados (deals MT5): {n_real} | "
        f"PnL realizado: R$ {pnl_real:+.2f}")
linhas.append(
    f"Contagem por log (referência): v22={n_v22} + Faixa1={n_romp}")
```

> Com isso, 11/11 passaria a mostrar **2 trades** e **−R$ 35,00**,
> incluindo o fecho manual.

---

## 6. Plano de teste

### 6.1 Offline (obrigatório antes de aplicar)

```powershell
cd C:\AIOFEN
C:\AIOFEN\venv310\Scripts\python.exe -m py_compile `
  patches\robustez_fecho_helpers.py tests\test_robustez_fecho.py
C:\AIOFEN\venv310\Scripts\python.exe tests\test_robustez_fecho.py
C:\AIOFEN\venv310\Scripts\python.exe -m pytest tests\test_robustez_fecho.py -q
```

Cobertura dos 12 testes:

- fecho normal (SELL fecha com BUY; BUY fecha com SELL);
- `10031` → reconecta 1×, backoff 5 s, fecha na 2ª tentativa;
- `10031` persistente → `(0, [ticket])` + log `critical` (não mente);
- `order_send None` em todos os fillings → reconecta e fecha;
- `retcode DONE` **sem** a posição sair → **não** conta como sucesso;
- posição já ausente → conta como fechada, sem enviar ordem;
- magic alheio (123457) ignorado;
- `posicoes_restantes` só devolve magics do robô;
- bitmask de fillings (FOK/IOC/RETURN) e fallback;
- deals: conta só `DEAL_ENTRY_OUT` dos magics do robô, com swap/comissão;
- sem histórico → `(0, 0.0)`.

### 6.2 Demo (depois de aplicar)

1. Abrir 1 posição de teste (1 contrato) e rodar
   `fechar_todas_posicoes("teste C1")` → deve logar `FECHO CONFIRMADO` e
   `positions_get()` deve voltar vazio.
2. **Simular rede ruim:** desligar o Wi-Fi/roteador por ~10 s durante o fecho.
   Esperado: log de `10031`, chamadas de reconexão, e o fecho concluindo
   quando a rede voltar (dentro das 5 tentativas).
3. **Simular falha persistente:** manter a rede off. Esperado: `critical`
   com os tickets restantes; **nunca** “POSIÇÕES FECHADAS”.
4. **Trava de shutdown:** com posição aberta, criar `parar.txt`.
   Esperado: `SHUTDOWN BLOQUEADO`, tentativa de fecho, processo **não**
   encerra; com `MONSTRO_FORCE_SHUTDOWN=1`, encerra.
5. **Relatório:** fechar uma posição manualmente após as 17:35 e conferir que
   o relatório do dia seguinte conta o deal e o PnL.

### 6.3 Critério de aceite

- `pytest tests/test_robustez_fecho.py -q` → **12 passed**.
- Nenhum log de “POSIÇÕES FECHADAS” com `positions_get()` não vazio.
- Shutdown sem `MONSTRO_FORCE_SHUTDOWN` nunca termina com posição do robô aberta.
- Relatório diário bate com `history_deals_get` (inclui fecho manual).

---

## 7. Rollback

- A aplicação é **isolada**: `fechar_todas_posicoes`, bloco das 17:35,
  bloco de parada graciosa e `gerar_relatorio_diario`.
- Reverter com `git revert <commit-da-aplicacao>` (ou restaurar os 2 arquivos
  do commit anterior). Não há migração de estado/banco.
- `patches/robustez_fecho_helpers.py` e `tests/test_robustez_fecho.py` são
  **aditivos** e podem permanecer mesmo após o rollback.
- O comportamento antigo (`fechar_todas_posicoes` original) fica preservado
  no histórico do git.

---

## 8. Riscos e observações

1. **Mojibake:** o fonte tem strings corrompidas. Aplicar via script que leia
   e grave em UTF-8, e rodar `py_compile` + um teste de fumaça em demo.
   Não usar “salvar como” que troque o encoding.
2. **Tempo de fecho:** 5 tentativas × 5 s ≈ 25 s (mais fillings). Há folga
   até o after-market (~18:25), então é seguro.
3. **Trava de shutdown:** por design pode manter o processo vivo. O escape
   hatch `MONSTRO_FORCE_SHUTDOWN=1` evita bloqueio operacional.
4. **Magic no request:** o helper usa `pos.magic`; o código atual grava
   `MAGIC_NUMBER` fixo (L10656). É uma correção latente para a Faixa 1.
5. **Contagem por deals:** um fecho parcial gera mais de um `DEAL_ENTRY_OUT`.
   Com 1 contrato isso não ocorre; se o volume mudar, contar posições, não deals.
6. **Não altera lógica de entrada/saída.** Nenhum gate, stop, alvo ou filtro
   é tocado. O patch é exclusivamente de fecho/encerramento/relatório.

---

## 9. Checklist de aplicação (Fase 1 — revisão humana)

- [ ] Revisar este documento e os helpers.
- [ ] Aprovar os textos de log e o escape hatch `MONSTRO_FORCE_SHUTDOWN`.
- [ ] Aplicar C1–C4 em branch separada (não direto na `main`).
- [ ] Rodar `py_compile` e os 12 testes.
- [ ] Teste em demo com rede ruim simulada.
- [ ] Só então merge na `main` e acompanhar um fecho real às 17:35.
