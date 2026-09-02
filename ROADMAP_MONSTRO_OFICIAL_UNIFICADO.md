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
| 6 | WIN "golden goose" | Backtest WIN A: PF 1.94, +R$654k, **MaxDD -R$43k**. Robô em produção é **WDO**. | 🟠 **Decisão estratégica**, não bug |

**⚠️ RISCO Nº1 IDENTIFICADO (não é bug, é processo):** múltiplos agentes/sessões editando `config.json` **em paralelo** (prova: `sniper_ratio_min` virou 1.5 depois da minha sessão de 01/09 sem commit correspondente). Esta é a real ameaça à integridade — qualquer "unificação" será inútil se a escrita concorrente continuar. **Ação: single-writer lock em config/prod.**

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
| E2 | Se WIN: validar Margem/contrato/custos reais + Backtest A **sem overfitting** (MaxDD -R$43k exige sizing ≤2% capital) | Paper 20 dias antes de real |
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

*Mantido por: Mestre Super + Kiro AI Agent — revisado e direcionado por Ox Alfa (dev/quant sênior)*
