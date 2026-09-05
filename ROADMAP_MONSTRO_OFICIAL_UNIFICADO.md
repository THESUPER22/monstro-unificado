# 🚀 ROADMAP OFICIAL — MONSTRO TRADER V2
**Última atualização:** 01/09/2026
**Versão:** Monstro Unificado V22 (Engine v22.2 — Sete Velas: Gestão de Posição + Backtest A/B)
**Arquivo principal:** `monstro_unificado_v22.py`
**Status geral:** Fase 10 concluída; v22.1b reparada; v22.2 (Fase 3) implementada — 7 Velas em incubação out-of-sample (n≥30)

---

## 📦 v22.1 — 2026-08-28 (Engine Robustness & Audit Patch)

### 🚀 Implementado & Auditado
- [x] **Infraestrutura**: Servidor de produção Waitress (8 threads) + liberação de porta 5001 com 3-probes e backoff persistido (Commit `bd40ec0`).
- [x] **Corte #1 (Engine)**: Reconciliação de posições órfãs via `PENDING_RECONCILIATION` persistida em JSON. Fim das perdas fantasmas por perda de sincronia de deals no MT5.
- [x] **Corte #2 (Engine)**: Fallback para `order_send=None` no fecho forçado das 17:35 com varredura retroativa de 60s via `history_deals_get`.
- [x] **Corte #3 (Dados)**: Garantia de header estático de 22 colunas (`timestamp` na 1ª coluna) na função `_migrar_historico_timestamp`. Recomposição do dataset Shadow Mode ($n=25$; Trades #1 = −80, #7 = −5, total semanal −R$755).

### 🚀 v22.1 — 2026-08-29 (Multi-Estratégia & Teoria das 7 Velas)

#### 🚀 Implementações & Melhorias
- **Arquitetura Multi-Estratégia Sequencial (Faixa 1 & Faixa 2):**
  - **Faixa 1 (09:00–11:30 BRT):** Execução exclusiva do módulo `sete_velas_orquestrador.py` em M15 (Dólar WDO) com 5 contratos (5 CC) e `magic_number = 7007`.
  - **Faixa 2 (11:30+ BRT):** Transição automática para o modo `PADRAO_MONSTRO` reativando os agentes (Keras, Sniper %R, Supermo) com lote normal (2 CC).
- **Módulos Criados:**
  - `sete_velas_util.py`: Funções puras de processamento M15, contagem de direção de velas e acumulação de CVD (Volume de Agressão por Ticks).
  - `sete_velas_orquestrador.py`: Maquinário de estado (`ESTADO_SISTEMA`), controle de idempotência, filtro CVD e emissão via callback.
  - `shadow_sete_velas_wdo.py`: Script de shadow mode ao vivo e retrospectivo (54 registros) com parâmetro de auto-saída `--ate HH:MM`.
- **Blindagens & Fixes em `monstro_unificado_v22.py`:**
  - Atualização da assinatura de `executar_ordem` para suporte a `magic_override`, `comment` e desativação de shadow individual.
  - Inserção do **Gatekeeper da Faixa 1** dentro de `executar_ordem` para bloquear chamadas de outros agentes durante `SETE_VELAS_EXCLUSIVO`.
  - Inserção da flag `ignore_max_loss` no Circuit Breaker CB2 para evitar travamento geral do robô em caso de Stop Loss da 7 Velas (5 CC) na janela matutina.

#### ✅ Validação Quantitativa Final (2026-08-29)
- **Backtest Robusto com Dados Reais MT5 (M1):** 87 dias úteis / 174 sinais (Abr–Ago 2026)
- **Janela V9 (11:15) — TIRO CERTO VALIDADO:**
  - **Modo DUAL (Gatekeeper):** WR 52.9% | PF 1.41 | PnL +R$ 3.900 | Max DD R$ 1.800 | 23 stops evitados
  - **Modo SECO:** WR 43.4% | PF 0.96 ❌ | PnL -R$ 800
  - **Gatekeeper salvou a estratégia:** 32 sinais filtrados, 23 stops evitados
- **Janela V7 (10:45) — DESATIVADA:**
  - Ganho marginal (WR 47.7% → 48.1%), PnL reduzido (R$ 2.500 → R$ 1.800)
  - **Decisão:** Desativada (`V7_1045_ATIVO: false`) para focar capital no V9
- **Configuração Produção (config.json):**
  - `"ativo": true, "variante": 9, "V7_1045_ATIVO": false, "V9_1115_ATIVO": true`
  - `gatekeeper_dual: true`, `cb2_ignore_max_loss: true`
  - SL 8.0 / TP 10.0 / Lote 5 CC / Magic 7007

### 📌 Próximos Passos (Semana 31/08 – 04/09)
- [x] **Segunda 31/08 - 08:50:** Disparar Shadow Mode (`shadow_sete_velas_wdo.py --ate 18:35`)
- [x] **Segunda 31/08 - 08:55:** Iniciar Monstro v22.1 (`python monstro_unificado_v22.py`)
- [x] **09:00–11:30:** Monitorar `SETE_VELAS_EXCLUSIVO` ativo — V9 (11:15) com Gatekeeper DUAL
- [x] **11:15:** Verificar disparo V9 DUAL (5 CC, SL 8 / TP 10) se CVD + VWAP alinhados
- [x] **11:30:** Transição automática `PADRAO_MONSTRO` (2 CC) — Keras/Sniper/Supermo ativos
- [x] **Pós-pregão:** Validar Shadow CSV (meta n≥30) e comparar com execução real
- [x] **01/09:** Fase 1 (idempotência + parametrização config), Fase 2 (backtest A/B 352 dias), Fase 3 (TP parcial 1:1 + BE + trava macro) — commit `1b7aa3d` + `5518a74`
- [ ] **Correção de autópsia (01/09, pós-sessão):** reducer raiz `max_loss_diario` → -1000.0 alinhado com `risk_management` (Kill-Switch mantido em R$1.000, inalterado); rate-limit no append de `historico_multitf.csv` (1 write/60s) — commit pendente
- [ ] **Início incubação OOS:** 02/09/2026 (V9 + Gatekeeper Dual + TP parcial/BE + trava macro) — meta n≥30
- [ ] **Retomada na SEXTA 04/09 (Payroll — teste da trava `VETADO_MACRO`):** validar que a janela 11:15 fica bloqueada na 1ª sexta do mês (conferir CSV/state com `VETADO_MACRO` e nenhum trade aberto)
- [ ] **Pós-semana:** Decisão `ativo: true` permanente baseada em n≥30 out-of-sample (critérios da seção v22.2)
- [ ] **Congelamento de Parâmetros:** Manter Whitelist, Sniper %R fixo, SL 8.0 pts WDO

### 🚨 v22.1b HOTFIX — 2026-09-01 (Reparo da Integração 7 Velas)

#### 🔍 Auditoria Pós-Agente (descoberta de melhorias que quebraram o engine)
- **Causa-raiz:** Altera antigo agente aplicou diff parcial/corrompido (`dd77a00`) no `monstro_unificado_v22.py`:
  - L1386 usava `ignore_max_loss` sem declarar na assinatura do CB2 → **NameError a cada ciclo (~3min)**
  - `executar_ordem` com assinatura nova mas corpo com nomes antigos (`sniper`, `symbol`, `lots`, `modo_operacional`) → contrato quebrado c/ chamada L7995
  - Gatekeeper duplicado (L5247-5250 + L5254-5257) e variáveis fantasma `ESTADO_SISTEMA`/`MAGIC_SETE_VELAS` **nunca definidas**
  - `_orq = Orquestrador7Velas(...)` importado mas **nunca instanciado** → robô cego p/ Faixa 1
- **Evidência:** `NameError: name 'ignore_max_loss' is not defined` 09:20–09:48 (01/09) + Magic=123456 (sem exclusividade)

#### 🛠️ Correções Aplicadas (v22.1b)
- [x] **CB2**: `verificar_circuit_breakers(self, spread_atual, ignore_max_loss=False)` + call site L7933 com `_cb2_ignore` (só libera CB2 na janela exclusiva 7 Velas)
- [x] **executar_ordem**: assinatura reconciliada `(action, lots=VOLUME_PADRAO, symbol, modo_operacional, sniper, sl_points_override, tp_points_override, magic_override, comment, shadow)` — compatível c/ engine e 7 Velas; `magic_final` e `comment` injetados no `order_send`
- [x] **Globals 7 Velas**: `SETE_VELAS_CFG/ATIVO/MAGIC_SETE_VELAS/INICIO_HORA/FIM_HORA` + `ESTADO_SISTEMA="PADRAO_MONSTRO"` + `_atualizar_estado_sistema()` lendo `config.json` (brt)
- [x] **Gatekeeper**: único (regra: na exclusividade só Magic 7007 passa) em `executar_ordem`
- [x] **Orquestrador**: `_orq = Orquestrador7Velas(fn_executar=wrapper, symbol=SYMBOL, ativo=SETE_VELAS_ATIVO)` instanciado em `monstro_thread` + `_orq.orquestrar()` no loop quando `SETE_VELAS_EXCLUSIVO`
- [x] **Instância única**: processos duplicados encerrados; único venv310 reiniciado 10:30 — log confirma `[7VELAS] Orquestrador instanciado (magic 7007)` e zero NameErrors pós-restart
- [x] **py_compile** 100% (4 módulos) + commit/push

