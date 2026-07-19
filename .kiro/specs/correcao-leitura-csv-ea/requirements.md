# Requirements Document - Correção de Leitura CSV do EA

## Introduction

O sistema Monstro está enfrentando problemas críticos na leitura do arquivo CSV gerado pelo Expert Advisor (EA) do MetaTrader 5. O erro "UTF-16 stream does not start with BOM" está impedindo a leitura dos dados do book de ofertas, causando falha na análise de mercado e tomada de decisões de trading.

## Requirements

### Requirement 1

**User Story:** Como um sistema de trading automatizado, eu quero ler corretamente os dados do book de ofertas do arquivo CSV gerado pelo EA, para que possa tomar decisões de trading baseadas em dados válidos.

#### Acceptance Criteria

1. WHEN o sistema tenta ler o arquivo book_data_win.csv THEN deve conseguir processar o arquivo independente da codificação utilizada
2. WHEN o arquivo CSV contém dados em diferentes codificações THEN o sistema deve detectar automaticamente a codificação correta
3. WHEN ocorre erro de codificação THEN o sistema deve tentar múltiplas codificações antes de falhar
4. WHEN o arquivo está sendo escrito pelo EA THEN o sistema deve aguardar e tentar novamente sem gerar erro crítico

### Requirement 2

**User Story:** Como um desenvolvedor do sistema, eu quero ter logs detalhados sobre a leitura do arquivo CSV, para que possa diagnosticar problemas de codificação e formato.

#### Acceptance Criteria

1. WHEN o sistema tenta ler o arquivo CSV THEN deve logar a codificação detectada e utilizada
2. WHEN há erro na leitura THEN deve logar o tipo específico do erro e a tentativa de correção
3. WHEN o arquivo é lido com sucesso THEN deve logar estatísticas básicas dos dados lidos
4. WHEN múltiplas tentativas são feitas THEN deve logar cada tentativa e seu resultado

### Requirement 3

**User Story:** Como um sistema robusto, eu quero ter mecanismos de fallback para leitura de dados, para que continue operando mesmo com problemas temporários no arquivo CSV.

#### Acceptance Criteria

1. WHEN o arquivo CSV não pode ser lido THEN deve usar dados do book do MT5 como fallback
2. WHEN há problemas de acesso ao arquivo THEN deve aguardar e tentar novamente com backoff exponencial
3. WHEN o arquivo está corrompido THEN deve detectar e reportar o problema sem travar o sistema
4. WHEN não há dados válidos disponíveis THEN deve aguardar sem consumir recursos excessivos

### Requirement 4

**User Story:** Como um sistema de trading, eu quero validar a integridade dos dados lidos do CSV, para que não tome decisões baseadas em dados corrompidos.

#### Acceptance Criteria

1. WHEN dados são lidos do CSV THEN deve validar se os volumes são números válidos e positivos
2. WHEN há dados inconsistentes THEN deve descartar a leitura e tentar novamente
3. WHEN os dados passam na validação THEN deve processar normalmente
4. WHEN há padrões suspeitos nos dados THEN deve alertar mas continuar operando

### Requirement 5

**User Story:** Como um operador do sistema, eu quero que o sistema seja resiliente a problemas de arquivo, para que não pare de operar por problemas temporários de I/O.

#### Acceptance Criteria

1. WHEN há erro de permissão no arquivo THEN deve aguardar e tentar novamente
2. WHEN o arquivo não existe temporariamente THEN deve aguardar sua criação
3. WHEN há lock no arquivo pelo EA THEN deve aguardar a liberação
4. WHEN há múltiplas falhas consecutivas THEN deve aumentar o intervalo entre tentativas
