# Implementation Plan - Correção de Leitura CSV do EA

- [x] 1. Implementar detector de codificação robusto
  - Criar função para detectar automaticamente a codificação do arquivo CSV
  - Implementar lista de fallback de codificações (utf-8, utf-16, utf-16-le, utf-16-be, ascii, latin-1, cp1252)
  - Adicionar tratamento específico para BOM (Byte Order Mark)
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Criar validador de dados do book
  - Implementar validação de integridade dos volumes lidos
  - Adicionar sanitização de dados corrompidos quando possível
  - Criar detecção de padrões suspeitos nos dados
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 3. Implementar sistema de retry com backoff exponencial
  - Criar gerenciador de tentativas com delays crescentes
  - Implementar controle de número máximo de tentativas
  - Adicionar tratamento específico para diferentes tipos de erro (permissão, arquivo não encontrado, etc.)
  - _Requirements: 3.2, 3.3, 5.1, 5.2, 5.3, 5.4_

- [ ] 4. Desenvolver mecanismo de fallback para MT5
  - Implementar função para obter dados do book diretamente do MT5
  - Converter formato do MT5 para formato esperado pelo sistema
  - Adicionar marcação de origem dos dados (CSV vs MT5)
  - _Requirements: 3.1, 3.4_

- [ ] 5. Criar nova função ler_book_csv_robust()
  - Integrar todos os componentes em uma função principal
  - Manter interface compatível com função original
  - Implementar cache de codificação para otimização
  - Adicionar timeout para operações de I/O
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6. Implementar logging detalhado
  - Adicionar logs de codificação detectada e utilizada
  - Logar tentativas de leitura e seus resultados
  - Registrar estatísticas de dados lidos com sucesso
  - Alertar sobre uso de fallback MT5
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 7. Adicionar configurações para o sistema robusto
  - Criar parâmetros configuráveis (max_retries, delays, timeouts)
  - Implementar flag para ativar/desativar novo sistema
  - Adicionar configuração de nível de validação (strict/permissive)
  - _Requirements: 1.1, 3.2, 5.4_

- [ ] 8. Integrar nova função no loop principal
  - Substituir chamada da função original pela nova
  - Adicionar tratamento de erros específicos no contexto do loop
  - Implementar fallback para função original em caso de falha crítica
  - Testar integração com fluxo de decisão do modelo IA
  - _Requirements: 1.1, 3.1, 3.4_

- [ ] 9. Criar testes unitários para validação
  - Testar detecção de codificação com diferentes arquivos
  - Validar sistema de retry e backoff exponencial
  - Testar fallback para dados do MT5
  - Verificar validação de dados e sanitização
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 10. Implementar monitoramento e métricas
  - Adicionar contadores de sucesso/falha na leitura
  - Registrar distribuição de codificações utilizadas
  - Monitorar frequência de uso do fallback MT5
  - Medir tempo médio de leitura e performance
  - _Requirements: 2.1, 2.2, 2.3, 2.4_