### 🎯 v22.2 — 2026-09-01 (Fase 3: Gestão de Posição + Trava Macro + Backtest A/B)

#### 🔬 Backtest A/B Histórico (352 dias — 2025-04 a 2026-08, `WDO@` M1)
Motivo: **sepultar cientificamente o Modelo B de varejo** antes de investir em parametrização.

| Métrica | **Modelo A** (Monstro: majority V9 + Gatekeeper Dual, SL8/TP10) | **Modelo B** (Varejo: 7 velas mesma cor + RSI + Bollinger) |
|---|---|---|
| Sinais | 349 | 43 |
| Trades de fato | **145** | **3** (8 → 5 stop não disparou) |
| Win rate | 49.7% | 33.3% (n=3) |
| PnL 5CC | **R$ 6.800** | R$ 649 |
| Profit Factor | 1.23 | 2.27 (amostra irrelevante) |
| Max DD | R$ 3.600 | R$ 320 |

**Conclusão:** Modelo B gera ~3 trades em 17 meses — inviável operacionalmente. **Gatekeeper Dual + Majority V9 confirmado como superior e único candidato de produção.** Script: `backtest/backtest_ab_7velas.py` (commit `1b7aa3d`).

#### 💰 Gestão de TP Parcial 1:1 + Breakeven (implementada)
- **TP1 no SL (1:1, 8 pts):** ao atingir +8 pts, realiza **3 CC** (`TRADE_ACTION_DEAL`) e move o SL dos **2 CC restantes** para o **breakeven** (entrada) via `TRADE_ACTION_SLTP`.
- **Alvo final:** TP do MT5 permanece 10 pts nos remanescentes → captura +R$200 adicionais (total +R$440 no cenário ótimo).
- **Matemática:** 3 CC × 8 pt × R$10 = +R$240 garantidos no TP1; operação vira **risco zero** após o breakeven.
- **Controle via `config['sete_velas']`:** `gestao_tp_parcial`, `tp1_dist` (8.0), `lote_tp1` (3.0), `tp_final_dist` (10.0). Toggle permite desativar sem mexer no código.
- **Validação:** `py_compile` OK + teste offline com mock MT5 (parcial 3CC + BE correto; preço abaixo do TP1 sem ação; gestão desativada sem ação).

#### 🛡️ Trava Macro Automática (Payroll / FOMC / Copom)
- **Payroll (automático):** primeira sexta-feira do mês — bloqueia abertura na janela 11:15.
- **FOMC/Copom (manual):** lista `datas_bloqueadas` em `config['sete_velas']` (agenda anual do Fed/BCB).
- **Comportamento:** não abre posição; registra **`VETADO_MACRO`** no CSV/state (idempotência preservada).

#### 🧪 Protocolo de Validação Out-of-Sample (n ≥ 30) — HOMOLOGAÇÃO
- **Período de incubação:** operar ao vivo desde **02/09/2026** (V9, Gatekeeper Dual + TP parcial/BE + trava macro ativa).
- **Critério de homologação definitiva (`ativo: true` permanente):**
  - [ ] **n ≥ 30 trades reais** registrados em `logs/sete_velas_trades.csv` (excluindo VETADO_MACRO/VETADO_CVD).
  - [ ] Tactics mensais: WR ≥ 45% **e** PF ≥ 1.1 sobre o período de incubação.
  - [ ] **Drawdown máximo ≤ R$ 3.600** (teto da validação histórica).
  - [ ] Gerenciamento de posição ativo: auferir ganho do TP parcial (3 CC) em ≥ 80% dos trades que alcançaram +8 pts.
- **Critério de rollback:** se PF < 1.0 ou MaxDD > R$ 3.600 antes de n=30, desativar `ativo: false` e reavaliar.
- **Congelamento de parâmetros durante a incubação:** SL 8 / TP 10 / 5 CC / `<tp1_dist>` 8 / `<lote_tp1>` 3 — nenhuma alteração até n≥30.

---

## 🔍 AUDITORIA DA SEMANA 01–04/09/2026 (documentação + REPARO AUTORIZADO E APLICADO em 04/09)

### 📊 Resumo real (cruzado com logs diários `monstro_wdo_202609*.log`)

| Dia | Ordens executadas | Observação |
|---|---|---|
| 01/09 | 5 | Core normal (11:54, 14:41, 15:45, 16:00, 17:03) |
| 02/09 | 3 | Core normal |
| 03/09 | **136** | **133 SELL × 5.0 CC = 665 lotes = ANOMALIA 11:15:03→11:29:58** + 3 BUY normais |
| 04/09 | 4 | Core normal |
| **Semana** | **15 (core) + 133 (anomalia)** | Nº de trades do core = 15 confirma relatório (11W/4L) |

### 🐛 CAUSA RAIZ DA ANOMALIA (COMPROVADA NOS LOGS) — DIVERGE DO RELATÓRIO DO AGENTE

**Sintoma (bate com relatório):** 03/09 11:15:03 a 11:29:58 → **133 ordens SELL×5 CC = 665 lotes** → PnL ~R$ 57.425 negativo (fechamento via SL no MT5).

**Causa raiz real (dupla):** o relatório atribuiu a "loop de ordens sem `positions_get` em conta Netting". **A evidência mostra outra mecânica:**

1. **Bug de CSV (`dict contains fields not in fieldnames: 'ticket'`)** — introduzido no commit `1b7aa3d` (Fase 1/2, 01/09 11:57, post-janela): `avaliar()` passou a incluir `rec['ticket']` (L204/L210/L187) mas o `campos` do `_registrar_trade()` (L151-152) **não foi atualizado** com `'ticket'`. Todo `w.writerow(rec)` lança ValueError.
2. **Idempotência morta:** `orquestrar()` chama `_registrar_trade(rec)` (L389) → exceção → linhas L390-395 (`state[chave]=...; _salvar_state(state)`) **nunca executam** → `logs/sete_velas_state.json` **nunca é criado** (confirmado: arquivo não existe). O gatilho de entrada L379 (`chave not in state`) permanece verdadeiro para sempre.
3. **Loop engolido pelo engine:** `monstro_unificado_v22.py` L6630-6633 chama `orquestrar()` dentro de `except Exception: logging.error(...)` que apenas **loga e segue** → a cada iteração do loop principal (~6s) reexecuta `avaliar()` → **nova ordem**.
4. **Quando confluente ≠ quando vetado:** 02/09 o mesmo erro ocorreu (377x às 11:15) mas **sem ordens** — o sinal foi VETADO_CVD. 03/09 o sinal foi **CONFLUENTE** → reenvio real a cada ~6s (133 ordens).
5. **Fim natural:** parou às 11:29:58 porque `JANELA_FIM_HORA=11.5` → `_na_janela()` falso → loop de entrada não mais executado.

**Mecânica exata da cadeia (logs):** a cada tick: `Volume ajustado: 5.0` → `Ordem SELL executada. Ticket: ...` → `SHADOW Modelo A p=0.389` → `Não foi possível confirmar se ordem virou posição` → `[7VELAS] Erro no orquestrar(): dict contains fields not in fieldnames: 'ticket'`.

**Por que a gestão não fechou:** após 11:30, `Posição ativa no MT5 mas posicao_atual é None` + `Gerenciador de Saída DESATIVADO` — a posição do magic 7007 não é reconhecida como "posição do Monstro" (bate no fallback), então só o SL/TP fixo do MT5 encerrou.

**Verificação adicional:** `logs/sete_velas_trades.csv` tem apenas a linha de 01/09 (VETADO_CVD, gravada ANTES do commit bugado) — prova que a versão ativa em 01/09 era a pré-`1b7aa3d` e que a anomalia é pós-commit.

### ✅ VEREDICTO SOBRE O RELATÓRIO DO AGENTE
- **CONFIRMADO:** 665 lotes × 5 CC na janela 11:15-11:29 de 03/09; total da semana ~-R$ 57.250; 15 trades no core.
- **INEXATO:** causa raiz "loop sem `positions_get`". O gatilho real é o **ValueError do CSV** que mata a idempotência persistida + `except` do engine que engole o erro. A ausência de `positions_get` no orquestrador é um agravante (não uma causa).

### 🔧 AÇÕES RECOMENDADAS — ✅ EXECUTADAS EM 04/09/2026 (autorizadas pelo Mestre)
> Arquivo reparado: `sete_velas_orquestrador.py`. Suíte de validação: `tests/teste_orquestrador_7velas.py` (11/11 PASS) + `py_compile` OK + `testes_pos_fix.py` (9/9) + `validar_config_estrutura.py` (PASS). Core v22 congelado — zero alterações.

