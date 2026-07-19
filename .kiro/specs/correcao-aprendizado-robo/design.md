# Dnt

## Overview

Este documento detalha o design técnico para corrigir os problemas críticos do robô de trading "Monstro" que está perdendo R$ 1000 por dia sem aprender com seus erros. O design foca em três áreas principais: correção do sistema de replay enviesado, reativação de circuit breakers efetivos, e otimização do processo de treinamento.

## Architecture

### Current Architecture Problems

1. **Biased Replay System**: A função `obter_batch_replay()` só seleciona experiências positivas (`indices_positivos`), criando um viés que impede o aprendizado com perdas
2. **Disabled Circuit Breakers**: Os circuit breakers estão desabilitados ou com limites muito altos (R$ 1000 de perda diária)
3. **Inefficient Training**: Treinamento ocorre apenas a cada 10 experiências com parâmetros inadequados
4. **Overtrading**: Sistema executa centenas de operações por dia sem filtros adequados

### Proposed Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Experience    │    │   Balanced      │    │   Enhanced      │
│   Collection    │───▶│   Replay───▶│   Training      │
│                 │    │   System        │    │   Pipeline      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Circuit       │    │   Quality       │    │   Performance   │
│   Breakers      │    │   Filters       │    │   Monitoring    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Balanced Replay System

**Current Implementation Problem:**
```python
# PROBLEMA: Só seleciona experiências positivas
exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)
                 if i in self.indices_positivos]
```

**New Implementation:**
```python
class BalancedReplayBuffer:
    def obter_batch_replay_balanceado(self) -> Tuple[List, List]:
        """Obtém batch balanceado com experiências positivas e negativas."""

        # Separa experiências por tipo
        exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)
                        if i in self.indices_positivos]
        exp_negativas = [(i, exp) for i, exp in enumerate(self.experiencias)
                        if i in self.indices_negativos]

        # Calcula proporção 50/50 ou baseada em prioridade
        n_positivas = min(BATCH_SIZE // 2, len(exp_positivas))
        n_negativas = min(BATCH_SIZE // 2, len(exp_negativas))

        # Prioriza por valor absoluto do reward
        exp_positivas.sort(key=lambda x: abs(self.experiencias[x[0]][2]), reverse=True)
        exp_negativas.sort(key=lambda x: abs(self.experiencias[x[0]][2]), reverse=True)

        # Seleciona experiências balanceadas
        indices_replay = ([idx for idx, _ in exp_positivas[:n_positivas]] +
                         [idx for idx, _ in exp_negativas[:n_negativas]])

        return self._build_batch(indices_replay)
```

### 2. Enhanced Circuit Breaker System

**Interface:**
```python
class EnhancedCircuitBreaker:
    def __init__(self):
        self.max_consecutive_losses = 3
        self.daily_loss_limit = -500.0  # Reduzido de -1000
        self.max_spread = 10
        self.max_individual_loss = -100.0
        self.cooldown_minutes = 30

    def check_all_breakers(self, context: Dict) -> Tuple[bool, str]:
        """Verifica todos os circuit breakers em ordem de prioridade."""

    def register_trade_result(self, profit: float) -> None:
        """Registra resultado de operação para tracking."""

    def is_blocked(self) -> bool:
        """Verifica se sistema está bloqueado."""

    def get_detailed_status(self) -> Dict:
        """Retorna status detalhado de todos os breakers."""
```

### 3. Optimized Training Pipeline

**Current Problems:**
- `LIMITE_EXPERIENCIAS_PARA_TREINO = 10` (muito alto)
- `BATCH_SIZE = 32` (muito baixo)
- `EPOCHS_TREINO = 3` (insuficiente)
- `PESO_REPLAY = 0.3` (muito baixo)

**New Configuration:**
```python
# Parâmetros otimizados
LIMITE_EXPERIENCIAS_PARA_TREINO = 5  # Treina mais frequentemente
BATCH_SIZE = 64                      # Batch maior para estabilidade
EPOCHS_TREINO = 5                    # Mais epochs por sessão
PESO_REPLAY = 1.0                    # Peso total para experiências antigas
MIN_EXPERIENCIAS_TREINO = 50         # Mínimo antes do primeiro treino
```

**Training Pipeline:**
```python
class OptimizedTrainingPipeline:
    def should_train(self) -> bool:
        """Verifica se deve treinar com nova lógica."""
        return (self.new_experiences_count >= LIMITE_EXPERIENCIAS_PARA_TREINO and
                len(self.memory.experiencias) >= MIN_EXPERIENCIAS_TREINO)

    def train_with_balanced_data(self, model, memory) -> Any:
        """Treina modelo com dados balanceados."""
        batch, decays = memory.obter_batch_replay_balanceado()

        # Preserva sinal negativo das recompensas
        X, y = self._prepare_training_data(batch, preserve_negative_rewards=True)

        # Treina com parâmetros otimizados
        return self._train_model(model, X, y, epochs=EPOCHS_TREINO)
```

