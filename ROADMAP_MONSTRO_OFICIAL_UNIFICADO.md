# 🚀 ROADMAP OFICIAL UNIFICADO — MONSTRO TRADER V2
**Última atualização:** 17/07/2026
**Versão:** Monstro Unificado V2 — **ARQUITETURA NATIVA (Book direto do MT5)**
**Arquivo principal:** `monstro_unificado_v2.py`
**Status:** FASE 9 IMPLEMENTADA (Book Nativo) — Aguardando teste em produção 15h

---

## 📋 ESTADO ATUAL DO SISTEMA

| Item | Valor |
|---|---|
| Símbolo | WINQ26 (front-month dinâmico) |
| SL | 100 pontos |
| TP | 250 pontos (R/R 1:2.5) |
| Volume | 5 contratos |
| Trailing Gatilho | 80 pontos **REAIS** |
| Trailing Distância | 40 pontos **REAIS** |
| Dashboard | http://localhost:5002 |
| **Fonte de dados** | **BOOK NATIVO MT5 (`market_book_get`) — EA/CSV ELIMINADOS** |
| Filtro Sniper (Python) | **5000cc / ratio 2.0** (constantes `SNIPER_VOLUME_MIN` / `SNIPER_RATIO_MIN`) |
| Diretriz de entrada | **SEGUIR OS BIGS** — veto de operar contra o lado dominante do book |
| Cooldown | **DESATIVADO** (`COOLDOWN_ATIVO = False`) — proteção via SL/MaxLoss/inversão |
| Timeout de posição | **DESATIVADO** — trade respira até SL/TP/trailing/inversão |
| IA Status | Keras/h5 mantido (aprendizado incremental em tempo real) |

---

## ✅ HISTÓRICO DE IMPLEMENTAÇÕES (Ordem Cronológica)

### 📦 FASE 1 — Estrutura Base
- [x] Integração Python ↔ MetaTrader5 API
- [x] Leitura de book via arquivo CSV/JSON do EA
- [x] Modelo IA Keras/TensorFlow (4 camadas densas)
- [x] Features de entrada (18 variáveis)
- [x] Loop principal com monitoramento de posições
- [x] Dashboard Flask (porta 5002)
- [x] Seleção dinâmica de contrato front-month

### 📦 FASE 2 — Melhorias de Performance (+19.5%)
- [x] **M1** Trailing Stop Inteligente (+3%)
- [x] **M2** Balanceamento BUY/SELL (+2%)
- [x] **M3** Modos de Mercado — CONSERVADOR/NORMAL (+2%)
- [x] **M4** Circuit Breakers Essenciais (+1.5%)
- [x] **M5** Saída Inteligente de Posição (+1.5%)
- [x] **M6** Sistema de Confluência (+4%)
- [x] **M7** Filtro de Horário Premium (+2%)
- [x] **M8** Detector de Tendência EMA (+3%)
- [x] **M9** Cooldown Inteligente (+1.5%)
- [x] **M10** Filtro de Spread Dinâmico (+1%)

### 📦 FASE 3 — Plano de Ação (25/01/2026) — Ciclo de perdas interrompido
- [x] **PA1** Trava de Horário: apenas 09:00–12:00 e 15:00–17:30
- [x] **PA2** Filtro de Memória: treina só com `lucro > 0`
- [x] **PA3** Reset de Memória da IA (limpeza de experiências negativas)

### 📦 FASE 4 — Correções Críticas (mai/2026)
- [x] **C8** Filtro de qualidade de setup desativado temporariamente (C8: SETUP FORÇADAMENTE APROVADO)
- [x] **C9** Contador de treinamento conta só experiências lucrativas (`lucro > 0`)
- [x] Erro `NameError: name 'acao' is not defined` em `registrar_resultado_confluencia` corrigido
- [x] Erro de indentação nas linhas 376–377 corrigido
- [x] Variável `detector_tenden` corrigida para `detector_tendencia`
- [x] `tf.random.set_seed(42)` adicionado para determinismo no treino

### 📦 FASE 5 — Refatoração Sniper (05/06/2026) ← **ÚLTIMA GRANDE REFATORAÇÃO**

#### 🔒 5.1 — Soberania da IA (>80% confiança)
- [x] IA com probabilidade > 0.8 ou < 0.2 **NÃO pode ser invertida** pela Confluência
- [x] Log: `🔒 IA ALTA CONFIANÇA CONFIRMADA` / `🔒 INVERSÃO BLOQUEADA`
- [x] Implementado em `verificar_confluencia()` e no loop principal

#### 🎯 5.2 — Confluência Sniper (mínimo 2 sinais)
- [x] Confluência exige **≥ 2 sinais técnicos** para validar qualquer entrada
- [x] Com < 2 sinais → retorna `"NADA"`, 0.0
- [x] Log: `⚠️ CONFLUÊNCIA INSUFICIENTE: BUY=1, SELL=0 (mínimo 2 sinais)`

#### 📏 5.3 — Alvos Ampliados (anti-violinada)
- [x] **SL:** 30–90 pts → **100 pts**
- [x] **TP base:** 35 pts → **250 pts**
- [x] Alvos dinâmicos por volume:
  - 5000cc+: SL 100 / TP 250 (R/R 1:2.5)
  - 3000cc+: SL 100 / TP 230 (R/R 1:2.3)
  - 2000cc+: SL 100 / TP 220 (R/R 1:2.2)
  - demais: SL 100 / TP 200 (R/R 1:2.0)

### 📦 FASE 7 — Correções Pós-Produção (13–15/07/2026) ← **CONCLUÍDA**

#### 🐛 7.1 — GerenciadorDeSaida C12 incompatível com TP=250pts (CRÍTICO)
**Problema:** Trade abriu BUY em 177590, chegou a ~75pts de lucro, e o C12 saiu prematuramente
- REGRA 1 (Timeout): 90s sem lucro → saía antes do alvo de 250pts
- REGRA 2 (Proteção): pico > 15pts e caiu 25% → disparava com qualquer oscilação normal
- REGRA 3 (Estagnação): 120s com lucro < 10pts → muito agressivo
- **Ambas as instâncias** (linhas ~147 e ~1932) estavam com valores antigos

**Correção aplicada (ambas as instâncias):**
- REGRA 1: Timeout 90s → **300s** (5 minutos)
- REGRA 2: pico > 15pts / 25% → **pico > 80pts / 30%** (1/3 do alvo de 250)
- REGRA 3: 120s/10pts → **480s/20pts** (8 minutos)

#### 🐛 7.2 — Trailing hardcoded ignorava config 80/40 (CRÍTICO)
**Problema:** Segunda instância da REGRA 4 usava `>= 15` e `5 * TICK_SIZE` fixos
- Ignorava completamente `self.config['trailing_gatilho_pts']` = 80
- Movia o SL de 177490 → 177565 em 23 segundos (antes do gatilho de 80pts)
- Resultado: trade stopado em -20 em vez de buscar 177840 (+250pts)

**Correção:** Substituído `>= 15` e `5 * TICK_SIZE` por `self.config['trailing_gatilho_pts']` e `self.config['trailing_distancia_pts'] * TICK_SIZE`

#### 🐛 7.3 — Short-circuit no bloco de Confluência pós-NADA
**Problema:** Mesmo quando `prever_acao` retornava `NADA` pelo cooldown P0, o código:
1. Chamava `modelo.predict()` novamente (custo computacional)
2. Calculava confluência desnecessariamente
3. Gerava logs confusos como `🔒 INVERSÃO BLOQUEADA: IA=NADA`

