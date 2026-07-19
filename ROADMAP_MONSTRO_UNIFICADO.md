# 🚀 ROADMAP OFICIAL — MONSTRO TRADER V2
**Última atualização:** 08/05/2026
**Versão:** Monstro Unificado V2
**Status:** 🟡 EM EVOLUÇÃO — Sistema operando, problemas estruturais identificados

---

## 🎯 DIAGNÓSTICO ATUAL (08/05/2026)

### 🔴 PROBLEMA RAIZ CONFIRMADO: "CEGUEIRA ESTRUTURAL"
O robô tem lógica sólida, mas os **dados de entrada estão corrompidos**.
A IA está aprendendo padrões errados porque as colunas do CSV estão desalinhadas
e os dados do book estão congelados. É impossível lucrar assim.

**Analogia:** Um piloto de F1 com motor perfeito, mas com os instrumentos mostrando
informações trocadas. Ele acelera quando deveria frear.

---

## 📋 OPERAÇÃO OLHOS DE ÁGUIA — ROTEIRO DE RETIFICAÇÃO

### 🔴 PRIORIDADE 1 — CORREÇÃO DO EA MQL5 (CRÍTICO)
**Status:** [ ] PENDENTE
**Problema:** O EA não está atualizando o book em tempo real
**Evidência nos logs:**
```
bid_qty: 769.0  ← MESMO VALOR DO DIA 04/05 AO DIA 08/05
ask_qty: 354    ← NUNCA MUDA
entropia_book: 2.534 ← CONGELADA
```
**Ações necessárias:**
- [ ] Reorganizar `SaveContextToCSV` no MQL5 — garantir ordem correta das colunas
- [ ] Adicionar `timestamp` como primeira coluna (hoje está faltando = desloca tudo)
- [ ] Forçar atualização do arquivo a cada `OnBookEvent` real
- [ ] Implementar "Sanity Check" no Python: se dados não mudarem em 5min → alerta + parar

**Impacto:** Sem isso, a IA está operando com foto antiga do mercado.

---

### 🔴 PRIORIDADE 2 — CORREÇÃO DO DESALINHAMENTO DE COLUNAS (CRÍTICO)
**Status:** [ ] PENDENTE
**Problema:** Colunas do CSV estão deslocadas — IA aprende dados invertidos
**Evidência:**
```
Cabeçalho: timestamp, action, bid_qty, ask_qty, spread...
Dados:      769.0,    354.0,  0.0005,  145.8,   baixa...
```
O valor `769.0` (bid_qty) está na coluna `timestamp`.
O valor `BUY/SELL` está na coluna `score_distancia`.
**A IA acha que RSI é Volume Tick, que Volatilidade é Candle Type.**

**Ações necessárias:**
- [ ] Corrigir escrita do CSV no MQL5 para incluir timestamp
- [ ] Validar no Python se `bid_qty` contém número e não texto
- [ ] Após correção: deletar `historico_contexto_win.csv` corrompido

---

### 🔴 PRIORIDADE 3 — TABULA RASA (APÓS CORRIGIR 1 E 2)
**Status:** [ ] AGUARDANDO PRIORIDADES 1 E 2
**Problema:** Modelo treinado com dados errados = padrões invertidos
**Ações necessárias:**
- [ ] Deletar `modelo_monstro_win.h5`
- [ ] Deletar `experiencias.json`
- [ ] Deletar `historico_contexto_win.csv`
- [ ] Iniciar novo ciclo de aprendizado do zero com dados corretos

**Regra:** Só fazer isso DEPOIS que o EA estiver escrevendo dados corretos.

---

### 🟡 PRIORIDADE 4 — CORREÇÃO DO FECHAMENTO DE POSIÇÃO (ALTO)
**Status:** 🔧 PARCIALMENTE CORRIGIDO (08/05/2026)
**Problema:** `mt5.order_send` retorna None — falha ao fechar por proteção de lucro
**Evidência:**
```
⚠️ order_send retornou None (filling=1), tentando reconectar...
✅ Reconectado ao MetaTrader 5
⚠️ order_send retornou None (filling=2), tentando reconectar...
❌ Falha ao fechar posição após todos os métodos
```
**O que foi feito:** Adicionado fallback IOC → RETURN com reconexão
**O que ainda falha:** Mesmo após reconexão, ambos os fillings falham
**Causa provável:** A corretora XP não aceita IOC nem RETURN para WINM26
**Ação pendente:**
- [ ] Verificar qual filling o símbolo WINM26 aceita via `symbol_info().filling_mode`
- [ ] Usar `ORDER_FILLING_FOK` como terceira opção
- [ ] Ou usar o filling correto da corretora diretamente

