# Implementation Plan

- [ ] 1. Corrigir sistema de replay enviesado
  - Implementar função `obter_batch_replay_balanceado()` que seleciona 50% experiências positivas e 50% negativas
  - Adicionar priorização por valor absoluto do reward para selecionar experiências mais significativas
  - Modificar estrutura de dados para rastrear `indices_negativos` além dos `indices_positivos`
  - Preservar sinal negativo das recompensas durante o treinamento (remover normalização que elimina informação)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 2. Reativar e otimizar circuit breakers
  - Reduzir limite de perda diária de R$ 1000 para R$ 500 na configuração
  - Reativar circuit breaker de 3 perdas consecutivas (atualmente desabilitado)
  - Implementar circuit breaker para spread > 10 pontos
  - Adicionar circuit breaker para perdas individuais > R$ 100
  - Implementar cooldown de 30 minutos após ativação de circuit breaker
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 3. Otimizar parâmetros de treinamento
  - Reduzir `LIMITE_EXPERIENCIAS_PARA_TREINO` de 10 para 5 (treina mais frequentemente)
  - Aumentar `BATCH_SIZE` de 32 para 64 (batches maiores para estabilidade)
  - Aumentar `EPOCHS_TREINO` de 3 para 5 (mais epochs por sessão)
  - Aumentar `PESO_REPLAY` de 0.3 para 1.0 (experiências antigas com peso total)
  - Aumentar `MIN_EXPERIENCIAS_TREINO` para 50 (mínimo antes do primeiro treino)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 4. Implementar sistema anti-overtrading
  - Adicionar intervalo mínimo de 30 segundos entre operações
  - Implementar limite de 50 operações por hora
  - Detectar e bloquear reversões rápidas (BUY→SELL→BUY) por 5 minutos
  - Implementar modo conservador quando ATR < 50 (reduz volume em 50%)
  - Adicionar cooldown de 2 minutos em alta volatilidade
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 5. Melhorar logging e monitoramento
  - Registrar tipo de experiência (positiva/negativa) e valor do reward ao adicionar ao buffer
  - Logar composição do batch durante treinamento (% positivas vs negativas)
  - Registrar motivo específico e duração quando circuit breaker é ativado
  - Implementar métricas de performance (taxa de acerto, drawdown, frequência de operações)
  - Manter histórico das últimas 1000 operações para análise
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 6. Criar testes unitários para validação
  - Testar balanceamento 50/50 no replay buffer
  - Testar ativação individual de cada circuit breaker
  - Testar preservação de sinal negativo no treinamento
  - Testar detecção de overtrading e reversões rápidas
  - _Requirements: Todos os requirements_

- [ ]* 7. Implementar testes de integração
  - Testar sequência completa de aprendizado com perdas
  - Testar interação entre diferentes circuit breakers
  - Testar performance sob alta frequência de operações
  - _Requirements: Todos os requirements_

- [ ]* 8. Executar backtesting com dados históricos
  - Testar correções com dados dos últimos 30 dias de perdas
  - Simular diferentes condições de mercado
  - Comparar métricas antes/depois das correções
  - _Requirements: Todos os requirements_