**Correção:** Adicionado short-circuit antes do bloco de confluência:
```python
if acao_predita == "NADA" and confianca_predita == 0.0:
    acao_para_executar = "NADA"
    confianca_decisao = 0.0
elif sistema_confluencia:
    # ... calcula confluência só se IA não retornou NADA
```

#### ✅ 7.4 — EA Sniper V5 confirmado em produção
**Observado nos logs MT5:**
- `SINAL SNIPER ENVIADO! Vol: ~14.500cc | Ratio: ~1.52–1.62` — funcionando perfeitamente
- Python recebe `🎯 [SNIPER]` no log de leitura do book
- Volume massivo (14.500cc) com desequilíbrio real detectado

#### 🐛 7.5 — Primeira operação aleatória removida (13/07/2026)
**Problema:** Na inicialização, a variável `primeira_operacao = True` fazia o robô entrar aleatoriamente (BUY ou SELL) **antes da IA ter qualquer contexto**. Isso causava:
1. Entrada sem análise no primeiro ciclo
2. Conflito de fechamento: C12 tentava fechar por "proteção de lucro", mas o TP do MT5 já havia fechado → `order_send None` × 3 tentativas

**Correção:**
- Removida a variável `primeira_operacao` e o bloco `if/else`
- A IA decide desde o primeiro ciclo normalmente (sem random)
- Log `🎲 Primeira decisão aleatória` não aparece mais

#### 🐛 7.6 — Verificação de posição antes de fechar (race condition MT5/Python)
**Problema:** `fechar_posicao_atual()` chamada mesmo quando MT5 já fechou a posição pelo TP/SL
- Causava 3 tentativas de `order_send None` com logs de erro falsos
- A posição estava fechada (lucro R$130 no TP), mas o Python não sabia

**Correção:** Antes de tentar fechar, verifica se a posição ainda existe no MT5:
```python
posicoes_mt5 = mt5.positions_get(symbol=SYMBOL)
posicao_ainda_aberta = any(p.ticket == ticket for p in posicoes_mt5)
if not posicao_ainda_aberta:
    logging.info("✅ Posição já foi fechada pelo MT5 (TP/SL). Sem ação necessária.")
else:
    # Tenta fechar com até 3 tentativas
```

#### 🐛 7.7 — Erro de CSV histórico rebaixado de ERROR para WARNING
**Problema:** `❌ Erro ao carregar experiências do CSV: 'reward'` aparecia como ERROR em toda inicialização
- CSV antigo usa colunas `lucro`/`score_distancia`, novo usa `reward`
- O sistema já corrigia automaticamente, mas logava como erro crítico falso

**Correção:** `logging.error` → `logging.warning` com mensagem clara de autocorreção

#### 🐛 7.8 — Scaler NotFittedError corrigido (15/07/2026)
**Problema:** `MinMaxScaler instance is not fitted yet` em loop — robô travado sem conseguir decidir
- Scaler perdia estado fitted após encerramento forçado pelo agendador de tarefas
- Erro se propagava em loop infinito a cada 2 segundos

**Correção:** Verificação `check_is_fitted()` antes de `transform()`. Se não fitted, faz auto-fit com dados atuais como fallback:
```python
try:
    check_is_fitted(scaler_global)
except:
    scaler_global = MinMaxScaler()
    df[colunas_numericas] = scaler_global.fit_transform(df[colunas_numericas])
```

#### 🐛 7.9 — Trailing Stop convertia ticks em vez de pontos reais (15/07/2026 — CRÍTICO)
**Problema:** `lucro_em_pontos` era calculado dividindo por `TICK_SIZE(0.2)`, resultando em **ticks** não pontos
- Com gatilho "80", na verdade ativava com apenas **16 pontos reais** (80 ticks ÷ 5)
- SL era movido 2 segundos após a entrada → trade stopado em -15 imediatamente
- Distância trailing: `40 * 0.2 = 8 pontos` de folga (impossível de sobreviver)

**Correção (AMBAS as instâncias do GerenciadorDeSaida):**
```python
# ANTES (bug):
lucro_em_pontos = (preco_entrada - preco_atual) / TICK_SIZE  # → ticks
distancia_trailing_preco = config['trailing_distancia_pts'] * TICK_SIZE  # → 8pts

# DEPOIS (correto):
lucro_em_pontos = (preco_entrada - preco_atual)  # → pontos reais
distancia_trailing_preco = config['trailing_distancia_pts']  # → 40pts reais
```

**Resultado confirmado em produção:**
- Trade SELL 177790: trailing ativou após 90s (lucro ~85pts > gatilho 80pts) ✅
- SL movido: 177885 → 177745 → 177725 (40pts acima do melhor preço) ✅
- Lucro: R$65 ✅

#### 🐛 7.10 — CSV histórico recriado com esquema correto (15/07/2026)
**Problema:** CSV recriado com 13 colunas antigas em vez das 21 atuais
- Cada gravação nova (21 colunas) corrompia o CSV com esquema de 13
- Warning `Expected 13 fields, saw 21` a cada ciclo

**Correção:** Esquema de recriação atualizado para 21 colunas (18 features + action + reward)

#### 🐛 7.11 — `order_send None` tratado como posição já fechada (15/07/2026)
**Problema:** `fechar_posicao_atual` falhava quando MT5 já havia fechado pelo TP/SL
- `order_send` retornava None porque a posição não existia mais

**Correção:** Após falha, verifica se ticket ainda existe no MT5:
```python
posicoes_check = mt5.positions_get(symbol=SYMBOL)
if not any(p.ticket == posicao_atual.ticket for p in posicoes_check):
    logging.info("✅ Posição já foi fechada pelo MT5")
    return True
```

#### ✅ 7.12 — EA Sniper calibrado para 5000cc / ratio 2.0 (14/07/2026)
**Evolução dos parâmetros do EA:**
- v1: 1500cc / 1.5 ratio → disparava a cada 1-3s (inútil para WIN)
- v2: 3500cc / 1.8 ratio → ainda muito frequente
- v3 (atual): **5000cc / 2.0 ratio** → dispara apenas com desequilíbrio institucional real

---

### 📦 FASE 8 — Sincronização Sniper Avançada ← **PRÓXIMA FASE (pendente)**

**Objetivo:** Transformar o robô em "Caçador Silencioso" que reage apenas a sinais de ultra-relevância.

#### 🎯 8.1 — Trava de Sincronia por Timestamp (anti-dados-velhos)
- [x] **IMPLEMENTADO 15/07/2026**
- [x] Variável `timestamp_inicializacao` salva momento do boot
- [x] Verifica se `timestamp` do JSON do EA é POSTERIOR à inicialização
- [x] Se dado é antigo → ignora com log `🔒 TRAVA TIMESTAMP: Ignorando dado antigo`
- [x] Quando EA atualiza com dado novo → libera com `✅ TRAVA TIMESTAMP LIBERADA`
- [x] Evita operações com dados velhos na reinicialização

#### 🎯 8.2 — Desativar Modo Emergência (LIMITE_REJEICOES)
- [ ] Definir `LIMITE_REJEICOES_EMERGENCIA = 999999` (ou remover)
- [ ] Sniper de 5000cc pode ficar horas sem operar — isso é CORRETO
- [ ] Robô não deve "forçar" operações por rejeição acumulada

#### 🎯 8.3 — Ajuste de Escala de Volume no Python
- [ ] MIN_VOLUME_BOOK → 4500 (margem para 5000 do EA)
- [ ] Score qualidade: +3 para vol >= 5000, +2 para vol >= 4000
- [ ] Entropia mínima → 0.7 (caos direcional institucional)

