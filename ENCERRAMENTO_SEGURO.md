# 🔴 SISTEMA DE ENCERRAMENTO SEGURO - MONSTRO DAS NEGOCIAÇÕES

## 📋 Visão Geral

O sistema de encerramento seguro garante que o robô Monstro das Negociações seja desligado de forma controlada, salvando todos os dados importantes e fechando conexões adequadamente.

## ⏰ Sequência de Encerramento

### 1. **18:15 - Parada de Novas Ordens**
- ✅ Para de aceitar novas ordens de entrada
- ✅ Posições abertas continuam sendo monitoradas
- ✅ Trailing stops e gerenciamento de risco continuam ativos

### 2. **18:20 - Fechamento de Posições**
- ✅ Fecha **TODAS** as posições abertas automaticamente
- ✅ Salva o modelo de IA
- ✅ Registra estatísticas da sessão
- ✅ Atualiza variáveis globais para encerramento

### 3. **18:32 - Encerramento Completo**
- ✅ Salva todos os dados finais
- ✅ Fecha conexões MT5
- ✅ Para threads de forma segura
- ✅ Gera relatórios finais
- ✅ **DESLIGA O SISTEMA AUTOMATICAMENTE**

## 💾 Dados Salvos no Encerramento

### Modelo de IA
- `modelo_monstro.h5` - Modelo principal
- `modelo_monstro.keras` - Backup em formato Keras
- Backups automáticos com timestamp

### Experiências e Dados
- `experiencias_finais.json` - Todas as experiências da sessão
- `estatisticas_finais.json` - Estatísticas completas
- `decisions.csv` - Histórico de decisões
- `historico_contexto.csv` - Contexto histórico

### Estatísticas Finais
```json
{
  "timestamp_encerramento": "2025-01-14T18:32:00",
  "total_experiencias": 150,
  "total_lucros": 245.50,
  "total_operacoes": 45,
  "historico_loss": [0.234, 0.189, 0.145],
  "contagem_acoes": {
    "BUY": 23,
    "SELL": 20,
    "NADA": 2
  },
  "razao_buy_sell": 0.535
}
```

## 🛡️ Proteção Contra Fechamento Abrupto

### Tratamento de Sinais
- **SIGTERM** - Encerramento solicitado pelo sistema
- **SIGINT** - Ctrl+C do usuário
- **SIGBREAK** - Interrupção no Windows

### Comportamento
1. **Primeiro sinal**: Inicia encerramento seguro
2. **Segundo sinal**: Força encerramento imediato
3. **Dados salvos**: Mesmo em caso de erro

## 🔧 Como Usar

### Execução Normal
```bash
cd /d C:\AIOFEN
call venv310\Scripts\activate
python monstro_unificado.py
```

### Teste do Sistema
```bash
# Testa todos os componentes
python teste_encerramento_seguro.py

# Testa apenas horários
python teste_encerramento.py
```

### Configuração de Horários
```bash
# Altera horários interativamente
python configurar_encerramento.py
```

## 🚨 Situações de Emergência

### Encerramento Manual Seguro
```python
# No código ou console Python
encerramento_seguro_completo(modelo_ia_local, memoria_experiencias)
```

### Encerramento por Sinal
```bash
# Linux/Mac
kill -TERM <pid_do_processo>

# Windows
taskkill /PID <pid_do_processo>

# Ou simplesmente
Ctrl+C
```

## 📁 Estrutura de Arquivos Após Encerramento

```
C:\AIOFEN\
├── modelo_monstro.h5                 # Modelo principal
├── modelo_monstro.keras              # Backup Keras
├── modelo_monstro.backup_*           # Backups automáticos
├── experiencias_finais.json          # Experiências da sessão
├── estatisticas_finais.json          # Estatísticas completas
├── decisions.csv                     # Decisões tomadas
├── historico_contexto.csv           # Contexto histórico
└── monstro.log                      # Log completo
```

## 🔍 Verificação Pós-Encerramento

### Checklist de Verificação
- [ ] Arquivo `modelo_monstro.h5` existe e não está corrompido
- [ ] Arquivo `experiencias_finais.json` contém dados válidos
- [ ] Arquivo `estatisticas_finais.json` tem timestamp correto
- [ ] Log `monstro.log` termina com "Sistema sendo desligado..."
- [ ] Nenhum processo Python do robô está rodando
- [ ] Conexão MT5 foi fechada corretamente

### Comandos de Verificação
```bash
# Verifica se processo ainda está rodando
tasklist | findstr python

# Verifica tamanho dos arquivos
dir *.json *.h5 *.log

# Verifica última linha do log
Get-Content monstro.log -Tail 10
```

## ⚠️ Avisos Importantes

1. **NÃO FORCE O FECHAMENTO** durante o encerramento automático
2. **Aguarde até 18:41** para confirmar que o sistema desligou
3. **Verifique os arquivos** após cada encerramento
4. **Mantenha backups** dos modelos treinados
5. **Monitore logs** para detectar problemas

## 🛠️ Troubleshooting

### Problema: Sistema não desliga após 18:32
```bash
# Verifica se há erro no log
Get-Content monstro.log -Tail 50

# Força encerramento se necessário
taskkill /F /IM python.exe
```

### Problema: Arquivos não salvos
```bash
# Verifica espaço em disco
dir C:\AIOFEN

# Verifica permissões
icacls C:\AIOFEN
```

### Problema: Modelo corrompido
```bash
# Usa backup mais recente
copy modelo_monstro.backup_* modelo_monstro.h5
```

## 📊 Monitoramento

### Logs Importantes
- `💾 Iniciando salvamento final de dados...`
- `🔌 Iniciando fechamento seguro de conexões...`
- `🏁 ENCERRAMENTO SEGURO CONCLUÍDO COM SUCESSO`
- `💤 Sistema sendo desligado...`

### Alertas de Erro
- `❌ Erro ao salvar dados finais`
- `❌ Erro ao fechar conexões`
- `❌ Erro crítico no encerramento seguro`

## 🎯 Próximos Desenvolvimentos

- [ ] Encerramento programado por horário personalizado
- [ ] Backup automático para nuvem
- [ ] Relatórios de performance em HTML
- [ ] Notificações por email/Telegram
- [ ] Análise de performance pós-encerramento

---

**Desenvolvido com 💙 para o Mestre Super**
**Monstro das Negociações - Sistema de Encerramento Seguro v1.0**
