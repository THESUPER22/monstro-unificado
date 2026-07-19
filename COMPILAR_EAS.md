# 🔧 GUIA RÁPIDO - COMPILAR EAs

## 📋 ERROS CORRIGIDOS
- ✅ Removidos caracteres especiais (acentos)
- ✅ Corrigida sintaxe MQL5
- ✅ Removidos comentárioseres inválidos
- ✅ EAs prontos para compilação

## 🚀 COMPILAÇÃO PASSO A PASSO

### **1. Abrir MetaEditor**
```
1. Abra MT5
2. Pressione F4 ou clique no ícone MetaEditor
3. MetaEditor será aberto
```

### **2. Compilar EA_BookData_WDO.mq5**
```
1. No MetaEditor: File → Open → EA_BookData_WDO.mq5
2. Pressione F7 ou clique em "Compile"
3. Verifique se aparece "0 errors, 0 warnings"
4. EA compilado com sucesso!
```

### **3. Compilar EA_BookData_WIN.mq5**
```
1. No MetaEditor: File → Open → EA_BookData_WIN.mq5
2. Pressione F7 ou clique em "Compile"
3. Verifique se aparece "0 errors, 0 warnings"
4. EA compilado com sucesso!
```

## 📊 INSTALAÇÃO NOS GRÁFICOS

### **Sistema Principal (WDO):**
```
1. Abra gráfico WDO (ex: WDOF25)
2. Navigator → Expert Advisors → EA_BookData_WDO
3. Arraste para o gráfico
4. Configurações:
   - InpUpdateInterval: 100
   - InpDebugMode: false
5. Clique OK
6. Verifique log: "Book WDO ativado com sucesso"
```

### **Sistema WIN v2:**
```
1. Abra gráfico WIN (ex: WINF25)
2. Navigator → Expert Advisors → EA_BookData_WIN
3. Arraste para o gráfico
4. Configurações:
   - InpUpdateInterval: 100
   - InpDebugMode: false
5. Clique OK
6. Verifique log: "Book WIN ativado com sucesso"
```

## ✅ VERIFICAÇÃO DE FUNCIONAMENTO

### **Logs Esperados:**
```
WDO: "EA BookData WDO iniciando..."
WDO: "Usando contrato WDO: WDOF25"
WDO: "Book WDO ativado com sucesso para WDOF25"
WDO: "Arquivo WDO criado: book_data.csv"

WIN: "EA BookData WIN iniciando..."
WIN: "Usando contrato WIN: WINF25"
WIN: "Book WIN ativado com sucesso para WINF25"
WIN: "Arquivo WIN criado: book_data_win.csv"
```

### **Arquivos Gerados:**
```
Pasta: C:\Users\[USER]\AppData\Roaming\MetaQuotes\Terminal\[ID]\MQL5\Files\

Deve conter:
✅ book_data.csv (WDO)
✅ book_data_win.csv (WIN)
```

## 🎯 INICIALIZAÇÃO DOS SISTEMAS

### **Após EAs Funcionando:**
```
# Sistema Principal WDO
iniciar_monstro.bat

# Sistema WIN v2
iniciar_monstro_win_v2.bat
```

## 🔍 TROUBLESHOOTING

### **Erro de Compilação:**
```
Solução:
1. Verifique se não há caracteres especiais
2. Salve arquivo em UTF-8
3. Recompile
```

### **EA não encontra contrato:**
```
Solução:
1. Adicione símbolo ao Market Watch
2. Verifique se símbolo está ativo
3. Reinicie EA
```

### **Arquivo CSV não é criado:**
```
Solução:
1. Verifique permissões pasta MQL5\Files
2. Reinicie MT5
3. Recompile EA
```

## 📋 CHECKLIST FINAL

- [ ] EA_BookData_WDO.mq5 compilado sem erros
- [ ] EA_BookData_WIN.mq5 compilado sem erros
- [ ] EA_BookData_WDO ativo no gráfico WDO
- [ ] EA_BookData_WIN ativo no gráfico WIN
- [ ] Arquivo book_data.csv sendo gerado
- [ ] Arquivo book_data_win.csv sendo gerado
- [ ] Logs dos EAs funcionando
- [ ] Sistemas prontos para inicialização

---
**🤖 EAs corrigidos e prontos para uso!**
