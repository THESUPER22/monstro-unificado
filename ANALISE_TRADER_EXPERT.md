# ANALISE TRADER EXPERT - Monstro v22 (WDO)
# Data: 10/11/2026
# Base: codigo (monstro_unificado_v22.py), roadmap, autopsias, logs

## 1. VISAO GERAL DO SISTEMA

O Monstro v22 e um sistema de trading automatizado para WDO (Mini Dolar) que opera
via MetaTrader 5, com dashboard Flask, IA (Keras/TensorFlow), e multiplas estrategias.
O sistema tem 25 componentes/estrategias, 14 filtros, e opera em modo de alta seletividade.

### Arquitetura
- Robo principal: monstro_unificado_v22.py (11.639 linhas)
- Dashboard: Flask + waitress, porta 5001
- IA: Keras (modelo_monstro_wdo.h5, 22 features de book - sinteticas)
- Modelo A: modelo_a_filtro_wdo.keras (22 features MTF/M1 - dados reais, shadow mode)
- Memoria: historico_contexto_wdo.csv (5,001 linhas, 6 trades reais)
- Experiencias: experiencias_wdo.json (6 experiencias reais)

---

## 2. ANALISE POR ESTRATEGIA

### 2.1 Faixa 1 (Rompimento 1a Hora) - Magic 7008
**Status: ATIVA (09:00-11:00)**
**Avaliacao: POSITIVA com ressalvas**

Pontos fortes:
- Backtest: E = +2.36 pts com filtro R/R >= 1.0 (P(E>0) = 88.6%)
- SL com ATR dinamico (max(piso, min(SL_caixa, 2.5 * ATR14)))
- Filtro R/R >= 1.0 elimina trades com R/R desfavoravel
- ~33 trades/ano (1 a cada ~8 dias) - seletivo

Pontos fracos:
- Sub-Trader (Corpo 1H) tem 0% WR (4 trades, 4 losses) - PRECISA SER REVISADO
- Faixa 1 tem WR de 11.1% no periodo (9 trades, 1 gain, 8 losses) - SANGRANDO
- A trava financeira de R$ 1.500/dia nao esta protegendo (-R$ 744.60/semana)

Recomendacao:
- Desativar ou revisar o Sub-Trader (pior modulo do sistema)
- Revisar a trava financeira da Faixa 1
- Manter Faixa 1 com SL ATR (funcionando)

### 2.2 Sniper %R (Larry Williams)
**Status: ATIVO (cerebro atual desde 08/08/2026)**
**Avaliacao: NEUTRA - precisa de mais dados**

Pontos fortes:
- Baseado em Williams %R (indicador comprovado)
- Trailing 50% do lucro (fiel ao backtest)
- Cooldown 120s entre disparos (evita overtrading)

Pontos fracos:
- 29 disparos hoje, 0 executados (bloqueados por vetos)
- WR do sniper: -38.5 (FORA DE ZONA) - mercado lateral
- Nao tem poder preditivo suficiente (correlacao 0.088)

Recomendacao:
- Manter ativo (nao ha alternativa melhor)
- Aguardar mercado com tendencia (nao lateral) para avaliar

### 2.3 Core (Confluencia de Indicadores)
**Status: ATIVO (modo NORMAL)**
**Avaliacao: NEUTRA - precisa de mais dados**

Pontos fortes:
- WR de 52.2% no periodo (67 trades, 35 gains, 32 losses)
- Ligeiramente acima de 50% (nao catastrófico)
- Balanceamento BUY/SELL

Pontos fracos:
- Net -R$ 612.60 (negativo)
- Score 0.000 hoje (sem sinal forte)
- Confianca 0% (sem confluencia)

Recomendacao:
- Manter congelado (n < 100 trades pos-04/09, sem base estatistica para mudar)

### 2.4 Filtros (14 filtros ativos)
**Avaliacao: MUITO RESTRITIVO - pode estar bloqueando trades validos**

O robo tem 14 filtros em cascata. Hoje:
- 277 decisoes finais (SELL + BUY)
- 897 vetos (Williams %R + Mean Reversion)
- 83 bloqueados (Multi-TF + Consenso tendencia)
- 0 trades executados

O problema nao e falta de sinais, e excesso de filtros. O robô esta "paralisado" por vetos.

Recomendacao:
- Revisar a ordem e intensidade dos filtros
- Considerar relaxar Multi-TF veto (hoje bloqueia SELL em mercado bullish)
- Considerar relaxar Mean Reversion (RSI 1.0/100.0 sao extremos raros)

### 2.5 Sentinela de Fluxo (Macro)
**Status: ATIVO (NEUTRO hoje)**
**Avaliacao: OK - fail-open**

- DXY, US10Y, USD/JPY para classificar RISK_ON/RISK_OFF/NEUTRO
- Fail-open: sem veto se dados indisponiveis
- Nao ha evidencia de que melhora ou piora os resultados