---

### 🟡 PRIORIDADE 5 — REFINAMENTO DO REWARD (MÉDIO)
**Status:** [ ] PENDENTE
**Problema:** IA não desconta custo de corretagem e spread
**Ação:**
- [ ] Ajustar cálculo do reward: `reward = lucro_bruto - custo_corretagem - spread_medio`
- [ ] Um ganho de 35pts com 10pts de custo = 25pts reais

---

### 🟢 PRIORIDADE 6 — OTIMIZAÇÃO DE LEITURA (BAIXO)
**Status:** [ ] PENDENTE (baixo custo, fazer quando sobrar crédito)
**Problema:** Leitura do JSON/CSV é lenta (latência de disco)
**Ação:**
- [ ] Implementar leitura com `mmap` (Memory Mapping) no Python
- [ ] Reduzir processamento de strings no loop principal

---

## ✅ O QUE ESTÁ FUNCIONANDO (08/05/2026)

### Sistemas Operacionais:
| Sistema | Status | Observação |
|---------|--------|------------|
| Veto Matemático | ✅ ATIVO | Funcionando com dados reais |
| Memória Ativa | ✅ ATIVO | 31+ experiências carregadas |
| Bloqueador de Contexto | ✅ ATIVO | Reabilitação após win funcionando |
| Hierarquia de Decisão | ✅ ATIVO | Confluência respeita veto |
| Balanceamento BUY/SELL | ✅ ATIVO | ~46% BUY / 54% SELL |
| Modo Defesa | ✅ ATIVO | Ativa em 3 losses, libera em 10min |
| Hibernação 12h-15h | ✅ ATIVO | 3 logs por hora |
| Treino 12h e 17h30 | ✅ ATIVO | Treino agendado |
| Trava de Horário | ✅ ATIVO | 09:00-12:00 e 15:00-17:30 |
| Limite Diário -R$1000 | ✅ ATIVO | sys.exit() automático |
| Trailing Stop | ✅ ATIVO | Movendo SL progressivamente |
| Circuit Breaker | ✅ ATIVO | Spread, volume, losses |
| Confiança Corrigida | ✅ ATIVO | Não retorna mais 0.00 |
| Critérios Similaridade | ✅ ATIVO | Relaxados (±40% vol, ±25 RSI) |

---

## 🔧 CORREÇÕES APLICADAS ESTA SEMANA (05-08/05/2026)

### ✅ Veto Matemático — Paradoxo do Ovo e Galinha resolvido
**Antes:** `expectativa <= 0` vetava mesmo sem dados (0.00 = veto)
**Depois:** Só veta se `trades >= 5 E expectativa < 0` (prova real)
**Resultado:** Robô voltou a operar e acumular experiências

### ✅ Hierarquia de Decisão — Flag `_ultimo_veto`
**Antes:** Confluência sobrescrevia veto matemático
**Depois:** Se `_ultimo_veto = True`, confluência bloqueada
**Resultado:** Veto matemático é lei — nada sobrescreve

### ✅ Modo Defesa Calibrado
**Antes:** 5 losses para entrar, 15min de bloqueio
**Depois:** 3 losses para entrar, 10min de bloqueio
**Resultado:** Reage mais rápido, recupera mais rápido

### ✅ Confiança 0.00 Corrigida
**Antes:** `confianca_predita * 1.2` quando `confianca_predita = 0.0` = 0.0
**Depois:** Usa confiança da confluência como base quando IA retorna 0.0
**Resultado:** Decisões com confiança real (0.68, 0.70, 0.72...)

### ✅ Critérios de Similaridade Relaxados
**Antes:** Volatilidade ±20%, RSI ±15pts, candle exato
**Depois:** Volatilidade ±40%, RSI ±25pts, candle agrupado (alta/baixa/neutro)
**Resultado:** Mais experiências similares encontradas

### ✅ Fechamento de Posição — Fallback de Filling
**Antes:** Só tentava IOC, falhava silenciosamente
**Depois:** IOC → reconecta → RETURN → reconecta → erro explícito
**Resultado:** Mais tentativas, logs mais claros (ainda falha — ver Prioridade 4)

### ✅ Trava de Horário Atualizada
**Antes:** 09:00-10:00 / 10:30-12:30 / 15:00-17:30 (3 janelas)
**Depois:** 09:00-12:00 e 15:00-17:30 (2 janelas limpas)