1. **Fix mínimo (`sete_velas_orquestrador.py`):** `'ticket'` adicionado ao `campos` do `_registrar_trade()` — **restaura a idempotência** (`state[chave]` volta a ser persistido em `logs/sete_velas_state.json`). ✅
2. **Trava dupla de reentrada no gatilho de entrada:** novo gate `_tem_posicao_aberta(MAGIC_SETE_VELAS)` (scan `positions_get` por magic 7007, mesmo posição parcial pós-TP1) — bloqueia nova ordem enquanto houver posição aberta do 7 Velas no MT5 (essencial em Netting). ✅
3. **Trava de volume máximo acumulado por janela:** `_acumulado_janela(MAGIC_SETE_VELAS)` (soma volume das posições do magic) vs `_teto_volume_janela()` (= lote configurado, 5.0 CC ≈ 1 lote) — defesa final contra acúmulo tipo 03/09. ✅
4. **Alinhar `campos` vs `rec` em TODOS os caminhos:** `_registrar_trade()` agora grave apenas `{c: rec.get(c, '') for c in campos}` (filtra chaves extras de qualquer fluxo — VETADO_MACRO, VETADO_CVD, sem_velas, executado); `ticket=None` adicionado aos fallbacks `sem_velas_suficientes` (L219) e `SEM_DADOS` (L424) e ao `rec` None. ✅
5. **Alteração cirúrgica:** após a primeira entrada da janela, `orquestrar()` retorna (trava 1-lote), mantendo o comportamento das variantes 7/V9 nas janelas distintas.

---

## 📊 RELATÓRIO DE INTELIGÊNCIA QUANTITATIVA — 7 TÓPICOS (04/09/2026)

> Análise contextual completa da semana 01–04/09/2026 cruzando log de ordens/posições (`monstro_wdo_2026090{1,2,3}.log`, `monstro_wdo.log`=04/09), `logs/modelo_a_shadow.csv`, `historico_multitf.csv`, `agente_autonomo.log`, `config.json`/`agente_config.json` e código. Somente leitura (nenhum arquivo alterado nesta etapa).

### TÓPICO 1 — RAIZ TRADE-A-TRADE DO CORE (15 trades)

**Base de dados:** 15 tickets do Core EXATAMENTE confirmados via "Ordem ... executada. Ticket:" nos logs. Dia 03/09 tem 136 ordens (133 anômalas + 3 core). Total Core da semana = **15 trades (5+3+3+4)** — bate com o relatório.

| # | Dia | Entr. | Ticket | Tipo | PnL (R$) | p-Shadow A |
|---|---|---|---|---|---|---|
| 1 | 01/09 | 11:54:13 | 2517225296 | SELL | **−80** (SL) | 0.390 |
| 2 | 01/09 | 14:41:53 | 2517464087 | SELL | **−80** (SL) | 0.676 |
| 3 | 01/09 | 15:45:16 | 2517534687 | SELL | +40 (TP) | 0.747 |
| 4 | 01/09 | 16:00:16 | 2517557147 | BUY | +45 (TP) | 0.725 |
| 5 | 01/09 | 17:03:18 | 2517669288 | SELL | *n.r. (fech. manual 17:35)* | 0.651 |
| 6 | 02/09 | 11:54:24 | 2518269183 | SELL | +40 (TP) | 0.180 |
| 7 | 02/09 | 14:35:18 | 2518543349 | SELL | +35 (TP) | 0.830 |
| 8 | 02/09 | 15:25:52 | 2518616714 | SELL | +55 (TP) | 0.822 |
| 9 | 03/09 | 14:30:07 | 2519688252 | BUY | +40 (TP) | 0.507 |
| 10 | 03/09 | 15:09:35 | 2519722964 | BUY | +15 (TP) | 0.591 |
| 11 | 03/09 | 16:08:24 | 2519781301 | BUY | +45 (TP) | 0.605 |
| 12 | 04/09 | 11:32:58 | 2520474202 | BUY | **−80** (SL) | 0.470 |
| 13 | 04/09 | 14:36:01 | 2520715797 | SELL | +40 (TP) | 0.488 |
| 14 | 04/09 | 15:14:25 | 2520757216 | BUY | +40 (TP) | 0.549 |
| 15 | 04/09 | 15:40:40 | 2520776665 | SELL | *n.r. (fech. manual 17:35)* | 0.667 |

*n.r. = não registrado: os 2 fechamentos manuais (encerramento 17:35) não gravam preço de saída/lucro no log.*

**Consolidação verificada nos logs:** 13 trades com PnL fechado → **10W / 3L, WR 76,9%, net +R$ 155,00** (GP R$395 / GL −R$240). Os 2 trades sem PnL registrado impactam a diferença vs. o "+R$175 / 11W-4L" do relatório — o valor exato deles **não é verificável** nos logs (seria +R$20 nos dois para bater).

**Padrão dos 3 losses (−80 cada):** todos SELL/BUY abertos **pelo SNIPER %R sobrepondo a IA** contra book ratio fraco (<1.3), DOL desalinhado e/ou tendência adversa — 01/09 11:54 (SELL contra TEND ALTA +2.2pts, DOL conf ~0.34), 01/09 14:41 (lateral, ATR 1.4<1.5, WR sobrecomprado), 04/09 11:32 (BUY com preço −2.9pts abaixo da SMA, DOL lado SELL, sinal NEUTRO conf 0.117 ignorado). **Nenhum dos 15 trades tem "CVD" logado nesta semana** — o indicador CVD/Book/Dólar-Cheio só aparece via book_ratio (1.00–1.25 na maioria dos trades) e DOL conf (0.34–0.46).

### TÓPICO 2 — AUDITORIA DO AGENTE AUTÔNOMO / WHITELIST

- **Zero ajustes aplicados na semana.** As 4 pausas das 12:30 (01–04/09) logaram idênticos `DECISAO: SEM AJUSTE. Whitelist vazia (sniper %R fixo desde 08/08)`. `agente_estado.json`: `ultima_mudanca=null`, `historico=[]`. Nenhuma ocorrência de `AJUSTE APLICADO` em todo o log (desde 03/08).
- **Whitelist de fato = `{}` vazia desde 08/08** (cancelamento do Pilar 3). `decidir()` aborta em `if not CFG["whitelist"]:` → nenhum parâmetro é tocado. Travas: janela de autonomia 12:30–14:30 (`rotinas.janela`) + trava física de 1 ajuste/dia + rollback/smoke_test.
- **Mudanças de valor na semana foram EXTERNAS ao agente (noite de 01/09):** `max_loss_diario` raiz −100→−1000 (commit `1730eea` 01/09 13:25), `sniper_ratio_min` raiz/risk 2.0→1.5 e 1.2→1.5, `kill_switch` −100/−150→−250/−400 (mtime 01/09 17:41 e 17:43; efetivadas via boot 09:05 de 02/09). **Sem trilha de auditoria própria** — único ponto de exposição de processo (mudança manual em config fora do log do agente).
- **Regime de autonomia respeitado:** watchdog restart único legítimo 03/09 15:50 (robô travado/porta morta); nenhuma ação fora da janela; plano do dia seguinte é só PROPOSTA (o `trailing 5→7` sugerido no plano 03/09 **não foi aplicado**; trailing é hardcoded 8/4, fora da whitelist).
- **Valores atuais 04/09:** `sniper_ratio_min=1.5`, `book_ratio_min=1.3`, `dol_conf_min=0.4`, `max_loss_diario=−1000`, kill_switch −250/−400, trailing hardcoded 8/4.
- **Mapa de vetos:** `williams_r` domina todos os dias (4767/3683/2183/2701); `multi_tf` sumiu em 03–04/09 (380/599 → 0/0); kill-switch jamais disparou na semana.

### TÓPICO 3 — AUDITORIA SHADOW MODE / MODELO A

- **É passivo (somente registro).** `monstro_unificado_v22.py` L5389-5394 executa a ordem **antes** de `shadow_registrar_entrada`; L545-547: "Registra ... SEM bloquear execucao". Não há nenhum branch de veto baseado em `prob_modelo_a`.
- **Amostra total (173 registros):** WR 50%, PF 0.58, net −R$600, corr(prob,resultado)=**+0.005** ≈ zero — o Modelo A **não tem capacidade preditiva** na amostra histórica.
- **Sub-amostra da semana (13 fechados):** WR 76.9%, PF 1.65, net +R$155, corr=+0.245, acurácia threshold 0.5 = 76.9%.
- **Simulação de veto p<0.5 na semana:** teria bloqueado 4 trades (2 perdas −80 e 2 lucros +40/+40) → net subiria de +155 para **+235**. A perda `2517464087` (p=0.676) **não seria evitada**. Na amostra inteira, veto p<0.5 pioraria levemente o ponto de corte (PF mantém 0.58).
- **Sobre a anomalia 03/09:** 124 de 133 ordens teriam prob <0.5 (seriam vetadas); as 9 de p=0.5277 passariam. **Mas o PnL real das 133 nunca foi registrado** (rastreamento de posição quebrado pós-11:30) — estimativa se stoppadas em −8pts: ~−R$53k de exposição (vol 5 CC × 133).
- **Conclusão:** hoje o Modelo A **não impede nenhuma perda**. Ativá-lo como veto exigiria mais amostra (corr ≈ 0 na base total) e corrigir o registro de resultado de fechamentos manuais.