### 2.6 Fluxo Tempo Real (Monitoramento)
**Status: ATIVO (read-only)**
**Avaliacao: OK - nao afeta decisoes**

- Captura ticks, calcula delta, thread daemon
- is_executable: false (somente monitoramento)
- Nao afeta decisoes de trading

---

## 3. PROBLEMAS IDENTIFICADOS

### 3.1 Regime LATERAL predominante
- 100% LATERAL no periodo auditado (19/10-31/10)
- O robo nao tem estrategia para mercado lateral
- Todos os filtros (Williams %R, Multi-TF, Mean Reversion) sao baseados em tendencia
- Em mercado lateral, tudo e veto

### 3.2 Book ratio baixo
- Book ratio medio: 1.16 (minimo 1.3)
- DOL desalinhado
- Fluxo INDISPONIVEL/ATRASADO
- O robô nao consegue identificar desequilibrio claro

### 3.3 Shadow Mode sem poder preditivo
- WR 51.56%, net -R$ 8.100, PF 0.83
- Correlacao 0.088 (abaixo do gate 0.15)
- Pesos sinteticos (nao reais)
- Nao ha evidencia de que o veto melhora os resultados

### 3.4 Memoria vazia
- experiencias_wdo.json tinha 1 experiencia (agora 6)
- historico_contexto_wdo.csv tem 5,001 linhas mas apenas 6 trades reais
- O treino nao tem dados suficientes

### 3.5 Watchdog: 50 force kills
- O robo nao encerra graciosamente
- Feed estagnado recorrente (7 dias com erro IPC)
- MT5 congela (verificacao de modelo bloqueava porta 5001 - CORRIGIDO)

---

## 4. RECOMENDACOES DO TRADER EXPERT

### 4.1 Curto prazo (implementar agora)
1. **Desativar hibernacao 12:30-14:30** - ELIMINADO (operacao continua)
2. **Corrigir bug de schema CSV** - CORRIGIDO (os.replace)
3. **Instalar PyWebView** - INSTALADO
4. **Eliminar bloqueio de porta 5001** - CORRIGIDO (verificacao leve)
5. **Aumentar timeout watchdog** - CORRIGIDO (10s -> 30s)

### 4.2 Medio prazo (proximas semanas)
1. **Revisar filtros** - relaxar Multi-TF veto em mercado lateral
2. **Desativar Sub-Trader** - 0% WR, sangrando
3. **Revisar trava financeira da Faixa 1** - R$ 1.500/dia nao protege
4. **Acumular dados reais** - manter Shadow Mode ativo
5. **Corrigir pesos sinteticos** - retreinar Monstro WDO com dados reais

### 4.3 Longo prazo (proximos meses)
1. **Habilitar gate do Modelo A** - quando correlacao >= 0.15 sustentada
2. **Implementar estrategia para mercado lateral** - o robo nao tem
3. **Melhorar qualidade do feed** - book ratio, DOL alinhado
4. **Monitoramento externo** - UptimeRobot/Healthchecks.io

---

## 5. META: GANHAR DINHEIRO

### O que precisa acontecer para o robo ser vencedor:

1. **Mercado com tendencia** (nao lateral) - o robo performa melhor em tendencia
2. **Book ratio >= 1.3** - desequilibrio claro entre compradores e vendedores
3. **DOL alinhado** - fluxo institucional confirmado
4. **Sniper em zona** - WR <= -80 (sobrevendido) ou >= -20 (sobrecomprado)
5. **Faixa 1 disparar** - rompimento da caixa da 1a hora (09:00-11:00)

### O que esta funcionando:
- Faixa 1 tem E = +2.36 pts com filtro R/R >= 1.0 (backtest)
- Core tem WR 52.2% (ligeiramente acima de 50%)
- Sniper %R tem base teorica (Williams %R comprovado)

### O que precisa melhorar:
- Filtros muito restritivos (14 filtros em cascata)
- Sem estrategia para mercado lateral
- Pesos sinteticos (IA nao tem poder preditivo)
- Feed de baixa qualidade (book ratio 1.16 < 1.3)
- Sub-Trader com 0% WR

### Veredito do trader expert:
O robo tem POTENCIAL para ser vencedor, mas precisa de:
1. Mais dados reais (acumular trades)
2. Re-treino com dados reais (eliminar pesos sinteticos)
3. Revisao dos filtros (relaxar em mercado lateral)
4. Desativar Sub-Trader (sangrando)
5. Melhorar qualidade do feed (book ratio, DOL)

O robo NAO esta quebrado. Ele esta FILTRANDO corretamente. O problema e que
o mercado esta lateral e os filtros sao baseados em tendencia. Quando o mercado
tiver tendencia, o robo devera operar e ser vencedor.

### Meta realista:
- Curto prazo: acumular dados, manter Shadow Mode
- Medio prazo: revisar filtros, desativar Sub-Trader, retreinar IA
- Longo prazo: habilitar gate, operar com alta conviccao (p >= 0.60)