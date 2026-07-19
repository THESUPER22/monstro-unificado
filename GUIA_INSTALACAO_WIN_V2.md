# 🎯 GUIA DE INSTALAÇÃO - MONSTRO WIN V2

## 🔍 **PROBLEMA IDENTIFICADO**
O MT5 mostra apenas **1 book por vez** na interface, mas nossos EAs funcionam via **API** e são **independentes da tela ativa**.

## ✅ **SOLUÇÃO IMPLEMENTADA**

### 📊 **EAs Específicos Criados**
- ✅ `EA_BookData_WDO.mq5` → Para sistema principal (WDO)
- ✅ `EA_BookData_WIN.mq5` → Para sistema WIN v2
- ✅ **Funcionam independente da tela ativa**
- ✅ **Usam API diretamente, não interface visual**

### 📁 **Arquivos Separados**
- ✅ WDO: `book_data.csv`
- ✅ WIN: `book_data_win.csv`
- ✅ **Sem conflitos entre sistemas**

## 🚀 **INSTALAÇÃO PASSO A PASSO**

### **1. Preparação dos EAs**
```
1. Abra MetaEditor no MT5
2. Compile EA_BookData_WDO.mq5
3. Compile EA_BookData_WIN.mq5
4. Verifique se compilaram sem erros
```

### **2. Configuração WDO (Sistema Principal)**
```
1. Abra gráfico WDO (ex: WDOF25)
2. Adicione EA_BookData_WDO.mq5
3. Configurações:
   - InpUpdateInterval: 100
   - InpDebugMode: false
4. Clique OK
5. Verifique log: "✅ Book WDO ativado com sucesso"
```

### **3. Configuração WIN (Sistema v2)**
```
1. Abra gráfico WIN (ex: WINF25)
2. Adicione EA_BookData_WIN.mq5
3. Configurações:
   - InpUpdateInterval: 100
   - InpDebugMode: false
4. Clique OK
5. Verifique log: "✅ Book WIN ativado com sucesso"
```

### **4. Verificação dos Arquivos**
```
Pasta: C:\Users\[SEU_USUARIO]\AppData\Roaming\MetaQuotes\Terminal\[ID_TERMINAL]\MQL5\Files\

Deve conter:
✅ book_data.csv (WDO)
✅ book_data_win.csv (WIN)
```

### **5. Inicialização dos Sistemas**
```
# Sistema Principal WDO
iniciar_monstro.bat

# Sistema WIN v2
iniciar_monstro_win_v2.bat
```

## 🔧 **FUNCIONAMENTO TÉCNICO**

### **Como Funciona Independente da Tela**
```mql5
// Os EAs usam API diretamente:
MarketBookGet(symbol, book);  // ← Não depende da interface
OnBookEvent(symbol);          // ← Evento automático
OnTimer();                    // ← Atualização contínua
```

### **Detecção Automática de Contratos**
```mql5
// EA encontra automaticamente o contrato ativo:
string FindActiveWDOContract() // Para WDO
string FindActiveWINContract() // Para WIN

// Busca em:
1. Market Watch
2. Todos os símbolos disponíveis
3. Adiciona automaticamente se necessário
```

## 📊 **MONITORAMENTO**

### **Logs dos EAs**
```
WDO: "📊 WDO WDOF25 - BIDs: 10 (1500cc) | ASKs: 12 (1800cc)"
WIN: "📊 WIN WINF25 - BIDs: 15 (2500cc) | ASKs: 18 (3200cc)"
```

### **Dashboards Separados**
```
WDO: http://localhost:5001
WIN: http://localhost:5002
```

## ⚠️ **PONTOS IMPORTANTES**

### **1. Não Precisa Ficar na Tela**
- ✅ EAs funcionam **mesmo minimizados**
- ✅ EAs funcionam **mesmo em outra aba**
- ✅ EAs funcionam **24h independente**

### **2. Um EA por Gráfico**
- ✅ EA_BookData_WDO → Gráfico WDO
- ✅ EA_BookData_WIN → Gráfico WIN
- ✅ **Não misturar EAs nos gráficos**

### **3. Arquivos Separados**
- ✅ `book_data.csv` → Sistema WDO
- ✅ `book_data_win.csv` → Sistema WIN
- ✅ **Sem conflitos entre sistemas**

## 🔍 **TROUBLESHOOTING**

### **Problema: EA não encontra contrato**
```
Solução:
1. Verifique se símbolo está no Market Watch
2. Verifique se símbolo está ativo para trading
3. EA adicionará automaticamente se necessário
```

### **Problema: Arquivo CSV não é criado**
```
Solução:
1. Verifique permissões da pasta MQL5\Files
2. Reinicie o EA
3. Verifique logs do MT5
```

### **Problema: Book vazio**
```
Solução:
1. Verifique se símbolo suporta book
2. Verifique conexão com servidor
3. Tente reativar o EA
```

## 📋 **CHECKLIST FINAL**

### **Antes de Iniciar**
- [ ] EA_BookData_WDO compilado e ativo
- [ ] EA_BookData_WIN compilado e ativo
- [ ] Arquivos CSV sendo gerados
- [ ] Logs dos EAs funcionando
- [ ] MT5 conectado ao servidor

### **Sistemas Funcionando**
- [ ] WDO: Dashboard localhost:5001
- [ ] WIN: Dashboard localhost:5002
- [ ] Logs separados (monstro.log e monstro_v2.log)
- [ ] Modelos separados (.h5)

## 🎉 **RESULTADO FINAL**

Com essa configuração você terá:

✅ **Sistema WDO** operando **100% independente**
✅ **Sistema WIN** operando **100% independente**
✅ **Books funcionando** mesmo sem estar na tela
✅ **Sem conflitos** entre os sistemas
✅ **Monitoramento separado** para cada sistema

---

**🤖 Agora os dois sistemas podem operar simultaneamente sem interferência!**