### TÓPICO 4 — ANÁLISE DE REGIME POR DIA (SelecionadorRegime)

- **Fato estrutural:** o `SelecionadorRegime` (Sessão 19, perfis NORMAL/LATERAL/EXPLOSAO/CONSERVADOR/DEFESA/AGUARDANDO) **NÃO está plugado no v22** — docstring literal "NAO esta plugado ... ainda (mercado em operacao)"; nenhuma ocorrência de REGIME nos 4 logs. Em produção só operam `DetectorModoMercado`/`ModoOperacional` (NORMAL o tempo todo — ATR C10 2.4–4.8 nunca <1.5).
- **Regime inferido (filtro de tendência interno TENDENCIA: LATERAL/tend + métricas C10):**
  - **01/09:** LATERAL 66% → virada de tendência fraca à tarde. ATR med 2.40.
  - **02/09:** LATERAL forte 84%. ATR med 2.90.
  - **03/09:** LATERAL 88% mas ATR med **3.20** (mais alta da semana; M30 sobrecomprado 80.5–87.3).
  - **04/09:** LATERAL 69% → **TENDÊNCIA ALTA à tarde** (ALTA 25.6%; ATR P90 4.6).
- **Trades vs regime:** o Core é mean-reversion e entrou **contra a tendência** em 4+ ocasiões (01/09 11:54 SELL vs TEND ALTA → −80; 01/09 17:03 SELL vs ALTA → sem PnL; 02/09 11:54 SELL vs ALTA → +40; 04/09 15:40 SELL vs ALTA contínua → sem PnL). O maior lucro (+55, 02/09 15:25) também foi SELL com estado ALTA. **Se o SelecionadorRegime tivesse veto de direção, teria cortado lucros E perdas (líquido − falso: evitaria apenas o −80 de 01/09).**
- **Confluências M15/M30:** divergência marcante em 03/09 — M15 RSI 23–37 (sobrevendido) vs M30 RSI 80–87 (sobrecomprado); as 3 compras dessa divergência deram lucro (+40/+15/+45). WR M15/M30 na maioria das entradas em zona sobrevendida/estendida (−3 a −93) — consistentes com o viés mean-reversion do Core.

### TÓPICOS 5–7 — SÍNTESE CRUZADA

5. **Causa raiz da anomalia (síntese operacional):** o mesmo loop que reenviou SELL 133×também **deixou invisível o PnL** dessas ordens (o rastreamento de posição falhou — `Posição ativa no MT5 mas posicao_atual é None`, Gerenciador de Saída DESATIVADO). A anomalia destrói a validade da métrica "PF semanal" e do shadow — corrigida pelo reparo 7 Velas aplicado (trava dupla + teto de volume + idempotência restaurada).
6. **Perfis dos 3 losses confirmam o risco SNIPER:** as 3 perdas vieram de entradas do SNIPER %R que **sobrepõem a IA e ignoram book/DOL/tendência**. Precisão do SNIPER na semana: 10 de 15 trades são dele, 12 positivos/neutros se excluirmos SL — porém 2 dos 3 fechamentos manuais também foram SELL do SNIPER contra tendência de alta.
7. **Decisão para o Core v22 (CONGELADO):** nenhuma alteração nesta semana. O padrão da semana (10W/3L, +R$155 confirmáveis) corrobora a manutenção dos parâmetros atuais. Ações sugeridas apenas como follow-ups (fora do Core): documentar fechamentos manuais com PnL no shadow CSV; auditar mudanças manuais de config fora do log do agente; avaliar plug do `SelecionadorRegime` quando fora de mercado (sessão dedicada, com OOS n≥30).

---
## 📋 ESTADO ATUAL DO SISTEMA

| Item | Valor |
|---|---|
| Símbolo | WINQ26 (front-month dinâmico) |
| SL / TP | 100 pts / 250 pts (R/R 1:2.5) |
| Volume | 5 contratos |
| Trailing | Gatilho 80 pts / Distância 40 pts (REAIS) |
| Fonte de dados | `mt5.market_book_get()` — book nativo, EA eliminado |
| Filtro Sniper | 5000cc volume + ratio 2.0 (Python) |
| Diretriz de entrada | **SEGUIR OS BIGS** (veto duro contra o lado dominante) |
| Cooldown | DESATIVADO — proteção via SL/MaxLoss/inversão |
| Timeout de posição | DESATIVADO — trade respira até SL/TP/trailing/inversão |
| IA | Keras/h5 — aprendizado incremental em tempo real |
| Horários PA1 | 09:00–12:00 e 15:00–17:30 |
| MaxLoss diário | -R$1.000 |

---

## 🛡️ PROTEÇÕES ATIVAS (Rede de Segurança)

- SL fixo 100 pts (nunca alterado)
- MaxLoss diário -R$1.000
- Veto "seguir os bigs" (nunca contra o lado dominante do book)
- Saída por inversão de fluxo (2 níveis: fecha em prejuízo / breakeven em lucro)
- Trailing stop após 80 pts de lucro
- Proteção de lucro (C12): pico > 80 pts e queda 30% → fecha
- Salvamento atômico do modelo (.tmp + os.replace)
- Save imediato após cada trade real

---

## ✅ FASES CONCLUÍDAS (Resumo)

### FASE 1 — Estrutura Base
Integração Python↔MT5, modelo Keras 4 camadas, 18 features, loop principal, dashboard Flask, seleção dinâmica de contrato.

### FASE 2 — Melhorias de Performance
Trailing stop, balanceamento BUY/SELL, modos de mercado, circuit breakers, saída inteligente, confluência, horário premium, EMA, cooldown, spread dinâmico.

### FASE 3 — Plano de Ação (jan/2026)
Trava de horário PA1 (09–12 / 15–17:30), filtro memória positiva, reset de experiências negativas.

### FASE 4 — Correções Críticas (mai/2026)
Filtro C8 desativado, contador treino corrigido, NameError/indentação/variável corrigidos, seed determinístico.

### FASE 5 — Refatoração Sniper (jun/2026)
Soberania da IA (>80% confiança protegida), confluência mínima 2 sinais, SL 100 / TP 250 dinâmico por volume.

### FASE 6 — Calibração (jun/2026)
Trailing 80/40 pts, penalidade "morte súbita" (<15s), cooldown P0, trava pós-loss, modo standby Sniper, EA Sniper V5.

### FASE 7 — Correções Pós-Produção (jul/2026)
C12 calibrado para TP=250, trailing em pontos reais (não ticks), race condition MT5/Python, scaler fallback, primeira operação aleatória removida, CSV 21 colunas.

### FASE 8 — Sincronização Sniper (jul/2026 — parcial)
- ✅ Trava timestamp, inversão de fluxo, replay buffer corrigido, CSV corrigido
- ⏳ Pendente: modo emergência desativado (8.2), ajuste escala volume (8.3), dashboard KPIs (8.5)

### FASE 9 — Arquitetura Nativa "Adeus EA/CSV" (17/07/2026)
Book nativo `market_book_get`, filtro Sniper migrado para Python, inversão de fluxo 2 níveis, diretriz "seguir os bigs", cooldown/timeout desativados, log adaptativo (84 linhas/hora em standby), warnings de libs silenciados, bloqueio PA1 eficiente.

### FASE 10 — Blindagem de Persistência + Features (18–19/07/2026)
Salvamento atômico, entropia ressuscitada, escora BID corrigida, handlers de sinal reativados, save após cada trade, decisions.csv só trades reais, código morto removido, bug do logging (force=True) corrigido.

---

## ⏰ CHECKPOINT — VETO "SEGUIR OS BIGS"

**Estado:** Veto DURO ativo (IA nunca opera contra o lado dominante do book passivo).

**Critérios para evoluir (afrouxar para override por confiança):**
- [ ] ≥ 100 trades reais no `historico_contexto_win.csv`
- [ ] Win rate ≥ 55% seguindo os bigs
- [ ] Modelo `.h5` evoluindo consistentemente (hash mudando)

**Quando atender os 3:** permitir override por confiança > 80% (Soberania da IA já existente).

**Evolução futura adicional:** considerar fluxo AGRESSIVO vs passivo (preço furando escora = seguir o agressor, não o passivo). Registrado em 17/07/2026 — caso real: BID dominante mas preço CAINDO = absorção → venda era correta.

**Última verificação:** 19/07/2026 — critérios NÃO atendidos. Veto duro mantido.

---

## 📊 ESTADO DAS 18 FEATURES

