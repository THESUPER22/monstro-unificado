# 🚀 ROADMAP OFICIAL — MONSTRO TRADER V2
**Última atualização:** 28/08/2026
**Versão:** Monstro Unificado V22 (Engine v22.1 — Robustness & Audit Patch)
**Arquivo principal:** `monstro_unificado_v22.py`
**Status geral:** Fase 10 concluída; Engine v22.1 blindada contra perdas fantasmas e dados corrompidos

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
  - Correção cirúrgica do bug de deslocamento de velas (`n_velas`) no backtest original.

### 📌 Próximos Passos (Semana 31/08 – 04/09)
- [ ] **Observação Passiva**: Coleta do Modelo A em Shadow Mode até atingir $n \ge 30\text{--}60$ com o CSV corrigido.
- [ ] **Monitoramento Horário**: Auditagem da janela das 09:15 às 10:30 para avaliar se a perda concentrada em regime de baixa volatilidade (ATR < 2.5) exige regra de bloqueio.
- [ ] **Congelamento de Parâmetros**: Manter Whitelist intacta, Sniper %R fixo e piso de Stop Loss em 8,0 pts no WDO.

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

*Mantido por: Mestre Super + Kiro AI Agent*
*Última atualização: 19/07/2026*