#### 🎯 8.4 — Correção do Treinamento (colunas CSV + replay buffer)
- [x] **CSV corrigido** — 21 colunas (18 features + action + reward)
- [x] **Replay buffer corrigido (16/07/2026)** — batch agora inclui TODAS as experiências reais (BUY/SELL), não apenas positivas
- [x] **Causa raiz:** `obter_batch_replay()` filtrava apenas `indices_positivos` → se os 3 trades no contador eram losses/breakeven, batch ficava vazio → treino nunca executava
- [x] **Fix:** Batch agora pega qualquer BUY/SELL → IA aprende com acertos E erros

#### 🎯 8.5 — KPIs de Monitoramento
**Metas definidas:**
| KPI | Meta |
|---|---|
| Taxa de Acerto (Win Rate) | > 60% |
| Fator de Lucro | > 1.5 |
| Lucro Médio por Trade | > R$100 |
| Operações/Dia | < 5 |
| Drawdown Máximo | < 5% |
| Tempo Médio Trade | 30s – 5min |
| Eficácia Trailing Stop | > 80% |

#### 🎯 8.6 — Saída por Inversão de Fluxo (big players inverteram)
- [x] **IMPLEMENTADO 15/07/2026**
- [x] Monitoramento contínuo do book durante posição aberta
- [x] Se SELL e BID/ASK ratio ≥ 2.0 favorecendo BUY → move SL para breakeven
- [x] Se BUY e ASK/BID ratio ≥ 2.0 favorecendo SELL → move SL para breakeven
- [x] Log: `🔄 INVERSÃO DE FLUXO DETECTADA! Movendo SL para breakeven`
- [x] Estratégia conservadora: não fecha direto, move SL para entrada

#### ⏱️ 6.1 — Trailing Stop Calibrado para alvos longos
- [x] `TRAILING_GATILHO`: 30 pts → **80 pts** (só protege após movimento sólido)
- [x] `TRAILING_DISTANCIA`: 15 pts → **40 pts** (respira sem ser stopado cedo)
- [x] `trailing_gatilho_pts` no GerenciadorDeSaida: 30 → **80**
- [x] `trailing_distancia_pts` no GerenciadorDeSaida: 15 → **40**
- [x] Variáveis do `config.json` removidas (não sobrescrevem mais os valores fixos)

#### ☠️ 6.2 — Penalidade por "Morte Súbita"
- [x] Em `obter_lucro_ultima_ordem`: se `lucro < 0` e `tempo_trade < 15s` → `score_dist = -1.5`
- [x] Se `lucro < 0` e `tempo_trade < 30s` → penalidade média (`score_dist * 1.5`, mínimo `-1.0`)
- [x] Log: `⚠️ MORTE SÚBITA DETECTADA (Xs): Penalizando IA com score -1.5`
- [x] IA aprende a evitar entradas em falsos rompimentos

#### 🛑 6.3 — Cooldown como Prioridade 0 (topo absoluto)
- [x] Verificação de cooldown movida para **primeira linha** de `prever_acao()`
- [x] Se cooldown ativo → retorna `"NADA", 0.0` **sem ler book, sem consultar IA**
- [x] Log: `🛑 [P0] COOLDOWN ATIVO (Xs restantes) — Bloqueio total`
- [x] Cooldown duplicado no Filtro 3 removido (evita log duplicado)

#### 🔒 6.4 — Trava Rígida Pós-Loss (180s mínimo)
- [x] Após qualquer loss: cooldown mínimo garantido de **180 segundos**
- [x] 1 loss → 300s (5 min) | 2 losses → 600s (10 min) | 3+ → 900s (15 min)
- [x] Log: `🔒 TRAVA PÓS-LOSS: Xs bloqueado | Nenhum sinal pode ultrapassar esta trava!`

#### 😴 6.5 — Modo Standby Sniper (reativo ao EA)
- [x] Quando `book_data` retorna `None` → dorme 2s com log `DEBUG` silencioso
- [x] Log reduzido: `😴 Standby: Aguardando sinal institucional do EA Sniper...`
- [x] Evita spam de logs quando EA Sniper não envia dados
- [x] Compatibilidade com EA antigo mantida (sem `relevancia` = aceita normalmente)
- [x] EA Sniper V5 envia `"relevancia": true` → log adicional `🎯 [SNIPER]`

#### 🤖 6.6 — EA Sniper V5 (MQL5)
- [x] EA novo criado: `EA_BookData_Sniper_V5.mq5`
- [x] **Filtro 1:** Volume total mínimo > 1500cc (ignora sardinhas)
- [x] **Filtro 2:** Desequilíbrio mínimo 1.5x entre BID/ASK
- [x] Só escreve arquivo quando **ambos os filtros passam** (modo evento, não polling)
- [x] Envia flag `"relevancia": true` no JSON para o Python
- [x] Usa `OnBookEvent` (máxima responsividade, sem timer constante)

---

## 🔍 DIAGNÓSTICO — POR QUE O ROBÔ LUCRAVA "NO ESCURO" (HISTÓRICO)

> ⚠️ **SUPERADO PELA FASE 9 (17/07/2026):** esta análise refere-se à era do EA + CSV.
> Com o book nativo (`market_book_get`) e o filtro Sniper no Python, o problema de
> latência/ruído/dados-congelados do EA foi eliminado na raiz. Mantido como registro histórico.

**Descoberta (26/06/2026):**
- Quando o EA estava **fora do gráfico** (book congelado), o robô lucrava consistentemente
- Com o EA ativo gerando dados a cada 100ms, o robô só perdia
- Ajustar para 1000ms não resolveu

**Causa Raiz identificada:**
- O EA antigo enviava **todos os ticks do book** — incluindo ruído de sardinhas
- O robô tentava reagir a micro-oscilações sem relevância institucional
- Sem dados (book congelado), o robô só operava por indicadores técnicos puros → lucrava

**Solução implementada:**
- EA Sniper V5 filtra **apenas big players** (>1500cc + desequilíbrio >1.5x)
- Python em **modo standby silencioso** esperando sinal institucional
- Robô se comporta como se estivesse "no escuro" mas com dados de qualidade

---

## 📊 CONFIGURAÇÃO ATUAL COMPLETA (17/07/2026)

### Filtro Sniper NATIVO (Python — EA ELIMINADO)
| Parâmetro | Valor | Onde ajustar |
|---|---|---|
| `SNIPER_VOLUME_MIN` | **5000cc** | topo do `monstro_unificado_v2.py` (ou `config.sniper_volume_min`) |
| `SNIPER_RATIO_MIN` | **2.0** (ratio) | topo do `monstro_unificado_v2.py` (ou `config.sniper_ratio_min`) |
| Máximo níveis book | 10 (todos os retornados por `market_book_get`) | — |
| Fonte | `mt5.market_book_get(SYMBOL)` (nativo) | — |
| Símbolo | WIN (dinâmico: WINQ26) | detecção automática |

> ⚠️ O `EA_BookData_Sniper_V5.mq5` NÃO é mais necessário. Toda a filtragem de volume/ratio acontece no Python (função de gate no loop de entrada).

### Horários de Operação (PA1)
- 09:00 – 12:00 (manhã)
- 15:00 – 17:30 (tarde)

### Alvos (SL/TP) — DINÂMICOS POR VOLUME (em `executar_ordem`)
| Volume no book | SL | TP | R/R |
|---|---|---|---|
| 5000cc+ (cenário Sniper real) | 100 pts | 250 pts | 1:2.5 |
| 3000cc+ | 100 pts | 230 pts | 1:2.3 |
| 2000cc+ | 100 pts | 220 pts | 1:2.2 |
| demais (com dados) | 100 pts | 200 pts | 1:2.0 |
| fallback sem volume | 90 pts (`config.sl_points`) | 35 pts (`config.tp_points`) | — |