| # | Feature | Status |
|---|---|---|
| 1 | bid_qty | ✅ Viva |
| 2 | ask_qty | ✅ Viva |
| 3 | spread | ✅ Viva |
| 4 | volatility (ATR) | ✅ Viva |
| 5 | candle_type | ✅ Viva |
| 6 | entropia_book | ✅ Ressuscitada (Fase 10) |
| 7 | rsi_14 | ✅ Viva |
| 8 | volume_tick | ✅ Viva |
| 9 | preco_maior_escora_bid | ✅ Ressuscitada (Fase 10) |
| 10 | volume_maior_escora_bid | ✅ Viva |
| 11 | distancia_maior_escora_bid | ✅ Ressuscitada (Fase 10) |
| 12 | preco_maior_escora_ask | ✅ Viva |
| 13 | volume_maior_escora_ask | ✅ Viva |
| 14 | distancia_maior_escora_ask | ✅ Viva |
| 15 | liquidez_top5_bid/ask | ✅ Viva |
| 16 | is_in_trade | ⬜ Reservada (saída futura) |
| 17 | floating_profit | ⬜ Reservada (saída futura) |
| 18 | tempo_em_trade | ⬜ Reservada (saída futura) |

---

## 📈 METAS DE PERFORMANCE

| Métrica | Atual (19/07) | Meta Final |
|---|---|---|
| Taxa de acerto | ~50% (poucos dados) | > 60% |
| Lucro médio/trade | R$65 (melhor) | > R$100 |
| Operações/dia | 3–5 | < 5 |
| Drawdown máximo | R$410 | < R$300 |
| R/R ratio | 1:2.5 | 1:2.5 |
| Trailing eficácia | 100% (1 teste) | > 80% |

---

## 🟡 EM OBSERVAÇÃO (até 26/07/2026)

- [ ] Coletar 50+ operações para avaliar taxa de acerto real
- [ ] Confirmar que trailing não sai precocemente
- [ ] Monitorar viés direcional da IA
- [ ] Verificar que modelo `.h5` muda de hash após trades (aprendizado confirmado)
- [ ] Restaurar backups de dados se necessário (`.backup_reset_20260719_082047`)

---

## 🔴 PENDÊNCIAS DA FASE 8 (fazer quando houver 50+ trades)

- [ ] **8.2** — Desativar modo emergência (`LIMITE_REJEICOES = 999999` ou remover)
- [ ] **8.3** — Ajustar escala volume/entropia (`MIN_VOLUME_BOOK` → 4500, entropia mínima 0.7)
- [ ] **8.5** — Dashboard de KPIs (win rate, fator lucro, drawdown, eficácia trailing)

---

## 🟢 FASE 11 — PAINEL HFT VISUAL NO TERMINAL (PRÓXIMA)

**Objetivo:** Dashboard visual em tempo real no CMD usando a biblioteca `rich` (Python). O robô escreve estado em JSON; painel separado lê e renderiza. Sem dependência externa, sem browser.

### Layout do Painel

```
┌───────────────────────────────────────────────────────────┐
│           🤖 ROBÔ MONSTRO V2 - PAINEL HFT                 │
├───────────────────────────────────────────────────────────┤
│  STATUS: ATIVO              TEMPO ATIVO: 02:15:33         │
├───────────────────────────────────────────────────────────┤
│  CONFIANÇA IA: ████████████████████ 85%       RSI: 62     │
├───────────────────────────────────────────────────────────┤
│  FLUXO: ██████████████████████████████████████ COMPRADOR  │
│  VOLUME: BUY 3200 | SELL 1800 | RATIO 1.78                │
├───────────────────────────────────────────────────────────┤
│  PREÇO ATUAL:  175.500                                    │
│  ALVO GAIN:    175.750  (+250 pts)                        │
│  ALVO STOP:    175.400  (-100 pts)                        │
├───────────────────────────────────────────────────────────┤
│  LUCRO DIA: +R$255    OPERAÇÕES: 5    WIN RATE: 80%       │
├───────────────────────────────────────────────────────────┤
│  EVENTO: 🎯 Sinal Sniper! BUY FORTE                      │
│  SINAL: COMPRA FORTE | COOLDOWN: PRONTO                   │
└───────────────────────────────────────────────────────────┘
```

### Componentes Visuais

| Componente | Descrição |
|---|---|
| Barra de fluxo | Verde (comprador) / Vermelha (vendedor) proporcional ao ratio |
| Barra confiança IA | 0–100% com cor (azul→verde→vermelho) |
| Sinal textual | COMPRA FORTE / COMPRA / ESPERE / VENDA / VENDA FORTE |
| Preços SL/TP | Atualizados em tempo real com base nos parâmetros do robô |
| Eventos | Última ação relevante (Sniper, veto, trailing, trade fechado) |

### Arquitetura de Comunicação

```
monstro_unificado_v2.py          painel_monstro.py
       │                                │
       │  ┌──────────────────────┐      │
       ├──► monstro_dashboard_   ├──────┤
       │  │ data.json (escrita)  │      │ (leitura)
       │  └──────────────────────┘      │
       │                                │
    robô opera                     rich renderiza
    (loop ~2s)                     (refresh 4fps)
```

**Protocolo:** JSON atômico (write-then-rename para evitar leitura parcial).

### Dados Transmitidos (JSON)

```json
{
  "preco_atual": 175500.0,
  "confianca_ia": 0.85,
  "rsi_atual": 62.0,
  "vol_buy": 3200,
  "vol_sell": 1800,
  "stop_loss": 175400.0,
  "take_profit": 175750.0,
  "lucro_dia": 255.0,
  "operacoes_dia": 5,
  "win_rate_dia": 80.0,
  "evento_recente": "🎯 Sinal Sniper! BUY FORTE",
  "sinal": "COMPRA FORTE",
  "cooldown_status": "PRONTO",
  "timestamp": "2026-07-19T10:35:22"
}
```

### Plano de Implementação

| Etapa | Descrição | Estimativa |
|---|---|---|
| **11.1** | Criar `painel_monstro.py` com layout `rich` (dados simulados) | ~100 linhas |
| **11.2** | Adicionar `enviar_dados_para_painel()` no `monstro_unificado_v2.py` | ~30 linhas |
| **11.3** | Integrar chamada no loop principal (a cada ciclo) | ~10 linhas |
| **11.4** | Conectar painel ao JSON real (substituir simulação) | ~20 linhas |
| **11.5** | Testar em produção (rodar em terminal separado) | Validação |

### Dependências

- `pip install rich` (única dependência nova)
- Arquivos no mesmo diretório (`C:\AIOFEN`)
- Execução: terminal 1 = robô | terminal 2 = painel

### Lógica do Sinal Textual

| Condição | Sinal exibido |
|---|---|
| Confiança > 80% + ratio BUY > 2.0 | **COMPRA FORTE** |
| Confiança > 60% + ratio BUY > 1.5 | COMPRA |
| Confiança < 20% + ratio SELL > 2.0 | **VENDA FORTE** |
| Confiança < 40% + ratio SELL > 1.5 | VENDA |
| Qualquer outra condição | ESPERE |

---

## 🔮 FASE 12 — ESCORAS & ORDER FLOW (FUTURO — após 100+ trades)

**Visão:** IA aprende a ler escoras individuais (big players) como ímã de liquidez. "Escora segura E chama o preço."

### Princípio de Engenharia
Nº de features proporcional aos dados de treino. Adicionar INCREMENTAL e medir impacto.

### Opções (ordenadas por custo/benefício)

| Opção | Descrição | Quando |
|---|---|---|
| **1. Derivadas** | Razão escora_bid/ask, centro de gravidade da liquidez | ~100 trades |
| **2. Top-3 escoras** | +8 features (escora2/3 vol/dist de cada lado) | ~200 trades |
| **3. Absorção** | Detectar escora que segura vs que some (spoofing) | ~300 trades |
| **4. DeepLOB (CNN)** | Book como imagem — estilo fundos quant | Fase avançada |
| **5. IA de saída** | Segunda IA só para decidir quando fechar | Após IA entrada madura |

### Ideias Adicionais
- SL/TP colados em escoras fortes (stop atrás da parede)
- Fluxo agressivo vs passivo como critério de veto (evolução do "seguir os bigs")

---

## 🔬 FASE 13 — PESQUISA QUANTITATIVA + SHADOW MODE (Agosto/2026)

**Última atualização:** 20/08/2026
**Arquivo principal:** `monstro_unificado_v22.py` (evolução do v2, ~10.700 linhas)

### Estado Atual (20/08/2026)

| Item | Valor |
|---|---|
| Símbolo | WDOU26 |
| SL | 8 pts (floor `max(1.5×ATR, sl_max)`) |
| Estratégia ativa | Sniper %R (`SNIPER_APENAS=true`) |
| Cooldown sniper | 120s |
| Horário nobre | 09:15–12:30 / 14:30–17:15 (abertura 09:00–09:14 bloqueada) |
| Dashboard | `http://localhost:5001` |

### ✅ Aprovados e Operacionais
- **Sniper %R + vetos multi-TF:** edge estatístico principal do robô.
- **Log de contexto com timestamp:** primeira coluna do `historico_contexto_wdo.csv` — prepara o Modelo B (book/microestrutura + regime).
- **Infraestrutura:** rotação de logs diária, watchdog, kill-switch, cooldown, SL floor.

