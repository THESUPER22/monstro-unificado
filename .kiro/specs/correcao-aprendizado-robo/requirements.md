# Requirem Document

## Introduction

O robô de trading "Monstro" está perdendo R$ 1000 por dia há 30 dias consecutivos sem aprender com seus erros. A análise do código e logs revelou problemas críticos no sistema de aprendizado por reforço, replay de experiências e circuit breakers que impedem o robô de evoluir e se proteger adequadamente.

## Glossary

- **Replay Buffer**: Sistema de memória que armazena experiências passadas para retreinamento do modelo
- **Circuit Breaker**: Mecanismo de proteção que para operações quando certas condições de risco são atingidas
- **Experience Replay**: Processo de retreinamento usando experiências armazenadas anteriormente
- **Positive Bias**: Tendência do sistema de só aprender com experiências positivas, ignorando perdas
- **Overtrading**: Execução excessiva de operações em alta frequência
- **Reward Signal**: Sinal de recompensa usado para treinar o modelo de IA

## Requirements

### Requirement 1

**User Story:** Como um operador do robô, eu quero que o sistema aprenda tanto com lucros quanto com perdas, para que ele possa evitar repetir os mesmos erros.

#### Acceptance Criteria

1. WHEN o sistema executa replay de experiências, THE Replay_System SHALL incluir tanto experiências positivas quanto negativas na proporção de 50/50
2. WHEN o sistema seleciona experiências para treino, THE Replay_System SHALL priorizar experiências com maior valor absoluto de reward independente do sinal
3. WHEN o modelo é treinado, THE Training_System SHALL preservar o sinal negativo das recompensas sem normalização que remova informação crítica
4. WHERE experiências negativas existem, THE Replay_System SHALL garantir que pelo menos 30% do batch contenha experiências com reward negativo
5. WHILE o sistema opera, THE Learning_System SHALL registrar e utilizar todas as experiências de perda para aprendizado contínuo

### Requirement 2

**User Story:** Como um gestor de risco, eu quero que o robô pare de operar rapidamente quando detectar padrões de perda, para que não acumule prejuízos excessivos.

#### Acceptance Criteria

1. WHEN o robô acumula 3 perdas consecutivas, THE Circuit_Breaker_System SHALL bloquear novas operações imediatamente
2. WHEN o prejuízo diário atinge R$ 500, THE Circuit_Breaker_System SHALL parar todas as operações do dia
3. WHEN o spread excede 10 pontos, THE Circuit_Breaker_System SHALL rejeitar a operação
4. IF uma operação individual perde mais de R$ 100, THEN THE Circuit_Breaker_System SHALL aumentar o nível de proteção
5. WHILE o sistema está bloqueado por circuit breaker, THE Trading_System SHALL aguardar pelo menos 30 minutos antes de tentar reativar

### Requirement 3

**User Story:** Como um desenvolvedor do sistema, eu quero que o treinamento do modelo ocorra com frequência adequada e dados balanceados, para que o aprendizado seja efetivo.

#### Acceptance Criteria

1. WHEN o sistema acumula 5 experiências novas, THE Training_System SHALL iniciar um ciclo de treinamento
2. WHEN o treinamento é executado, THE Training_System SHALL usar batch size de 64 experiências
3. WHEN o modelo é retreinado, THE Training_System SHALL executar 5 epochs por sessão de treino
4. WHERE experiências antigas existem, THE Training_System SHALL aplicar peso de replay de 1.0 para manter relevância
5. WHILE o sistema treina, THE Training_System SHALL manter pelo menos 50 experiências mínimas antes do primeiro treino

### Requirement 4

**User Story:** Como um operador, eu quero que o robô reduza a frequência de operações e melhore a qualidade dos sinais, para que pare de fazer overtrading.

#### Acceptance Criteria

1. WHEN o sistema detecta alta volatilidade, THEstem SHALL aumentar o intervalo mínimo entre operações para 2 minutos
2. WHEN o robô executa mais de 50 operações em uma hora, THE Trading_System SHALL ativar modo conservador
3. WHEN uma operação é fechada, THE Trading_System SHALL aguardar pelo menos 30 segundos antes da próxima
4. IF o sistema detecta reversões rápidas (BUY→SELL→BUY), THEN THE Trading_System SHALL bloquear operações por 5 minutos
5. WHILE o mercado está lateral (ATR < 50), THE Trading_System SHALL reduzir o volume de operações em 50%

### Requirement 5

**User Story:** Como um analista de performance, eu quero que o sistema mantenha logs detalhados e métricas de aprendizado, para que eu possa monitorar a evolução do robô.

#### Acceptance Criteria

1. WHEN uma experiência é adicionada ao replay buffer, THE Logging_System SHALL registrar o tipo (positiva/negativa) e valor do reward
2. WHEN o treinamento é executado, THE Logging_System SHALL registrar a composição do batch (% positivas vs negativas)
3. WHEN um circuit breaker é ativado, THE Logging_System SHALL registrar o motivo específico e duração do bloqueio
4. WHERE métricas de performance são calculadas, THE Logging_System SHALL incluir taxa de acerto, drawdown máximo e frequência de operações
5. WHILE o sistema opera, THE Logging_System SHALL manter histórico das últimas 1000 operações para análise