> Como o filtro Sniper exige **5000cc**, os trades reais caem sempre na linha 5000cc+ (SL 100 / TP 250). O fallback 90/35 do `config_win_v2.json` praticamente nunca dispara.
> **Volume operação:** 5 contratos (`volume_padrao` = 5.0).

### Trailing Stop (GerenciadorDeSaida)
| Parâmetro | Valor | Unidade |
|---|---|---|
| Gatilho | 80 | pontos REAIS de preço |
| Distância | 40 | pontos REAIS de preço |
| Proteção lucro (C12) | pico > 80pts, queda 30% | pontos REAIS |
| Timeout | 300s (5min) sem lucro | |
| Estagnação | 480s (8min) com <20pts | |

### Filtros Ativos
| Filtro | Valor |
|---|---|
| Volume mínimo book (`MIN_VOLUME_BOOK`) | 300cc (pré-filtro; gate Sniper exige 5000cc) |
| Filtro Sniper (gate de entrada) | 5000cc + ratio 2.0 (Python nativo) |
| Score qualidade | ≥ 4/11 (C8 desativado) |
| Confluência | ≥ 2 sinais técnicos |
| RSI | livre |
| Spread máximo | 10 pts (`config.max_spread`) |

### Cooldown (em segundos)
| Situação | Cooldown |
|---|---|
| Win / Break-even | 240s (4 min) |
| 1 Loss | 300s (5 min) |
| 2 Losses | 600s (10 min) |
| 3+ Losses | 900s (15 min) |
| Mínimo pós-loss | 180s (garantido) |

### Penalidade de Score por Duração
| Situação | Score |
|---|---|
| Trade normal (>30s) | calculado normal |
| Stop rápido (15–30s) | score * 1.5 (mínimo -1.0) |
| Morte Súbita (<15s) | -1.5 (fixo) |

---

## 🚀 PRÓXIMOS PASSOS (Atualizado 15/07/2026)

### 🟢 CONCLUÍDO (Fase 7)
- [x] EA Sniper V5 testado e calibrado (5000cc / 2.0)
- [x] Trailing Stop corrigido — pontos reais, não ticks
- [x] C12 calibrado para TP=250pts
- [x] Scaler NotFittedError resolvido
- [x] Primeira operação aleatória removida
- [x] Race condition MT5/Python tratada
- [x] Morte Súbita penalizando IA corretamente
- [x] Short-circuit pós-NADA implementado

### 🟡 EM OBSERVAÇÃO (1 semana — até 22/07/2026)
- [ ] Coletar 50+ operações para avaliar taxa de acerto
- [ ] Confirmar que trailing não sai precocemente (verificado 1× com sucesso)
- [ ] Monitorar viés SELL da IA (normal — poucos dados ainda)
- [ ] Verificar se `🧊 DADOS CONGELADOS` persiste (normal com 5000cc)
- [ ] Resolver problema do Agendador de Tarefas (SIGTERM na inicialização)

### 🔴 FASE 8 — Sincronização Sniper (após 50+ trades)
- [ ] 8.1: Trava de sincronia por timestamp
- [ ] 8.2: Desativar modo emergência
- [ ] 8.3: Ajustar escala volume/entropia no Python
- [ ] 8.4: Correção treinamento (colunas CSV 21→21)
- [ ] 8.5: Dashboard de KPIs

### 🟢 MÉDIO PRAZO (agosto 2026)
- [ ] Interface gráfica Tkinter
- [ ] Sistema de alertas (Telegram/WhatsApp)
- [ ] Multi-timeframe analysis
- [ ] Backup automático em nuvem

---

## 📈 METAS DE PERFORMANCE (Atualizado 15/07/2026)

| Métrica | Antes (jun/2026) | Atual (15/07) | Meta Final |
|---|---|---|---|
| Taxa de acerto | ~30% | ~50% (poucos dados) | >60% |
| Lucro médio/trade | R$14 | R$65 (melhor trade) | >R$100 |
| Operações/dia | 10–20 | 3–5 | <5 |
| Drawdown máximo | R$1000 | R$410 (14/07) | <R$300 |
| R/R ratio | 1:1.5 | 1:2.5 | 1:2.5 |
| Trailing eficácia | 0% (saía cedo) | 100% (1 teste) | >80% |

---

## 🔧 ARQUIVOS DO PROJETO

| Arquivo | Descrição |
|---|---|
| `monstro_unificado_v2.py` | Sistema principal (8500+ linhas) |
| `EA_BookData_Sniper_V5.mq5` | EA Sniper — novo |
| `EA_BookData_WIN_CORRIGIDO.mq5` | EA antigo (v4.1) — compatível |
| `modelo_monstro_win.h5` | Modelo IA treinado |
| `modelo_monstro_win.keras` | Modelo IA (formato nativo Keras) |
| `config.json` | Configurações principais |
| `experiencias.json` | Buffer de experiências |
| `decisions.csv` | Log de todas as decisões |
| `historico_contexto_win.csv` | Base histórica de contextos |
| `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` | Este arquivo |

---

## 📋 LOGS ESPERADOS COM O NOVO SISTEMA

```
# Cooldown Prioridade 0
🛑 [P0] COOLDOWN ATIVO (180s restantes) — Bloqueio total, aguardando...

# Trava pós-loss
🔒 TRAVA PÓS-LOSS: 300s bloqueado após 1 loss(es) | Nenhum sinal pode ultrapassar esta trava!

# Modo Standby Sniper
😴 Standby: Aguardando sinal institucional do EA Sniper...

# Dados Sniper chegando
✅ JSON válido e completo (utf-16): 10 bids, 10 asks 🎯 [SNIPER]

# IA Alta Confiança protegida
🔒 IA ALTA CONFIANÇA (BUY): 0.87 - Confluência não pode inverter
🔒 INVERSÃO BLOQUEADA: IA=BUY (conf:0.87) PREVALECE sobre Confluência=SELL

# Confluência insuficiente
⚠️ CONFLUÊNCIA INSUFICIENTE: BUY=1, SELL=0 (mínimo 2 sinais)

# Morte Súbita detectada
⚠️ MORTE SÚBITA DETECTADA: Trade durou 3.2s com prejuízo de R$-27.50 | Penalizando IA com score -1.5

# Trailing calibrado
🚀 VOLUME MONUMENTAL (5000cc+): SL=100, TP=250 (R/R 1:2.5)
```

---

*Mantido por: Mestre Super + Kiro AI Agent*
*Última atualização: 07/07/2026*

---

### 📦 FASE 9 — ARQUITETURA NATIVA "ADEUS EA E CSV" (17/07/2026) ← **IMPLEMENTADA**

**Objetivo:** Eliminar o gargalo do EA MQL5 escrevendo em `book_data_win.csv` e o Python lendo o arquivo (latência de disco, race conditions, "dados congelados", JSON incompleto utf-16). O robô passa a ler o book (Depth of Market) **direto da memória do terminal** via `mt5.market_book_get(SYMBOL)`. HFT caseiro de verdade.

#### 🚀 9.1 — Book Nativo (`ler_book_nativo`)
- [x] Nova função `ler_book_nativo()` usa `mt5.market_book_get(SYMBOL)`
- [x] Converte tupla `BookInfo` → mesmo dict `{'bids':[{price,volume}], 'asks':[...]}` que o código já usava
- [x] **Mapeamento correto** (documentação oficial MT5): `type=2/4` = COMPRA (BID) | `type=1/3` = VENDA (ASK)
- [x] Usa `volume_dbl` (mais preciso) com fallback para `volume`
- [x] Ordena: melhor BID (maior preço) e melhor ASK (menor preço) primeiro
- [x] `mt5.market_book_add(SYMBOL)` na inicialização (subscrição em tempo real)
- [x] `mt5.market_book_release(SYMBOL)` no encerramento seguro