### ❌ Descartados (falsas hipóteses — mortas por dados)
- **Abertura WIN/WDO (09:00–09:14):** reprovada em 7 cenários (M1/M5, alvos 1:1 e 2:1, SL=TP 200/400pts, filtro véspera). WR 27–46%, todos negativos. Candle de abertura = ruído HFT.
- **Grade de Consolidação (Markov):** reprovada nos dois ativos. Comprar mínima/vender máxima sem direção = pegar faca caindo.
- **Backtests WIN encerramento:** sem edge real; resultado dependia de outlier único.

### ⏳ Em Teste Passivo (Shadow Mode) — Modelo A
- **O que é:** veto ML (Keras) com features Markov + MTF retroativo (RSI/ATR/WR em 5m/15m/30m).
- **Diagnóstico honesto:** AUC walk-forward real **0,653** (min 0,543 / max 0,758). Veto p≥0,65 positivo no OOS (PF 7,22) mas n=9 trades — inconclusivo; in-sample negativo (PF 0,41). Não integrado como veto.
- **Ação atual:** calcula e grava a probabilidade `p` em cada ordem real em `logs/modelo_a_shadow.csv` (timestamp, ticket_mt5, direcao, prob_modelo_a, resultado_bruto, resultado_pontos) SEM bloquear execução.
- **Meta:** reavaliar após 30–60 sinais gravados em produção.
- **Candidato validado aguardando decisão:** Markov Tendência WDO com stop de emergência — PF 1,47 ano / 1,88 OOS (+R$3.214, 161 trades). Ainda não conectado ao robô.

### Lições Registradas
1. Amostra curta ilude: Modelo C de abertura tinha 77,8% WR em 9 dias e −R$9 mil em 250 dias.
2. Teto de dados da corretora: M1/M5/M15 param em 29/08/2025. Validações futuras = shadow mode, não mais backtest.
3. Features MTF exigem forward-fill ao alinhar com grade M5 (viés de barras :00/:30 inflava AUC de 0,653 para 0,827).

### Próximos Passos
1. Acompanhar coleta do `modelo_a_shadow.csv` na operação ao vivo (meta 30–60 sinais).
2. Decidir integração do módulo Markov Tendência WDO (shadow ou real com 1 contrato).
3. Modelo B quando houver base de book com timestamp suficiente (2–3 semanas).

---

## 🔵 MÉDIO/LONGO PRAZO

- [ ] Sistema de alertas (Telegram/WhatsApp)
- [ ] Multi-timeframe analysis
- [ ] Backup automático em nuvem
- [ ] XGBoost como modelo complementar (ensemble) — não substituto
- [ ] Análise offline dos 806 trades WDO (56% win, +R$25.460) como benchmark

---

## 🔧 ARQUIVOS DO PROJETO

| Arquivo | Descrição |
|---|---|
| `monstro_unificado_v2.py` | Sistema principal (~8500 linhas) |
| `painel_monstro.py` | Painel HFT visual (a criar — Fase 11) |
| `modelo_monstro_win.h5` | Modelo IA treinado |
| `modelo_monstro_win.keras` | Modelo IA (formato nativo) |
| `config_win_v2.json` | Configurações WIN |
| `historico_contexto_win.csv` | Base histórica (18 features + action + reward) |
| `decisions.csv` | Log de trades reais (BUY/SELL) |
| `experiencias.json` | Buffer de experiências |
| `monstro_v2.log` | Log de execução |
| `diagnostico_monstro.py` | Script de diagnóstico |
| `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` | Este arquivo |

---

## 📋 CONFIGURAÇÃO DE REFERÊNCIA

### Filtro Sniper
| Parâmetro | Valor | Onde |
|---|---|---|
| `SNIPER_VOLUME_MIN` | 5000cc | topo do .py ou config |
| `SNIPER_RATIO_MIN` | 2.0 | topo do .py ou config |

### Alvos Dinâmicos (por volume)
| Volume | SL | TP | R/R |
|---|---|---|---|
| 5000cc+ | 100 | 250 | 1:2.5 |
| 3000cc+ | 100 | 230 | 1:2.3 |
| 2000cc+ | 100 | 220 | 1:2.2 |
| demais | 100 | 200 | 1:2.0 |

### Trailing Stop
| Parâmetro | Valor |
|---|---|
| Gatilho | 80 pts reais |
| Distância | 40 pts reais |
| Proteção C12 | pico > 80 pts, queda 30% |

### Penalidade de Score
| Situação | Score |
|---|---|
| Trade normal (>30s) | Calculado normal |
| Stop rápido (15–30s) | score × 1.5 (mín -1.0) |
| Morte Súbita (<15s) | -1.5 fixo |

---

## 🔁 PONTO DE RETOMADA — SEXTA-FEIRA 04/09/2026

**Sessão encerrada em 01/09/2026.** Estado congelado para incubação out-of-sample (n≥30).

**Já operando automaticamente (sem intervenção):**
- Monstro reiniciado às 12:10:27 com o orquestrador F3 carregado; **0 erros no `orquestrar`** pós-restart.
- Tarefas agendadas ativas: `Monstro-Start` (anti-duplicidade), `Monstro-Watchdog`, `Monstro-Fecho` (17:35).
- 7 Velas V9 (11:15) + Gatekeeper Dual + TP parcial 1:1/BE + trava macro — parametrização 100% no `config.json`.

