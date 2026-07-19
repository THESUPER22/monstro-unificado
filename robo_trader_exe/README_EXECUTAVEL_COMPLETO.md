# 🤖 ROBÔ TRADER MONSTRO - EXECUTÁVEL COMPLETO

## 📋 VISÃO GERAL

Este é o executável completo do Robô Trader Monstro, um sistema de trading automatizado com IA que opera contratos de mini dólar (WDO) e mini índice (WIN) na B3.

## 🎯 CARACTERÍSTICAS PRINCIPAIS

✅ **Executável único (.exe)** - Tudo empacotado em um arquivo
✅ **Proteção por data** - Expira automaticamente após 30 dias
✅ **Modo silencioso** - Não abre terminal do Windows
✅ **IA integrada** - Modelos Keras/TensorFlow incluídos
✅ **Expert Advisor universal** - Funciona com WIN e WDO
✅ **Gerador CSV** - Coleta dados do índice automaticamente
✅ **Dashboard web** - Interface de monitoramento

## 📁 ARQUIVOS INCLUÍDOS

### Executável Principal
- `RoboTraderMonstro.exe` - Sistema principal completo

### Expert Advisor MQL5
- `EA_BookData_Universal.mq5` - EA universal para WIN/WDO

### Configurações
- `config_win_v2.json` - Configuração para WIN (Mini Índice)
- `config.json` - Configuração geral/WDO

### Modelos de IA
- `modelo_monstro.h5` - Modelo principal (WDO)
- `modelo_monstro_win.h5` - Modelo WIN
- `modelo_monstro.keras` - Backup formato Keras
- `modelo_monstro_metadata.json` - Metadados do modelo

### Dados e Históricos
- `historico_contexto.csv` - Histórico WDO
- `historico_contexto_win.csv` - Histórico WIN
- `decisions.csv` - Log de decisões
- `memoria.pkl` - Buffer de experiências
- `parametros_ia_saida.json` - Parâmetros da IA

### Scripts Auxiliares
- `gerador_csv_universal.py` - Gerador de CSV com dados do índice
- `dashboard_tempo_real.py` - Dashboard web
- `diagnostico_monstro.py` - Diagnóstico do sistema

## 🚀 INSTALAÇÃO E USO

### 1. Preparação
```
1. Extraia todos os arquivos do ZIP
2. Certifique-se que o MetaTrader 5 está instalado
3. Tenha uma conta de trading configurada
```

### 2. Configuração MT5
```
1. Abra o MetaTrader 5
2. Pressione F4 para abrir o MetaEditor
3. Abra o arquivo EA_BookData_Universal.mq5
4. Pressione F7 para compilar (deve mostrar "0 errors")
5. Feche o MetaEditor
```

### 3. Ativação do EA
```
1. No MT5, abra um gráfico WIN (ex: WINF25) ou WDO (ex: WDOF25)
2. No Navigator, vá em Expert Advisors
3. Arraste EA_BookData_Universal para o gráfico
4. Configure:
   - InpUpdateInterval: 100
   - InpDebugMode: false
5. Clique OK
6. Verifique se aparece um "smile" no gráfico
```

### 4. Execução do Robô
```
1. Execute RoboTraderMonstro.exe
2. O sistema iniciará automaticamente
3. Aguarde a mensagem "Sistema iniciado com sucesso"
4. Monitore os logs na tela
```

## 🔧 FUNCIONALIDADES ESPECIAIS

### Gerador CSV Universal
O executável inclui um gerador CSV que coleta dados do índice:
- Reconhece automaticamente WIN ou WDO
- Gera arquivo `dados_coletados_win.csv` ou `dados_coletados_wdo.csv`
- Coleta: preços, volumes, spread, níveis do book
- Funciona com qualquer EA MQL5 que gere `book_data.csv`

### Dashboard Web
Acesse `http://localhost:5001` ou `http://localhost:5002` para ver:
- Performance em tempo real
- Gráficos de P&L
- Status das operações
- Métricas da IA

### Proteção por Data
- O executável expira automaticamente após 30 dias
- Mostra aviso quando restam 7 dias ou menos
- Para renovar, solicite nova versão

## ⚙️ CONFIGURAÇÕES

### Para WIN (Mini Índice)
- Volume: 5 contratos
- SL: 90 pontos
- TP: 35 pontos
- Tick size: 0.2

### Para WDO (Mini Dólar)
- Volume: 1 contrato
- SL: 5 pontos
- TP: 10 pontos
- Tick size: 0.5

## 🛡️ GERENCIAMENTO DE RISCO

- **Stop Loss diário**: -R$ 1.000 (WIN) / -R$ 500 (WDO)
- **Spread máximo**: 10 pontos (WIN) / 5 pontos (WDO)
- **Horário de operação**: 09:00 às 18:20
- **Circuit breakers**: 3 losses seguidos = pausa
- **Trailing stop**: Ativo após 15-20 pontos de lucro

## 📊 MONITORAMENTO

### Logs do Sistema
O executável gera logs detalhados mostrando:
- Decisões da IA com probabilidades
- Execução de ordens
- Monitoramento de posições
- Alertas de risco

### Arquivos Gerados
- `monstro_v2.log` - Log principal
- `dados_coletados_*.csv` - Dados coletados
- Backups automáticos dos modelos

## 🔍 SOLUÇÃO DE PROBLEMAS

### EA não está funcionando
```
1. Verifique se o EA foi compilado sem erros
2. Certifique-se que está no gráfico correto (WIN/WDO)
3. Verifique se o arquivo book_data.csv está sendo gerado
4. Caminho: MT5/MQL5/Files/book_data.csv
```

### Executável não inicia
```
1. Execute como Administrador
2. Verifique se o MT5 está aberto
3. Certifique-se que todos os arquivos foram extraídos
4. Verifique se não há antivírus bloqueando
```

### Sem conexão com MT5
```
1. Verifique se o MT5 está logado na conta
2. Teste a conexão manualmente no MT5
3. Reinicie o MT5 e tente novamente
```

## 📈 PERFORMANCE ESPERADA

### Metas do Sistema
- **Taxa de acerto**: 60-70%
- **Profit Factor**: > 1.5
- **Drawdown máximo**: < 10%
- **Operações/dia**: 5-15

### Melhorias Implementadas
1. **Trailing Stop Inteligente** (+3% eficácia)
2. **Balanceamento BUY/SELL** (+2% eficácia)
3. **Modos de Mercado** (+2% eficácia)
4. **Circuit Breakers** (+1.5% eficácia)
5. **Saída Inteligente** (+1.5% eficácia)

## 🔒 SEGURANÇA

- Código ofuscado (opcional)
- Proteção por data de expiração
- Backups automáticos dos modelos
- Validação de dados de entrada
- Encerramento seguro de posições

## 📞 SUPORTE

Para renovação, suporte técnico ou dúvidas:
- **Data de expiração**: Verificar no executável
- **Versão**: 2.0 Executável
- **Compatibilidade**: Windows 10/11, MT5

## ⚠️ AVISOS IMPORTANTES

1. **Teste sempre em conta demo primeiro**
2. **Monitore as operações regularmente**
3. **Mantenha backup das configurações**
4. **Não altere os arquivos de modelo**
5. **Respeite os horários de operação**
6. **Use apenas em contas com capital adequado**

---

**🎯 Meta: Chegar a 100% de eficácia mantendo simplicidade**

*Sistema desenvolvido para traders profissionais. Use com responsabilidade.*
