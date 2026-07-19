# 🎯 MONSTRO WIN V2 - MINI ÍNDICE

## 📋 VISÃO GERAL
O Monstro WIN v2 é uma versão especializada do sistema de trading automatizado para operar no **Mini Índice (WIN)** da B3, mantendo o mesmo núcleo de IA do sistema principal mas com configurações otimizadas para o WIN.

## ⚙️ CONFIGURAÇÕES PRINCIPAIS

### 📊 Especificações WIN
- **Símbolo**: WIN (Mini Índice Bovespa)
- **Volume**: 5 contratos por operação
- **Stop Loss**: 90 pontos
- **Take Profit**: 35 pontos
- **Tick Size**: 0.2 pontos
- **Ticks por Ponto**: 10.000 (1 ponto = 10.000 ticks)

### 💰 Gestão de Risco
- **Perda Máxima Diária**: -R$ 1.000
- **Drawdown Máximo**: -R$ 500 por operação
- **Spread Máximo**: 10 pontos
- **Volume Mínimo Book**: 500 contratos

### 🕐 Horários de Operação
- **Pregão**: 09:00 às 18:20
- **After Market**: até 18:32
- **Limite Ordens**: 18:15
- **Encerramento Automático**: 18:20

## 🔧 INSTALAÇÃO E CONFIGURAÇÃO

### 1. Arquivos Necessários
```
✅ monstro_unificado_v2.py      # Sistema principal WIN
✅ config_win_v2.json           # ConfiguraWIN
✅ EA_BookData_Universal.mq5    # EA para capturar book
✅ iniciar_monstro_win_v2.bat   # Script de inicialização
```

### 2. Configuração MT5
1. Abra o MetaTrader 5
2. Compile o EA_BookData_Universal.mq5
3. Adicione o EA em um gráfico WIN (ex: WINF25)
4. Configure o EA:
   - **InpSymbol**: (deixe vazio para usar símbolo do gráfico)
   - **InpUpdateInterval**: 100ms
   - **InpDebugMode**: false

### 3. Inicialização
```batch
# Execute o script de inicialização
iniciar_monstro_win_v2.bat
```

## 🧠 INTELIGÊNCIA ARTIFICIAL

### Compartilhamento com Sistema Principal
- ✅ **Pode usar o mesmo modelo Keras/H5** do sistema principal
- ✅ **Arquitetura neural idêntica** (11 features)
- ✅ **Mesmo algoritmo de aprendizado** por reforço
- ⚠️ **Arquivos separados** para evitar conflitos:
  - `modelo_monstro_win.h5` (WIN)
  - `modelo_monstro.h5` (WDO)

### Transferência de Aprendizado
O sistema WIN v2 pode:
1. **Iniciar com modelo zerado** (aprendizado do zero)
2. **Copiar modelo do WDO** (transferência de conhecimento)
3. **Evoluir independentemente** após inicialização

## 📊 DIFERENÇAS TÉCNICAS WIN vs WDO

| Aspecto | WDO (Principal) | WIN (v2) |
|---------|-----------------|----------|
| **Tick Size** | 0.5 | 0.2 |
| **Ticks/Ponto** | 1.000 | 10.000 |
| **Volume Padrão** | 1 contrato | 5 contratos |
| **SL** | 5 pontos | 90 pontos |
| **TP** | 10 pontos | 35 pontos |
| **Magic Number** | 123456 | 123457 |
| **Port Dashboard** | 5001 | 5002 |
| **Log File** | monstro.log | monstro_v2.log |

## 🎯 CÁLCULOS DE PONTOS E TICKS

### WIN (Mini Índice)
```python
# 1 ponto WIN = 10.000 ticks
# SL 90 pontos = 900.000 ticks
# TP 35 pontos = 350.000 ticks

# Exemplo de cálculo:
preco_entrada = 125000  # 125.000 pontos
sl_buy = preco_entrada - (90 * 10000 * 0.2)  # 90 pontos abaixo
tp_buy = preco_entrada + (35 * 10000 * 0.2)  # 35 pontos acima
```

### Validação dos Cálculos
- ✅ **SL 90 pontos** = 900.000 ticks = R$ 180 por contrato (aprox)
- ✅ **TP 35 pontos** = 350.000 ticks = R$ 70 por contrato (aprox)
- ✅ **5 contratos** = Risco máximo ~R$ 900 por operação

## 🌐 DASHBOARD WEB

### Acesso
- **URL**: http://localhost:5002
- **Funcionalidades**:
  - Performance em tempo real
  - Distribuição de scores
  - Progresso do aprendizado
  - Status de bloqueios
  - Balanceamento BUY/SELL

## 📁 ESTRUTURA DE ARQUIVOS

```
C:\AIOFEN\
├── monstro_unificado.py          # Sistema principal (WDO)
├── monstro_unificado_v2.py       # Sistema WIN (este)
├── config.json                   # Config WDO
├── config_win_v2.json           # Config WIN
├── modelo_monstro.h5             # Modelo WDO
├── modelo_monstro_win.h5         # Modelo WIN
├── historico_contexto.csv        # Histórico WDO
├── historico_contexto_win.csv    # Histórico WIN
├── EA_BookData_Universal.mq5     # EA universal
└── iniciar_monstro_win_v2.bat    # Inicialização WIN
```

## ⚠️ IMPORTANTES CONSIDERAÇÕES

### 1. Não Interferência
- ✅ **Sistema principal WDO** permanece **100% intacto**
- ✅ **Arquivos separados** evitam conflitos
- ✅ **Magic numbers diferentes** (123456 vs 123457)
- ✅ **Ports diferentes** (5001 vs 5002)

### 2. EA Universal
- ✅ **Mesmo EA** serve para WDO e WIN
- ✅ **Detecção automática** do tipo de contrato
- ✅ **Formato CSV idêntico** para ambos sistemas

### 3. Modelo de IA
- ✅ **Pode compartilhar** conhecimento inicial
- ✅ **Evolui independentemente** após inicialização
- ✅ **Mesma arquitetura** neural (11 features)

## 🚀 COMANDOS RÁPIDOS

```batch
# Iniciar WIN v2
iniciar_monstro_win_v2.bat

# Ver logs WIN
type monstro_v2.log

# Dashboard WIN
start http://localhost:5002

# Parar sistema
Ctrl+C no terminal
```

## 📞 SUPORTE

Para dúvidas ou problemas:
1. Verifique os logs em `monstro_v2.log`
2. Confirme se o EA está ativo no MT5
3. Verifique se o book está habilitado
4. Teste a conectividade MT5-Python

---
**🤖 Monstro WIN v2 - Especializado em Mini Índice**
*Mantendo a excelência do sistema principal com otimizações para WIN*