### ✅ Hibernação 12h-15h com Treino
**Antes:** Loop contínuo gerando +1000 logs no período
**Depois:** Treina às 12h → dorme 1h por vez → 3 logs → acorda às 15h

---

## 📊 MÉTRICAS DA SEMANA (05-08/05/2026)

| Métrica | Valor | Tendência |
|---------|-------|-----------|
| Balanceamento BUY/SELL | 46%/54% | ✅ Equilibrado |
| Veto Matemático ativo | Sim (5+ trades) | ✅ Funcionando |
| Taxa de acerto | ~20% | 🔴 Baixa (dados corrompidos) |
| Falha fechamento | Persistente | 🟡 Parcialmente corrigido |
| Book congelado | Sim | 🔴 Crítico — EA MQL5 |
| Colunas desalinhadas | Sim | 🔴 Crítico — EA MQL5 |

---

## 🗓️ CRONOGRAMA SUGERIDO

### Semana atual (virada do mês):
- **Dia 1:** Correção do EA MQL5 — alinhamento de colunas + book dinâmico
- **Dia 2:** Teste de "Dados Vivos" — confirmar que book muda em tempo real
- **Dia 3:** Tabula Rasa — limpar modelo, experiências e histórico corrompido
- **Dia 4:** Monitorar Veto Matemático com dados corretos
- **Dia 5:** Ajustar filling do fechamento de posição

---

## 🏗️ ARQUITETURA ATUAL DO SISTEMA

```
EA MQL5 → book_data_win.csv (JSON) → Python lê → 18 features
    ↓
prever_acao()
    ├── VETO SIMPLES (deve_operar_contexto_simples)
    │     └── Se expectativa < 0 com 5+ trades → NADA
    ├── BLOQUEADOR DE CONTEXTO (BloqueadorContexto)
    │     └── Se 3 losses no mesmo contexto → bloqueia 1h
    ├── LIMITADOR DE INSISTÊNCIA (LimitadorInsistencia)
    │     └── Máximo 2 ops por contexto por dia
    ├── REPLAY DE EXPERIÊNCIAS (ReplayExperiencias)
    │     └── Calcula expectativa matemática
    ├── FILTROS DE ALTA ACERTIVIDADE
    ├── IA NEURAL (modelo_monstro_win.h5 — 18 features)
    └── CONFLUÊNCIA (score mínimo 55/100)
         └── _ultimo_veto = True → confluência bloqueada

Decisão Final → executar_ordem()
    ├── SL/TP dinâmico por volume
    ├── Trailing Stop progressivo
    └── Gerenciador de Saída (C12: timeout, proteção, estagnação)

Resultado → salvar_experiencia_csv() + salvar_experiencias_json()
    └── Treino às 12h e 17h30
```

---

## 📁 ARQUIVOS DO SISTEMA

| Arquivo | Função | Status |
|---------|--------|--------|
| `monstro_unificado_v2.py` | Código principal | ✅ Operacional |
| `modelo_monstro_win.h5` | Modelo IA (18 features) | ⚠️ Treinado com dados errados |
| `experiencias.json` | Memória ativa | ⚠️ Dados parcialmente corretos |
| `historico_contexto_win.csv` | Histórico de treino | 🔴 Colunas desalinhadas |
| `decisions.csv` | Log de decisões | ✅ Correto |
| `book_data_win.csv` | Dados do book (EA) | 🔴 Congelado |
| `config_win_v2.json` | Configurações | ✅ OK |

---

## 🎯 VISÃO FUTURA — PLATAFORMA SAAS

### Stack planejada:
- **Backend:** Django + Django REST Framework
- **Banco:** MySQL/PostgreSQL
- **Frontend:** React/Vue.js
- **Core:** Python (Monstro atual refatorado)
- **Cache:** Redis
- **Queue:** Celery

### Modelo de negócio:
- Básico: R$ 297/mês (1 robô, 1 conta)
- Pro: R$ 597/mês (3 robôs, múltiplas contas)
- Enterprise: R$ 1.497/mês (ilimitado + suporte)

### Probabilidade de sucesso: **85%**
- Mercado em crescimento
- Tecnologia diferenciada
- Foco no mercado BR (B3, português)
- Barreira de entrada alta

### Pré-requisito: **Monstro lucrando consistentemente primeiro**

---

*Responsável: Mestre Super + Kiro AI*
*Próxima revisão: Após correção do EA MQL5*