#### 🗑️ 9.2 — Remoção Total do CSV/EA
- [x] Removidas as funções `_ler_book_csv_core`, `ler_book_csv_with_retry`, `ler_book_csv`
- [x] Removida variável global `BOOK_FILE_PATH` (não usada mais)
- [x] Removido log DEBUG que imprimia o book bruto a cada ciclo (poluía os logs)
- [x] Substituídos os 4 call sites de `ler_book_csv()` por `ler_book_nativo()`
- [x] `verificar_estado_book` fora do pregão retorna True direto (book nativo vazio = normal)
- [x] EA `EA_BookData_Sniper_V5.mq5` **não é mais necessário** para operar

#### 🎯 9.3 — Filtro Sniper migrado do EA para o Python
- [x] Constantes ajustáveis no topo do arquivo:
  - `SNIPER_VOLUME_MIN = 5000` (volume total bid+ask nos 10 níveis)
  - `SNIPER_RATIO_MIN = 2.0` (desequilíbrio mínimo entre os lados)
- [x] Também aceitam override via `config.json` (`sniper_volume_min` / `sniper_ratio_min`)
- [x] Gate no loop de entrada: se `total < 5000` OU `ratio < 2.0` → `😴 Standby: Aguardando Big Players...` (log a cada ~10s, sem spam)
- [x] Ajuste fácil sem recompilar EA (basta editar as constantes e reiniciar)

#### 🔄 9.4 — Inversão de Fluxo em 2 NÍVEIS (melhorada)
- [x] Agora usa book nativo em tempo real e lucro flutuante REAL (`positions_get().profit`)
- [x] **NÍVEL 1** — fluxo virou contra E posição em **PREJUÍZO** → `fechar_posicao_atual()` IMEDIATO (corta a perda, "o mercado veio na cara")
  - Log: `🔄🚨 INVERSÃO DE FLUXO CONTRA POSIÇÃO EM PREJUÍZO! ... SAINDO IMEDIATAMENTE`
- [x] **NÍVEL 2** — fluxo virou contra E posição em **LUCRO/zero** → move SL para breakeven (protege e deixa correr)
  - Log: `🔄 INVERSÃO DE FLUXO (posição no lucro)! ... Movendo SL para breakeven`
- [x] Usa `SNIPER_RATIO_MIN` como gatilho de inversão

#### 🔒 9.5 — Proteção anti-dados-antigos preservada
- [x] `ler_book_nativo()` inclui `timestamp` = tempo do último tick (`symbol_info_tick().time`)
- [x] A TRAVA DE TIMESTAMP existente continua funcionando: mercado fechado → tick velho → bloqueia operação com dado antigo
- [x] Elimina a antiga brecha do "trade lucrativo voltou na nossa cara" (dados velhos do CSV)

#### ✅ 9.6 — Decisões de Engenharia (defendidas)
- [x] **XGBoost REJEITADO (por ora):** o diferencial do robô é o aprendizado incremental em tempo real (Keras `fit` a cada trade). XGBoost exige retreino em lote e perde essa vantagem. A latência (5ms vs ~180ms) é irrelevante para quem opera 3–5x/dia com cooldown de 4min. **Keras/h5 mantido.**
- [x] **Trava pós-loss 180s mantida:** proteção real contra revenge trading em mercado choppy pós-loss.
- [x] **Corte TOTAL do CSV (sem fallback):** arquitetura limpa; há backup do robô antigo caso necessário.

#### 🧪 9.7 — Validação
- [x] `py_compile` OK (sem erros de sintaxe)
- [x] Modelos `modelo_monstro_win.h5` / `.keras` atualizados em 16/07 17:10 (IA salvando aprendizado)
- [ ] **Teste em produção pendente** — retorno das 15h (mercado aberto)

---

## 🚀 PRÓXIMOS PASSOS (Atualizado 17/07/2026)

### 🟢 CONCLUÍDO (Fase 9)
- [x] Book nativo `market_book_get` substituindo EA + CSV
- [x] Filtro Sniper 5000/2.0 migrado para constantes no Python
- [x] Inversão de fluxo em 2 níveis (sai em prejuízo / breakeven em lucro)
- [x] Proteção timestamp preservada via tick time

### 🟡 A VALIDAR NO TESTE DAS 15H
- [ ] Confirmar `📗 Book nativo ATIVADO para WINQ26` no log de boot
- [ ] Confirmar logs `😴 Standby: Aguardando Big Players...` quando sem volume
- [ ] Confirmar `📊 Mercado (nativo)` com liquidez real
- [ ] Confirmar que NÃO há operação imediata com dado antigo na inicialização
- [ ] Confirmar hash MD5 do `modelo_monstro_win.h5` muda após trade (IA aprendeu)

### 🔵 FUTURO (Fase 10 — possível)
- [ ] Reavaliar XGBoost como modelo COMPLEMENTAR (ensemble), não substituto
- [ ] Enriquecer features com `account_info()` (margem/saldo) e `positions_get()` (floating em tempo real na decisão de saída)


#### 🐛 9.8 — BUG CRÍTICO: `corrigir_csv_historico()` zerava TODOS os rewards a cada boot (17/07/2026)
**Sintoma:** No boot das 14:10 o filtro C1 achava `7 POSITIVAS`; no boot das 14:27, `0 POSITIVAS`. Inspeção do `historico_contexto_win.csv` mostrou a coluna `reward` **inteira zerada** (min=0, max=0) nas 5000 linhas — inclusive nas 34 operações reais (20 SELL + 14 BUY).

**Causa raiz:** A função `corrigir_csv_historico()` (roda em TODO boot) tinha uma "limpeza de outliers" por IQR que incluía a coluna `reward`:
```python
for col in ['bid_qty', 'ask_qty', 'volume_tick', 'reward']:
    q1 = df[col].quantile(0.25); q3 = df[col].quantile(0.75)
    ... df[col] = df[col].clip(lower_bound, upper_bound)
```
Como ~99% das linhas são `NAO_AGIU` com reward=0, os quartis Q1=Q3=0 → limites [0,0] → `clip` **zerava TODAS as recompensas reais**. Ou seja: a cada reinício o robô APAGAVA o sinal de aprendizado acumulado.

**Correção:** Removida a coluna `reward` do loop de clipping (mantidas só as features de volume `bid_qty/ask_qty/volume_tick`). Reward é sinal de recompensa, não feature — nunca deve ser normalizado por IQR.
```python
for col in ['bid_qty', 'ask_qty', 'volume_tick']:  # reward REMOVIDO
    ...
```
**Impacto:** A partir de agora as recompensas persistem entre reinícios → a IA acumula aprendizado de verdade. Os 7 positivos históricos não foram recuperáveis (sem backup do CSV), mas os pesos do modelo `.h5` estavam intactos (carregam normalmente).