### 4. Anti-Overtrading System

**Interface:**
```python
class AntiOvertradingFilter:
    def __init__(self):
        self.min_interval_seconds = 30
        self.max_trades_per_hour = 50
        self.reversal_cooldown_minutes = 5
        self.last_trade_time = None
        self.trades_this_hour = []
        self.last_actions = collections.deque(maxlen=3)

    def can_trade(self, proposed_action: str) -> Tuple[bool, str]:
        """Verifica se pode executar operação."""

    def register_trade(self, action: str) -> None:
        """Registra operação executada."""

    def detect_rapid_reversals(self) -> bool:
        """Detecta reversões rápidas (BUY→SELL→BUY)."""
```

## Data Models

### Experience Data Structure
```python
@dataclass
class TradingExperience:
    context: Dict[str, Any]      # Contexto de mercado
    action: str                  # "BUY", "SELL", "NAO_AGIU"
    reward: float               # Lucro/prejuízo (preserva sinal negativo)
    score_distance: float       # Score baseado em distância TP/SL
    timestamp: datetime         # Timestamp da experiência
    is_positive: bool          # Flag para classificação rápida
    absolute_reward: float     # Valor absoluto para priorização
```

### Circuit Breaker State
```python
@dataclass
class CircuitBreakerState:
    consecutive_losses: int
    daily_pnl: float
    last_trade_time: datetime
    blocked_until: Optional[datetime]
    block_reason: str
    individual_losses: List[float]
    spread_violations: int
```

## Error Handling

### 1. Replay System Errors
- **Empty Experience Buffer**: Retorna batch vazio e adia treinamento
- **Insufficient Negative Experiences**: Usa todas disponíveis e completa com positivas
- **Memory Corruption**: Recarrega do CSV de backup

### 2. Circuit Breaker Failures
- **State Persistence**: Salva estado em arquivo JSON para recuperação
- **Time Sync Issues**: Usa timestamp local como fallback
- **Configuration Errors**: Usa valores padrão seguros

### 3. Training Pipeline Errors
- **Model Loading Failures**: Cria novo modelo com arquitetura padrão
- **Data Preparation Errors**: Filtra dados inválidos e continua
- **Training Convergence Issues**: Reduz learning rate automaticamente

## Testing Strategy

### 1. Unit Tests
- **Replay Buffer**: Testa balanceamento 50/50 e priorização por reward absoluto
- **Circuit Breakers**: Testa cada condição de ativação individualmente
- **Training Pipeline**: Testa preservação de sinal negativo e parâmetros otimizados
- **Anti-Overtrading**: Testa detecção de reversões e limites de frequência

### 2. Integration Tests
- **End-to-End Learning**: Simula sequência de perdas e verifica aprendizado
- **Circuit Breaker Integration**: Testa interação entre diferentes breakers
- **Performance Under Load**: Testa sistema com alta frequência de operações

### 3. Backtesting
- **Historical Data**: Testa correções com dados dos últimos 30 dias de perdas
- **Scenario Testing**: Simula diferentes condições de mercado
- **Performance Metrics**: Compara métricas antes/depois das correções

## Performance Considerations

### 1. Memory Management
- **Experience Buffer Size**: Limita a 1000 experiências mais recentes
- **Batch Processing**: Processa experiências em chunks para evitar memory overflow
- **Garbage Collection**: Limpa experiências antigas periodicamente

### 2. Training Efficiency
- **GPU Utilization**: Usa GPU se disponível para treinamento
- **Parallel Processing**: Processa features em paralelo quando possível
- **Model Checkpointing**: Salva modelo a cada 10 sessões de treino

### 3. Real-time Performance
- **Circuit Breaker Checks**: Otimiza verificações para < 1ms
- **Experience Storage**: Usa estruturas de dados eficientes
- **Logging Overhead**: Minimiza logs em produção

## Security Considerations

### 1. Data Integrity
- **Experience Validation**: Valida dados antes de adicionar ao buffer
- **Model Checksum**: Verifica integridade do modelo salvo
- **Configuration Validation**: Valida parâmetros de configuração

### 2. Risk Management
- **Hard Limits**: Implementa limites absolutos que não podem ser desabilitados
- **Fail-Safe Defaults**: Usa configurações conservadoras como padrão
- **Emergency Stop**: Implementa parada de emergência manual

### 3. Audit Trail
- **Decision Logging**: Registra todas as decisões de trading com contexto
- **Configuration Changes**: Registra mudanças de configuração
- **Performance Metrics**: Mantém histórico de métricas para auditoria
