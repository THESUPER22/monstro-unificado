# ESTRATEGIAS EXISTENTES NO CODIGO - Monstro v22 (WDO)

## 1. FAIXA 1 - ROMPIMENTO DA 1A HORA (Orquestrador Rompimento)
- Magic: 7008
- Janela: 09:00-11:00 (configuravel)
- Estrategia: Rompimento da caixa da primeira hora
- Sub-trader (Corpo 1H): candle 09:00-10:00 agregado das 12 M5
  - Entrada: rompimento do Corpo (BUY ask >= Corpo_Topo / SELL bid <= Corpo_Fundo)
  - SL/TP no Pavio
  - Bloqueia Faixa 1 enquanto aberto
  - Libera gatilho imediatamente ao encerrar
  - EOD fecha a mercado
- SL com ATR: max(piso, min(SL_caixa, fator * ATR14 manha))
- Filtro R/R >= 1.0 (so opera R/R >= 1:1)
- ~33 trades/ano (1 a cada ~8 dias)
- Modulo: rompimento_orquestrador.py

## 2. SNIPER %R (Larry Williams - reversao de extremo)
- Cerebro atual do robo (desde 08/08/2026)
- Ativa quando WR <= -80 (sobrevendido -> BUY) ou WR >= -20 (sobrecomprado -> SELL)
- Cooldown: 120s entre disparos
- Volume minimo: SNIPER_SUPERMO_VOLUME = 1.0
- SL/TP por ATR (dinamico)
- Trailing: 50% do lucro quando atingir threshold
- Registra posicao com sniper_wr=1
- Classe: SniperSupermo (L3085)

## 3. SNIPER DE ELITE (Book Nativo MT5)
- Filtro: volume total do book >= SNIPER_VOLUME_MIN (800)
- Desequilibrio: ratio >= SNIPER_RATIO_MIN (1.5)
- Verifica se o lado dominante tem >= 2x o outro
- Roda antes do Sniper %R
- Pode bloquear operacao se book insuficiente

## 4. CORE (Robo Principal - Magic 123456)
- Estrategia base: confluencia de indicadores (RSI, ATR, Williams %R, Book)
- Volume adaptativo baseado em liquidez do book
- Balanceamento BUY/SELL
- Trailing stop inteligente
- Circuit breakers (max loss diario, max drawdown, etc.)
- Gate de %R (veto em sobrecomprado/sobrevendido)
- Multi-TF veto (M5/M15/M30)
- Tendencia (SMA-50 + Momentum)
- Mean Reversion (RSI + Z-Score + ADX)
- Sentinela de Fluxo (gatekeeper macro - DXY, US10Y, USD/JPY)

## 5. FILTRO SNIPER BLOQUEADO
- verificar_sniper_bloqueado(): verifica se sniper esta bloqueado
- Pode bloquear por: book ratio baixo, DOL desalinhado, etc.

## 6. FILTRO DE HORARIO PREMIUM
- FiltroHorarioPremium: is_horario_premium()
- Horarios premium: 09:15-10:30, 14:30-15:30, 16:00-17:00
- +2% eficacia

## 7. DETECTOR DE TENDENCIA (SMA-50 + Momentum)
- 3 camadas: SMA-50, Momentum (20 ticks), Consenso
- Bloqueia operacoes contra a tendencia
- margem_pts: 4.5

## 8. FILTRO MEAN REVERSION (RSI + Z-Score + ADX)
- RSI por zonas (70/50/30)
- Z-Score (desvio padrao da media)
- ADX Trend Classifier (lateral vs tendencia)
- Bloqueia BUY em sobrecomprado, SELL em sobrevendido

## 9. SENTINELA DE FLUXO (Gatekeeper Macroeconomico)
- Classifica cenario: RISK_ON / RISK_OFF / NEUTRO
- Baseado em: DXY, US 10Y, USD/JPY
- RISK_OFF -> so BUY liberado (dolar forte)
- RISK_ON -> so SELL liberado (dolar fraco)
- NEUTRO -> sem veto

## 10. FLUXO TEMPO REAL (Monitoramento - read-only)
- Captura ticks do simbodo operado
- Calcula delta comprador/vendedor
- Qualidade: INFERIDO (flags != agressao real)
- is_executable: false (somente monitoramento)
- Thread daemon, 200ms intervalo
- NAO afeta decisoes de trading