#### 🧹 9.9 — Logs limpos (fim da "propaganda") + monitoramento ao vivo (17/07/2026)
- [x] Removidos todos os `(+X% eficácia)`, `+19.5% TOTAL`, `VOLUME MONUMENTAL` e o bloco de tiers de volume (marketing vazio)
- [x] Init dos 11 subsistemas consolidada em 1 linha real (`🧩 Subsistemas ativos: ...`)
- [x] Banner do "PLANO DE AÇÃO" reduzido a 1 linha objetiva
- [x] Log `Nenhuma posição ativa...` rebaixado para DEBUG (era spam por ciclo)
- [x] **Log de mercado enriquecido:** `📊 WINQ26 | Preço: X | Spread | BID/ASK | Desequilíbrio Nx | lado dominante`
- [x] **💓 Heartbeat da posição (a cada ~5s):** tipo, entrada→atual, pontos, lucro flutuante R$ real, SL/TP


#### 🐛 9.10 — HOTFIX CRÍTICO: TRAVA TIMESTAMP bloqueava TODAS as operações (17/07/2026, 15:xx)
**Sintoma:** No pregão das 15h o robô observava o book ao vivo (preço/volumes atualizando) mas NÃO operava. Log: `🔒 TRAVA TIMESTAMP: Ignorando dado antigo do EA (timestamp EA: 1784300400.0 | Robô iniciou: 14:47:01)`.

**Causa raiz:** Na migração para book nativo (9.5), passei a preencher `book['timestamp']` com `tick.time` do MT5. Mas `tick.time` vem no **fuso horário do servidor da corretora** (não é POSIX/UTC local), enquanto `timestamp_inicializacao = time.time()` é relógio local. A diferença (~26h) fez a TRAVA interpretar todo dado como "antigo" → `continue` infinito → nunca chegava ao filtro Sniper/decisão.

**Correção:** `ler_book_nativo()` agora usa `time.time()` (relógio local, mesma base do `timestamp_inicializacao`) no campo `timestamp`. O book nativo é sempre AO VIVO (mercado fechado → `market_book_get` vazio → retorna None antes), então o risco de "dado velho de sessão anterior" — exclusivo do CSV/EA — não existe. A TRAVA passa a validar corretamente.

#### 🧹 9.11 — Nível de log ajustado para INFO (17/07/2026)
- [x] `setup_logging()`: `logging.DEBUG` → `logging.INFO` (arquivo e console)
- [x] Elimina o spam de DEBUG (rajada de "Nenhuma posição ativa", "EA Data", logs internos de libs)
- [x] Mantém tudo que importa: mercado ao vivo, Sniper, decisões, heartbeat, trailing, erros


### 📦 FASE 9.12 — DIRETRIZ "SEGUIR OS BIGS" + FIM DOS COOLDOWNS/TIMEOUTS (17/07/2026)

**Contexto:** primeiro trade real pós-correção do reward (SELL) perdeu -R$100 porque a IA operou CONTRA o lado dominante do book (comprador 2.04x) e o mercado subiu na cara. Decisão do mestre super: o robô deve SEGUIR OS BIG PLAYERS, e os cooldowns/timeouts não fazem sentido quando o filtro Sniper (ratio 2.0) já é raro e restritivo.

#### 🐋 9.12.1 — Veto "Seguir os Bigs" (entrada)
- [x] Antes de `executar_ordem`, se a decisão (BUY/SELL) for CONTRA o lado dominante do book (BID vs ASK), a ordem é **vetada** → vira NAO_AGIU (a IA aprende o contexto).
- [x] A IA continua decidindo QUANDO e SE opera; só não pode brigar com a fita.
- [x] Log: `🐋 VETO SEGUIR OS BIGS: decisão X é CONTRA o lado dominante...`

#### ❌ 9.12.2 — Cooldowns desativados
- [x] `COOLDOWN_ATIVO = False` — elimina trava pós-loss (300s) e cooldown geral (240s).
- [x] Justificativa: com ratio 2.0 (raro), os cooldowns só impediam o robô de operar/aprender.

#### ❌ 9.12.3 — Timeout de posição desativado
- [x] GerenciadorDeSaida: REGRA 1 (timeout sem evolução) e REGRA 3 (estagnação) DESATIVADAS.
- [x] A posição respira até: SL 100pts | TP 250pts | Trailing (REGRA 4) | Inversão de fluxo.
- [x] REGRA 2 (proteção de lucro após 80pts) MANTIDA.

#### 🛡️ Proteções que RESTAM (rede de segurança)
SL fixo 100pts · MaxLoss diário -R$1000 · Veto seguir os bigs · Saída por inversão de fluxo (2 níveis).

---

## ⏰ CHECKPOINT RECORRENTE — REAVALIAR O VETO "SEGUIR OS BIGS"
> **INSTRUÇÃO PARA O AGENTE (Kiro): toda vez que ler este ROADMAP, PARAR AQUI e verificar este checkpoint.**

**Estado atual:** veto DURO ativo (a IA NUNCA opera contra o lado dominante do book).

**Motivo do veto duro:** a IA ainda é novata — histórico de reward recém-restaurado (bug 9.8 corrigido em 17/07). Confiança dela ainda não é confiável. Fase de "aprender a andar seguindo o fluxo".

**⚡ QUANDO EVOLUIR (afrouxar para override por confiança):**
Quando a IA tiver um histórico real robusto, trocar o veto duro por um **override inteligente**:
> "A IA só pode operar CONTRA os bigs se estiver com confiança MUITO alta (>0.80 / <0.20) — usando o mecanismo de Soberania da IA já existente."

**Critérios objetivos para liberar o override (checar a cada leitura do roadmap):**
- [ ] IA acumulou **≥ 100 trades reais** (BUY/SELL com reward != 0) no `historico_contexto_win.csv`.
- [ ] Win rate geral **≥ 55%** seguindo os bigs (base sólida provada).
- [ ] Modelo `.h5` mudou de hash várias vezes (treino real acontecendo de forma consistente).

**Se os 3 critérios forem atendidos:** propor ao mestre super implementar o override por confiança (a IA ganha o direito de fadear o book quando MUITO convicta) e medir se ela tem edge de contra-fluxo (detecção de armadilha/absorção).

**Enquanto NÃO atender:** manter o veto duro. Registrar aqui a data da última verificação.
- Última verificação: 17/07/2026 — critérios NÃO atendidos (IA com ~1 trade real). Veto duro mantido.


#### 🧹 9.13 — Diagnóstico de arquivos corrigido + confirmação cooldown/timeout (17/07/2026)
- [x] `diagnostico_monstro.py`: lista de arquivos corrigida para os nomes REAIS do WIN v2 (`monstro_unificado_v2.py`, `config_win_v2.json`, `modelo_monstro_win.h5/.keras`, `historico_contexto_win.csv`). Antes apontava para nomes antigos/WDO inexistentes → avisos falsos a cada diagnóstico.
- [x] "Arquivo opcional não encontrado" rebaixado de WARNING → DEBUG (fim do spam).
- [x] **Confirmado:** `COOLDOWN_ATIVO = False` (cooldown/trava pós-loss mortos).
- [x] **Confirmado:** timeout de posição morto — REGRA 1/3 do GerenciadorDeSaida ativo desativadas E as funções `monitorar_posicao_ativa` / `verificar_saida_inteligente` (que tinham timeouts de 120s/90s) são CÓDIGO MORTO (sem call sites). Prova: trade das 15:38 ficou 16min aberto sem timeout fechar.


#### 🩹 9.14 — Heartbeat da posição confiável (17/07/2026)
- [x] Removida a condição `datetime.now().second % 5 == 0` do log 💓 do lucro flutuante.
- [x] **Causa:** ficava fora de fase com o `time.sleep(INTERVALO_CHECK_SCORE=5s)` do loop → o 💓 sumia por minutos e reaparecia (dois ciclos de 5s se cancelando).
- [x] Agora loga a cada iteração (o loop já é pausado em 5s) → lucro flutuante aparece confiável em tempo real. O monitoramento real (SL/TP/inversão) nunca foi afetado; era só o log.


