# Design Document - Correção de Leitura CSV do EA

## Overview

Este design implementa uma solução robusta para leitura do arquivo CSV gerado pelo Expert Advisor (EA) do MetaTrader 5, resolvendo problemas de codificação UTF-16 e implementando mecanismos de fallback e retry para garantir operação contínua do sistema de trading.

## Architecture

### Componente Principal: CSVReaderRobust
- **Responsabilidade**: Gerenciar leitura robusta do arquivo CSV com múltiplas estratégias
- **Localização**: Substituirá a função `ler_book_csv()` atual
- **Dependências**: os, time, logging, codecs

### Fluxo de Leitura
1. **Detecção de Codificação**: Tenta detectar automaticamente a codificação do arquivo
2. **Leitura Multi-Encoding**: Tenta múltiplas codificações em ordem de prioridade
3. **Validação de Dados**: Verifica integridade dos dados lidos
4. **Fallback Strategy**: Usa dados do MT5 se CSV falhar
5. **Retry Logic**: Implementa backoff exponencial para tentativas

## Components and Interfaces

### 1. CSVEncodingDetector
Responsabilidades:
- Detectar codificação do arquivo automaticamente
- Fornecer lista ordenada de codificações para tentar
- Usar heurísticas baseadas no conteúdo do arquivo

### 2. CSVDataValidator
Responsabilidades:
- Validar integridade dos dados do book
- Sanitizar dados corrompidos quando possível
- Detectar padrões suspeitos nos dados

### 3. CSVReaderRobust
Responsabilidades:
- Coordenar todo o processo de leitura
- Implementar retry logic com backoff
- Gerenciar fallback para dados do MT5

### 4. RetryManager
Responsabilidades:
- Gerenciar tentativas com backoff exponencial
- Controlar número máximo de tentativas
- Calcular delays apropriados entre tentativas

## Data Models

### BookData
- bids: List[int]
- asks: List[int]
- timestamp: datetime
- source: str (csv ou mt5_fallback)
- encoding_used: Optional[str]
- validation_passed: bool

### ReadResult
- success: bool
- data: Optional[BookData]
- error_message: Optional[str]
- attempts_made: int
- encoding_used: Optional[str]

## Error Handling

### Estratégia de Codificação
1. **Detecção Automática**: Usa chardet ou similar para detectar codificação
2. **Lista de Fallback**: utf-8, utf-16, utf-16-le, utf-16-be, ascii, latin-1, cp1252
3. **Tratamento de BOM**: Remove BOM quando presente
4. **Encoding Caching**: Cache da codificação que funcionou para próximas leituras

### Tratamento de Erros Específicos
- **UnicodeDecodeError**: Tenta próxima codificação da lista
- **FileNotFoundError**: Aguarda criação do arquivo (EA pode estar reiniciando)
- **PermissionError**: Aguarda liberação do arquivo pelo EA
- **Empty File**: Aguarda EA escrever dados
- **Malformed Data**: Tenta sanitizar ou descarta leitura

## Testing Strategy

### Unit Tests
1. **Encoding Detection**: Testa detecção com arquivos de diferentes codificações
2. **Data Validation**: Testa validação com dados válidos e inválidos
3. **Retry Logic**: Testa backoff exponencial e limites de tentativas
4. **Fallback**: Testa ativação do fallback quando CSV falha

### Integration Tests
1. **EA Integration**: Testa leitura com arquivo real gerado pelo EA
2. **MT5 Fallback**: Testa fallback para dados do MT5
3. **Performance**: Testa impacto no desempenho do loop principal
4. **Stress Test**: Testa com múltiplas falhas consecutivas

## Performance Considerations

### Otimizações
- **Encoding Cache**: Cache da codificação que funcionou
- **File Size Check**: Verifica tamanho antes de tentar ler
- **Lazy Loading**: Só carrega detector de codificação quando necessário
- **Timeout Control**: Timeout para operações de I/O

### Monitoring
- **Read Success Rate**: Taxa de sucesso na leitura do CSV
- **Encoding Distribution**: Quais codificações são mais usadas
- **Fallback Usage**: Frequência de uso do fallbackMT5
- **Performance Metrics**: Tempo médio de leitura

## Configuration

### Parâmetros Configuráveis
- max_retries: 5
- base_delay: 0.1
- max_delay: 2.0

- encoding_cache_ttl: 3)
- fallbaced: True
- validation_strict: False

## Migration Strategy

### Fa
- t()
- Mantém função oriack
- Adic para anfiguraçãode coflag iona

### Fase 2: Testes em Produção
- Ativa nova função em ambiente de produção
- Monitora métricas de performance e erro
- Compara resultados com função original

### Fase 3: Substituita
- Remove função original após validação
- Atualiza toda documentação
- Remove flags de configuração temporárias