## 11. SUB-TRADER (Corpo 1H) - dentro do Orquestrador Rompimento
- Entra no rompimento do Corpo (BUY ask >= Corpo_Topo / SELL bid <= Corpo_Fundo)
- SL/TP no Pavio
- Bloqueia Faixa 1 enquanto aberto
- Libera gatilho imediatamente ao encerrar
- EOD fecha a mercado
- Filtro R/R >= 1.0

## 12. GERENCIADOR DE BLOQUEIO
- Bloqueia lado (BUY/SELL) apos sequencia de losses
- MAX_LOSSES_SEQUENCIA: 3
- CICLOS_BLOQUEIO: 5
- Reduz bloqueio gradualmente com lucro

## 13. TRAILING STOP
- TRAILING_ATIVO: True
- TRAILING_INTERVALO: 5s
- TRAILING_GATILHO: 8.0 pts
- TRAILING_DISTANCIA: 4.0 pts
- Inteligente: trava lucro baseado em score

## 14. CIRCUIT BREAKERS
- MAX_LOSS_DIARIO: -R$ 500
- MAX_DRAWDOWN: -R$ 250
- MAX_SPREAD: 5 pts
- MAX_LOSSES_SEQUENCIA: 3
- Pode criar parar.txt e desligar o robo

## 15. LIMITADOR DE INSISTENCIA
- Limita operacoes no mesmo contexto no mesmo dia
- max_operacoes_contexto_dia: 2
- Hash: data + faixa 2h + volatilidade + RSI + candle

## 16. BALANCEAMENTO BUY/SELL
- Controla proporcao de BUY vs SELL
- Evita concentracao em um lado

## 17. GERENCIADOR DE VOLUME ADAPTATIVO
- Ajusta volume baseado na liquidez do book
- WDO: 1 contrato padrao
- Aumenta se liquidez MUITO alta

## 18. SAIDA INTELIGENTE DE POSICAO
- Verifica inversao de score
- Verifica enfraquecimento
- Trava lucro baseado em score
- Fecha por score se necessario

## 19. RECONCILIACAO DE POSICOES
- PENDING_RECONCILIATION persistida em JSON
- Varredura retroativa de 60s via history_deals_get
- Re-checagem assincrona (15s/30s)

## 20. MEMORIA UNIFICADA (Keras)
- Snapshot real do book na entrada (D1)
- Reward em R$ (D2)
- Sub-Trader no dataset (D3)
- Gate desligado (pesos sinteticos)
- Correlacao >= 0.15 necessaria para liberar gate

## 21. APRENDIZADO (IA)
- Treino continuo com Keras/TensorFlow
- Replay de experiencias
- Early stopping, decay, etc.
- Minimo 3 experiencias para treino
- Maximo 1000 experiencias na memoria

## 22. HIBERNACAO
- 12:30-14:30: reduzida (sniper continua ativo)
- Fora do horario: aguarda proxima janela

## 23. MONITORAMENTO DE SPREAD
- Monitora spread do mercado
- Thread separada
- Atualiza a cada segundo

## 24. WATCHDOG DLL
- Destrava thread principal se MT5 congelar
- PATCH A v22.2

## 25. SENTINELA DE FLUXO (macro)
- Gatekeeper macroeconomico
- DXY, US10Y, USD/JPY
- RISK_ON/RISK_OFF/NEUTRO
- Fail-open (sem veto se dados indisponiveis)

## ORDEM DE EXECUCAO (prioridade):
1. Faixa 1 (Rompimento 1a Hora) - 09:00-11:00 - EXCLUSIVO
2. Sniper %R (reversao de extremo) - quando WR <= -80 ou >= -20
3. Sniper Elite (book nativo) - filtro de volume/ratio
4. Core (confluencia de indicadores) - modo NORMAL
5. Sub-Trader (corpo 1H) - dentro do rompimento

## FILTROS APLICADOS (em ordem):
1. Horario (pregao 09:00-17:35)
2. Spread (max 5 pts)
3. Volume book (min 200cc)
4. Sniper ratio (min 1.5)
5. Williams %R (veto sobrecomprado/sobrevendido)
6. Multi-TF (M5/M15/M30)
7. Tendencia (SMA-50 + Momentum)
8. Mean Reversion (RSI + Z-Score + ADX)
9. Sentinela (DXY/US10Y/USDJPY)
10. Balanceamento BUY/SELL
11. Limitador de insistencia (max 2 ops/contexto/dia)
12. Gerenciador de bloqueio (losses sequenciais)
13. Circuit breakers (max loss diario, max drawdown)
14. Fluxo tempo real (monitoramento only, nao afeta decisoes)