#### 🧹 9.15 — Fim do spam de log na decisão (17/07/2026)
**Problema:** sem cooldown, quando um desequilíbrio 2.0+ contra a IA persistia, o bloco de decisão rodava a cada ~1s cuspindo ~15 linhas (incluindo o dicionário gigante do contexto) + gravava `decisions.csv` e experiência NAO_AGIU a cada segundo → log ilegível e churn de disco.
**Correções:**
- [x] Rebaixados para DEBUG (repetiam a cada decisão): `Contexto para decisão`, `Expectativa`, `Histórico truncado`, `Book - Ratio`, os 3 logs de `salvar_decisao_csv`, `CONFLUÊNCIA`+`Sinais BUY/SELL`, `IA ALTA CONFIANÇA (BUY/SELL/CONFIRMADA/MANTIDA)`, `Decisão Final`.
- [x] Veto "seguir os bigs": log com **throttle de 15s** (`VETO_LOG_INTERVALO_S`) — não spamma mais; e **removida a gravação de NAO_AGIU a cada 1s** (floodava memória/disco — o veto é regra fixa, não aprendizado).
- [x] Sleep pós-veto 1s → **5s** (re-checa a cada 5s; não precisa 1s para "não brigar").
**Resultado:** no INFO ficam só: pulso de mercado (📊, ~5s), standby (😴), veto (🐋, ~15s), heartbeat da posição (💓) e os trades reais (entrada/saída/P&L). O resto vai para DEBUG.


---

## 💡 OBSERVAÇÃO DE OURO — VETO x FLUXO AGRESSIVO (17/07/2026, ~17:00)
> **INSTRUÇÃO PARA O AGENTE: ler junto com o CHECKPOINT do veto "seguir os bigs".**

**Caso real observado:** entre 16:56 e 17:00 o preço do WINQ26 CAIU forte (175285 → 175145, −140 pts). Durante TODA a queda o book mostrava **BID dominante (~2.0x compra)**, então a IA quis **VENDER** (leu a queda corretamente) e o **veto bloqueou** ("bigs comprando").

**A sacada técnica:**
- **Profundidade PASSIVA do book** (`bid_qty` vs `ask_qty`) ≠ **fluxo AGRESSIVO** (quem realmente move o preço com ordens a mercado).
- BID grande + preço caindo = compradores passivos sendo **ABSORVIDOS/atropelados** por vendedores agressivos → cenário BAIXISTA. Vender era o certo.
- O veto atual usa só a profundidade passiva → nesse momento **divergiu do preço** e barrou uma venda provavelmente lucrativa.

**Implicação para a evolução do veto (quando os critérios do checkpoint forem atendidos):**
Não afrouxar apenas por "confiança da IA > 80%". Considerar também a **direção do preço vs o lado dominante passivo**:
- Se o preço está caindo forte CONTRA um BID dominante passivo (absorção) → permitir SELL (seguir o fluxo agressivo).
- Se o preço está subindo forte CONTRA um ASK dominante passivo → permitir BUY.
- Ideia de implementação futura: comparar a variação de preço nos últimos N segundos com o lado dominante; se o preço "fura" o lado passivo, o veto NÃO deve bloquear (o fluxo agressivo é o verdadeiro "big").

**Status:** apenas REGISTRADO como aprendizado. Veto duro (por profundidade) mantido enquanto a IA é novata. Reavaliar junto com o checkpoint (≥100 trades / win rate ≥55% / h5 evoluindo).


#### 🔇 9.16 — Log adaptativo: silencioso em standby, completo em operação (17/07/2026)
**Pedido do mestre super:** em operação, logar à vontade; em standby, só um "sinal de vida" (~60/hora); o robô é SEMPRE prioridade (nenhuma mudança na lógica/velocidade — só na frequência de ESCRITA do log).
**Implementado (helper `_log_periodico(chave, intervalo)` — só controla frequência de log):**
- [x] 📊 Pulso de mercado (standby): de cada 5s → **1x a cada 60s** (preço + book + desequilíbrio = "está vivo + estado do mercado").
- [x] 😴 Standby Sniper: de cada 10s → **1x a cada 300s**.
- [x] 👁️ Observando: de cada 30s → **1x a cada 300s**; status de bloqueios só loga se houver bloqueio ativo.
- [x] 🛡️ Verificação periódica do modelo + "✅ Modelo íntegro" + "✅ Diagnóstico OK": → **DEBUG** (continuam RODANDO, só não logam).
- [x] 💓 Heartbeat da posição: mantido a cada ~5s ("log à vontade em operação").
- [x] Condições (ratio 2.0 → decisão/veto/trade) continuam logando o evento (veto com throttle de 60s).
**Resultado:** standby caiu de ~1200 linhas/hora para **~84/hora**. Em operação, log completo. O robô continua lendo book e decidindo a cada ciclo — zero impacto na performance.


#### 🔇 9.17 — Silenciados warnings benignos das libs (TF/sklearn) (17/07/2026)
- [x] `TF_CPP_MIN_LOG_LEVEL='3'` movido para ANTES do `import tensorflow` (só assim silencia o log C++ repetido `NodeDef ... use_unbounded_threadpool`).
- [x] `warnings.filterwarnings('ignore', category=UserWarning)` — remove `sklearn: X has feature names...` e `TF: experimental_run_functions_eagerly...` (repetiam a cada predict).
- [x] `tf.get_logger().setLevel('ERROR')`.
- [x] Confirmado em produção (boot 17:23): pulso 📊 1x/60s, veto 🐋 1x, standby 😴 1x — log adaptativo (9.16) funcionando. Esta 9.17 remove o resto do ruído das bibliotecas.


#### 🚫 9.18 — Bloqueio de horário PA1 sem churn nem spam (17/07/2026)
**Problema:** após 17:30 (fora da janela PA1, mas mercado ainda aberto até 18:30), o robô processava decisão + salvava NAO_AGIU + treinava a cada ~2s só para bloquear no fim → spam de log (`🚫 PA1 HORÁRIO BLOQUEADO` + `⏸️ Não agindo`) e desperdício de CPU/disco.
**Correções (o bloqueio às 17:30 CONTINUA — só ficou eficiente e silencioso):**
- [x] Guarda de horário ANTECIPADA no loop (só no ramo sem posição): se `not horario_permitido()` → loga 1x/300s (`🚫 Fora do horário PA1...`) e `sleep(30)` + continue. Não processa decisão/salva/treina à toa. Posições abertas continuam sendo monitoradas normalmente.
- [x] Log `🚫 PA1 HORÁRIO BLOQUEADO` (em `prever_acao`) com throttle 300s.
- [x] Log `⏸️ Não agindo: NADA` com throttle 60s (evita spam em horário de operação quando dá NADA repetido).


---

### 📦 FASE 10 — BLINDAGEM DE PERSISTÊNCIA + RESSURREIÇÃO DAS FEATURES (18/07/2026) ← **IMPLEMENTADA**

**Contexto:** Autópsia completa revelou por que a IA NUNCA aprendeu em +1 ano:
1. **6 de 18 features estavam mortas** (constantes) — a IA aprendia com 1/3 de parede branca.
2. **O modelo não persistia** de forma confiável entre reinícios.
3. **2000+ operações reais** (recuperadas do `monstro.log` de 176MB: 806 trades WDO, 56% win, +R$25.460) nunca viraram treino limpo — mas são de WDO (mini dólar), instrumento diferente do WIN atual. Decisão: **opção C** — consertar o pipeline e deixar o WIN aprender limpo no instrumento certo. WDO fica para análise offline futura (XGBoost).

