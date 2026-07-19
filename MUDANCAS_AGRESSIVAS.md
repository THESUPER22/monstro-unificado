# 🔥 MUDANÇAS PARA TORNAR O MONSTRO MAIS AGRESSIVO

## Problema Identificado
O Monstro estava muito conservador, bloqueando muitas operações e perdendo oportunidades de lucro.

## Mudanças Implementadas

### 1. Configurações de Bloqueio de Lado (MAIS AGRESSIVO)
- **MAX_LOSSES_SEQUENCIA**: 3 → 5 (permite mais losses antes de bloquear)
- **CICLOS_BLOQUEIO**: 5 → 2 (bloqueia por menos tempo)
- **MIN_LUCRO_DESBLOQUEIO**: 0.0 → -50.0 (permite pequenos prejuízos para desbloquear)

### 2. Circuit Breakers (MAIS TOLERANTES)
- **MAX_LOSS_DIARIO**: -500 → -1000 (dobrou limite diário)
- **MAX_DRAWDOWN**: -250 → -500 (dobrou limite por operação)
- **MAX_SPREAD**: 5 → 10 pontos (permite spreads maiores)
- **MIN_VOLUME_BOOK**: 200 → 50 (aceita volumes menores)

### 3. Modos Situacionais (MENOS RESTRITIVOS)
- **THRESHOLD_ATR_BAIXO**: 50 → 25 (sai do modo lateral mais facilmente)
- **THRESHOLD_ENTROPIA_BAIXA**: 0.3 → 0.2 (menos restritivo)
- **MIN_VOLUME_CRESCIMENTO**: 1.5 → 1.2 (aceita crescimento menor)
- **MAX_LOSSES_SEGUIDOS**: 3 → 5 (permite mais losses antes do modo defesa)
- **TEMPO_DEFESA**: 30 → 15 minutos (fica menos tempo em defesa)
- **MIN_RATIO_BOOK**: 0.1 → 0.05 (aceita books mais desequilibrados)

### 4. Stop Inteligente (MAIS AGRESSIVO)
- **INVERSAO_SCORE_MIN**: 0.3 → 0.5 (precisa de mais mudança para sair)
- **SCORE_LOCK_PROFIT**: 0.5 → 0.7 (trava lucro apenas em scores maiores)
- **TEMPO_MIN_POSICAO**: 30 → 15 segundos (sai mais rapidamente)
- **THRESHOLD_INVERSAO_SCORE**: -0.2 → -0.4 (mais tolerante a inversões)

### 5. Filtros de Volume (MENOS RESTRITIVOS)
- Agora só bloqueia se volume < 100 E não crescente E não estiver em modo NORMAL/EXPLOSAO
- Tempo de espera reduzido de 30 para 10 segundos

### 6. Previsão de Ação (MAIS AGRESSIVA)
- **max_ajuste**: 0.15 → 0.25 (25% de ajuste no threshold)
- Balanceamento mais tolerante: 45%-55% → 35%-65%
- Multiplicador de ajuste: 2.5 → 3.0 (mais agressivo)

### 7. Lógica de Bloqueio (MAIS FLEXÍVEL)
- Só conta como loss se prejuízo > 25 reais
- Decrementa contador de losses gradualmente
- Reduz bloqueio gradualmente ao invés de zerar instantaneamente

## Como Testar

```bash
cd /d C:\AIOFEN
call venv310\Scripts\activate
python monstro_unificado.py
```

## Resultados Esperados
- Mais operações executadas
- Menos tempo em modo defesa/bloqueio
- Maior aproveitamento de oportunidades
- Possível aumento na volatilidade dos resultados (risco/retorno)

## Monitoramento
- Acompanhar via dashboard web (http://localhost:5001)
- Verificar logs para confirmar menos bloqueios
- Monitorar balanceamento de operações BUY/SELL
- Observar se está operando mais frequentemente

## Reversão se Necessário
Se o robô ficar muito arriscado, pode-se reverter gradualmente:
1. Reduzir limites de drawdown primeiro
2. Aumentar tempo de defesa
3. Tornar filtros mais restritivos
4. Reduzir tolerância a losses 