**Agenda automática da semana:**
- **02/09 (qua)** → V9 normal (incubação trade #1).
- **03/09 (qui)** → V9 normal (incubação trade #2).
- **04/09 (sex) = Payroll** → validar trava `VETADO_MACRO` (janela 11:15 bloqueada; **nenhum trade abrir**; conferir CSV/state).

**Checklist de retomada em 04/09 (após 11:30):**
1. Verificar `logs/sete_velas_trades.csv`: presença de `VETADO_MACRO` na 04/09 e **ausência de trade real** nesse dia.
2. Confirmar no `monstro_wdo.log`: `[7VELAS ...] DIA MACRO (Payroll/FOMC) -> VETADO_MACRO`.
3. Revisar os trades reais de 02–03/09 (WR, PF, MaxDD, ganho do TP parcial em +8pts).
4. Se tudo limpo e critérios OOS seguindo favoráveis, **marcar retomada** para decisão de homologação quando n≥30.

*Mantido por: Mestre Super + Kiro AI Agent*
*Última atualização: 19/07/2026*

---

## 🔍 CORREÇÃO DE AUTÓPSIA — 01/09 (PÓS-SESSÃO)

**Autópsia original alegou:** Sniper bloqueado por gate `sniper_ratio_min=2.0` (L6845) → `continue` antes de chegar ao Sniper %R.

**Contra-evidência (código real + log):**
- O gate real está na **L7375** e **já é pulado em `SNIPER_APENAS=true`** (`if not SNIPER_APENAS and (...)`). O ratio 2.0 da raiz **NÃO** bloqueia o Sniper.
- Log de 01/09 (monstro_wdo.log) prova o bloqueador real = **veto multi-TF** (M15/M30 em consenso extremo):
  - 11:31 `%R=-80 BUY` → bloqueado `M15=-97 M30=-97`
  - 11:46 `%R=-88 BUY` → bloqueado `M15=-98 M30=-98`
  - 11:51/52 `%R=-17 SELL` → bloqueado `M15=-92 M30=-92`
  - 11:54 **`%R=-15 SELL` disparou** (fora do consenso extremo) → ticket 2517225296, **-8 pts**
- Conclusão: o veto multi-TF funcionou como projetado (bloqueou entradas contra consenso M15/M30). O trade que escapou perdeu. **NÃO mexer no `sniper_ratio_min` nem criar bypass no gate.**

**Ações executadas (passivas/seguras):**
1. Root `max_loss_diario`: -100.0 → **-1000.0** (alinha com `risk_management`; Kill-Switch em R$1.000 inalterado — engine lê ninho L810-811).
2. `historico_multitf.csv`: append a cada ciclo (33.3k linhas) → **rate-limit 1x/60s** via `_log_periodico` (mantém auditoria, corta bloat ~120x).

**Avaliação veto multi-TF:** legítimo e protetivo — manter. Rigidez p/ scalp 8SL/6TP é conservadora por design (fix 13/08). Nenhum afrouxamento sem backtest.

**Validação:** `py_compile` OK (v22 + agente), `tests/testes_pos_fix.py` **9/9 PASS**, config `ALINHADO`.

---

# 🧭 DELIBERAÇÃO DE SEXTA-FEIRA — 04/09/2026 (PÓS-FECHAMENTO)

> **Objetivo deste bloco:** consolidar a semana **01/09–04/09**, separar factos verificados de alegações de autópsia, e tomar **decisão GO/NÃO-GO** sobre as MUDANÇAS propostas nos relatórios (`para ox alpha.txt`). Nada abaixo deve ser implementado às cegas — cada item tem **estado verificado** e **critério objetivo** de decisão (VIDE SEMANA).

---

## 0. PREMISSAS VERIFICADAS EM CÓDIGO (independente — base para tudo)

| # | Alegação de autópsia | **Estado VERIFICADO (02/09)** | Veredito |
|---|---|---|---|
| 1 | "Bug 7 Velas L198: truth value of array ambiguous" | **JÁ CORRIGIDO.** Orquestrador reescrito (Fase 2, 01/09) usa `calcular_cvd_janela()` → retorna **escalar float** e `cvd_confluente = (ups>downs and cvd>0)...` (boolean escalar). **Não existe** `cvd.any()/.all()`. | ✅ Já resolvido — **não mexer** |
| 2 | "historico_multitf.csv PARADO em 08/08" | **FUNCIONANDO.** Último registro 2026.09.02 17:14. | ✅ Já resolvido |
| 3 | "Config bagunça total (sniper 2.0 vs 1.2)" | `sniper_ratio_min` **1.5** (raiz + risk), `max_loss_diario` **-1000** (raiz + risk), kill_switch **-250/-400** (agente). | 🟡 **Maioria alinhada** |
| 4 | "experiencias_wdo.json VAZIO" | **Só 3 registros.** | 🔴 **GAP REAL — priorizar** |
| 5 | "Shadow Model A correlação invertida" | Base: n=27, WR 33%, PF 0.34, -R$395 — **nunca teve poder de veto** (passivo). | 🟡 Validar, risco baixo |
| 6 | WIN "golden goose" | Backtest WIN A **original viciado**: PF 1.94, +R$654k, MaxDD -R$43k. **Corrigido 03/09 (auditoria):** PF 1.68, +R$107.734, **MaxDD -R$12.810** (ver bloco AUDITORIA abaixo). Robô em produção é **WDO**. | 🟠 **Decisão estratégica**, não bug |

**⚠️ RISCO Nº1 IDENTIFICADO (não é bug, é processo):** múltiplos agentes/sessões editando `config.json` **em paralelo** (prova: `sniper_ratio_min` virou 1.5 depois da minha sessão de 01/09 sem commit correspondente). Esta é a real ameaça à integridade — qualquer "unificação" será inútil se a escrita concorrente continuar. **Ação: single-writer lock em config/prod.**

---

## 🔍 AUDITORIA BACKTEST ARTHUR 777 — CORRIGIDO EM 03/09 (números calibrados)

**Contexto:** o backtest original do agente (`backtest_arthur777.py`) apresentava **2 vícios de metodologia** que inflavam os resultados. Auditoria feita por mim em 03/09/2026, corrigida e **validada matematicamente** (fator 2 + zero sobreposição restante).

| Vício | Antes (inflado) | Depois (corrigido) |
|---|---|---|
| **Fator 2 (dupla contagem do tick)** — `pts` medido em TICKS multiplicava `valor_por_ponto` como se fosse pontos de preço (`tick_size=0.5` → 1 ponto = 2 ticks). Todo PnL e MaxDD dobrados. | WIN A TP = R$7.500/trade | **R$3.750/trade** ✔ (bate c/ distância real em preço) |
| **Sobreposição temporal** — loop abria trade a cada sinal SEM avançar o cursor após o fechamento (≥1 posição simultânea impossível no MT5). | 50% dos trades WIN sobrepostos (até 17/dia) | **0 sobreposições** (máx 8/dia, 1 por vez) ✔ |

### RESULTADOS CALIBRADOS (5 contratos, custos reais XP RLP, 15/04–28/08/26)
| Cenário | Ativo | Trades | WR | Saldo líq | PF | Payoff | MaxDD |
|---|---|---|---|---|---|---|---|
| **A (Tendência)** | **WIN** | **229** | 31.0% | **+R$107.734** | **1.68** | 3.74 | **-R$12.810** |
| B (Scalper) | WIN | 338 | 64.2% | -R$67.510 | 0.44 | 0.25 | -R$68.501 |
| A (Tendência) | WDO | 121 | 27.3% | +R$5.786 | 1.25 | 3.34 | -R$4.913 |
| B (Scalper) | WDO | 228 | 70.2% | -R$7.052 | 0.60 | 0.25 | -R$7.397 |

**LEITURA SÊNIOR:** a **tese estatística principal se MANTÉM** — Cenário A (Tendência) > Cenário B; **WIN A segue o melhor setup** (PF 1.68, payoff 3.74, +R$107k). Mas o risco é **muito menor do que os "R$654k / -R$43k" falsos**: MaxDD real de **-R$12.810** em 229 trades (5 cts) é **dimensionável** (≤5%/trade), não 4,3x capital como os relatórios alarmistas afirmavam. **Cenário B permanece geneticamente perdedor** (payoff 0.25 < custos) — nunca subir. **WIN V2 real já existe portado para MT5** (`monstro_unificado_v2.py` + `config_win_v2.json` + `modelo_monstro_win.h5`); o NO-GO de "matar/não colocar WIN" foi baseado em número inflado — decisão deve ser reavaliada com dados calibrados em SEX 04/09.


---

## 1. ESTADO DA SEMANA (compilar SEX 18:00 — via MT5 + logs)

Semana real 01–02/09 (WDOV26, 1 ct): 8 trades | 5 W / 3 L | **62.5% WR** | PnL bruto +R$80 | **líq +R$73.60** após custos.

⚠️ **LEITURA SÊNIOR (honesta):**
- **n=8 é estatisticamente irrelevante.** 62.5% não prova edge — pode ser sorte. NÃO aumentar lote por causa disto.
- Os 3 losses de 01/09 foram **entradas contra fluxo** (multi-TF) → reforça que o veto multi-TF está **correto**, não "restritivo demais".
- Os 3 gains de 02/09 foram **a favor da tendência** → valida a direção do sistema.

**Para SEX 18:00:** gerar relatório consolidado 01–04/09 (trades, WR, PF, MaxDD, PnL líq, custos) e **marcar cada item abaixo como GO / NÃO-GO / ADIAR** com base na semana + critérios objetivos.

---

## 2. DECISÕES EM PAUTA (VOTAR SEX, IMPLEMENTAR RÁPIDO NÃO-IMEDIATO)

### 🟢 A. UNIFICAR CONFIG (verificado: 85% já feito — completar de forma SEGURA)
| Item | Ação | Critério de GO |
|---|---|---|
| A1 | **Single-writer lock** de `config.json`/`agente_config.json` (mutex p/ edição; git diff obrigatório antes de commit) | **SEMPRE — sem isso nada vale** |
| A2 | Verificar `custos_operacionais` = valores XP RLP (R$0,80 WDO / R$0,25 WIN) | Presente e coerente c/ `backtest/custos_reais.py` |
| A3 | `py_compile` config.json + `python -c "json.load(...)"` em config + agente_config | Exit 0 |
| A4 | Criar `tests/validar_config_estrutura.py` (checa 1 ocorrência de cada chave crítica + tipos) | 9/9 + novo teste PASS |

### 🟡 B. EXPERIENCIAS_WDO.JSON (GAP REAL — PRIORIDADE 1)
| Item | Ação | Critério de GO |
|---|---|---|
| B1 | Popular `experiencias_wdo.json` a partir de `decisions_wdo.csv` + `historico_contexto_wdo.csv` (feats → contexto, label = resultado real do trade) | **>100 registros** válidos |
| B2 | Alimentar automaticamente **no fecho** (`Monstro-Fecho` / fim de `orquestrar`) | Todo pregão registra experiências |
| B3 | Validar distribuição: ≥30% wins / losses (não só NÃO_AGIU) | Distribuição balanceada |

### 🟠 C. SHADOW MODEL A (validar, NÃO desligar às cegas)
| Item | Ação | Critério de GO |
|---|---|---|
| C1 | Confirmar em código que Modelo A **não tem poder de veto** (só shadow/passivo) | Verificar execução real |
| C2 | Re-analisar com n≥60 (meta) a correlação confiança×resultado | Curva monotônica OU desligar |

### 🔴 D. CENÁRIO B (SCALPER) — NUNCA subir em produção
| Item | Ação | Critério de GO |
|---|---|---|
| D1 | Confirmar que NENHUM caminho de produção invoca escalper puro (payoff<0.3) | grep: nenhuma chamada ativa |
| D2 | Se existir código morto de scalper: marcar/remover **COM TESTE** (nunca remover lógica viva às cegas) | py_compile + testes 9/9 |

### 🔴 E. MUDANÇA DE PRODUTO WDO → WIN (DECISÃO ESTRATÉGICA — NÃO é ajuste de config)
> **Ponto que os relatórios não enfatizam:** o robô em produção opera **WDO**. A recomendação "WIN A como golden goose" é **trocar de produto** — implica: símbolo, tick/point, contrato, custos, margem, corretora (WIN ≠ WDO no demo XP? confirmar contrato), gestão de risco do ativo. **Não é "ligar uma flag".**
| Item | Ação | Critério de GO |
|---|---|---|
| E1 | Alinhar com Mestre Super: **WDO (atual) × WIN × ambos** | Decisão explícita do dono |
| E2 | Se WIN: validar Margem/contrato/custos reais + Backtest A **calibrado** (MaxDD -R$12.810 em 229 trades → sizing ≤5% capital) | Paper 20 dias antes de real |
| E3 | Se manter WDO: **foco em V9 DUAL** (PF 1.44) + consolidar incubação n≥30 | n≥30 OOS |

---

## 3. PAPER TRADING / EMULAÇÃO (GATE PARA DINHEIRO REAL)

| # | Etapa | Duração | Critério de SAÍDA |
|---|---|---|---|
| P1 | Rodar produção atual em **conta demo** (sem descongelar) | até n≥30 OOS | Critérios v22.2 (WR≥45%, PF≥1.1, MaxDD≤R$3.600) |
| P2 | Se E2 (WIN): **paper dedicado em WIN** | 20 dias | PF≥1.5, MaxDD<15% capital, ≥30 trades |
| P3 | Nenhum **aumento de lote** antes de P1/P2 GO | — | GO só com critérios batidos |

---

## 4. CHECKLIST EXECUTÁVEL SEXTA (pós 17:40 fecho — ORDEM)

```powershell
# 0) Single-writer: confirmar ninguém editando (git status limpo)
cd C:\AIOFEN
git status

# 1) Unificação segura (A)
python -m py_compile config.json
python -c "import json;json.load(open('config.json'));json.load(open('agente_config.json'));print('configs OK')"

# 2) Experiências (B) — popular + validar
python scripts/popular_experiencias.py        # (criar) exporta decisions->experiencias
python -c "import json;print(len(json.load(open('experiencias_wdo.json'))))"   # >100

# 3) Bugs reais (D/C) — só se existirem
python -m py_compile monstro_unificado_v22.py agente_monstro_core.py sete_velas_util.py

# 4) Testes
python tests/testes_pos_fix.py                # 9/9
python tests/validar_config_estrutura.py      # (novo) PASS

# 5) Backtests (referência, não regressão)
python backtest/backtest_sete_velas.py         # gera CSV
python backtest/backtest_arthur777.py          # 4 cenários
```

## 5. ENTREGÁVEIS MÍNIMOS DE SEXTA
- [ ] Relatório consolidado da semana 01–04/09 (com custos).
- [ ] Decisão explícita registrada p/ **cada** item A–E (GO/NÃO-GO/ADIAR).
- [ ] `experiencias_wdo.json` **>100** registros + alimentação no fecho ativa.
- [ ] Single-writer lock documentado (não necessariamente codificado — pode ser **protocolo/checklist**).
- [ ] Se E1=WIN: paper WIN P2 montado. Se E1=WDO: incubação V9 continua até n≥30.
- [ ] Commit + push de configs/scripts validados (com diff revisado).

---

# 🧪 FASE 6 — MÓDULO WIN V2 EM PARALELO (SIMULADO DUPLO WDO+WIN)

> **Decisão do Mestre (04/09):** a descoberta WIN A (PF 1.68, Payoff 3.74, MaxDD -R$12.810 calibrado) **não fica na gaveta**. Roda em **conta Simulador MT5, em paralelo** com o WDO, via **multi-instância** (2 processos Python independentes) — sem gambiarra de Keras, sem poluir o WDO que já funciona.

## 6.1 ARQUITETURA (2 PROCESSOS / 1 CONTA SIMULADOR)

```
[MetaTrader 5 (Conta Demo/Simulador)] ──┬──> Processo 1: monstro_unificado_v22.py  (WDO)  magic 7007
                                        └──> Processo 2: monstro_unificado_v2.py   (WIN)  magic 2002
```
- **Isolamento total de memória Keras**: cada processo carrega seu próprio `.h5` (`modelo_monstro_wdo` / `modelo_monstro_win.h5`) em memória separada. Sem conflito de thread/estado.
- **Magic separados** impedem o MT5 de misturar posições.
- **Kill-switch independente** por processo (config próprio).

## 6.2 ⚠️ CORREÇÕES AO RELATÓRIO (o relatório propõe valores INCORRETOS — usar os reais)
| Item | Relatório propõe | **CORRETO (verificado em código)** |
|---|---|---|
| Nome do script | "criar monstro_win_v2.py" | **JÁ EXISTE** `monstro_unificado_v2.py` |
| Config | "criar config_win.json" | **JÁ EXISTE** `config_win_v2.json` — apenas **alinhar** |
| **tick_size WIN** | **5.0** ❌ | ⚠️ **CONFLITO no repo:** `custos_reais.py`=0.5tick/2pts, engine/config=0.2 & ticks_por_ponto=10000. **GATE 6.2a os resolve lendo o símbolo real** |
| **valor ponto WIN** | "0.20/ct" | Backtest auditado usou **R$1,00/pt × 5ct = R$5,00/pt** (Cenário A). Confirmar contrato real no GATE |
| magic | "2002" (inexistente) | Definir **de verdade** em `config_win_v2.json → geral.magic_number` (atual usa default 123457) |
| sniper_ratio_min | 1.5 | Alinhar `config_win_v2.json` (atual **2.0**) → **1.5** |
| modelo | "modelo_win_v2.h5" | `modelo_monstro_win.h5` |

### 6.2a 🔑 GATE OBRIGATÓRIO — VALIDAR UNIDADE DO SÍMBOLO WIN NO MT5 (ANTES DE LIGAR)
> O repo tem **3 tick_sizes WIN conflitantes** (0.2, 0.5, 5.0). **Não chutar.** O passo mais importante de toda a Fase 6: conectar ao MT5 da conta **Simulador** e ler as **specs reais** do contrato WIN vigente, comparando com a config antes de abrir qualquer ordem.
```python
# scripts/validar_simbolo_win.py  (a criar)
import MetaTrader5 as mt5
info = mt5.symbol_info("WINV26")          # contrato vigente (ou WIN$)
print("point     =", info.point)          # tick em preço
print("trade_tick_value =", info.trade_tick_value)  # R$/tick
print("trade_tick_size  =", info.trade_tick_size)   # preço por tick
# validação: config_win_v2.json contrato.tick_size/ticks_por_ponto devem reproduzir
#            R$/ponto observado no símbolo. Se divergir >1e-6 → BLOQUEIA, corrige config.
```
**Critério de GO:** `validar_simbolo_win` imprime specs reais e **bate** com config; só então prosseguir à incubação.

## 6.3 PASSOS EXECUTÁVEIS (SEX 04/09 18:00 — ORDEM)
```powershell
# 0) GATE 6.2a — validar unidade do símbolo WIN no MT5 simulado (BLOQUEANTE)
python scripts/validar_simbolo_win.py

# 1) Alinhar config WIN (não criar do zero) — USANDO specs reais do GATE
#    - geral.magic_number = 2002
#    - sniper_ratio_min = 1.5
#    - max_loss_diario = -1000.0
#    - contrato.symbol_prefix = WIN
#    - contrato.tick_size / ticks_por_ponto  ← valores do GATE 6.2a (NÃO 0.2 cego)
#    - sl_points / tp_points: Cenário A Tendência (SL 200 / TP 750 no backtest auditado)
#      → o config_win_v2 atual (100/250) é config clássica v2, NÃO o Arthur A.

# 2) Validar WIN engine (compila + modelo carrega)
python -m py_compile monstro_unificado_v2.py
python -c "from tensorflow.keras.models import load_model; m=load_model('modelo_monstro_win.h5'); print('WIN modelo OK', m.layers[0].input_shape)"

# 3) Reusar/ajustar iniciar_monstro_win_v2.bat (já existe) apontando pro config_win_v2.json
#    Garantir MODO SIMULADOR (sem ordens reais) e magic 2002

# 4) Disparar DUPLO (rodar_simulador_duplo.bat):
#    - Processo 1: python monstro_unificado_v22.py   (WDO, magic 7007)
#    - Processo 2: python monstro_unificado_v2.py    (WIN, magic 2002, simulado)
#    (nome real do script WIN é monstro_unificado_v2.py, NÃO monstro_win_v2.py)

# 5) Log consolidado: historico_simulado_duplo.csv (um registro/dia por ativo)
```

## 6.4 MÉTRICAS DE CORTE PARA LIBERAÇÃO DE CAPITAL REAL (30 DIAS DE INCUBAÇÃO SIMULADO)
| Critério | Meta | Status |
|---|---|---|
| Trades executados (WIN) | ≥ 30 | — |
| Profit Factor real (WIN) | ≥ 1.50 | — |
| Drawdown diário respeitando travas | R$ 250 / R$ 400 (kill-switch WIN) | — |
| Zero exceção de tipo/desconexão nos logs | 0 falhas | — |
| MaxDD acumulado (WIN) | ≤ 20% do capital simulado | — |

> **Anteparo de honestidade:** incubação simulada ≠ garantia de lucro real. NÃO aumentar lote no WDO nem misturar capital até os critérios 6.4 batidos. WIN real exige validar **margem/contrato/custos reais** (potencialmente outra corretora/terminal que o demo XP atual) — decisão separada, agendada.

*Mantido por: Mestre Super + Kiro AI Agent — revisado e direcionado por Ox Alfa (dev/quant sênior)*