#### 🔧 10.1 — Salvamento atômico (anti-corrupção)
- [x] `salvar_modelo()` agora salva em `.tmp` e troca via `os.replace()` (atômico no NTFS)
- [x] Se o robô morrer NO MEIO do save, o `.h5`/`.keras` bom permanece intacto
- [x] Vale para ambos os formatos (h5 e keras)

#### ⭐ 10.2 — Entropia RESSUSCITADA (a joia do projeto)
- [x] **Causa raiz:** `salvar_experiencia_csv` gravava `min(1, entropia)` → toda entropia real (~2.6-3.0) virava 1 no CSV
- [x] `corrigir_csv_historico` também re-esmagava com `.clip(0,1)` a cada boot
- [x] **Correção:** ambos agora preservam o valor real (só piso 0). A IA finalmente "vê" a entropia — distingue book lateral de explosivo

#### 🔧 10.3 — Escora BID corrigida
- [x] Bug: `analisar_profundidade_book` lia a chave `'p'` em vez de `'price'`
- [x] Consequência: `preco_maior_escora_bid` sempre 0 e `distancia_maior_escora_bid` sempre 999
- [x] **Correção:** `.get('price', 0.0)` — 2 features vivas de novo (parede de compra dos bigs)

#### 🛡️ 10.4 — Handlers de sinal reativados (item A)
- [x] `SIGTERM`, `SIGINT` e `SIGBREAK` (Windows) reativados
- [x] Ctrl+C / fechar janela / taskkill não-forçado → roda `encerramento_seguro_completo` e SALVA antes de morrer
- [x] ⚠️ `taskkill /F` não pode ser capturado — por isso existe o item B

#### 💾 10.5 — Save após cada trade (item B)
- [x] Modelo salvo IMEDIATAMENTE após cada trade real fechado
- [x] Mesmo com `taskkill /F`, o aprendizado do último trade já está no disco
- [x] Antes só salvava após treino-com-melhoria/18:20 → fechar no meio do dia perdia a sessão

#### 📊 Estado das 18 features após a Fase 10
- **15 vivas:** bid_qty, ask_qty, spread, volatility, candle_type, **entropia_book (ressuscitada)**, rsi_14, volume_tick, **preco_maior_escora_bid (ressuscitada)**, volume_maior_escora_bid, **distancia_maior_escora_bid (ressuscitada)**, preco_maior_escora_ask, volume_maior_escora_ask, distancia_maior_escora_ask, liquidez_top5_bid/ask
- **3 inofensivas (sempre 0 na entrada):** is_in_trade, floating_profit, tempo_em_trade — só teriam valor DURANTE a posição (decisão de saída). Mantidas para não mudar N_FEATURES=18 e não apagar o modelo.

#### 🧹 10.6 — decisions.csv enxugado
- [x] `salvar_decisao_csv` agora grava SOMENTE trades reais (BUY/SELL). NADA/NAO_AGIU não é mais gravado (o treino nunca leu esse arquivo — só o `historico_contexto_win.csv` alimenta a IA)

#### 🧹 10.7 — Limpezas anteriores (mesma sessão)
- [x] Classe `GerenciadorDeSaida` duplicada (código morto ~110 linhas) removida
- [x] Log `🔒 TRAVA PÓS-LOSS` rebaixado para DEBUG (cooldown está desativado, log só fazia volume)
- [x] `LIMITE_REJEICOES_EMERGENCIA` 30 → 999999 (modo emergência morto; filtro Sniper já faz o trabalho)

**Validação:** `py_compile` OK em todas as alterações.


---

## 🔮 FASE FUTURA (IDEIAS) — VISÃO DE ESCORAS INDIVIDUAIS / ORDER FLOW
> **Registrado 18/07/2026 — visão do mestre super. NÃO implementado ainda. Discussão/planejamento.**

**Visão do mestre super (tape reading profissional):**
- Grandes ordens passivas (escoras/big players: XP, Morgan, BTG etc.) funcionam como **ímã de liquidez**: "uma boa escora segura o preço E chama o preço". O mercado tende a caminhar em direção ao volume grande pendurado (para as instituições conseguirem executar).
- Objetivo: a IA aprender a ler **escoras individuais** (não só o book agregado) e antecipar "para onde o mercado quer ir antes de ir", além de usar as escoras para posicionar SL/TP (colar o stop atrás de uma escora forte).
- Diretriz de simplicidade: manter UMA IA (não criar segunda IA agora). Manter as 18 features atuais (as 3 de posição ficam reservadas para uma futura "IA/lógica de saída").

**O que a IA JÁ vê hoje (base):**
- Agregado: `bid_qty`, `ask_qty`, `liquidez_top5_bid/ask`
- Maior escora individual de cada lado: `preco/volume/distancia_maior_escora_bid` e `_ask` (agora VIVAS após a Fase 10)

### ⚠️ PRINCÍPIO DE ENGENHARIA (ler antes de adicionar features)
Nº de features deve ser **proporcional à quantidade de dados de treino**. Com poucos trades WIN, MUITAS features → overfitting (a IA decora ruído). Regra: **adicionar features de escora de forma INCREMENTAL e medir impacto** — nunca despejar "um caminhão de dados" de uma vez. Só expandir quando houver dados suficientes para justificar.

### Opções técnicas (ordenadas por custo/benefício)

**OPÇÃO 1 — Escoras individuais top-3 de cada lado (recomendada, incremental)**
- Adicionar `escora2_vol/dist` e `escora3_vol/dist` (bid e ask) → +8 features (18→26)
- Dá à IA a "textura" do book (várias paredes), não só a maior
- Custo baixo, alinhado à visão. Fazer só quando houver ~100+ trades WIN
- ⚠️ Muda N_FEATURES → recria modelo (aceitável no momento certo)

**OPÇÃO 2 — Features derivadas de desequilíbrio de escoras (baixíssimo custo)**
- Ex.: razão maior_escora_bid/maior_escora_ask; distância ponderada por volume; "centro de gravidade" da liquidez
- Captura "para onde o peso está" SEM explodir o nº de features
- Boa relação custo/benefício — poucas features, muito sinal

**OPÇÃO 3 — Detecção de absorção/parede (série temporal)**
- Feature que detecta escora que SEGURA o preço (preço bate e não passa = suporte real) vs escora que SOME (spoofing/isca)
- Exige comparar book atual com anteriores (memória de curto prazo)
- Alto valor (é o "segura e chama" do mestre), custo médio

**OPÇÃO 4 — Book como "imagem" (CNN / estilo DeepLOB) — NÃO recomendada agora**
- Tratar os 10 níveis do book como matriz e usar rede convolucional (o que grandes fundos fazem)
- Pesado, complexo, contra a filosofia de simplicidade. Só considerar em fase muito avançada

**OPÇÃO 5 — Segunda IA dedicada à SAÍDA — adiada**
- IA só para decidir QUANDO fechar (usaria is_in_trade, floating_profit, tempo_em_trade + escoras)
- Válida, mas dobra complexidade. Só após a IA de ENTRADA estar madura

### Recomendação do engenheiro
1. Primeiro: acumular dados WIN LIMPOS com as 18 features já corrigidas (Fase 10).
2. Quando houver ~100+ trades: implementar **OPÇÃO 2** (derivadas, custo mínimo) e medir.
3. Se der sinal: evoluir para **OPÇÃO 1** (top-3 escoras) e depois **OPÇÃO 3** (absorção).
4. OPÇÕES 4 e 5 só em fase madura.
5. Usar SL/TP colados em escoras fortes (ideia do mestre) pode entrar junto com a Opção 3.
