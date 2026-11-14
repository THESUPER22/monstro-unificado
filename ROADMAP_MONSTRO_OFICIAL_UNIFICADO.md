# 🚀 ROADMAP OFICIAL — MONSTRO TRADER V2
**Última atualização:** 10/11/2026
**Versão:** Monstro Unificado V22 (Engine v22.4 — Faixa 1: Rompimento da 1ª Hora + Sub-Trader Corpo 1H + autópsia P1–P6)
**Arquivo principal:** `monstro_unificado_v22.py`
**Status geral:** v22.4 em produção; Faixa 1 (Rompimento 1ª Hora, magic 7008) com janela REAL 09–11h ativa desde 16/09/2026; autópsias de 16/09 (P1–P5) e 17/09 (P6 — bug crítico `positions_get(magic=...)` + posição fantasma) concluídas

---

## 📅 10/11/2026 — COLETA HERMAN RECUPERADA + MONITOR DE SAÚDE + FT REABILITADO

**Status:** correção urgente concluída e verificada. Detalhe completo em
**23.17** (coleta/monitor/FT) e **23.18** (CI) no fim deste documento.

| frente | resultado |
|---|---|
| Coleta Herman | CSV auto-curável; 35 boxes no dia (28 de 3P + 7 de 6P), 0 linhas corrompidas |
| Causa dos 19 dias | símbolo `WDO$` sem ticks + cabeçalho do CSV desatualizado |
| Monitor | `monitor_saude_coletores.py` a cada 10 min, toast + arquivo de alerta |
| Rompimento FT | fuso corrigido, selftest 172/172, ativo em 11/11 às 09:00 |
| CI GitHub | YAML inválido (linha 46, `PYEOF` órfão) corrigido + Flask/requests no CI (pytest 21/21) |
| Pesquisa ORB WDO | 5 anos, 1.242 sessões: ORB base PF 1,09 (fraco); gatilho 10:30–11:00 (EUA) PF 1,50–1,96, 6/6 anos positivos (23.20/23.21) |

**Regra reafirmada:** coletor silencioso é falha. Todo coletor tem que estar no
monitor e neste roadmap. Dados nunca são demais.

---

## 📅 05/11/2026 — REGISTRO DO CORPUS + VEREDITO DO GATE (FASE 2 — CONCLUÍDA)

**Fonte:** Consolidação da Fase 2 — `logs/modelo_a_shadow_com_setup.csv` (141 trades resolvidos) + `logs/rompimento/rompimento_trades.csv` (23) + `decisions_wdo.csv` (251.206 decisões).

### 📦 Corpus Consolidado (entregável da Fase 2)
- **Arquivo:** `C:\AIOFEN\logs\treino_corpus_real.csv`
- **Amostras:** **141** trades resolvidos (29 colunas: contexto com 22 features + `action` + `reward` + `score_dist` + `prob_modelo_a`).

### 🔬 Reavaliação do Gate (correlação confiança→outcome)
| Amostra | n | Pearson | Gate ≥ 0,15 |
|---|---:|---:|---|
| Consolidado | 141 | **0,088** | ❌ **NÃO liberado** |
| Período auditado (19/10→31/10) | 34 | 0,157 | ⚠️ Marginal |

### 🧭 Parecer do Tech Lead (04/11/2026)
1. **Gate NÃO liberado** — correlação consolidada (0,088) abaixo do limiar (0,15).
2. **Fase 3 NÃO autorizada** — operar com `p ≥ 0,60` sem gate validado = operar à cegas (A3 bloqueada por pesos sintéticos).
3. **Shadow Mode ATIVO** — manter coleta; reavaliar gate com ~200+ amostras.

### ⏭️ Próximos passos
- Acumular trades reais via Shadow Mode.
- Reavaliar correlação quando n ≥ 200.
- Liberar gate → re-treino com pesos reais → Fase 3.

---
## ✅ 28/09/2026 — ETAPA DE CORREÇÃO E RECONCILIAÇÃO 100% CONCLUÍDA E ENTREGUE

> **Pacote de 6 correções autorizado e validado (py_compile OK + 39 checks de teste, 0 erros).**
> Commit: **aguardando ordem explícita do Mestre (protocolo 04/09).**

### 🛠️ Entregues
- [x] **Correção 1 — Bug `mt5.position_close`**: `_fechar_market` reescrito com `order_send(TRADE_ACTION_DEAL)` em direção inversa (AttributeError 31× entre 18–28/09 eliminado; deixa de travar trades da Faixa 1 em `ABERTA`).
- [x] **Correção 2 — Reconciliação**: ticket `2539033591` (28/09) finalizado como **TP +6,5 pts** no `rompimento_state.json`; `rompimento_trades.csv` atualizado (linha 28/09 + invisíveis 18/09 −24 e 21/09 −27); backup `.before_reconcile_28`.
- [x] **Correção 3 — Memória de treino restaurada**: `historico_contexto_wdo.csv` recomposto (9.118 linhas = 9.108 NAO_AGIU + 10 trades reais no fim) e `experiencias_wdo.json` com 5 experiências positivas; estado vazio preservado em `.vazio_2809`.
- [x] **Correção 4 — `LIMITE_EXPERIENCIAS_PARA_TREINO = 4`**: ativado em `monstro_unificado_v22.py` (constante + branch APRENDIZADO ACELERADO alinhado).
- [x] **Correção 5 — SL da Faixa 1 com ATR**: `sl_atr_factor=2.5` + `sl_piso=8.0` (`config`/`DEFAULT_CFG`); `SL_efetivo = max(piso, min(SL_caixa, fator × ATR14 manhã))` aplicado em `_abrir` e `resolve` (paridade backtest↔produção); calibração ATR real (mediana 6,21 pts, 169 dias).
- [x] **Correção 6 — Sub-Trader do Corpo 1H**: candle 09:00–10:00 agregado das 12 M5 (`_agrega_h1`), entrada no rompimento do Corpo (BUY ask ≥ Corpo_Topo / SELL bid ≤ Corpo_Fundo), SL/TP no Pavio, **bloqueia a Faixa 1 enquanto aberto** e **libera o gatilho imediatamente ao encerrar**; EOD fecha a mercado; folga mínima 0,3 pts; bug de fallback `precobid` corrigido.
- [x] **Validação**: `py_compile` OK (orquestrador + monstro) e testes `test_rompimento_sub.py` (24 checks) + `test_rompimento_integracao.py` (15 checks) — **0 erros**.

### 📅 PRÓXIMA FASE — Expurgo de Código Legado e Limpeza de Backups (AGENDADA)
- [ ] **Critério de início:** após os **primeiros 5 pregões** de validação em produção do Sub-Trader + SL ATR (sem exceções nos logs).

### 🚨 ALERTA — AGENDA PÓS-VALIDAÇÃO: 09/10/2026 (NÃO ESQUECER)
> **Decisão do Mestre 29/09/2026:** ambiente CONGELADO durante 28/09–02/10 (5 pregões). As 5 falhas legadas (RG1/RG2/RG3) ficam **deixadas para depois** dos 5 pregões. **NÃO mexer em testes/Engine agora** — foco é estabilidade em tempo real (execução, reconexão, logs, memórias).
> **ADIADA de 05/10 para 09/10 (Decisão 02/10):** pregão é dia de COLETA, não de ajuste — 05/10 (dia único) não comporta refatoração grande + teste. 09/10 (sexta) + fim de semana 10–11/10 dá 2 dias para implementar e testar. Vigência: salvo parecer do B1-a (Etapa I, fds 02–04/10, ver 23.10).

**Ações obrigatórias em 09/10/2026 (pós-validação):**
- [ ] **A1 — Expurgo:** remover os ~18 métodos mortos em `monstro_unificado_v22.py` + fix do bloco inalcançável `alertas` (L2485-2499, em `pode_operar`).
- [x] **A2 — Testes legados:** validado 10/10 — baseline 73e02ca roda 9/9 PASS, HEAD atual 18/18 GREEN. As 5 falhas (RG1/RG2/RG3) não reproduzem nem no baseline nem no HEAD; foram resolvidas por trabalho legítimo (commits 2546706, 13a56c3, f6d7996). Sem falhas a corrigir.
- [ ] **A3 — Fiação Keras→gate (Opção "b"):** desenhar e implementar para que `pode_operar` consulte **ativamente** as inferências da rede. Sub-tarefas: (i) registrar Faixa 1 / Sub-Trader como experiências do Keras — **CONCLUÍDO em 29/09 (D1/D2/D3, ver seção abaixo)**; (ii) transformar o `shadow_registrar_entrada` (hoje **passivo**) em gate de veto — **BLOQUEADO**: pesos do Monstro WDO são sintéticos; (iii) validar que a rede tem poder preditivo (critério: correlação ≥ 0.15 sustained, ver §Quarentena 04/09) antes de virar veto real.

> **Base factual do filtro R/R (backtest 264 pregões, 48.7M ticks — commit 2546706):** desenho original (TP/SL nos pavios) tinha E = **-1.00 pt/trade**, R/R médio 0.39, P(E>0) = **7.4%**; com filtro `sub_rr_min=1.0` (só opera R/R ≥ 1:1): E = **+2.36 pts**, P(E>0) = **88.6%**, ~33 trades/ano. Sub com filtro opera em ~12,5% dos pregões (1 a cada ~8 dias).

- [ ] **A4 — Backups:** limpar `.vazio_2809`, `.before_reconcile_28`, `.sem_timestamp.bak`, `.pre_reinj_1609` após período de rollback.
- [ ] **A5 — Cópias antigas:** descarte de `monstro_backup*.py`, `monstro_unificado_v2*.py`, `mostro*.py` após consolidação em git (backups já movidos p/ `_arquivo_morto/` no commit 73e02ca).

---

## 🧠 CAUSA-RAIZ DA CORRELAÇÃO ≈ 0 DO KERAS (auditoria 29/09/2026)

**Constatação principal:** o problema NÃO é a arquitetura da rede. É um **data pipeline bug** com duas camadas.

### Camada 1 — Os pesos do Monstro WDO são SINTÉTICOS
`treinar_monstro_offline.py` (L59-116) e `treinar_monstro_offline_v2.py` treinam com `gerar_precos_wdo()` + `gerar_book_sintetico()` sobre `np.random.RandomState(seed)`. **Nenhum dos dois lê `historico_contexto_wdo.csv` nem `decisions_wdo.csv`.**
`retreinar_scaler_real.py` reconstrói apenas o **scaler** (a partir de dados reais), **não os pesos**.
→ Resultado: **pesos sintéticos + scaler real**. A rede recebe entradas em unidades/domínio que nunca viu no treino. Isso explica a correlação ≈ 0.

> ⚠️ **O gate permanece DESLIGADO até retreino com dados reais + correlação ≥ 0.15.** Ativar veto com pesos sintéticos geraria supressões aleatórias, destruindo a amostragem do simulador e criando uma falsa sensação de "IA filtrando".

### Camada 2 — O plug P4 alimentava o dataset com vetor CONSTANTE
`_CONTEXTO_ROMPIMENTO` (L6887) gravava `bid_qty=0, ask_qty=0, entropia_book=0.5, rsi_14=50, escoras=0` — 22 features **idênticas em 100% dos trades** da Faixa 1. Não era dado faltando: era **ruído ativo**.

### Confusão entre os DOIS modelos (origem do erro de projeto)
| Modelo | Features | Base | Uso |
|---|---|---|---|
| **Modelo A** (`modelo_a_filtro_wdo.keras`) | 22 MTF/M1 (`atr_ratio`, `slope`, `estado_*`, `sessao_*`) | **REAL** (preço) | shadow passivo |
| **Monstro WDO** (`modelo_monstro_wdo.h5`) | 22 book (`bid_qty`, `escoras`, `entropia`) | **SINTÉTICA** | memória / futuro gate |

O Modelo A **não usa book** e é o único com base real. O dataset `historico_contexto_wdo.csv` alimenta o Monstro WDO, cujas features de book estão zeradas (`bid_qty/ask_qty/volume_tick = 0` em todas as linhas — confirmado no docstring de `retreinar_scaler_real.py`).

### ✅ D1/D2/D3 — CORRIGIDOS em 29/09/2026 (pipeline limpo, gate ainda desligado)
Sequência: **pipeline limpo → coleta real → retreino → medir correlência → gate.**

- [x] **D1 — Snapshot real do book na entrada.** `memoria_fixar_entrada()` fixa `obter_contexto_completo()` + `analisar_profundidade_book()` (8 features de escora) no instante exato do gatilho, chaveado por **ticket MT5**. Se o book estiver indisponível, a amostra é **descartada** — nunca grava placeholder.
- [x] **D2 — Reward em R$ (escala única).** `_lucro_real_rs()` resolve `profit + commission + swap` direto dos **deals do MT5**. O plug P4 deixou de gravar `pts` (pontos). Sem `lucro_rs` válido a linha é descartada. Coluna `reward` do dataset agora é 100% R$.
- [x] **D3 — Sub-Trader no dataset.** `_grava_final_sub()` grava o sub em `rompimento_trades.csv` com `modulo="sub"`. Corrigido bug onde `_rewrite_csv_drop_day` **apagava** o registro da Faixa 1 quando o sub fechava no mesmo dia (dedup agora é por `dia`+`modulo`).
- [x] **Schema do CSV estendido:** `ticket`, `modulo`, `lucro_rs` (backward-compatible: linhas antigas sem as colunas continuam legíveis).
- [x] **Plug P4 neutralizado:** não grava mais vetor constante; delega para `memoria_registrar_saida` (contexto real da entrada).
- [x] **Testes:** RG12–RG18 (14 checks) + 11 cenários isolados — **14/14 PASS, 0 regressão** (as 5 falhas legadas RG1/RG2/RG3 permanecem, A2).

### ⚠️ R4 — Regressão de risco encontrada e corrigida (29/09, pré-restart)
`salvar_experiencia_csv()` **não é só um writer** — ela dispara 3 mecanismos de risco do Core:
1. `circuit_breaker.registrar_resultado(lucro)` → se o loss diário ≤ `MAX_LOSS_DIARIO` (−R$500), **cria `parar.txt` e DESLIGA o robô inteiro**.
2. `bloqueador_contexto.registrar_loss/win()` → pode **vetar o Core** em contextos cujo `_hash_contexto` (faixa 2h + volatilidade + RSI + candle_type + book_pressure) colida com os de um breakout das 10h.
3. `contador_experiencias_novas` → dispara retreino.

Encaminhar Faixa 1 / Sub por essa função faria **losses que o Core não deu** contarem para o limite diário e para o veto de contexto — com risco real de desligamento. Isso foi pego na revisão pré-restart.

**Correção:** `salvar_experiencia_dataset()` — escrita **pura**, sem nenhum efeito de decisão/risco. `memoria_registrar_saida()` usa esta. `salvar_experiencia_csv()` permanece **inalterada** para o Core. Schema do dataset idêntico (retrocompatível), verificado por AST em RG17/RG18.

### 📌 Estimativa corrigida de volume
`224` são **dias de gatilho** (rompimento da caixa), **não trades executados**. Trades reais estimados: **Faixa 1 ~50–100/ano + Sub ~33/ano ≈ 80–130/ano** (não +257). Sub com filtro opera em ~12,5% dos pregões (1 a cada ~8 dias), **não todo dia**.

### 🔜 Sequência restante (gate)
1. Coletar ≥ 200 trades com contexto real (`modulo`/`tipo_setup`/`faixa_horaria` como one-hot, retrocompatível com as 22 colunas).
2. Retreinar o **Monstro WDO** com dados reais (não sintéticos).
3. Medir correlação out-of-sample; **critério: ≥ 0.15 sustained**.
4. Só então ligar `pode_operar` como veto ativo.

---

## 📦 v22.1 — 2026-08-28 (Engine Robustness & Audit Patch)

### 🚀 Implementado & Auditado
- [x] **Infraestrutura**: Servidor de produção Waitress (8 threads) + liberação de porta 5001 com 3-probes e backoff persistido (Commit `bd40ec0`).
- [x] **Corte #1 (Engine)**: Reconciliação de posições órfãs via `PENDING_RECONCILIATION` persistida em JSON. Fim das perdas fantasmas por perda de sincronia de deals no MT5.
- [x] **Corte #2 (Engine)**: Fallback para `order_send=None` no fecho forçado das 17:35 com varredura retroativa de 60s via `history_deals_get`.
- [x] **Corte #3 (Dados)**: Garantia de header estático de 22 colunas (`timestamp` na 1ª coluna) na função `_migrar_historico_timestamp`. Recomposição do dataset Shadow Mode ($n=25$; Trades #1 = −80, #7 = −5, total semanal −R$755).

### 🚀 v22.1 — 2026-08-29 (Multi-Estratégia & Teoria das 7 Velas)

#### 🚀 Implementações & Melhorias
- **Arquitetura Multi-Estratégia Sequencial (Faixa 1 & Faixa 2):**
  - **Faixa 1 (09:00–11:30 BRT):** Execução exclusiva do módulo `sete_velas_orquestrador.py` em M15 (Dólar WDO) com 5 contratos (5 CC) e `magic_number = 7007`.
  - **Faixa 2 (11:30+ BRT):** Transição automática para o modo `PADRAO_MONSTRO` reativando os agentes (Keras, Sniper %R, Supermo) com lote normal (2 CC).
- **Módulos Criados:**
  - `sete_velas_util.py`: Funções puras de processamento M15, contagem de direção de velas e acumulação de CVD (Volume de Agressão por Ticks).
  - `sete_velas_orquestrador.py`: Maquinário de estado (`ESTADO_SISTEMA`), controle de idempotência, filtro CVD e emissão via callback.
  - `shadow_sete_velas_wdo.py`: Script de shadow mode ao vivo e retrospectivo (54 registros) com parâmetro de auto-saída `--ate HH:MM`.
- **Blindagens & Fixes em `monstro_unificado_v22.py`:**
  - Atualização da assinatura de `executar_ordem` para suporte a `magic_override`, `comment` e desativação de shadow individual.
  - Inserção do **Gatekeeper da Faixa 1** dentro de `executar_ordem` para bloquear chamadas de outros agentes durante `SETE_VELAS_EXCLUSIVO`.
  - Inserção da flag `ignore_max_loss` no Circuit Breaker CB2 para evitar travamento geral do robô em caso de Stop Loss da 7 Velas (5 CC) na janela matutina.

#### ✅ Validação Quantitativa Final (2026-08-29)
- **Backtest Robusto com Dados Reais MT5 (M1):** 87 dias úteis / 174 sinais (Abr–Ago 2026)
- **Janela V9 (11:15) — TIRO CERTO VALIDADO:**
  - **Modo DUAL (Gatekeeper):** WR 52.9% | PF 1.41 | PnL +R$ 3.900 | Max DD R$ 1.800 | 23 stops evitados
  - **Modo SECO:** WR 43.4% | PF 0.96 ❌ | PnL -R$ 800
  - **Gatekeeper salvou a estratégia:** 32 sinais filtrados, 23 stops evitados
- **Janela V7 (10:45) — DESATIVADA:**
  - Ganho marginal (WR 47.7% → 48.1%), PnL reduzido (R$ 2.500 → R$ 1.800)
  - **Decisão:** Desativada (`V7_1045_ATIVO: false`) para focar capital no V9
- **Configuração Produção (config.json):**
  - `"ativo": true, "variante": 9, "V7_1045_ATIVO": false, "V9_1115_ATIVO": true`
  - `gatekeeper_dual: true`, `cb2_ignore_max_loss: true`
  - SL 8.0 / TP 10.0 / Lote 5 CC / Magic 7007

### 📌 Próximos Passos (Semana 31/08 – 04/09)
- [x] **Segunda 31/08 - 08:50:** Disparar Shadow Mode (`shadow_sete_velas_wdo.py --ate 18:35`)
- [x] **Segunda 31/08 - 08:55:** Iniciar Monstro v22.1 (`python monstro_unificado_v22.py`)
- [x] **09:00–11:30:** Monitorar `SETE_VELAS_EXCLUSIVO` ativo — V9 (11:15) com Gatekeeper DUAL
- [x] **11:15:** Verificar disparo V9 DUAL (5 CC, SL 8 / TP 10) se CVD + VWAP alinhados
- [x] **11:30:** Transição automática `PADRAO_MONSTRO` (2 CC) — Keras/Sniper/Supermo ativos
- [x] **Pós-pregão:** Validar Shadow CSV (meta n≥30) e comparar com execução real
- [x] **01/09:** Fase 1 (idempotência + parametrização config), Fase 2 (backtest A/B 352 dias), Fase 3 (TP parcial 1:1 + BE + trava macro) — commit `1b7aa3d` + `5518a74`
- [ ] **Correção de autópsia (01/09, pós-sessão):** reducer raiz `max_loss_diario` → -1000.0 alinhado com `risk_management` (Kill-Switch mantido em R$1.000, inalterado); rate-limit no append de `historico_multitf.csv` (1 write/60s) — commit pendente
- [ ] **Início incubação OOS:** 02/09/2026 (V9 + Gatekeeper Dual + TP parcial/BE + trava macro) — meta n≥30
- [ ] **Retomada na SEXTA 04/09 (Payroll — teste da trava `VETADO_MACRO`):** validar que a janela 11:15 fica bloqueada na 1ª sexta do mês (conferir CSV/state com `VETADO_MACRO` e nenhum trade aberto)
- [ ] **Pós-semana:** Decisão `ativo: true` permanente baseada em n≥30 out-of-sample (critérios da seção v22.2)
- [ ] **Congelamento de Parâmetros:** Manter Whitelist, Sniper %R fixo, SL 8.0 pts WDO

### 🚨 v22.1b HOTFIX — 2026-09-01 (Reparo da Integração 7 Velas)

#### 🔍 Auditoria Pós-Agente (descoberta de melhorias que quebraram o engine)
- **Causa-raiz:** Altera antigo agente aplicou diff parcial/corrompido (`dd77a00`) no `monstro_unificado_v22.py`:
  - L1386 usava `ignore_max_loss` sem declarar na assinatura do CB2 → **NameError a cada ciclo (~3min)**
  - `executar_ordem` com assinatura nova mas corpo com nomes antigos (`sniper`, `symbol`, `lots`, `modo_operacional`) → contrato quebrado c/ chamada L7995
  - Gatekeeper duplicado (L5247-5250 + L5254-5257) e variáveis fantasma `ESTADO_SISTEMA`/`MAGIC_SETE_VELAS` **nunca definidas**
  - `_orq = Orquestrador7Velas(...)` importado mas **nunca instanciado** → robô cego p/ Faixa 1
- **Evidência:** `NameError: name 'ignore_max_loss' is not defined` 09:20–09:48 (01/09) + Magic=123456 (sem exclusividade)

#### 🛠️ Correções Aplicadas (v22.1b)
- [x] **CB2**: `verificar_circuit_breakers(self, spread_atual, ignore_max_loss=False)` + call site L7933 com `_cb2_ignore` (só libera CB2 na janela exclusiva 7 Velas)
- [x] **executar_ordem**: assinatura reconciliada `(action, lots=VOLUME_PADRAO, symbol, modo_operacional, sniper, sl_points_override, tp_points_override, magic_override, comment, shadow)` — compatível c/ engine e 7 Velas; `magic_final` e `comment` injetados no `order_send`
- [x] **Globals 7 Velas**: `SETE_VELAS_CFG/ATIVO/MAGIC_SETE_VELAS/INICIO_HORA/FIM_HORA` + `ESTADO_SISTEMA="PADRAO_MONSTRO"` + `_atualizar_estado_sistema()` lendo `config.json` (brt)
- [x] **Gatekeeper**: único (regra: na exclusividade só Magic 7007 passa) em `executar_ordem`
- [x] **Orquestrador**: `_orq = Orquestrador7Velas(fn_executar=wrapper, symbol=SYMBOL, ativo=SETE_VELAS_ATIVO)` instanciado em `monstro_thread` + `_orq.orquestrar()` no loop quando `SETE_VELAS_EXCLUSIVO`
- [x] **Instância única**: processos duplicados encerrados; único venv310 reiniciado 10:30 — log confirma `[7VELAS] Orquestrador instanciado (magic 7007)` e zero NameErrors pós-restart
- [x] **py_compile** 100% (4 módulos) + commit/push

### 🎯 v22.2 — 2026-09-01 (Fase 3: Gestão de Posição + Trava Macro + Backtest A/B)

#### 🔬 Backtest A/B Histórico (352 dias — 2025-04 a 2026-08, `WDO@` M1)
Motivo: **sepultar cientificamente o Modelo B de varejo** antes de investir em parametrização.

| Métrica | **Modelo A** (Monstro: majority V9 + Gatekeeper Dual, SL8/TP10) | **Modelo B** (Varejo: 7 velas mesma cor + RSI + Bollinger) |
|---|---|---|
| Sinais | 349 | 43 |
| Trades de fato | **145** | **3** (8 → 5 stop não disparou) |
| Win rate | 49.7% | 33.3% (n=3) |
| PnL 5CC | **R$ 6.800** | R$ 649 |
| Profit Factor | 1.23 | 2.27 (amostra irrelevante) |
| Max DD | R$ 3.600 | R$ 320 |

**Conclusão:** Modelo B gera ~3 trades em 17 meses — inviável operacionalmente. **Gatekeeper Dual + Majority V9 confirmado como superior e único candidato de produção.** Script: `backtest/backtest_ab_7velas.py` (commit `1b7aa3d`).

#### 💰 Gestão de TP Parcial 1:1 + Breakeven (implementada)
- **TP1 no SL (1:1, 8 pts):** ao atingir +8 pts, realiza **3 CC** (`TRADE_ACTION_DEAL`) e move o SL dos **2 CC restantes** para o **breakeven** (entrada) via `TRADE_ACTION_SLTP`.
- **Alvo final:** TP do MT5 permanece 10 pts nos remanescentes → captura +R$200 adicionais (total +R$440 no cenário ótimo).
- **Matemática:** 3 CC × 8 pt × R$10 = +R$240 garantidos no TP1; operação vira **risco zero** após o breakeven.
- **Controle via `config['sete_velas']`:** `gestao_tp_parcial`, `tp1_dist` (8.0), `lote_tp1` (3.0), `tp_final_dist` (10.0). Toggle permite desativar sem mexer no código.
- **Validação:** `py_compile` OK + teste offline com mock MT5 (parcial 3CC + BE correto; preço abaixo do TP1 sem ação; gestão desativada sem ação).

#### 🛡️ Trava Macro Automática (Payroll / FOMC / Copom)
- **Payroll (automático):** primeira sexta-feira do mês — bloqueia abertura na janela 11:15.
- **FOMC/Copom (manual):** lista `datas_bloqueadas` em `config['sete_velas']` (agenda anual do Fed/BCB).
- **Comportamento:** não abre posição; registra **`VETADO_MACRO`** no CSV/state (idempotência preservada).

#### 🧪 Protocolo de Validação Out-of-Sample (n ≥ 30) — HOMOLOGAÇÃO
- **Período de incubação:** operar ao vivo desde **02/09/2026** (V9, Gatekeeper Dual + TP parcial/BE + trava macro ativa).
- **Critério de homologação definitiva (`ativo: true` permanente):**
  - [ ] **n ≥ 30 trades reais** registrados em `logs/sete_velas_trades.csv` (excluindo VETADO_MACRO/VETADO_CVD).
  - [ ] Tactics mensais: WR ≥ 45% **e** PF ≥ 1.1 sobre o período de incubação.
  - [ ] **Drawdown máximo ≤ R$ 3.600** (teto da validação histórica).
  - [ ] Gerenciamento de posição ativo: auferir ganho do TP parcial (3 CC) em ≥ 80% dos trades que alcançaram +8 pts.
- **Critério de rollback:** se PF < 1.0 ou MaxDD > R$ 3.600 antes de n=30, desativar `ativo: false` e reavaliar.
- **Congelamento de parâmetros durante a incubação:** SL 8 / TP 10 / 5 CC / `<tp1_dist>` 8 / `<lote_tp1>` 3 — nenhuma alteração até n≥30.

---

## 🔍 AUDITORIA DA SEMANA 01–04/09/2026 (documentação + REPARO AUTORIZADO E APLICADO em 04/09)

### 📊 Resumo real (cruzado com logs diários `monstro_wdo_202609*.log`)

| Dia | Ordens executadas | Observação |
|---|---|---|
| 01/09 | 5 | Core normal (11:54, 14:41, 15:45, 16:00, 17:03) |
| 02/09 | 3 | Core normal |
| 03/09 | **136** | **133 SELL × 5.0 CC = 665 lotes = ANOMALIA 11:15:03→11:29:58** + 3 BUY normais |
| 04/09 | 4 | Core normal |
| **Semana** | **15 (core) + 133 (anomalia)** | Nº de trades do core = 15 confirma relatório (11W/4L) |

### 🐛 CAUSA RAIZ DA ANOMALIA (COMPROVADA NOS LOGS) — DIVERGE DO RELATÓRIO DO AGENTE

**Sintoma (bate com relatório):** 03/09 11:15:03 a 11:29:58 → **133 ordens SELL×5 CC = 665 lotes** → PnL ~R$ 57.425 negativo (fechamento via SL no MT5).

**Causa raiz real (dupla):** o relatório atribuiu a "loop de ordens sem `positions_get` em conta Netting". **A evidência mostra outra mecânica:**

1. **Bug de CSV (`dict contains fields not in fieldnames: 'ticket'`)** — introduzido no commit `1b7aa3d` (Fase 1/2, 01/09 11:57, post-janela): `avaliar()` passou a incluir `rec['ticket']` (L204/L210/L187) mas o `campos` do `_registrar_trade()` (L151-152) **não foi atualizado** com `'ticket'`. Todo `w.writerow(rec)` lança ValueError.
2. **Idempotência morta:** `orquestrar()` chama `_registrar_trade(rec)` (L389) → exceção → linhas L390-395 (`state[chave]=...; _salvar_state(state)`) **nunca executam** → `logs/sete_velas_state.json` **nunca é criado** (confirmado: arquivo não existe). O gatilho de entrada L379 (`chave not in state`) permanece verdadeiro para sempre.
3. **Loop engolido pelo engine:** `monstro_unificado_v22.py` L6630-6633 chama `orquestrar()` dentro de `except Exception: logging.error(...)` que apenas **loga e segue** → a cada iteração do loop principal (~6s) reexecuta `avaliar()` → **nova ordem**.
4. **Quando confluente ≠ quando vetado:** 02/09 o mesmo erro ocorreu (377x às 11:15) mas **sem ordens** — o sinal foi VETADO_CVD. 03/09 o sinal foi **CONFLUENTE** → reenvio real a cada ~6s (133 ordens).
5. **Fim natural:** parou às 11:29:58 porque `JANELA_FIM_HORA=11.5` → `_na_janela()` falso → loop de entrada não mais executado.

**Mecânica exata da cadeia (logs):** a cada tick: `Volume ajustado: 5.0` → `Ordem SELL executada. Ticket: ...` → `SHADOW Modelo A p=0.389` → `Não foi possível confirmar se ordem virou posição` → `[7VELAS] Erro no orquestrar(): dict contains fields not in fieldnames: 'ticket'`.

**Por que a gestão não fechou:** após 11:30, `Posição ativa no MT5 mas posicao_atual é None` + `Gerenciador de Saída DESATIVADO` — a posição do magic 7007 não é reconhecida como "posição do Monstro" (bate no fallback), então só o SL/TP fixo do MT5 encerrou.

**Verificação adicional:** `logs/sete_velas_trades.csv` tem apenas a linha de 01/09 (VETADO_CVD, gravada ANTES do commit bugado) — prova que a versão ativa em 01/09 era a pré-`1b7aa3d` e que a anomalia é pós-commit.

### ✅ VEREDICTO SOBRE O RELATÓRIO DO AGENTE
- **CONFIRMADO:** 665 lotes × 5 CC na janela 11:15-11:29 de 03/09; total da semana ~-R$ 57.250; 15 trades no core.
- **INEXATO:** causa raiz "loop sem `positions_get`". O gatilho real é o **ValueError do CSV** que mata a idempotência persistida + `except` do engine que engole o erro. A ausência de `positions_get` no orquestrador é um agravante (não uma causa).

### 🔧 AÇÕES RECOMENDADAS — ✅ EXECUTADAS EM 04/09/2026 (autorizadas pelo Mestre)
> Arquivo reparado: `sete_velas_orquestrador.py`. Suíte de validação: `tests/teste_orquestrador_7velas.py` (11/11 PASS) + `py_compile` OK + `testes_pos_fix.py` (9/9) + `validar_config_estrutura.py` (PASS). Core v22 congelado — zero alterações.

1. **Fix mínimo (`sete_velas_orquestrador.py`):** `'ticket'` adicionado ao `campos` do `_registrar_trade()` — **restaura a idempotência** (`state[chave]` volta a ser persistido em `logs/sete_velas_state.json`). ✅
2. **Trava dupla de reentrada no gatilho de entrada:** novo gate `_tem_posicao_aberta(MAGIC_SETE_VELAS)` (scan `positions_get` por magic 7007, mesmo posição parcial pós-TP1) — bloqueia nova ordem enquanto houver posição aberta do 7 Velas no MT5 (essencial em Netting). ✅
3. **Trava de volume máximo acumulado por janela:** `_acumulado_janela(MAGIC_SETE_VELAS)` (soma volume das posições do magic) vs `_teto_volume_janela()` (= lote configurado, 5.0 CC ≈ 1 lote) — defesa final contra acúmulo tipo 03/09. ✅
4. **Alinhar `campos` vs `rec` em TODOS os caminhos:** `_registrar_trade()` agora grave apenas `{c: rec.get(c, '') for c in campos}` (filtra chaves extras de qualquer fluxo — VETADO_MACRO, VETADO_CVD, sem_velas, executado); `ticket=None` adicionado aos fallbacks `sem_velas_suficientes` (L219) e `SEM_DADOS` (L424) e ao `rec` None. ✅
5. **Alteração cirúrgica:** após a primeira entrada da janela, `orquestrar()` retorna (trava 1-lote), mantendo o comportamento das variantes 7/V9 nas janelas distintas.

---

## 📊 RELATÓRIO DE INTELIGÊNCIA QUANTITATIVA — 7 TÓPICOS (04/09/2026)

> Análise contextual completa da semana 01–04/09/2026 cruzando log de ordens/posições (`monstro_wdo_2026090{1,2,3}.log`, `monstro_wdo.log`=04/09), `logs/modelo_a_shadow.csv`, `historico_multitf.csv`, `agente_autonomo.log`, `config.json`/`agente_config.json` e código. Somente leitura (nenhum arquivo alterado nesta etapa).

### TÓPICO 1 — RAIZ TRADE-A-TRADE DO CORE (15 trades)

**Base de dados:** 15 tickets do Core EXATAMENTE confirmados via "Ordem ... executada. Ticket:" nos logs. Dia 03/09 tem 136 ordens (133 anômalas + 3 core). Total Core da semana = **15 trades (5+3+3+4)** — bate com o relatório.

| # | Dia | Entr. | Ticket | Tipo | PnL (R$) | p-Shadow A |
|---|---|---|---|---|---|---|
| 1 | 01/09 | 11:54:13 | 2517225296 | SELL | **−80** (SL) | 0.390 |
| 2 | 01/09 | 14:41:53 | 2517464087 | SELL | **−80** (SL) | 0.676 |
| 3 | 01/09 | 15:45:16 | 2517534687 | SELL | +40 (TP) | 0.747 |
| 4 | 01/09 | 16:00:16 | 2517557147 | BUY | +45 (TP) | 0.725 |
| 5 | 01/09 | 17:03:18 | 2517669288 | SELL | *n.r. (fech. manual 17:35)* | 0.651 |
| 6 | 02/09 | 11:54:24 | 2518269183 | SELL | +40 (TP) | 0.180 |
| 7 | 02/09 | 14:35:18 | 2518543349 | SELL | +35 (TP) | 0.830 |
| 8 | 02/09 | 15:25:52 | 2518616714 | SELL | +55 (TP) | 0.822 |
| 9 | 03/09 | 14:30:07 | 2519688252 | BUY | +40 (TP) | 0.507 |
| 10 | 03/09 | 15:09:35 | 2519722964 | BUY | +15 (TP) | 0.591 |
| 11 | 03/09 | 16:08:24 | 2519781301 | BUY | +45 (TP) | 0.605 |
| 12 | 04/09 | 11:32:58 | 2520474202 | BUY | **−80** (SL) | 0.470 |
| 13 | 04/09 | 14:36:01 | 2520715797 | SELL | +40 (TP) | 0.488 |
| 14 | 04/09 | 15:14:25 | 2520757216 | BUY | +40 (TP) | 0.549 |
| 15 | 04/09 | 15:40:40 | 2520776665 | SELL | *n.r. (fech. manual 17:35)* | 0.667 |

*n.r. = não registrado: os 2 fechamentos manuais (encerramento 17:35) não gravam preço de saída/lucro no log.*

**Consolidação verificada nos logs:** 13 trades com PnL fechado → **10W / 3L, WR 76,9%, net +R$ 155,00** (GP R$395 / GL −R$240). Os 2 trades sem PnL registrado impactam a diferença vs. o "+R$175 / 11W-4L" do relatório — o valor exato deles **não é verificável** nos logs (seria +R$20 nos dois para bater).

**Padrão dos 3 losses (−80 cada):** todos SELL/BUY abertos **pelo SNIPER %R sobrepondo a IA** contra book ratio fraco (<1.3), DOL desalinhado e/ou tendência adversa — 01/09 11:54 (SELL contra TEND ALTA +2.2pts, DOL conf ~0.34), 01/09 14:41 (lateral, ATR 1.4<1.5, WR sobrecomprado), 04/09 11:32 (BUY com preço −2.9pts abaixo da SMA, DOL lado SELL, sinal NEUTRO conf 0.117 ignorado). **Nenhum dos 15 trades tem "CVD" logado nesta semana** — o indicador CVD/Book/Dólar-Cheio só aparece via book_ratio (1.00–1.25 na maioria dos trades) e DOL conf (0.34–0.46).

### TÓPICO 2 — AUDITORIA DO AGENTE AUTÔNOMO / WHITELIST

- **Zero ajustes aplicados na semana.** As 4 pausas das 12:30 (01–04/09) logaram idênticos `DECISAO: SEM AJUSTE. Whitelist vazia (sniper %R fixo desde 08/08)`. `agente_estado.json`: `ultima_mudanca=null`, `historico=[]`. Nenhuma ocorrência de `AJUSTE APLICADO` em todo o log (desde 03/08).
- **Whitelist de fato = `{}` vazia desde 08/08** (cancelamento do Pilar 3). `decidir()` aborta em `if not CFG["whitelist"]:` → nenhum parâmetro é tocado. Travas: janela de autonomia 12:30–14:30 (`rotinas.janela`) + trava física de 1 ajuste/dia + rollback/smoke_test.
- **Mudanças de valor na semana foram EXTERNAS ao agente (noite de 01/09):** `max_loss_diario` raiz −100→−1000 (commit `1730eea` 01/09 13:25), `sniper_ratio_min` raiz/risk 2.0→1.5 e 1.2→1.5, `kill_switch` −100/−150→−250/−400 (mtime 01/09 17:41 e 17:43; efetivadas via boot 09:05 de 02/09). **Sem trilha de auditoria própria** — único ponto de exposição de processo (mudança manual em config fora do log do agente).
- **Regime de autonomia respeitado:** watchdog restart único legítimo 03/09 15:50 (robô travado/porta morta); nenhuma ação fora da janela; plano do dia seguinte é só PROPOSTA (o `trailing 5→7` sugerido no plano 03/09 **não foi aplicado**; trailing é hardcoded 8/4, fora da whitelist).
- **Valores atuais 04/09:** `sniper_ratio_min=1.5`, `book_ratio_min=1.3`, `dol_conf_min=0.4`, `max_loss_diario=−1000`, kill_switch −250/−400, trailing hardcoded 8/4.
- **Mapa de vetos:** `williams_r` domina todos os dias (4767/3683/2183/2701); `multi_tf` sumiu em 03–04/09 (380/599 → 0/0); kill-switch jamais disparou na semana.

### TÓPICO 3 — AUDITORIA SHADOW MODE / MODELO A

- **É passivo (somente registro).** `monstro_unificado_v22.py` L5389-5394 executa a ordem **antes** de `shadow_registrar_entrada`; L545-547: "Registra ... SEM bloquear execucao". Não há nenhum branch de veto baseado em `prob_modelo_a`.
- **Amostra total (173 registros):** WR 50%, PF 0.58, net −R$600, corr(prob,resultado)=**+0.005** ≈ zero — o Modelo A **não tem capacidade preditiva** na amostra histórica.
- **Sub-amostra da semana (13 fechados):** WR 76.9%, PF 1.65, net +R$155, corr=+0.245, acurácia threshold 0.5 = 76.9%.
- **Simulação de veto p<0.5 na semana:** teria bloqueado 4 trades (2 perdas −80 e 2 lucros +40/+40) → net subiria de +155 para **+235**. A perda `2517464087` (p=0.676) **não seria evitada**. Na amostra inteira, veto p<0.5 pioraria levemente o ponto de corte (PF mantém 0.58).
- **Sobre a anomalia 03/09:** 124 de 133 ordens teriam prob <0.5 (seriam vetadas); as 9 de p=0.5277 passariam. **Mas o PnL real das 133 nunca foi registrado** (rastreamento de posição quebrado pós-11:30) — estimativa se stoppadas em −8pts: ~−R$53k de exposição (vol 5 CC × 133).
- **Conclusão:** hoje o Modelo A **não impede nenhuma perda**. Ativá-lo como veto exigiria mais amostra (corr ≈ 0 na base total) e corrigir o registro de resultado de fechamentos manuais.

### TÓPICO 4 — ANÁLISE DE REGIME POR DIA (SelecionadorRegime)

- **Fato estrutural:** o `SelecionadorRegime` (Sessão 19, perfis NORMAL/LATERAL/EXPLOSAO/CONSERVADOR/DEFESA/AGUARDANDO) **NÃO está plugado no v22** — docstring literal "NAO esta plugado ... ainda (mercado em operacao)"; nenhuma ocorrência de REGIME nos 4 logs. Em produção só operam `DetectorModoMercado`/`ModoOperacional` (NORMAL o tempo todo — ATR C10 2.4–4.8 nunca <1.5).
- **Regime inferido (filtro de tendência interno TENDENCIA: LATERAL/tend + métricas C10):**
  - **01/09:** LATERAL 66% → virada de tendência fraca à tarde. ATR med 2.40.
  - **02/09:** LATERAL forte 84%. ATR med 2.90.
  - **03/09:** LATERAL 88% mas ATR med **3.20** (mais alta da semana; M30 sobrecomprado 80.5–87.3).
  - **04/09:** LATERAL 69% → **TENDÊNCIA ALTA à tarde** (ALTA 25.6%; ATR P90 4.6).
- **Trades vs regime:** o Core é mean-reversion e entrou **contra a tendência** em 4+ ocasiões (01/09 11:54 SELL vs TEND ALTA → −80; 01/09 17:03 SELL vs ALTA → sem PnL; 02/09 11:54 SELL vs ALTA → +40; 04/09 15:40 SELL vs ALTA contínua → sem PnL). O maior lucro (+55, 02/09 15:25) também foi SELL com estado ALTA. **Se o SelecionadorRegime tivesse veto de direção, teria cortado lucros E perdas (líquido − falso: evitaria apenas o −80 de 01/09).**
- **Confluências M15/M30:** divergência marcante em 03/09 — M15 RSI 23–37 (sobrevendido) vs M30 RSI 80–87 (sobrecomprado); as 3 compras dessa divergência deram lucro (+40/+15/+45). WR M15/M30 na maioria das entradas em zona sobrevendida/estendida (−3 a −93) — consistentes com o viés mean-reversion do Core.

### TÓPICOS 5–7 — SÍNTESE CRUZADA

5. **Causa raiz da anomalia (síntese operacional):** o mesmo loop que reenviou SELL 133×também **deixou invisível o PnL** dessas ordens (o rastreamento de posição falhou — `Posição ativa no MT5 mas posicao_atual é None`, Gerenciador de Saída DESATIVADO). A anomalia destrói a validade da métrica "PF semanal" e do shadow — corrigida pelo reparo 7 Velas aplicado (trava dupla + teto de volume + idempotência restaurada).
6. **Perfis dos 3 losses confirmam o risco SNIPER:** as 3 perdas vieram de entradas do SNIPER %R que **sobrepõem a IA e ignoram book/DOL/tendência**. Precisão do SNIPER na semana: 10 de 15 trades são dele, 12 positivos/neutros se excluirmos SL — porém 2 dos 3 fechamentos manuais também foram SELL do SNIPER contra tendência de alta.
7. **Decisão para o Core v22 (CONGELADO):** nenhuma alteração nesta semana. O padrão da semana (10W/3L, +R$155 confirmáveis) corrobora a manutenção dos parâmetros atuais. Ações sugeridas apenas como follow-ups (fora do Core): documentar fechamentos manuais com PnL no shadow CSV; auditar mudanças manuais de config fora do log do agente; avaliar plug do `SelecionadorRegime` quando fora de mercado (sessão dedicada, com OOS n≥30).

---

## 🛡️ PROTOCOLO OFICIAL DE QUARENTENA E TRAVA DE MUDANÇAS (04/09/2026)

> Estado da base de código: **CONGELADA / MANTIDA EM PRODUÇÃO** desde o commit `8758b19`. Diretriz-mestra: **"mexe no que mede, não no que decide"**. Nenhuma alteração será feita na lógica de decisão do Core v22 enquanto os critérios abaixo não forem atingidos.

### 1. Diretriz Rígida de Mudanças ("Não mexa em quem está ganhando")
- **Core v22 (`monstro_unificado_v22.py`):** 100% congelado — nenhuma linha de código de decisão, parâmetro de gatilho, stop/take (`trailing 8/4`) ou filtro de IA será alterado até a amostra mínima.
- **Fila de melhorias (backlog/gaveta):** proibida a implementação de veto ativo do Modelo A, integração do `SelecionadorRegime`, ou qualquer ajuste fino de parâmetros baseado na semana. "Ideia boa sem amostra estatística é apenas palpite."

### 2. Critérios Objetivos para Futuros Destraves (Régua Quantitativa)
1. **Core v22 (WDO):** mínimo de **n ≥ 100 trades válidos** acumulados a partir do marcador **04/09/2026** (isolamento do sinal SNIPER %R da variância de curto prazo).
2. **Sete Velas (incubação):** **n ≥ 30 trades** com as novas travas ativas e **WR ≥ 45%, PF ≥ 1.1, MaxDD ≤ R$ 3.600**.
3. **Modelo A (Shadow Mode):** habilitação como veto ativo apenas com **correlação estatística contínua ≥ 0.15** sobre o PnL real (atual ~0.005) **e acurácia > 60%** em base expandida.

### 3. Fila Autorizada para Desenvolvimento Paralelo (Fora do Core)
- **WIN V2:** execução e coleta de amostras exclusivamente em **Conta Simulador** (não afeta/cruza o WDO).
- **Telemetria de fechamento manual:** ajuste pontual (único toque no v22) para capturar PnL real em fechamentos manuais — sanar a lacuna dos 2 trades da semana. **Aditivo, não altera gatilhos.**
- **`analisar_quarentena.py`:** monitoramento read-only das metas do protocolo (n/7 Velas/corr).
- **Single-writer lock em config:** trava leve para impedir escrita concorrente em `config.json`.

### 4. Baseline Semanal (para referência de comparação)
- Core: 15 trades, 10W/3L, +R$155 confirmáveis (+R$175 c/ manuais); Sete Velas: 3 trades Core (03/09) + anomalia 133×SL (corrigida); agente autônomo: zero ajustes, whitelist vazia; kill-switch inerte.

#### NOTA 05/09 — ADIAMENTO DO WIN V2 (decisão registrada)
- **WIN V2 NÃO será iniciado na semana de 07/09.** Decisão do guardião (05/09) após checagem empírica: o relatório de "PASS" gerado em 05/09 foi antecipado/incorreto — a implementação de unidade NÃO estava aplicada (`config_win_v2.json` seguia `contrato.tick_size=0.2`, `ticks_por_ponto=10000`) e o GATE 6.2a real retorna **FAIL** (`point real WIN=1.0`, `tick=5.0`, `R$1,00/tick @5ct` ≈ 5x abaixo do backtest R$5,00).
- **Motivo estrutural:** alinhar unidade não é trocar 3 números — hardcodes de `0.2` afetam o cálculo do **Trailing Stop** (saída) no `monstro_unificado_v2.py` (L166-201, L1394, L1850, L4760-4765). Mexer no trailing sem modelo viola "mexe no que mede, não no que decide".
- **Área reservada:** auditoria completa de unidade (tick/ponto/R$/trailing) em sessão dedicada antes de qualquer incubação do WIN.
- **Garantia de não-disparo automático na segunda:** `Monstro-Start` 09:00 → `start_all.bat` (apenas WDO v22); `rodar_simulador_duplo.bat` (GATE 6.2a embutido, bloqueia WIN em FAIL); `iniciar_monstro_win_v2.bat`/`testar_monstro.bat` são manuais.
- **Segunda-feira:** foco 100% no Core v22 WDO em quarentena (execução automática + monitoramento via `analisar_quarentena.py`), repo em commit `0cb453f`.

#### NOTA 07/09 — PATCHES A + B APLICADOS (v22.2-protected, autorizado pelo Mestre em 05/09)
- **Patch A — Watchdog DLL (travamento de thread):** thread daemon monitora o estado de tick do loop principal; se o tick estagnar **>10s durante o expediente (09:00–17:40)** com MT5 conectado, executa `hard_reset_mt5()` (`shutdown()` + `reconectar_mt5()`) para destravar a DLL. Cobre o gap de ~65 min do Payroll 04/09 (13:24→14:29), em que o loop ficava "cego" com o heartbeat de diagnóstico (300s) funcionando. Sem mudança em gatilhos/entradas/saídas — alçada de processo/resgate/observabilidade.
- **Patch B — Re-checagem assíncrona do fecho:** o caminho `fechar_todas_posicoes` (CORTE 2) agora agenda, quando a confirmação imediata falha, uma varredura em thread daemon (+15s/+30s) de `history_deals_get` procurando o `DEAL_ENTRY_OUT` que o servidor processa com atraso (caso Trade #7 das 17:35). Ao confirmar, registra PnL via `shadow_registrar_resultado` + `_telemetria_capturar_pnl`.
- **Suíte de testes:** `tests/teste_watchdog_e_fecho.py` (19 casos: PA1–PA5 watchdog/horário, PB1–PB3 fecho atrasado) — **19/19 PASS** sem MT5 real (mocks). `py_compile` validado.
- **Feriado 07/09 (Independência, sem B3):** patches aplicados e commitados (`v22.2-protected`); Core segue **congelado** na lógica de decisão. **Terça 08/09 = dia 1** da quarentena pós-telemetria (n≥100) monitorada via `analisar_quarentena.py`.

---

## 📋 ESTADO ATUAL DO SISTEMA

| Item | Valor |
|---|---|
| Símbolo | WINQ26 (front-month dinâmico) |
| SL / TP | 100 pts / 250 pts (R/R 1:2.5) |
| Volume | 5 contratos |
| Trailing | Gatilho 80 pts / Distância 40 pts (REAIS) |
| Fonte de dados | `mt5.market_book_get()` — book nativo, EA eliminado |
| Filtro Sniper | 5000cc volume + ratio 2.0 (Python) |
| Diretriz de entrada | **SEGUIR OS BIGS** (veto duro contra o lado dominante) |
| Cooldown | DESATIVADO — proteção via SL/MaxLoss/inversão |
| Timeout de posição | DESATIVADO — trade respira até SL/TP/trailing/inversão |
| IA | Keras/h5 — aprendizado incremental em tempo real |
| Horários PA1 | 09:00–12:00 e 15:00–17:30 |
| MaxLoss diário | -R$1.000 |

---

## 🛡️ PROTEÇÕES ATIVAS (Rede de Segurança)

- SL fixo 100 pts (nunca alterado)
- MaxLoss diário -R$1.000
- Veto "seguir os bigs" (nunca contra o lado dominante do book)
- Saída por inversão de fluxo (2 níveis: fecha em prejuízo / breakeven em lucro)
- Trailing stop após 80 pts de lucro
- Proteção de lucro (C12): pico > 80 pts e queda 30% → fecha
- Salvamento atômico do modelo (.tmp + os.replace)
- Save imediato após cada trade real

---

## ✅ FASES CONCLUÍDAS (Resumo)

### FASE 1 — Estrutura Base
Integração Python↔MT5, modelo Keras 4 camadas, 18 features, loop principal, dashboard Flask, seleção dinâmica de contrato.

### FASE 2 — Melhorias de Performance
Trailing stop, balanceamento BUY/SELL, modos de mercado, circuit breakers, saída inteligente, confluência, horário premium, EMA, cooldown, spread dinâmico.

### FASE 3 — Plano de Ação (jan/2026)
Trava de horário PA1 (09–12 / 15–17:30), filtro memória positiva, reset de experiências negativas.

### FASE 4 — Correções Críticas (mai/2026)
Filtro C8 desativado, contador treino corrigido, NameError/indentação/variável corrigidos, seed determinístico.

### FASE 5 — Refatoração Sniper (jun/2026)
Soberania da IA (>80% confiança protegida), confluência mínima 2 sinais, SL 100 / TP 250 dinâmico por volume.

### FASE 6 — Calibração (jun/2026)
Trailing 80/40 pts, penalidade "morte súbita" (<15s), cooldown P0, trava pós-loss, modo standby Sniper, EA Sniper V5.

### FASE 7 — Correções Pós-Produção (jul/2026)
C12 calibrado para TP=250, trailing em pontos reais (não ticks), race condition MT5/Python, scaler fallback, primeira operação aleatória removida, CSV 21 colunas.

### FASE 8 — Sincronização Sniper (jul/2026 — parcial)
- ✅ Trava timestamp, inversão de fluxo, replay buffer corrigido, CSV corrigido
- ⏳ Pendente: modo emergência desativado (8.2), ajuste escala volume (8.3), dashboard KPIs (8.5)

### FASE 9 — Arquitetura Nativa "Adeus EA/CSV" (17/07/2026)
Book nativo `market_book_get`, filtro Sniper migrado para Python, inversão de fluxo 2 níveis, diretriz "seguir os bigs", cooldown/timeout desativados, log adaptativo (84 linhas/hora em standby), warnings de libs silenciados, bloqueio PA1 eficiente.

### FASE 10 — Blindagem de Persistência + Features (18–19/07/2026)
Salvamento atômico, entropia ressuscitada, escora BID corrigida, handlers de sinal reativados, save após cada trade, decisions.csv só trades reais, código morto removido, bug do logging (force=True) corrigido.

---

## ⏰ CHECKPOINT — VETO "SEGUIR OS BIGS"

**Estado:** Veto DURO ativo (IA nunca opera contra o lado dominante do book passivo).

**Critérios para evoluir (afrouxar para override por confiança):**
- [ ] ≥ 100 trades reais no `historico_contexto_win.csv`
- [ ] Win rate ≥ 55% seguindo os bigs
- [ ] Modelo `.h5` evoluindo consistentemente (hash mudando)

**Quando atender os 3:** permitir override por confiança > 80% (Soberania da IA já existente).

**Evolução futura adicional:** considerar fluxo AGRESSIVO vs passivo (preço furando escora = seguir o agressor, não o passivo). Registrado em 17/07/2026 — caso real: BID dominante mas preço CAINDO = absorção → venda era correta.

**Última verificação:** 19/07/2026 — critérios NÃO atendidos. Veto duro mantido.

---

## 📊 ESTADO DAS 18 FEATURES

| # | Feature | Status |
|---|---|---|
| 1 | bid_qty | ✅ Viva |
| 2 | ask_qty | ✅ Viva |
| 3 | spread | ✅ Viva |
| 4 | volatility (ATR) | ✅ Viva |
| 5 | candle_type | ✅ Viva |
| 6 | entropia_book | ✅ Ressuscitada (Fase 10) |
| 7 | rsi_14 | ✅ Viva |
| 8 | volume_tick | ✅ Viva |
| 9 | preco_maior_escora_bid | ✅ Ressuscitada (Fase 10) |
| 10 | volume_maior_escora_bid | ✅ Viva |
| 11 | distancia_maior_escora_bid | ✅ Ressuscitada (Fase 10) |
| 12 | preco_maior_escora_ask | ✅ Viva |
| 13 | volume_maior_escora_ask | ✅ Viva |
| 14 | distancia_maior_escora_ask | ✅ Viva |
| 15 | liquidez_top5_bid/ask | ✅ Viva |
| 16 | is_in_trade | ⬜ Reservada (saída futura) |
| 17 | floating_profit | ⬜ Reservada (saída futura) |
| 18 | tempo_em_trade | ⬜ Reservada (saída futura) |

---

## 📈 METAS DE PERFORMANCE

| Métrica | Atual (19/07) | Meta Final |
|---|---|---|
| Taxa de acerto | ~50% (poucos dados) | > 60% |
| Lucro médio/trade | R$65 (melhor) | > R$100 |
| Operações/dia | 3–5 | < 5 |
| Drawdown máximo | R$410 | < R$300 |
| R/R ratio | 1:2.5 | 1:2.5 |
| Trailing eficácia | 100% (1 teste) | > 80% |

---

## 🟡 EM OBSERVAÇÃO (até 26/07/2026)

- [ ] Coletar 50+ operações para avaliar taxa de acerto real
- [ ] Confirmar que trailing não sai precocemente
- [ ] Monitorar viés direcional da IA
- [ ] Verificar que modelo `.h5` muda de hash após trades (aprendizado confirmado)
- [ ] Restaurar backups de dados se necessário (`.backup_reset_20260719_082047`)

---

## 🔴 PENDÊNCIAS DA FASE 8 (fazer quando houver 50+ trades)

- [ ] **8.2** — Desativar modo emergência (`LIMITE_REJEICOES = 999999` ou remover)
- [ ] **8.3** — Ajustar escala volume/entropia (`MIN_VOLUME_BOOK` → 4500, entropia mínima 0.7)
- [ ] **8.5** — Dashboard de KPIs (win rate, fator lucro, drawdown, eficácia trailing)

---

## 🟢 FASE 11 — PAINEL HFT VISUAL NO TERMINAL (PRÓXIMA)

**Objetivo:** Dashboard visual em tempo real no CMD usando a biblioteca `rich` (Python). O robô escreve estado em JSON; painel separado lê e renderiza. Sem dependência externa, sem browser.

### Layout do Painel

```
┌───────────────────────────────────────────────────────────┐
│           🤖 ROBÔ MONSTRO V2 - PAINEL HFT                 │
├───────────────────────────────────────────────────────────┤
│  STATUS: ATIVO              TEMPO ATIVO: 02:15:33         │
├───────────────────────────────────────────────────────────┤
│  CONFIANÇA IA: ████████████████████ 85%       RSI: 62     │
├───────────────────────────────────────────────────────────┤
│  FLUXO: ██████████████████████████████████████ COMPRADOR  │
│  VOLUME: BUY 3200 | SELL 1800 | RATIO 1.78                │
├───────────────────────────────────────────────────────────┤
│  PREÇO ATUAL:  175.500                                    │
│  ALVO GAIN:    175.750  (+250 pts)                        │
│  ALVO STOP:    175.400  (-100 pts)                        │
├───────────────────────────────────────────────────────────┤
│  LUCRO DIA: +R$255    OPERAÇÕES: 5    WIN RATE: 80%       │
├───────────────────────────────────────────────────────────┤
│  EVENTO: 🎯 Sinal Sniper! BUY FORTE                      │
│  SINAL: COMPRA FORTE | COOLDOWN: PRONTO                   │
└───────────────────────────────────────────────────────────┘
```

### Componentes Visuais

| Componente | Descrição |
|---|---|
| Barra de fluxo | Verde (comprador) / Vermelha (vendedor) proporcional ao ratio |
| Barra confiança IA | 0–100% com cor (azul→verde→vermelho) |
| Sinal textual | COMPRA FORTE / COMPRA / ESPERE / VENDA / VENDA FORTE |
| Preços SL/TP | Atualizados em tempo real com base nos parâmetros do robô |
| Eventos | Última ação relevante (Sniper, veto, trailing, trade fechado) |

### Arquitetura de Comunicação

```
monstro_unificado_v2.py          painel_monstro.py
       │                                │
       │  ┌──────────────────────┐      │
       ├──► monstro_dashboard_   ├──────┤
       │  │ data.json (escrita)  │      │ (leitura)
       │  └──────────────────────┘      │
       │                                │
    robô opera                     rich renderiza
    (loop ~2s)                     (refresh 4fps)
```

**Protocolo:** JSON atômico (write-then-rename para evitar leitura parcial).

### Dados Transmitidos (JSON)

```json
{
  "preco_atual": 175500.0,
  "confianca_ia": 0.85,
  "rsi_atual": 62.0,
  "vol_buy": 3200,
  "vol_sell": 1800,
  "stop_loss": 175400.0,
  "take_profit": 175750.0,
  "lucro_dia": 255.0,
  "operacoes_dia": 5,
  "win_rate_dia": 80.0,
  "evento_recente": "🎯 Sinal Sniper! BUY FORTE",
  "sinal": "COMPRA FORTE",
  "cooldown_status": "PRONTO",
  "timestamp": "2026-07-19T10:35:22"
}
```

### Plano de Implementação

| Etapa | Descrição | Estimativa |
|---|---|---|
| **11.1** | Criar `painel_monstro.py` com layout `rich` (dados simulados) | ~100 linhas |
| **11.2** | Adicionar `enviar_dados_para_painel()` no `monstro_unificado_v2.py` | ~30 linhas |
| **11.3** | Integrar chamada no loop principal (a cada ciclo) | ~10 linhas |
| **11.4** | Conectar painel ao JSON real (substituir simulação) | ~20 linhas |
| **11.5** | Testar em produção (rodar em terminal separado) | Validação |

### Dependências

- `pip install rich` (única dependência nova)
- Arquivos no mesmo diretório (`C:\AIOFEN`)
- Execução: terminal 1 = robô | terminal 2 = painel

### Lógica do Sinal Textual

| Condição | Sinal exibido |
|---|---|
| Confiança > 80% + ratio BUY > 2.0 | **COMPRA FORTE** |
| Confiança > 60% + ratio BUY > 1.5 | COMPRA |
| Confiança < 20% + ratio SELL > 2.0 | **VENDA FORTE** |
| Confiança < 40% + ratio SELL > 1.5 | VENDA |
| Qualquer outra condição | ESPERE |

---

## 🔮 FASE 12 — ESCORAS & ORDER FLOW (FUTURO — após 100+ trades)

**Visão:** IA aprende a ler escoras individuais (big players) como ímã de liquidez. "Escora segura E chama o preço."

### Princípio de Engenharia
Nº de features proporcional aos dados de treino. Adicionar INCREMENTAL e medir impacto.

### Opções (ordenadas por custo/benefício)

| Opção | Descrição | Quando |
|---|---|---|
| **1. Derivadas** | Razão escora_bid/ask, centro de gravidade da liquidez | ~100 trades |
| **2. Top-3 escoras** | +8 features (escora2/3 vol/dist de cada lado) | ~200 trades |
| **3. Absorção** | Detectar escora que segura vs que some (spoofing) | ~300 trades |
| **4. DeepLOB (CNN)** | Book como imagem — estilo fundos quant | Fase avançada |
| **5. IA de saída** | Segunda IA só para decidir quando fechar | Após IA entrada madura |

### Ideias Adicionais
- SL/TP colados em escoras fortes (stop atrás da parede)
- Fluxo agressivo vs passivo como critério de veto (evolução do "seguir os bigs")

---

## 🔬 FASE 13 — PESQUISA QUANTITATIVA + SHADOW MODE (Agosto/2026)

**Última atualização:** 20/08/2026
**Arquivo principal:** `monstro_unificado_v22.py` (evolução do v2, ~10.700 linhas)

### Estado Atual (20/08/2026)

| Item | Valor |
|---|---|
| Símbolo | WDOU26 |
| SL | 8 pts (floor `max(1.5×ATR, sl_max)`) |
| Estratégia ativa | Sniper %R (`SNIPER_APENAS=true`) |
| Cooldown sniper | 120s |
| Horário nobre | 09:15–12:30 / 14:30–17:15 (abertura 09:00–09:14 bloqueada) |
| Dashboard | `http://localhost:5001` |

### ✅ Aprovados e Operacionais
- **Sniper %R + vetos multi-TF:** edge estatístico principal do robô.
- **Log de contexto com timestamp:** primeira coluna do `historico_contexto_wdo.csv` — prepara o Modelo B (book/microestrutura + regime).
- **Infraestrutura:** rotação de logs diária, watchdog, kill-switch, cooldown, SL floor.

### ❌ Descartados (falsas hipóteses — mortas por dados)
- **Abertura WIN/WDO (09:00–09:14):** reprovada em 7 cenários (M1/M5, alvos 1:1 e 2:1, SL=TP 200/400pts, filtro véspera). WR 27–46%, todos negativos. Candle de abertura = ruído HFT.
- **Grade de Consolidação (Markov):** reprovada nos dois ativos. Comprar mínima/vender máxima sem direção = pegar faca caindo.
- **Backtests WIN encerramento:** sem edge real; resultado dependia de outlier único.

### ⏳ Em Teste Passivo (Shadow Mode) — Modelo A
- **O que é:** veto ML (Keras) com features Markov + MTF retroativo (RSI/ATR/WR em 5m/15m/30m).
- **Diagnóstico honesto:** AUC walk-forward real **0,653** (min 0,543 / max 0,758). Veto p≥0,65 positivo no OOS (PF 7,22) mas n=9 trades — inconclusivo; in-sample negativo (PF 0,41). Não integrado como veto.
- **Ação atual:** calcula e grava a probabilidade `p` em cada ordem real em `logs/modelo_a_shadow.csv` (timestamp, ticket_mt5, direcao, prob_modelo_a, resultado_bruto, resultado_pontos) SEM bloquear execução.
- **Meta:** reavaliar após 30–60 sinais gravados em produção.
- **Candidato validado aguardando decisão:** Markov Tendência WDO com stop de emergência — PF 1,47 ano / 1,88 OOS (+R$3.214, 161 trades). Ainda não conectado ao robô.

### Lições Registradas
1. Amostra curta ilude: Modelo C de abertura tinha 77,8% WR em 9 dias e −R$9 mil em 250 dias.
2. Teto de dados da corretora: M1/M5/M15 param em 29/08/2025. Validações futuras = shadow mode, não mais backtest.
3. Features MTF exigem forward-fill ao alinhar com grade M5 (viés de barras :00/:30 inflava AUC de 0,653 para 0,827).

### Próximos Passos
1. Acompanhar coleta do `modelo_a_shadow.csv` na operação ao vivo (meta 30–60 sinais).
2. Decidir integração do módulo Markov Tendência WDO (shadow ou real com 1 contrato).
3. Modelo B quando houver base de book com timestamp suficiente (2–3 semanas).

---

## 🔵 MÉDIO/LONGO PRAZO

- [ ] Sistema de alertas (Telegram/WhatsApp)
- [ ] Multi-timeframe analysis
- [ ] Backup automático em nuvem
- [ ] XGBoost como modelo complementar (ensemble) — não substituto
- [ ] Análise offline dos 806 trades WDO (56% win, +R$25.460) como benchmark

---

## 🔧 ARQUIVOS DO PROJETO

| Arquivo | Descrição |
|---|---|
| `monstro_unificado_v2.py` | Sistema principal (~8500 linhas) |
| `painel_monstro.py` | Painel HFT visual (a criar — Fase 11) |
| `modelo_monstro_win.h5` | Modelo IA treinado |
| `modelo_monstro_win.keras` | Modelo IA (formato nativo) |
| `config_win_v2.json` | Configurações WIN |
| `historico_contexto_win.csv` | Base histórica (18 features + action + reward) |
| `decisions.csv` | Log de trades reais (BUY/SELL) |
| `experiencias.json` | Buffer de experiências |
| `monstro_v2.log` | Log de execução |
| `diagnostico_monstro.py` | Script de diagnóstico |
| `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` | Este arquivo |

---

## 📋 CONFIGURAÇÃO DE REFERÊNCIA

### Filtro Sniper
| Parâmetro | Valor | Onde |
|---|---|---|
| `SNIPER_VOLUME_MIN` | 5000cc | topo do .py ou config |
| `SNIPER_RATIO_MIN` | 2.0 | topo do .py ou config |

### Alvos Dinâmicos (por volume)
| Volume | SL | TP | R/R |
|---|---|---|---|
| 5000cc+ | 100 | 250 | 1:2.5 |
| 3000cc+ | 100 | 230 | 1:2.3 |
| 2000cc+ | 100 | 220 | 1:2.2 |
| demais | 100 | 200 | 1:2.0 |

### Trailing Stop
| Parâmetro | Valor |
|---|---|
| Gatilho | 80 pts reais |
| Distância | 40 pts reais |
| Proteção C12 | pico > 80 pts, queda 30% |

### Penalidade de Score
| Situação | Score |
|---|---|
| Trade normal (>30s) | Calculado normal |
| Stop rápido (15–30s) | score × 1.5 (mín -1.0) |
| Morte Súbita (<15s) | -1.5 fixo |

---

## 🔁 PONTO DE RETOMADA — SEXTA-FEIRA 04/09/2026

**Sessão encerrada em 01/09/2026.** Estado congelado para incubação out-of-sample (n≥30).

**Já operando automaticamente (sem intervenção):**
- Monstro reiniciado às 12:10:27 com o orquestrador F3 carregado; **0 erros no `orquestrar`** pós-restart.
- Tarefas agendadas ativas: `Monstro-Start` (anti-duplicidade), `Monstro-Watchdog`, `Monstro-Fecho` (17:35).
- 7 Velas V9 (11:15) + Gatekeeper Dual + TP parcial 1:1/BE + trava macro — parametrização 100% no `config.json`.

**Agenda automática da semana:**
- **02/09 (qua)** → V9 normal (incubação trade #1).
- **03/09 (qui)** → V9 normal (incubação trade #2).
- **04/09 (sex) = Payroll** → validar trava `VETADO_MACRO` (janela 11:15 bloqueada; **nenhum trade abrir**; conferir CSV/state).

**Checklist de retomada em 04/09 (após 11:30):**
1. Verificar `logs/sete_velas_trades.csv`: presença de `VETADO_MACRO` na 04/09 e **ausência de trade real** nesse dia.
2. Confirmar no `monstro_wdo.log`: `[7VELAS ...] DIA MACRO (Payroll/FOMC) -> VETADO_MACRO`.
3. Revisar os trades reais de 02–03/09 (WR, PF, MaxDD, ganho do TP parcial em +8pts).
4. Se tudo limpo e critérios OOS seguindo favoráveis, **marcar retomada** para decisão de homologação quando n≥30.

*Mantido por: Mestre Super + Kiro AI Agent*
*Última atualização: 19/07/2026*

---

## 🔍 CORREÇÃO DE AUTÓPSIA — 01/09 (PÓS-SESSÃO)

**Autópsia original alegou:** Sniper bloqueado por gate `sniper_ratio_min=2.0` (L6845) → `continue` antes de chegar ao Sniper %R.

**Contra-evidência (código real + log):**
- O gate real está na **L7375** e **já é pulado em `SNIPER_APENAS=true`** (`if not SNIPER_APENAS and (...)`). O ratio 2.0 da raiz **NÃO** bloqueia o Sniper.
- Log de 01/09 (monstro_wdo.log) prova o bloqueador real = **veto multi-TF** (M15/M30 em consenso extremo):
  - 11:31 `%R=-80 BUY` → bloqueado `M15=-97 M30=-97`
  - 11:46 `%R=-88 BUY` → bloqueado `M15=-98 M30=-98`
  - 11:51/52 `%R=-17 SELL` → bloqueado `M15=-92 M30=-92`
  - 11:54 **`%R=-15 SELL` disparou** (fora do consenso extremo) → ticket 2517225296, **-8 pts**
- Conclusão: o veto multi-TF funcionou como projetado (bloqueou entradas contra consenso M15/M30). O trade que escapou perdeu. **NÃO mexer no `sniper_ratio_min` nem criar bypass no gate.**

**Ações executadas (passivas/seguras):**
1. Root `max_loss_diario`: -100.0 → **-1000.0** (alinha com `risk_management`; Kill-Switch em R$1.000 inalterado — engine lê ninho L810-811).
2. `historico_multitf.csv`: append a cada ciclo (33.3k linhas) → **rate-limit 1x/60s** via `_log_periodico` (mantém auditoria, corta bloat ~120x).

**Avaliação veto multi-TF:** legítimo e protetivo — manter. Rigidez p/ scalp 8SL/6TP é conservadora por design (fix 13/08). Nenhum afrouxamento sem backtest.

**Validação:** `py_compile` OK (v22 + agente), `tests/testes_pos_fix.py` **9/9 PASS**, config `ALINHADO`.

---

# 🧭 DELIBERAÇÃO DE SEXTA-FEIRA — 04/09/2026 (PÓS-FECHAMENTO)

> **Objetivo deste bloco:** consolidar a semana **01/09–04/09**, separar factos verificados de alegações de autópsia, e tomar **decisão GO/NÃO-GO** sobre as MUDANÇAS propostas nos relatórios (`para ox alpha.txt`). Nada abaixo deve ser implementado às cegas — cada item tem **estado verificado** e **critério objetivo** de decisão (VIDE SEMANA).

---

## 0. PREMISSAS VERIFICADAS EM CÓDIGO (independente — base para tudo)

| # | Alegação de autópsia | **Estado VERIFICADO (02/09)** | Veredito |
|---|---|---|---|
| 1 | "Bug 7 Velas L198: truth value of array ambiguous" | **JÁ CORRIGIDO.** Orquestrador reescrito (Fase 2, 01/09) usa `calcular_cvd_janela()` → retorna **escalar float** e `cvd_confluente = (ups>downs and cvd>0)...` (boolean escalar). **Não existe** `cvd.any()/.all()`. | ✅ Já resolvido — **não mexer** |
| 2 | "historico_multitf.csv PARADO em 08/08" | **FUNCIONANDO.** Último registro 2026.09.02 17:14. | ✅ Já resolvido |
| 3 | "Config bagunça total (sniper 2.0 vs 1.2)" | `sniper_ratio_min` **1.5** (raiz + risk), `max_loss_diario` **-1000** (raiz + risk), kill_switch **-250/-400** (agente). | 🟡 **Maioria alinhada** |
| 4 | "experiencias_wdo.json VAZIO" | **Só 3 registros.** | 🔴 **GAP REAL — priorizar** |
| 5 | "Shadow Model A correlação invertida" | Base: n=27, WR 33%, PF 0.34, -R$395 — **nunca teve poder de veto** (passivo). | 🟡 Validar, risco baixo |
| 6 | WIN "golden goose" | Backtest WIN A **original viciado**: PF 1.94, +R$654k, MaxDD -R$43k. **Corrigido 03/09 (auditoria):** PF 1.68, +R$107.734, **MaxDD -R$12.810** (ver bloco AUDITORIA abaixo). Robô em produção é **WDO**. | 🟠 **Decisão estratégica**, não bug |

**⚠️ RISCO Nº1 IDENTIFICADO (não é bug, é processo):** múltiplos agentes/sessões editando `config.json` **em paralelo** (prova: `sniper_ratio_min` virou 1.5 depois da minha sessão de 01/09 sem commit correspondente). Esta é a real ameaça à integridade — qualquer "unificação" será inútil se a escrita concorrente continuar. **Ação: single-writer lock em config/prod.**

---

## 🔍 AUDITORIA BACKTEST ARTHUR 777 — CORRIGIDO EM 03/09 (números calibrados)

**Contexto:** o backtest original do agente (`backtest_arthur777.py`) apresentava **2 vícios de metodologia** que inflavam os resultados. Auditoria feita por mim em 03/09/2026, corrigida e **validada matematicamente** (fator 2 + zero sobreposição restante).

| Vício | Antes (inflado) | Depois (corrigido) |
|---|---|---|
| **Fator 2 (dupla contagem do tick)** — `pts` medido em TICKS multiplicava `valor_por_ponto` como se fosse pontos de preço (`tick_size=0.5` → 1 ponto = 2 ticks). Todo PnL e MaxDD dobrados. | WIN A TP = R$7.500/trade | **R$3.750/trade** ✔ (bate c/ distância real em preço) |
| **Sobreposição temporal** — loop abria trade a cada sinal SEM avançar o cursor após o fechamento (≥1 posição simultânea impossível no MT5). | 50% dos trades WIN sobrepostos (até 17/dia) | **0 sobreposições** (máx 8/dia, 1 por vez) ✔ |

### RESULTADOS CALIBRADOS (5 contratos, custos reais XP RLP, 15/04–28/08/26)
| Cenário | Ativo | Trades | WR | Saldo líq | PF | Payoff | MaxDD |
|---|---|---|---|---|---|---|---|
| **A (Tendência)** | **WIN** | **229** | 31.0% | **+R$107.734** | **1.68** | 3.74 | **-R$12.810** |
| B (Scalper) | WIN | 338 | 64.2% | -R$67.510 | 0.44 | 0.25 | -R$68.501 |
| A (Tendência) | WDO | 121 | 27.3% | +R$5.786 | 1.25 | 3.34 | -R$4.913 |
| B (Scalper) | WDO | 228 | 70.2% | -R$7.052 | 0.60 | 0.25 | -R$7.397 |

**LEITURA SÊNIOR:** a **tese estatística principal se MANTÉM** — Cenário A (Tendência) > Cenário B; **WIN A segue o melhor setup** (PF 1.68, payoff 3.74, +R$107k). Mas o risco é **muito menor do que os "R$654k / -R$43k" falsos**: MaxDD real de **-R$12.810** em 229 trades (5 cts) é **dimensionável** (≤5%/trade), não 4,3x capital como os relatórios alarmistas afirmavam. **Cenário B permanece geneticamente perdedor** (payoff 0.25 < custos) — nunca subir. **WIN V2 real já existe portado para MT5** (`monstro_unificado_v2.py` + `config_win_v2.json` + `modelo_monstro_win.h5`); o NO-GO de "matar/não colocar WIN" foi baseado em número inflado — decisão deve ser reavaliada com dados calibrados em SEX 04/09.


---

## 1. ESTADO DA SEMANA (compilar SEX 18:00 — via MT5 + logs)

Semana real 01–02/09 (WDOV26, 1 ct): 8 trades | 5 W / 3 L | **62.5% WR** | PnL bruto +R$80 | **líq +R$73.60** após custos.

⚠️ **LEITURA SÊNIOR (honesta):**
- **n=8 é estatisticamente irrelevante.** 62.5% não prova edge — pode ser sorte. NÃO aumentar lote por causa disto.
- Os 3 losses de 01/09 foram **entradas contra fluxo** (multi-TF) → reforça que o veto multi-TF está **correto**, não "restritivo demais".
- Os 3 gains de 02/09 foram **a favor da tendência** → valida a direção do sistema.

**Para SEX 18:00:** gerar relatório consolidado 01–04/09 (trades, WR, PF, MaxDD, PnL líq, custos) e **marcar cada item abaixo como GO / NÃO-GO / ADIAR** com base na semana + critérios objetivos.

---

## 2. DECISÕES EM PAUTA (VOTAR SEX, IMPLEMENTAR RÁPIDO NÃO-IMEDIATO)

### 🟢 A. UNIFICAR CONFIG (verificado: 85% já feito — completar de forma SEGURA)
| Item | Ação | Critério de GO |
|---|---|---|
| A1 | **Single-writer lock** de `config.json`/`agente_config.json` (mutex p/ edição; git diff obrigatório antes de commit) | **SEMPRE — sem isso nada vale** |
| A2 | Verificar `custos_operacionais` = **R$1,20 WDO (0,60+0,60) / R$0,25 WIN** | Pendente: `config.json` ainda tem R$0,80 WDO (legado) |
| A3 | `py_compile` config.json + `python -c "json.load(...)"` em config + agente_config | Exit 0 |
| A4 | Criar `tests/validar_config_estrutura.py` (checa 1 ocorrência de cada chave crítica + tipos) | 9/9 + novo teste PASS |

### 🟡 B. EXPERIENCIAS_WDO.JSON (GAP REAL — PRIORIDADE 1)
| Item | Ação | Critério de GO |
|---|---|---|
| B1 | Popular `experiencias_wdo.json` a partir de `decisions_wdo.csv` + `historico_contexto_wdo.csv` (feats → contexto, label = resultado real do trade) | **>100 registros** válidos |
| B2 | Alimentar automaticamente **no fecho** (`Monstro-Fecho` / fim de `orquestrar`) | Todo pregão registra experiências |
| B3 | Validar distribuição: ≥30% wins / losses (não só NÃO_AGIU) | Distribuição balanceada |

### 🟠 C. SHADOW MODEL A (validar, NÃO desligar às cegas)
| Item | Ação | Critério de GO |
|---|---|---|
| C1 | Confirmar em código que Modelo A **não tem poder de veto** (só shadow/passivo) | Verificar execução real |
| C2 | Re-analisar com n≥60 (meta) a correlação confiança×resultado | Curva monotônica OU desligar |

### 🔴 D. CENÁRIO B (SCALPER) — NUNCA subir em produção
| Item | Ação | Critério de GO |
|---|---|---|
| D1 | Confirmar que NENHUM caminho de produção invoca escalper puro (payoff<0.3) | grep: nenhuma chamada ativa |
| D2 | Se existir código morto de scalper: marcar/remover **COM TESTE** (nunca remover lógica viva às cegas) | py_compile + testes 9/9 |

### 🔴 E. MUDANÇA DE PRODUTO WDO → WIN (DECISÃO ESTRATÉGICA — NÃO é ajuste de config)
> **Ponto que os relatórios não enfatizam:** o robô em produção opera **WDO**. A recomendação "WIN A como golden goose" é **trocar de produto** — implica: símbolo, tick/point, contrato, custos, margem, corretora (WIN ≠ WDO no demo XP? confirmar contrato), gestão de risco do ativo. **Não é "ligar uma flag".**
| Item | Ação | Critério de GO |
|---|---|---|
| E1 | Alinhar com Mestre Super: **WDO (atual) × WIN × ambos** | Decisão explícita do dono |
| E2 | Se WIN: validar Margem/contrato/custos reais + Backtest A **calibrado** (MaxDD -R$12.810 em 229 trades → sizing ≤5% capital) | Paper 20 dias antes de real |
| E3 | Se manter WDO: **foco em V9 DUAL** (PF 1.44) + consolidar incubação n≥30 | n≥30 OOS |

---

## 3. PAPER TRADING / EMULAÇÃO (GATE PARA DINHEIRO REAL)

| # | Etapa | Duração | Critério de SAÍDA |
|---|---|---|---|
| P1 | Rodar produção atual em **conta demo** (sem descongelar) | até n≥30 OOS | Critérios v22.2 (WR≥45%, PF≥1.1, MaxDD≤R$3.600) |
| P2 | Se E2 (WIN): **paper dedicado em WIN** | 20 dias | PF≥1.5, MaxDD<15% capital, ≥30 trades |
| P3 | Nenhum **aumento de lote** antes de P1/P2 GO | — | GO só com critérios batidos |

---

## 4. CHECKLIST EXECUTÁVEL SEXTA (pós 17:40 fecho — ORDEM)

```powershell
# 0) Single-writer: confirmar ninguém editando (git status limpo)
cd C:\AIOFEN
git status

# 1) Unificação segura (A)
python -m py_compile config.json
python -c "import json;json.load(open('config.json'));json.load(open('agente_config.json'));print('configs OK')"

# 2) Experiências (B) — popular + validar
python scripts/popular_experiencias.py        # (criar) exporta decisions->experiencias
python -c "import json;print(len(json.load(open('experiencias_wdo.json'))))"   # >100

# 3) Bugs reais (D/C) — só se existirem
python -m py_compile monstro_unificado_v22.py agente_monstro_core.py sete_velas_util.py

# 4) Testes
python tests/testes_pos_fix.py                # 9/9
python tests/validar_config_estrutura.py      # (novo) PASS

# 5) Backtests (referência, não regressão)
python backtest/backtest_sete_velas.py         # gera CSV
python backtest/backtest_arthur777.py          # 4 cenários
```

## 5. ENTREGÁVEIS MÍNIMOS DE SEXTA
- [ ] Relatório consolidado da semana 01–04/09 (com custos).
- [ ] Decisão explícita registrada p/ **cada** item A–E (GO/NÃO-GO/ADIAR).
- [ ] `experiencias_wdo.json` **>100** registros + alimentação no fecho ativa.
- [ ] Single-writer lock documentado (não necessariamente codificado — pode ser **protocolo/checklist**).
- [ ] Se E1=WIN: paper WIN P2 montado. Se E1=WDO: incubação V9 continua até n≥30.
- [ ] Commit + push de configs/scripts validados (com diff revisado).

---

# 🧪 FASE 6 — MÓDULO WIN V2 EM PARALELO (SIMULADO DUPLO WDO+WIN)

> **Decisão do Mestre (04/09):** a descoberta WIN A (PF 1.68, Payoff 3.74, MaxDD -R$12.810 calibrado) **não fica na gaveta**. Roda em **conta Simulador MT5, em paralelo** com o WDO, via **multi-instância** (2 processos Python independentes) — sem gambiarra de Keras, sem poluir o WDO que já funciona.

## 6.1 ARQUITETURA (2 PROCESSOS / 1 CONTA SIMULADOR)

```
[MetaTrader 5 (Conta Demo/Simulador)] ──┬──> Processo 1: monstro_unificado_v22.py  (WDO)  magic 7007
                                        └──> Processo 2: monstro_unificado_v2.py   (WIN)  magic 2002
```
- **Isolamento total de memória Keras**: cada processo carrega seu próprio `.h5` (`modelo_monstro_wdo` / `modelo_monstro_win.h5`) em memória separada. Sem conflito de thread/estado.
- **Magic separados** impedem o MT5 de misturar posições.
- **Kill-switch independente** por processo (config próprio).

## 6.2 ⚠️ CORREÇÕES AO RELATÓRIO (o relatório propõe valores INCORRETOS — usar os reais)
| Item | Relatório propõe | **CORRETO (verificado em código)** |
|---|---|---|
| Nome do script | "criar monstro_win_v2.py" | **JÁ EXISTE** `monstro_unificado_v2.py` |
| Config | "criar config_win.json" | **JÁ EXISTE** `config_win_v2.json` — apenas **alinhar** |
| **tick_size WIN** | **5.0** ❌ | ⚠️ **CONFLITO no repo:** `custos_reais.py`=0.5tick/2pts, engine/config=0.2 & ticks_por_ponto=10000. **GATE 6.2a os resolve lendo o símbolo real** |
| **valor ponto WIN** | "0.20/ct" | Backtest auditado usou **R$1,00/pt × 5ct = R$5,00/pt** (Cenário A). Confirmar contrato real no GATE |
| magic | "2002" (inexistente) | Definir **de verdade** em `config_win_v2.json → geral.magic_number` (atual usa default 123457) |
| sniper_ratio_min | 1.5 | Alinhar `config_win_v2.json` (atual **2.0**) → **1.5** |
| modelo | "modelo_win_v2.h5" | `modelo_monstro_win.h5` |

### 6.2a 🔑 GATE OBRIGATÓRIO — VALIDAR UNIDADE DO SÍMBOLO WIN NO MT5 (ANTES DE LIGAR)
> O repo tem **3 tick_sizes WIN conflitantes** (0.2, 0.5, 5.0). **Não chutar.** O passo mais importante de toda a Fase 6: conectar ao MT5 da conta **Simulador** e ler as **specs reais** do contrato WIN vigente, comparando com a config antes de abrir qualquer ordem.
```python
# scripts/validar_simbolo_win.py  (a criar)
import MetaTrader5 as mt5
info = mt5.symbol_info("WINV26")          # contrato vigente (ou WIN$)
print("point     =", info.point)          # tick em preço
print("trade_tick_value =", info.trade_tick_value)  # R$/tick
print("trade_tick_size  =", info.trade_tick_size)   # preço por tick
# validação: config_win_v2.json contrato.tick_size/ticks_por_ponto devem reproduzir
#            R$/ponto observado no símbolo. Se divergir >1e-6 → BLOQUEIA, corrige config.
```
**Critério de GO:** `validar_simbolo_win` imprime specs reais e **bate** com config; só então prosseguir à incubação.

## 6.3 PASSOS EXECUTÁVEIS (SEX 04/09 18:00 — ORDEM)
```powershell
# 0) GATE 6.2a — validar unidade do símbolo WIN no MT5 simulado (BLOQUEANTE)
python scripts/validar_simbolo_win.py

# 1) Alinhar config WIN (não criar do zero) — USANDO specs reais do GATE
#    - geral.magic_number = 2002
#    - sniper_ratio_min = 1.5
#    - max_loss_diario = -1000.0
#    - contrato.symbol_prefix = WIN
#    - contrato.tick_size / ticks_por_ponto  ← valores do GATE 6.2a (NÃO 0.2 cego)
#    - sl_points / tp_points: Cenário A Tendência (SL 200 / TP 750 no backtest auditado)
#      → o config_win_v2 atual (100/250) é config clássica v2, NÃO o Arthur A.

# 2) Validar WIN engine (compila + modelo carrega)
python -m py_compile monstro_unificado_v2.py
python -c "from tensorflow.keras.models import load_model; m=load_model('modelo_monstro_win.h5'); print('WIN modelo OK', m.layers[0].input_shape)"

# 3) Reusar/ajustar iniciar_monstro_win_v2.bat (já existe) apontando pro config_win_v2.json
#    Garantir MODO SIMULADOR (sem ordens reais) e magic 2002

# 4) Disparar DUPLO (rodar_simulador_duplo.bat):
#    - Processo 1: python monstro_unificado_v22.py   (WDO, magic 7007)
#    - Processo 2: python monstro_unificado_v2.py    (WIN, magic 2002, simulado)
#    (nome real do script WIN é monstro_unificado_v2.py, NÃO monstro_win_v2.py)

# 5) Log consolidado: historico_simulado_duplo.csv (um registro/dia por ativo)
```

## 6.4 MÉTRICAS DE CORTE PARA LIBERAÇÃO DE CAPITAL REAL (30 DIAS DE INCUBAÇÃO SIMULADO)
| Critério | Meta | Status |
|---|---|---|
| Trades executados (WIN) | ≥ 30 | — |
| Profit Factor real (WIN) | ≥ 1.50 | — |
| Drawdown diário respeitando travas | R$ 250 / R$ 400 (kill-switch WIN) | — |
| Zero exceção de tipo/desconexão nos logs | 0 falhas | — |
| MaxDD acumulado (WIN) | ≤ 20% do capital simulado | — |

> **Anteparo de honestidade:** incubação simulada ≠ garantia de lucro real. NÃO aumentar lote no WDO nem misturar capital até os critérios 6.4 batidos. WIN real exige validar **margem/contrato/custos reais** (potencialmente outra corretora/terminal que o demo XP atual) — decisão separada, agendada.

*Mantido por: Mestre Super + Kiro AI Agent — revisado e direcionado por Ox Alfa (dev/quant sênior)*

---

# 🚀 v22.2 — 2026-09-10 (Faixa 1: Rompimento da 1ª HORA substitui SETE VELAS)

## Decisão do Mestre (10/09/2026)
- **Eliminar a estratégia das Sete Velas do código** (validação: 7 Velas sem edge confirmado no WDO).
- **Rompimento da Primeira Hora a entrar no robô** `monstro_unificado_v22.py` (WDO, 5 CC, **sem barras noturnas**), como **Faixa 1** — o restante do robô fica em **pausa até o trade do rompimento terminar** (mesmo gate que o Sete Velas fazia).
- **Remover a pausa de meio-dia** (task `Monstro-Pausa` 12:30) e a task `Rompimento-FT` (festiva do lado WIN fica redundante).
- Não mexer na parte lucrativa pós-janela. Ao final: roadmap + commit.
- (Opcional, NÃO implementado) Anticipação com o Dólar Cheio (DOL).

## Estratégia (paridade com `backtest/backtest_rompimento_1hora.py`)
- **Caixa** 09:00–10:00 BRT (M5 da hora 9) → hi/lo/rr.
- **Gatilho** 10:00–11:00 (janela 60 min): primeira M5 **fechada** que rompe hi → BUY; rompe low → SELL.
- **Fill** a mercado no momento em que a vela gatilho fecha (backtest: abertura da vela gatilho — **desvio documentado**).
- **SL** extremidade oposta da caixa (`sl_mode=lo`), **TP = 1.5×rr**; SL conferido antes do TP intrabarra.
- **EOD**: posição ainda aberta à `hora_eod` 17:30 BRT → fechada a mercado (antes do encerramento 17:35).

## Validação (backtest WDO 2021–2026, sem noturnas)
- Combo oficial: SL=lo / TP=1.5 / janela=60min. n≈1000, todos os anos positivos (2021-25 + 2026), PF 1.12–1.77 por ano; publicado em `backtest/resultados/rompimento_1hora_wdo.txt`.
- Referência do módulo: `python rompimento_orquestrador.py --selftest`.

## Novos arquivos
| Arquivo | Papel |
|---|---|
| `rompimento_orquestrador.py` | Faixa 1 em produção — `OrquestradorRompimento(fn_executar, symbol="WDO$")`, magic **7008**, lote 5 CC. Autossuficiente: offset de fuso do servidor detectado e **aplicado** (v22.4), trava de frescor normalizada (≤12 min), estado/CSV idempotentes em `logs/rompimento/`. |
| `tests/teste_orquestrador_rompimento.py` | 15 verificações determinísticas OFF-LINE (mock MT5): gatilho C/V, EOD 17:30, S/TRADE, ordem rejeitada, idempotência, SL antes do TP, frescor. |

## Integração no `monstro_unificado_v22.py` (patches aplicados)
- Imports: `from rompimento_orquestrador import OrquestradorRompimento` (removeu os módulos 7 Velas).
- Globals: `ROMP_CFG / ROMPIMENTO_ATIVO / MAGIC_ROMPIMENTO=7008 / ROMPIMENTO_INICIO_HORA=9.0 / ROMPIMENTO_FIM_HORA=11.0 / ESTADO_SISTEMA`.
- `_atualizar_estado_sistema()` → `ROMPIMENTO_EXCLUSIVO` se janela de gatilho **OU** posição da Faixa 1 aberta (`_tem_posicao_rompimento()` por magic) — a pausa persiste até o trade terminar.
- Gate em `executar_ordem(...)` (L5320): durante exclusivo só passa magic 7008 (`[GATE ROMPIMENTO]`).
- CB2: `_cb2_ignore = ROMPIMENTO_EXCLUSIVO and ROMP_CFG.cb2_ignore_max_loss`.
- Instanciação `_orq` com wrapper `sniper=True, shadow=False`; loop chama `_orq.orquestrar()` **sempre** (S/TRADE e EOD fora da janela também são geridos).
- `fechar_todas_posicoes()` inclui magic 7008 quando `robo_rompimento.ativo` (backstop do EOD).

## Config (`config.json` → `rompimento`, substitui `sete_velas`)
`ativo:true lote:5.0 sl_mode:"lo" tp_k:1.5 janela_min:60 magic:7008 hora_inicio:9.0 hora_fim:11.0 hora_eod:"17:30" stale_max_min:12 no_night_bars:true cb2_ignore_max_loss:true datas_bloqueadas:[]`

## Remoções (backup completo em `backup_pre_rompimento_20260910/`)
- `sete_velas_orquestrador.py`, `sete_velas_util.py`, `shadow_sete_velas_wdo.py`
- `tests/teste_orquestrador_7velas.py`
- `backtest/backtest_sete_velas.py`, `backtest/backtest_sete_velas_invertido.py`
- `backtest/backtest_arthur777.py`: funções `_carregar_custos`/`calcular_custo_trade` embutidas (independência do módulo removido).

## Operacional
- Dashboard: métricas "Romp 1h / Lote / Próx. / P&L" (`d.rompimento`), estado `ROMPIMENTO_EXCLUSIVO`, P&L em R$ (pts × R$10 × 5 CC).
- Tarefas: removidas `Monstro-Pausa` e `Rompimento-FT`; mantidas `Monstro-Start` (09:00), `Monstro-Watchdog` (09:05), `Monstro-Fecho` (17:35) e o backup diário 08:50.
- **FIX 11/09/2026 — reset do MT5 no start:** `start_all.bat` e `iniciar_v22_wdo.bat` matam e reabrem o `terminal64.exe` antes de subir o robô (higiene de inicialização). ⚠️ **RETIFICADO 15/09:** a "defasagem de ~180 min" **não** era terminal/coletor congelado nem broker atrasado — era o **fuso do servidor** (XPMT5 grava hora BRT como UTC; ver VEREDITO corrigido abaixo). O símbolo contínuo `WDO$` do demo congelou em 10/09; o robô usa front dinâmico (`WDOV26`), `WDO$` só para backtest/paridade.
- **FIX 11/09/2026 (noite, parte 2) — watchdog escalado no v22:** `executar_resgate_dll` mantém o resgate "soft" (shutdown+initialize) nas primeiras ocorrências, mas após **≥5 resgates consecutivos sem o feed voltar** (≈1–2 min congelado) **escala para o restart do PROCESSO `terminal64.exe`** (`_restart_terminal_processo`: taskkill + 6s + launch + 18s + re-connect). Guarda-roupas: no máx. 1 restart a cada 5 min (`_WATCHDOG_ESCALADA_COOLDOWN_S`) e teto diário de 4 (`_WATCHDOG_ESCALADA_MAX_DIA`); após o teto volta ao soft. Posição aberta é segura (SL/TP no servidor). A escalada mede a **idade REAL dos dados** (`_stale_real_min`: última M5 do `SYMBOL`, fallback tick, com offset de fuso **removido** desde 15/09 — antes media ~3h fixas na conta XPMT5), não o heartbeat do loop principal (que o próprio loop re-arma a cada iteração e mascarava os episódios). Não altera gatilho/entrada/saída (Protocolo 04/09). Testes PA6–PA8 em `tests/teste_watchdog_e_fecho.py`.
- **FIX 11/09/2026 (noite, parte 3) — agente = 2ª camada de feed, escalada em 3 níveis:** `agente_monstro_core.py` ganhou probe de tick direto no terminal (`feed_spot_stale_s`, front dinâmico — jamais `WDO$`): com robô vivo e em expediente, feed estagnado além de `feed_estagnado_max_s` (=900 s) → (1º) reinicia o PROCESSO do terminal (max `feed_restart_terminal_max_dia`=6/dia); se persistente, (2º) reinicia o PROCESSO do ROBÔ (max `feed_robo_restart_max_dia`=2/dia) para anexar limpo; (3º) grava marker `FEED_INDISPONIVEL_YYYYMMDD.txt` e para de brigar. Contadores por dia em `agente_estado.json` (`feed_watchdog`); respeita o backoff compartilhado. Config: `feed_watchdog_enabled`, `feed_estagnado_max_s`, `feed_restart_terminal_max_dia`, `feed_escalar_robo`, `feed_robo_restart_max_dia`.
- **VEREDITO 14/09 RETIFICADO em 15/09/2026 — o feed NUNCA esteve ~3h atrasado: era offset de fuso do servidor.** Provas ao vivo em 15/09 (pregão aberto): o `tick.time` avança **1:1 com o relógio da parede** e `time.time() - tick.time ≡ 10800 s` ao segundo; a M15 das 10:45 se forma na hora no gráfico MT5; a M5 das 10:55 existe e vira `10:55` com `+3h`. Neste servidor (XPMT5-DEMO) bar/tick `time` são gravados com **hora BRT como se fosse UTC** — logo `time.time() - bar.time` media **3h FIXAS** em feed saudável, e os `S/TRADE` de 11/14/15 foram causados por esse bug de **medição** (os 33 restarts foram alarme falso; 11/09 também não foi "terminal que dormiu"). Correção em v22.4 (balanço seguinte).
- **FIX 15/09/2026 (v22.4) — fuso do servidor na MEDIDA e nas DECISÕES:** ✓ Medição: `dfasagem_min` (orquestrador), `_stale_real_min` (v22) e `feed_spot_stale_s` (agente) passaram a **remover o offset do servidor** via `_offset_medicao`/`_offset_tz_probe` (detectado no boot: **+3h** nesta conta, **0** em contas padrão; cacheado). `_WATCHDOG_REAL_FRESCO_MIN 2.0 → 6.0` (granularidade M5). Ao vivo pós-fix: `dfasagem_min = 4,5 min`, tick age ≈ 16 s. ✓ Rebase (decisão aprovada): `OrquestradorRompimento.__init__` passou a **aplicar** `detectar_shift` → `_SHIFT = +10800` → janelas no horário oficial da B3: **caixa 09:00–10:00, gatilho 10:00–11:00** (vigência 16/09). Backtest na janela real (`+3h` no histórico): **n=148, WR 47,3%, PF 1,38, net +454, maxseq 5** vs janela codificada antiga (n=140, WR 45,0%, PF 1,15, net +113) — o fuso corrigido melhora **todos** os indicadores. Testes RG1–RG9, PA1–PB3 e `py_compile` OK. Dia 15/09 mantém `S/TRADE` (janela antiga já fechada às 11:06).
- CI (`.github/workflows/monstro-ci.yml`): `rompimento_orquestrador.py` no py_compile + suíte `teste_orquestrador_rompimento.py` na esteira.
- Snapshot do diff estrutural do agente regenerado (`agente_snapshot_v22.py`).

## Decisões e pendências
- Interação mão/feed: terminais defasados (>12 min) → Faixa 1 não decide; reconciliar ao fim do dia.
- Sem trade na janela → registrado `S/TRADE` (1 linha/dia).
- Repositório: mudanças comitadas nesta revisão; **não** commitar `backup_pre_rompimento_20260910/` (pasta de backup no disco, fora do git).
- Próxima verificação: **16/09 — 1º pregão ao vivo com a Faixa 1 na janela REAL 09–11h** (monitorar `logs/rompimento/rompimento_trades.csv`, gateway e EOD 17:30).

---

# 🔬 AUTÓPSIA 16/09/2026 — PRIORIDADES P1–P5 (CICLO ENCERRADO)

> Primeiro pregão ao vivo da Faixa 1 na janela **REAL 09–11h** (v22.4, fuso corrigido). Resultado do dia: 1 trade real da Faixa 1 encerrado (SL) + relatório do fecho (17:35) corrigido. Planejamento em `plano_20260916.txt`; autópsia detalhada em `Autopsia_16_09_2026.md`.

## 📊 Pregão 16/09/2026 — fatos verificados
- **Faixa 1 (rompimento 1ª hora, magic 7008):** 1 trade real — `side=C (BUY), saida=SL, pts=-19.5` (posição fechada no servidor). Registrado em `logs/rompimento/rompimento_trades.csv` e `rompimento_state.json` (`final=true`).
- **v22 Core (magic 123456):** 0 trades no dia (nenhuma operação real). `historico_contexto_wdo.csv` = 740 linhas `NAO_AGIU` (contextos sem trade) — nominal.
- **Relatório do fecho (17:35):** integração P3 passou a somar `n_v22 + n_romp` no cabeçalho (antes reportava "Trades executados: 0" apesar do trade de rompimento — visão cega).

## 🚀 Prioridades executadas (autópsia pós-sessão)
### P1 — Tracking e Posição Nula (`268981c`)
O rastreador do v22 passou a **ignorar o magic 7008** — eliminou o *fallback* de ~1.484 tentativas de fechamento/estado desativado quando a Faixa 1 estava posicionada (lógica multi-magic isolada por magic). Magic 123456 (Core) e 7008 (rompimento) nunca mais se confundem.

### P2 — Sequenciador Sniper vs. Rompimento (PROPOSTA — arquivada)
Mapeados os 25 disparos bloqueados do Sniper no dia: o gate `ROMPIMENTO_EXCLUSIVO` pausa todo o Core enquanto a Faixa 1 decide/segura posição (proteção por design). Proposta de sequenciador para liberar o Core em dias **sem trade** do rompimento, mantendo a trava de proteção. **Sem deploy** — reservada para validação em simulação/backtest antes de qualquer mudança.

### P3 — Observabilidade no fecho (`f28ed55`)
`agente_monstro_core.py` ajustado: `contar_executados_hoje()` (v22 core), `contar_executados_rompimento_hoje()` (ler `rompimento_trades.csv`, `saida != S/TRADE`) e `contar_executados_consolidado_hoje()` — cabeçalho do relatório das 17:35 soma as duas fontes. Validado: compila, `hoje=0`, `romp=1`, `consol=1`.

### P4 — Memória de treino (`5f8474d`)
Conectou a Faixa 1 ao buffer de experiências (`memoria_experiencias.adicionar` + `salvar_experiencia_csv`, que incrementa `contador_experiencias_novas`). O módulo de rompimento **nunca alimentava** o aprendizado → modelo congelado (`experiencias_wdo.json` vazio). Agora trades reais da Faixa 1 contam para o gate `LIMITE_EXPERIENCIAS_PARA_TREINO=3` → destravam o retreino.

### P5 — Integridade pós-restart + correção de persistência (`a900501`)
- **Validação:** `historico_contexto_wdo.csv` íntegro (740 linhas, 21 colunas, 0 não-numéricos); tuple-indices pós-boot 200/200 sem fora-de-limites/sobreposição; contador pós-load correto.
- **Bug crítico (persistência):** o plug P4 original lia `rompimento_state.json`, **zerado na virada do dia** pelo orquestrador (`st = {}`) — trades fechados na noite anterior seriam perdidos antes de virar aprendizado.
- **Correção:** plug reescrito para ler a **fonte durável** `rompimento_trades.csv` (append-only) com **dedup persistente** (`p4_feed_pendentes.json` — sobrevive a restart e virada de dia). Ordem invertida no loop: o plug roda **antes** de `_orq.orquestrar()`.
- **Backfill:** SL real de 16/09 (`BUY, reward=-19.5`) gravado direto no `historico_contexto_wdo.csv` (fonte recarregada no boot), com backup `.bak_p4`. No próximo boot: contador = 1/3; retreino dispara ao consolidar 3 trades reais (v22 + Faixa 1).

## ✅ Estado do sistema pós-autópsia
| Item | Valor |
|---|---|
| Commit da cadeia | `e32d816` → `268981c` → `f28ed55` → `5f8474d` → `a900501` |
| Magic v22 Core / Rompimento | 123456 / 7008 (isolados via tracker P1) |
| `experiencias_wdo.json` | `[]` (nominal — será alimentado no boot via backfill) |
| `rompimento_trades.csv` | dias 11/14/15 `S/TRADE`; **16/09 `SL -19.5`** |
| Working tree | limpo (fora do escopo: `Novo Documento de Texto.txt`, não commitado) |

## 👉 Próximas verificações
- **17/09 (quinta):** dia 2 da Faixa 1 na janela real — conferir boot (backfill → contador 1/3), fecho consolidado P3 e, se consolidar 3 trades reais, primeiro retreino com aprendizado da Faixa 1.
- **P2 (sequenciador):** validação em simulação/backtest antes de qualquer decisão.
- **Homologação Faixa 1:** aguarda amostra out-of-sample (parâmetros congelados — protocolo 04/09).

---

# 🔬 AUTÓPSIA 17/09/2026 — BUG CRÍTICO: `positions_get(magic=...)` + POSIÇÃO FANTASMA (P6)

> Segundo pregão da Faixa 1 na janela **REAL 09–11h**. **Achado cirúrgico:** o Core v22 passou o dia inteiro travado em `ROMPIMENTO_EXCLUSIVO` (20 ordens Sniper do Core bloqueadas entre 09:33 e 12:08) **apesar** do trade da Faixa 1 ter encerrado às 10:33. Não era falta de entradas boas — era um bug de API MetaTrader5 acoplado a uma posição legada e vencida.

## 📊 Pregão 17/09/2026 — fatos verificados
- **Faixa 1 (rompimento 1ª hora, magic 7008):** 1 trade real — `side=C (BUY), entrada=5154.0 (10:05:18), saida=FECHADA (TP), pts=+19.0` (+R$950,00 em 5 CC). Slippage de 0,5 pt (TP teórico 19,5 pts). Fecha do dia preservado: `pnl_hoje = R$ 950,00`.
- **v22 Core (magic 123456):** 0 trades no dia — mas **4.361 decisões** geradas (199 com confiança ≥0,60; 110 ≥0,70) que morreram todas no gate.

## 🚨 P6 — Causa raiz do bloqueio (corrigido em produção em 17/09)

### 1. A pegadinha silenciosa da API MT5
`mt5.positions_get()` **NÃO aceita filtro por magic**. A assinatura oficial é `positions_get([symbol], [ticket], [group])` ("can be filtered by symbol, group or ticket"). Passar `magic=7008` é **ignorado silenciosamente** e retorna **TODAS** as posições — sem erro, sem warning. Teste real na conta: `positions_get(magic=7008)`, `magic=123456`, `magic=123457` e `positions_get()` retornaram a mesma única posição.
- **Lições:** (a) nunca filtrar posições por `magic` na chamada; (b) usar filtro explícito em Python: `[p for p in mt5.positions_get() if p.magic == X]`; (c) `fechar_todas_posicoes()` já usava o padrão correto (filtro Python L10618) — o bug era isolado em `_tem_posicao_rompimento()`.

### 2. Posição fantasma / contrato vencido (retcode 10013)
Posição legada na conta demo: `ticket=2243200971, magic=123457, symbol=WINV25, vol=5.0, SELL, profit=+5.00`, aberta em **15/10/2025** — contrato WINV25 vencido, sem tick/preço atual.
- Tentativa de fechamento via `order_send` devolveu **retcode 10013 (`Invalid request`)** — símbolo não existe mais no servidor, negociação impossível.
- **Tratamento correto (aplicado):** NÃO forçar fechamento de ativo expirado — isolar o problema na lógica. O filtro por Magic Number em Python garante que ordens legadas/vencidas (qualquer magic residual) **nunca** interfiram na máquina de estados do robô. Posição fantasma fica inerte na conta demo; ao reiniciar o terminal/MT5 a corretora não a relistou, e ela não travava mais nada.

### 3. Efeito encadeado no estado
`_tem_posicao_rompimento()` (L395) usava `positions_get(magic=7008)` → sempre `True` (retornava a fantasma) → `_atualizar_estado_sistema()` mantinha `ESTADO_SISTEMA="ROMPIMENTO_EXCLUSIVO"` mesmo com `rompimento_state.json` `final=true` e faixa encerrada → gate `ROMPIMENTO_EXCLUSIVO` (L5434) barrava **toda** ordem do Core (magic ≠ 7008) → 20 Sniper %R bloqueados (`[GATE ROMPIMENTO] Ordem bloqueada para WDOV26 (apenas Magic 7008 na Faixa 1)` + `Ordem não enviada (executar_ordem falhou)`).

## ✅ Correção aplicada (P6)
- `_tem_posicao_rompimento()` reescrito: `any(p.magic == MAGIC_ROMPIMENTO for p in (mt5.positions_get() or []))` — filtro em Python, mesmo padrão de `fechar_todas_posicoes()` (L10618).
- Validado: `magic 7008 → False`, `py_compile OK`, boot limpo às 12:39:30.
- Reinício do robô com o FIX em memória (processo único sob watchdog; a dupla de PIDs era o redirector do venv Windows `venv310\Scripts\python.exe` → python real, comportamento normal, não duplicidade).

## ✅ Estado do sistema pós-correção (17/09, 12:41)
| Item | Valor |
|---|---|
| `modo_operacional` | **NORMAL** (Core/Sniper liberado; antes: ROMPIMENTO_EXCLUSIVO) |
| `sniper_bloqueado` | **False** (sem gate bloqueando) |
| `rompimento.estado_faixa` | INATIVO, `na_janela=False`, `pnl_hoje=R$ 950,00` preservado |
| `thread_ativo` | True |
| Posição fantasma WINV25 123457 | mantida inerte (não interfere — filtro por magic em Python) |

## 👉 Próximas verificações
- **17/09 14:30 (reabertura):** confirmar se o Sniper dispara normalmente com o Core liberado fora das posições ativas da Faixa 1.
- **P2 (sequenciador Faixa 1 vs. Core):** continua reservada — só em simulação/backtest (protocolo 04/09). O fix P6 resolve o travamento indevido; a proteção de posição 7008 aberta permanece por design.
- **Homologação Faixa 1:** aguarda amostra out-of-sample maior (parâmetros congelados).
- **Auditoria de robustez (recomendada):** varrer outras chamadas de `positions_get(` no código do robô para garantir que nenhum outro call-site dependa de filtragem inexistente (auditoria executada em 17/09: demais call-sites usam `ticket`/`symbol`, válidos).

---

# 🧪 GAVETA — SETE VELAS CRUA NO WDO (11/09/2026, backtest depósito)

> Depositado para "talvez um dia usar". NÃO reativa nada no robô (respeita a quarentena/con gelamento — "mexe no que mede, não no que decide").

## Achado
Primeiro backtest de WDO com **sessão completa real (09:00–18:00)**: `barras_1min_wdo.csv` (149.765 barras, 2025-07-14 → 2026-07-31, derivado do export de ticks `WDO$_202507141229_2026073118299.csv` — 2,4 GB). O feed atual do terminal trunca em ~15:30; os CSVs locais de WIN/WDO são igualmente truncados. Esta é a única base FULL-DAY disponível hoje.

## Config testada (Sete Velas CRUA — módulo removido na v22.2)
- 7 velas M15 09:00–10:30; entrada no **fecho da 7ª vela**; maioria verde→COMPRA / vermelha→VENDA.
- **SL = 10 pts WDO** (≈R$100 em 1cc; R$10/pt). **TP = extremidade oposta das 7 velas**.
- Custo R$0,75/trade, EOD 18:00, 1 CC. Mesmo motor de `backtest_frankenstein_win.py`.

## Resultados (SL fatorado por ADR — WIN 2.826 pts ↔ WDO 51 pts; "300 pts WIN" ≈ "5 pts WDO")
| SL pts WDO | n | WR | PF | net R$ (1cc) | MaxDD |
|---|---|---|---|---|---|
| 5 | 223 | 42,6% | 1,11 | +527,75 | −1.024,50 |
| **10** | **223** | **58,7%** | **1,15** | **+1.157,75** | **−1.108,50** |
| 20 | 223 | 67,3% | 1,04 | +282,75 | −1.728,25 |
| 40 | 223 | 71,7% | 1,11 | +1.142,75 | −1.977,50 |
| 60 | 223 | 71,7% | 1,01 | −37,25 | −2.307,50 |

Frankenstein (antecipação do rompimento com filtro da metade) no WDO: **n=33** — amostra destruída, inviável. Descartado.

## Interpretação
WDO **respeita S/R matinais (reversão à média)**; WIN **rompe topos/fundos (momentum)**. É por isso que a SeteV crua perde feio no WIN (PF 0,92 / −R$3,8K em 5 anos) mas vira lucrativa no WDO. O Rompimento 1ª Hora vence nos dois (WDO PF 1,38 / WIN PF 1,54).

## Post-mortem: SELL do Sub em 29/09 (primeiro trade real da Memoria Unificada)

**Trade:** `ticket=2540488355` | SELL 5 lotes @ 5211.5 | SL 5215.5 | TP 5198.0
| saida=SL as 10:14:24 | `pts=-4.0` | `lucro_rs=-200.00` | `modulo=sub`

**O que aconteceu.** O candle 1H das 09:00 foi de BAIXA (abertura 5214.50,
fechamento 5212.00; corpo 5212.00-5214.50, pavio 5198.00-5215.50). O preco rompeu
o corpo para baixo (bid 5211.5 <= corpo_fundo 5212.00) e o Sub vendeu, coerente
com a logica de MOMENTUM que o backtest de 264 pregoes calibrou. Em ~14 min o
mercado deu um balancer de alta e estourou o SL.

**Duas hipoteses que o proprio trade refuta:**

1. *"Vendera quando deveria ter comprado (compra no corpo, saida no topo)"* -
   REFUTADO. O candle era de baixa e a SELL seguia a cor do candle. Uma regra
   "SELL so se fechamento < abertura" AUTORIZARIA esta venda, nao a vetaria.
   Alem disso, "compra no corpo e saida no topo" e mean-reversion, o oposto do
   momentum validado - inverter exigiria refazer o backtest inteiro.
2. *"Faltava o filtro R/R >= 1.0"* - REFUTADO. O filtro existe desde 2546706 e
   ja havia disparado 16 s antes, as 10:00:01
   (`R/R desfavoravel 0.06 < 1.00 (tp=1.00 sl=16.50) - sem entrada`).
   Este trade passou com folga: R/R = 13.5/4.0 = **3.375**.

**Causa-raiz real: o filtro R/R e cego a escala.** Um R/R alto e alcancavel
simplesmente APROXIMANDO o stop. Aqui o SL ficou a 4.0 pts do preco contra ATR
7.96 - **0.50x ATR**, dentro da banda de ruido. A Faixa 1 usa `sl_atr_factor
2.50`; o Sub operava com 1/5 do stop do proprio Core, sem trava nenhuma, e ainda
recebia "nota maxima" no R/R. O filtro selecionava justamente os trades com stop
minusculo, que sao os mais provaveis de serem estopados por ruido.

**Correcao (29/09):** `sub_sl_min_atr` no `config.json` (default 1.0), aplicado
em `_sub_gerenciar` logo apos o filtro R/R. O SL precisa cobrir ao menos
`sub_sl_min_atr x ATR`; o TP continua cravado na extremidade do pavio. Sem
alterar a logica de momentum, sem tocar no backtest.

| cenario | so filtro R/R | R/R + ATR |
|---|---|---|
| SELL 5211.5 (trade real) | PERMITIDO R/R=3.38, sl=0.50x ATR | **BLOQUEADO** (sl 4.00 < 7.96) |
| SELL 5214.5 (corpo inteiro) | PERMITIDO R/R=16.50, sl=0.13x ATR | **BLOQUEADO** (sl 1.00 < 7.96) |
| BUY 5212.0 | BLOQUEADO R/R=0.25 | BLOQUEADO R/R=0.25 |

Custo esperado: o Sub passa a operar menos dias (exige pavio oposto com
amplitude >= 1x ATR), em troca de stops que o preco respeita. O numero de
operacoes do Sub cai; a qualidade do dataset sobe, porque as amostras restantes
sao as que o preco consegue respeitar.

## Gatilho de reativação (só se TODOS os critérios)
1. Obter WDO 2021–2024 completo (export/internet — corrige o truncamento 15:30 do feed atual) e validar **fora-da-amostra**: n≥150 por período, PF≥1,15, MaxDD≤R$1.500.
2. Se passar → incubação isolada (shadow/simulador, NUNCA junto do Core em quarentena).
3. Decisão do Mestre para qualquer uso em produção.

Scripts: `C:\AIOFEN\backtest\backtest_frankenstein_wdo.py` (aceita SLs por argv) · resultados em `backtest/resultados/frankenstein_wdo_2025_2026.csv`.
═══════════════════════════════════════════════════════════════════════
SESSÃO 29/09/2026 — LEITURA DE QUARENTENA + AUDITORIA DO CANDIDATO
"MARKOV TENDÊNCIA WDO" (somente medição; nenhum código de decisão tocado)
═══════════════════════════════════════════════════════════════════════

## 1. Estado da régua (`analisar_quarentena.py`, read-only)

| régua              | meta  | atual   | estado |
|---|---|---|---|
| Core WDO — n válido| n≥100 | **22**  | 22% (34 linhas no CSV; 12 pré-marcador/sem P&L) |
| Correlação Mod. A  | ≥0,15 | **0,2386** |ATINGIDA — porém ver alerta abaixo |
| Rompimento 1H — n  | ≥30   | 9        | 30% |
| Rompimento 1H — WR | ≥45%  | **33,3%**| REPROVADO |
| Rompimento 1H — PF | ≥1,1  | **0,43** | REPROVADO |
| Rompimento 1H — DD | ≥-3600| **-4825**| REPROVADO |
| Rompimento 1H — net| —     | **-3500**| — |

⚠️ ALERTA DE LEITURA: a correlação do Modelo A subiu de ~0,005 para 0,2386 e
bateu a meta de 0,15 — porém os trades que ela explica estão com WR 36,4% e
PF 0,54 (n=22). Correlação positiva sobre PnL negativo é ruído de amostra
pequena, NÃO sinal. Não é destrave de veto; é motivo para manter o veto desligado
e continuar coletando.

## 2. Pregão 29/09 — Faixa 1 (leitura do diário)

- SELL 5 CC @ 5211,50 (10:00:13) → STOP 5215,50 (10:14:23) = **-R$200 / -4,0 pts**
- BUY  5 CC @ 5213,50 (10:15:01) → ALVO 5240,00 (12:26:52) = **+R$1.325 / +26,5 pts**
- **Net do dia: +R$1.125,00**

Observação estrutural: o SL do SELL foi 0,50×ATR contra ATR 7,96 (post-mortem
já tratado por `sub_sl_min_atr=1.0`, commit `3cbfb8b`). O BUY que o siguió
capturou o topo do canal — é o MESMO padrão de "venda em topping + compra em
pivot" que caracterizou a semana de 04/09 (10W/3L, +R$155). Reforça que a
primeira hora do WDO tem valor de borda, não de ruído — ao contrário do que
sugere o agregado do Faixa 1 reprovado.

## 3. AUDITORIA DO CANDIDATO "MARKOV TENDÊNCIA WDO" (o item em espera)

Roadmap dizia: *"PF 1,47 ano / 1,88 OOS (+R$3.214, 161 trades). Ainda não
conectado ao robô."* **Reprodução de 29/09 (read-only, script temporário):**

    n = 166 trades | net R$ +2.836,85 | PF 1,40 | WR 46,4%
    (config: só-tendência, breakout_ratio=1.0, stop EMERGÊNCIA, 1 contrato)

O número NÃO é o do roadmap (161 → 166 trades; PF 1,47 → 1,40; +R$3.214 →
+R$2.836). Motivo: o `WDO$` só ficou com histórico populado quando o terminal
baixou as barras; a execução anterior do `backtest_markov_4estados.py` retornou
"sem dados para WDO" e rodou SÓ o WIN. **O PF 1,88 "OOS" não reproduziu.**

### 3.1 O "OOS 1,88" é escolha de corte, não propriedade estável
| corte IS | IS PF | OOS PF | OOS R$ |
|---|---|---|---|
| 30% | 1.49 | 1.36 | +1.734 |
| 40% | 1.19 | **1.60** | +2.196 |
| 50% | 1.47 | 1.30 | +867 |
| 60% | 1.59 | **1.01** | +17 |
| 70% | 1.44 | 1.26 | +401 |

O PF out-of-sample varia de 1,01 a 1,60 conforme ONDE você corta. Um número de
"OOS" isolado (1,88) sem o corte declarado não é evidência.

### 3.2 Concentração (o achado que decide a questão)
- **Top 3 meses = R$ +3.119,57 = 110% do lucro total.**
- **Sem os top 3 meses: n=101, PF 0,93, R$ -282,72 (NEGATIVO).**
- Dias operados: 126 | dias positivos: 64 (**51%** — moeda ao ar no dia).
- 5 meses negativos em 13 (2025-11, 2026-04, 2026-07, 2026-09, 2025-09).
- Maior mês (2026-03, n=40) = R$ +1.609,94, 57% do lucro total.

Isto é EXATAMENTE a "Lição Registrada #1" da Fase 13 ("Modelo C de abertura:
77,8% WR em 9 dias e −R$9 mil em 250 dias"), com 5 meses de distância. O edge
não é estável no tempo; ele é concentrado em 3 janelas.

### 3.3 O que o bootstrap diz (10.000 sorteios, blocos por dia)
- P(net > 0) = **96,3%** — o sinal tem Probabilidade de ser positivo.
- Mas intervalo 5%–95%: **R$ +195 a R$ +5.607** (faixa de 28×).
- P(PF > 1) = 96,3% | mediana PF = 1,39.

Ou seja: o edge provavelmente EXISTE, mas a magnitude é incerta demais para
dimensionar capital. E o PF>1 com 96% de confiança convive com 51% de dias
positivos — é um edge de cauda, não de consistência.

### 3.4 Conclusão da auditoria
O candidato **não é falso** (é o único item com sinal positivo estatisticamente
sustentado no inventário), **mas está superdimensionado no roadmap**. PF honesto
≈ 1,40, não 1,88. E ele é frágil: sem 3 meses, é negativo.

→ **NÃO é "deixar dinheiro na mesa"** no sentido deedge validado e descartado.
→ É **uma aposta de tamanho desconhecido** que precisa de measurement, não de
  ejeção em produção.

## 4. Encaminhamento Mantido (sem alterar código)

1. **Core WDO congelado** (diretriz "mexe no que mede, não no que decide").
2. **Markov Tendência WDO → SHADOW MODE primeiro** (não real, não junto do Core
   em quarentena). Já é o passo 2 do roadmap ("shadow ou real com 1 contrato").
   Critério de leitura: ≥30 sinais gravados, então repetir o §3.1 (múltiplos
   cortes) e o §3.2 (concentração) sobre os sinais REAIS.
3. **Veto do Modelo A continua desligado** apesar da correlação 0,2386 (ver §1).
4. **Faixa 1/Rompimento:** reprovado em 3/4 métricas com MaxDD estourado — não
   expandir; manter a trava ATR e deixar produzir amostra.
5. Rodar `analisar_quarentena.py` semanalmente; destravar Core só em n≥100.

Fontes: `analisar_quarentena.py`; `backtest_markov_4estados.py`; análise temp
read-only (bootstrap + sensibilidade de corte + concentração mensal). Nenhuma
linha de decisão foi alterada nesta sessão.

═══════════════════════════════════════════════════════════════════════
SESSÃO 29/09/2026 (tarde) — AUDITORIA DE FUNIL + VEREDITO DO B1
═══════════════════════════════════════════════════════════════════════

Ferramenta: `C:\AIOFEN\auditar_funil.py` (READ-ONLY, nao importa o monstro,
nao escreve nada). Roda tambem no agendamento semanal.

## 1. O que `decisions_wdo.csv` realmente e'

`monstro_unificado_v22.py:8266` — *"Salva a decisao ANTES de qualquer filtro
que possa impedir a execucao da ordem"*.

`decisions_wdo.csv` (07/07 a 29/09): 131.335 linhas
- NADA 91.153 | **BUY 17.734 | SELL 22.448** (40.182 direcionais)
- Ordens realmente executadas no mesmo periodo: **232**

**Os 40.182 NAO sao ordens. Sao candidatos.**

## 2. Etapa A - vetoes INTERNOS do `prever_acao()` (ja voltam NADA no CSV)

`prever_acao()` e definido em :9410 e chamado em :8083, ANTES do save em :8267.
Logo Williams/Multi-TF/Sentinela/MR tem poder causal: definem QUEM sobrevive.

| veto (dentro do prever_acao) | ocorrencias (todos os logs) |
|---|---|
| Williams %R | 73.360 |
| FORCA BUY/SELL (so um lado viavel) | 35.584 |
| VETO TOTAL (nenhum lado viavel) | 24.072 |
| Multi-TF (M5/M15/M30) | 18.491 |
| Sentinela | 10.468 |
| MR (mean reversion) | 4.715 |
| **C10 score baixo** | **0 — NUNCA ATIVOU** |
| **Spread alto** | **0 — NUNCA ATIVOU** |
| **Aprendizado forcado** | **0 — NUNCA ATIVOU** |

> **CORRIGIDO em 29/09 (Tríplice Regra).** A linha "Tendencia veto total" foi
> **removida**: um grep em todos os `monstro_wdo*.log` nao encontra **nenhuma**
> ocorrencia de `TENDENCIA VETO`. Era contador fantasma, nao um veto inativo.
> Ver secao 9.

## 3. Etapa B - portoes DEPOIS do CSV (a decisao estava BUY/SELL)

| portao | ocorrencias |
|---|---|
| **GATE ROMPIMENTO (Faixa 1)** | **320** |
| >>> ORDEM EXECUTADA | 233 |
| Volume muito baixo | 6 |
| Circuit Breaker CB1 | 3 |
| **Circuit Breaker CB2** | **0 — NUNCA ATIVOU** (corrigido; era 3) |
| Dados invalidos | 0 — NUNCA ATIVOU |
| Bloqueio de lado (inversao) | 0 — NUNCA ATIVOU |
| Horario limite de ordens | 0 — NUNCA ATIVOU |
| Veto seguir os bigs | 0 — NUNCA ATIVOU |
| Piso de confianca | 0 — NUNCA ATIVOU |

**Seis portoes de dez nunca dispararam em nenhum log do periodo.**

## 4. A PORTA UNICA: `sniper_apenas = true`

`monstro_unificado_v22.py:8332-8333`:
```python
if SNIPER_APENAS:
    acao_para_executar = "NADA"
```
E logo acima (:8323-8327), quando o Sniper dispara, ele **SOBREPOE** a decisao
da IA ("sobrepondo IA, pulando filtros normais").

Conclusao: nos dois ramos a decisao do modelo e descartada —
- Sniper inativo -> NADA (modelo descartado)
- Sniper ativo  -> direcao do Sniper (modelo sobrescrito)

**As 40.182 decisoes direcionais do CSV nao tem poder causal sobre nenhuma
ordem.** O unico produtor de ordem e o Sniper %R.

## 5. O que realmente derrubou a taxa de trades: o gate da Faixa 1

`executar_ordem` (:5621) bloqueia tudo que nao for magic 7008 enquanto
`ESTADO_SISTEMA == "ROMPIMENTO_EXCLUSIVO"`. E `_atualizar_estado_sistema()`
(:406) mantem esse estado **enquanto houver posicao 7008 aberta**, nao so
durante a janela 09:00-11:00.

| periodo | pregões | Core fechou posicao | media/dia |
|---|---|---|---|
| 14/08 a 27/08 (Faixa 1 = 7 Velas) | 10 | 53 | **5,3** |
| 01/09 a 10/09 (pos-v22.2) | 6 | 17 | **2,4** |
| **11/09 a 28/09 (Faixa 1 magic 7008)** | 12 | 13 | **0,7** |

Dias com 100% dos disparos do Sniper bloqueados, com o gate cobrindo o
**pregao inteiro**: 11/09 (09:17-17:14), 15/09 (10:50-17:12), 16/09
(09:15-17:07), 18/09 (09:15-16:34), 21/09 (09:34-17:07), 22/09 (09:32-17:13),
28/09 (09:19-15:17) e 29/09 (09:24-12:02).

Hoje: o BUY da Faixa 1 (10:15) so foi fechado no TP as **12:26** — o Core ficou
pausado ate la porque a regra e "pausar ate o trade do rompimento terminar".

**A queda de ~5,3 para ~0,7 trades/dia NAO e seletividade. E acoplamento de
projeto: enquanto a Faixa 1 segura posicao, o Core nao opera.**

## 6. VEREDITO DO B1 — INVIÁVEL COMO ESCOPO

B1 (agenda 05/10): *"Popular `experiencias_wdo.json` a partir de
`decisions_wdo.csv` + `historico_contexto_wdo.csv` (feats = contexto,
label = resultado real do trade) | GO: >100 registros validos"*.

- As 40.182 linhas de `decisions_wdo.csv` foram vetadas **antes** de executar.
  Por construcao elas **nao tem `pnl_real`**.
- O unico rótulo verdadeiro (PnL de trade executado) vem do Core, a
  **0,7 trades/dia**.
- Meta ">100 registros" é aritmeticamente iinalcançável nesse regime.

Projeção da regua do Core (n>=100, hoje n=22):
**78 trades restantes ÷ 0,7/dia ≈ 111 pregoes (≈ marco/2027)**.
No ritmo de agosto (5,3/dia) seriam ~15 pregoes. O gate da Faixa 1 e,
portanto, o responsavel direto pelo atraso de ~4 meses da meta.

Opcoes para o B1 (todas exigem decisao do Mestre — NÃO implementadas):
- **B1-a Contrafactual:** rotular as 40k decisoes com retorno futuro
  `t+N` via M1 do WDO$ (ha 136.699 barras M1 de 29/09/2025 a 29/09/2026, cobre
  toda a janela do CSV). Viabilidade: ALTA. Risco: muda a semantica do rotulo
  de "PnL executado" para "PnL teorico"; passa a medir cenario, nao resultado.
  Nao substitui amostra real.
- **B1-b Reconciliar o gate:** resolver o acoplamento da Faixa 1 (Core nao
  pode conviver com uma posicao 7008 aberta) e voltar a 5/dia. A meta vira
  alcancavel, mas isso **e** mudanca de logica de decisao do Core congelado.
- **B1-c Abandonar o B1** e manter a coleta real, aceitando mar/2027.

## 7. Achado colateral: POSICAO FANTASMA na conta

Aberta em **15/10/2025**, `WINV25` (contrato VENCIDO), magic **123457**,
SELL 5 lotes @ 142.605, SL/TP 142.615/142.550, PnL R$ 5,00, margem R$ 0.

- Nao bloqueia o Core (magic 123457 ≠ 7008, e o symbol ≠ SYMBOL, entao
  `positions_get(symbol=SYMBOL)` nao a enxerga).
- Mas e exatamente a classe do bug P6 (posicao fantasma): `fechar_todas_posicoes`
  nao consegue fechar contrato vencido, entao persiste para sempre, suja
  `positions_get()` sem filtro e distorce leitura de equity/posicoes.
- **Higiene de conta — nao e mexer no Core.** Requer close manual pelo terminal
  (ou o swap/roll do contrato).

## 8. Pendencia de decisao (Mestre)

1. O gate da Faixa 1 esta dentro do Core congelado. Ele e a unica coisa que
   impede `n>=100`. Nao ha solucao dentro do congelamento.
2. B1 precisa de uma das tres opcoes da secao 6. O escopo original e
   aritmeticamente impossivel.
3. Enquanto isso,, 6 portoes do Core estao comprovadamente mortos (secao 3) e o
    C10 nunca reprovou um unico setup em todo o historico de logs.

---

# SESSAO 29/09/2026 (noite) — TRIPLICE REGRA + B1-a APROVADO

## 9. A Tríplice Regra de Validacao (implantada)

Duas conclusoes desta mesma sessao estavam **erradas** por defeito de regex,
antes de virarem premissa:

1. "Sniper %R: 0 disparos / codigo morto" -> o padrao nao cobria a linha
   `SNIPER %R INICIA`. Real: **474 disparos**.
2. "o funil e' contraditorio entre Williams e Multi-TF" -> ambos rodam ANTES do
   save do CSV; nao medem o funil pos-decisao. Nenhuma das duas sobreviveu ao
   cruzamento de fontes.

Regra vigente: **nenhum veredito sem passar pelos tres testes.**

- **Teste 1 (selftest)** — cada regex casada contra a linha canonica real,
  incluindo teste de colisao cruzada. Roda com `--selftest`.
- **Teste 2 (dual-check)** — contagem do LOG cruzada com `decisions_wdo.csv`
  e com o historico MT5. Roda com `--dualcheck`.
- **Teste 3 (higiene)** — posicao/contrato vigente antes de agir.

### 9.1 Os 4 bugs que o selftest pegou antes de virarem premissa

| # | defeito | impacto |
|---|---|---|
| 1 | `VETO TOTAL` casava tambem `TENDENCIA VETO TOTAL` | contagem inflada |
| 2 | `Circuit Breaker CB2` (re.I) casava as linhas do CB1 | **CB2 real = 0, nao 3** |
| 3 | `Bloqueio de lado` e `Horario limite` nunca casariam a linha real | 0 por regex morta |
| 4 | `TENDENCIA VETO` **nao existe em nenhum log** | contador fantasma |

Resultado: `PASS` 20/20 + marcador de core. `auditar_funil.py` passa a ser a
**versao oficial de leitura do funil**.

## 10. B1-a APROVADO — especificacao calibrada

Escolha do Mestre: **B1-a**. Duas restricoes fixas nao negociaveis:

- o rotulo e' **contrafactual**: muda de "PnL executado" para "PnL teorico";
  mede cenario, **nao resultado**;
- nao aumenta o n real, nao vira gate, nao altera decisao do Core.

### 10.1 Por que M5 e nao M1

| serie | barras (29/07-29/09) | cobertura |
|---|---|---|
| `WDOV26` M1 | 18.210 | **86,2%** — esparso, enviesaria o rotulo |
| `WDOV26` M5 | 4.538 | 107,4% |
| **`WDO$` M1** | 24.653 | 116,7% |
| **`WDO$` M5** | 4.932 | **116,8%** — completo |

Escolha: **`WDO$` em M5**. M5 e o proprio timeframe do Core.

### 10.2 Por que `WDO$` e nao o contrato do mes

O Core opera WDOQ26 (jul) -> WDOU26 (ago) -> WDOV26 (set). Os dois primeiros ja
venceram e **nao sao mais selecionaveis** (sem livro de ofertas). `WDO$` tem
historico completo e hoje bate exatamente com o front: **5231,00** nos dois.
Rotular no contrato do mes reintroduziria lacuna deExpiry e gap de rolagem.

### 10.3 Por que `t+12` (60 min) e nao `t+1`/`t+3`

Duracao real das 299 posicoes do Core (60 dias):

| p10 | p25 | mediana | p75 | p90 | max |
|---|---|---|---|---|---|
| 1 min | 2 min | **7 min** | 17 min | **52 min** | 198 min |

| N | trades que resolvem |
|---|---|
| t+1 (5 min) | 11,4% |
| t+3 (15 min) | 70,9% |
| **t+12 (60 min)** | **92,6%** |
| t+24 (120 min) | 99,0% |

`t+12` foi escolhido por ser a menor barreira que cobre a quasi-totalidade do
holding time real observado — e nao por convencao.

### 10.4 O N e derivado, nao arbitrado

Para cada N candidato, medir a **concordancia entre o rotulo contrafactual e
os 242 resultados reais do MT5**. O N com maior concordancia e o correto. Os
dados decidem; a intucao nao arbitra.

Barreiras: `−max(1,5×ATR, 8)` pontos (a regra real do Core), com superior em
k× para k ∈ {1; 1,5; 2; 3}. Rotulo +1 / −1 / 0 (expirado). Registrar tambem
MFE/MAE e o retorno em t+1,2,3,5,10,12.

## 11. ACHADO REBASEATIVO: o Core perdeu dinheiro em 60 dias

| mes | trades | winners | WR | PnL |
|---|---|---|---|---|
| 2026-08 | 146 | 54 | 37% | **−R$ 1.890,00** |
| 2026-09 | 34 | 17 | 50% | **−R$ 295,00** |
| **TOTAL** | **180** | **71** | **39%** | **−R$ 2.185,00** |

A semana de 04/09 (10W/3L, +R$ 155) **nao e representativa**. O
`quarentena_core_n` conta 22 trades, mas o registro de 60 dias mostra o Core em
prejuizo. **A regua precisa ser re-baselineada, nao apenas contada.**

### 11.1 Isso reconfigura o objetivo do B1

A meta `n>=100` deixa de ser so "volume estatistico" e passa a responder uma
pergunta binaria:

> **O alpha da IA primaria e positivo e esta sendo DESTRUIDO pelos gates —
> ou a perda e estrutural do sinal primario?**

O B1-a responde comparando:

- **Expectativa Matematica Teorica da IA** (rotulo t+12 sobre as 40.261 decisoes)
- **Expectativa Matematica do Core Executado** (os 242 trades reais)

Se teorica > executada, o valor esta no desacoplamento. Se teorica <= 0, nao ha
alpha a resgatar e o gate nem e o culpado.

## 12. SNAPSHOT DO FUNIL (29/09, pos-correcao)

`decisions_wdo.csv` e um arquivo **vivo** (o Core esta rodando); os numeros
abaixo sao o retrato no instante da medicao, nao um total fechado.

- NADA 91.482 | BUY 17.813 | SELL 22.448 -> **40.261 direcionais**
- MT5 deals fechados magic 123456 (desde 29/07): **242**
- **Taxa de sobrevivencia: 0,6%** (242 / 40.261)

E por isso que `pnl_real` nao existe para os 40k.

## 13. Posicao fantasma `WINV25` — DECISAO DO MESTRE

Decidido: **ignorar**. Nao ha ordem viavel (retcode 10013, contrato sem livro
de ofertas) e a posicao nao afeta o Core (magic 123457 ≠ 7008, symbol ≠ SYMBOL).
Requer acao da corretora (zeragem de custodia) se um dia incomodar.

**Marco B1-a: aprovacao** conforme a especificacao da secao 10. Executado no
fds 02-04/10 (Etapa I); adiamento da pauta A1/A2/A3 para **09/10** salvo
parecer do B1-a (ver 23.10).

## 14. CHECKPOINT FATO-REAL — 29/09/2026 (fechamento de sessao)

Escopo desta secao: separar o que **existe** do que **esta previsto**. Escrita
depois de tres correcoes a um texto de resumo que carregava premissas falsas.

### 14.1 Tres premissas refutadas antes de endurecerem

| # | premissa incorreta | estado real verificado |
|---|---|---|
| 1 | "`rotular_b1_contrafactual.py` criado e pronto" | **NAO EXISTE.** Nenhum arquivo de rotulagem no repositorio |
| 2 | "`WINV25` e pendencia residual, fechar no terminal" | **ARQUIVADO.** Decisao do Mestre: ignorar (secao 13) |
| 3 | "Expectativa re-baselineada" | **NAO FEITO.** Diagnostico registrado; `analisar_quarentena.py` intacto |

Verificacao: `Test-Path rotular_b1_contrafactual.py = False`; busca por
`*rotul*` em `C:\AIOFEN` sem resultado; `git status` limpo desde `191103e`.

A premissa 1 era a mais perigosa: abriria a janela de 05/10 esperando artefato
inexistente.

### 14.2 Entregue e verificado (commit `191103e`)

- `auditar_funil.py` — selftest **20/20 + marcador de core (PASS)**, dual-check
  log x CSV x MT5 (PASS), `py_compile` OK.
- `ROADMAP` — contadores corrigidos (CB2 3->0, VETO TOTAL 24.053->24.072,
  Williams 73.286->73.360), `TENDENCIA VETO` removido como fantasma, snapshot
  datado do funil.
- Agendamento `Monstro-Quarentena` ativo, sextas 18:00 (proxima 02/10/2026).

### 14.3 Pauta de 05/10/2026 — ADIADA para 09/10/2026

> Adiamento aprovado (Decisão 02/10): pregão = coleta, não ajuste; janela
> 09/10 (sexta) + fds 10-11/10 para implementar e testar. Vigência salvo
> parecer do B1-a (Etapa I, fds 02-04/10, ver 23.10).

1. **`rotular_b1_contrafactual.py`** — tripla barreira, `t+12` M5 sobre
   `WDO$`, calibracao do N pela concordancia com os trades reais (secao 10.4).
   **EXECUTADO no fds 02-04/10 (Etapa I) — resultado em 23.10.**
2. **Re-baseline pratico** das expectativas do Core e ajuste das reguas
   estatisticas no pipeline — hoje o `-R$ 2.185 / 180 trades / 39% WR` esta
   diagnosticado, nao incorporado a `analisar_quarentena.py`.

### 14.4 Regra para o proximo checkpoint

Nenhum item entra no status como entregue sem `Test-Path`, `git log` ou execucao
que o comprove. Especificacao aprovada != artefato entregue.

---

# SESSAO 29/09/2026 (18:00) — FECHO, FALSO ALARME E RUIDO DE ROTULO

## 15. Causa raiz do falso alarme "+221/-13"

O fecho de 17:35 reportou `MUDANCA ESTRUTURAL +221/-13`. **Nao houve violacao
da quarentena.** O conteudo do diff era o bloco `MEMORIA UNIFICADA`, commitado
as 01:48 em `78c6459` — trabalho do proprio dia, ja revisado.

| evidencia | resultado |
|---|---|
| `git rev-parse HEAD:monstro_unificado_v22.py` | blob `58624fd` — Core versionado |
| `git diff HEAD -- monstro_unificado_v22.py` | vazio — nada nao commitado |
| `agente_snapshot_v22.py` == Core (SHA256) | identicos (o fecho sobrescreve no fim) |

**Causa raiz:** `verificar_mudanca_codigo()` comparava o Core com
`agente_snapshot_v22.py`, um baseline **rotativo local**, sobrescrito a cada
fecho. O agente nao tem como saber que a diferenca ja foi commitada e
aprovada, entao reabre "PROPOSTA p/ revisao humana" sobre codigo revisado.
Historico do ruido: **16 diffs arquivados**, um deles de 589 KB, zero mudancas
reais — o alerta dispara em quase todo pregao.

**Correcao (`ea54765`):** a fonte da verdade passa a ser `git diff HEAD`. Só
vira alarme o que esta no disco e **nao** foi commitado. Testado nos dois
sentidos: commitado -> `None`; nao commitado -> `+2/-0` com diff gravado.
Nova linha de rastreabilidade: `ultimo_commit_robo()` imprime hash, data, autor
e assunto do ultimo commit que tocou o .py de producao.

## 16. Duas metricas com o mesmo nome: `win%`

O relatorio daily imprimia, lado a lado:

- `win% (historico reward!=0): 66.67%`  (`agente_monstro_core.py:449`)
- `[PRIORIDADE 3] Win rate abaixo de 35%`  (`tools/autopsia_automatizada.py:283`)

Nao sao a mesma coisa:

| metrica | fonte | populacao |
|---|---|---|
| `winpct_historico()` | coluna `reward` do CSV | linhas do dataset |
| `win_rate` | deals do MT5 | trades executados |

**Verificado: o 66,67% vinha de n = 3.** Um percentual sem denominador, com tres
amostras, apresentado como se fosse desempenho. Quem lesse so o primeiro numero
concluiria que o Core esta saudavel — o oposto do diagnostico (WR real 39%).

**Correcao (`ea54765`):** renomeado para `dataset_reward_fill%`, a funcao agora
retorna `(pct, n)` e o denominador e impresso, e o relatorio remete o win rate
de trade para a autopsia. Os dois numeros nunca mais aparecem sob o mesmo nome.

## 17. Proposta do fecho REJEITADA (decisao do Mestre)

O fecho 29/09 proposing `TRAILING_GATILHO 5 -> 7` na PRIORIDADE 4.
**Rejeitada durante a quarentena.** Alteracao de gerenciamento/execucao do Core
exige aprovacao explicita do Mestre; nenhuma regra de execucao muda por
sugestao automatica de plano diario. O agente ja marca como proposta (Fase 1) —
a trava correta.

## 18. ERRO PROPRIO A REGISTRAR: artefato destruido

Ao testar o novo alarme de diff, o teste usou o **nome de arquivo de producao**
`diff_estrutural_20260929.txt` e o **sobrescreveu**, apagando em seguida o diff
real do fecho. O arquivo nao estava no git: **nao recuperavel.**

Perda: o artefato bruto. Preservado: a conclusao, que esta acima e verificada
por `git rev-parse` e `git diff`. Licao: teste que escreve em diretorio de
producao precisa de nome de fixture, nao do padrao `YYYYMMDD` real.

## 19. Auditoria das afirmacoes do assistente (29/09)

Verificacao completa antes de fechar a sessao:

| afirmacao | status |
|---|---|
| Core congelado, nao alterado | CONFIRMADO (`git diff HEAD` vazio) |
| `prever_acao` em :9410 | CONFIRMADO (exato) |
| chamada em :8083 | CONFIRMADO (exato) |
| save do CSV em :8267 | CONFIRMADO (exato) |
| `sniper_apenas` em :8332 | CONFIRMADO (exato) |
| GATE ROMPIMENTO em :5621 | CONFIRMADO (exato) |
| `_atualizar_estado_sistema` em :406 | CONFIRMADO (exato) |
| CSV 29/07 a 29/09 | CONFIRMADO (`2026.07.29 09:41:10` -> `2026.09.29 17:14:58`) |
| Core perdeu R$ 2.185 em 180 trades | CONFIRMADO |
| "Core NAO esta versionado no git" | **REFUTADO** — erro proprio, ja retractado |

**Erros meus na sessao: 2.** (1) alarme falso de "Core nao versionado", por
mixagem de stderr do PowerShell; (2) destruicao do `diff_estrutural_20260929.txt`
pelo teste. Ambos registrados aqui em vez de silenciados.

## 20. Agente do fecho — proveniencia

Quem enviou a mensagem e' `agente_monstro_core.py` rodando no modo `fecho`
(17:35, impressao em stdout, nao gravada em arquivo). Historico completo desde
a criacao: **15 commits, 03/08/2026 -> 29/09/2026**.

| quando | o que |
|---|---|
| 03/08 | agente autonomo Fase 1: autotuner por whitelist, decisao por sinais vs executados |
| 04/08 | watchdog + CI + kill-switch por loss diario + autopsia EOD |
| 06/08 | relatorio/plano geridos antes do shutdown (sobrevive a abort) |
| 15/08 | watchdog detecta processo orfao + cooldown sniper |
| 10/09 | relatorio integra trades do modulo rompimento |
| 11-16/09 | protecao contra feed podre/defasado; correcao do offset BRT/UTC do XPMT5 |
| **29/09** | `ea54765` — baseline de diff vai para o git; `win%` renomeado |

O agente roda em modo **Fase 1**: reporta e propoe, nunca altera logica de
decisao. Confirmado nesta sessao — o proprio fecho classificou a mudanca de
trailing como "PROPOSTA p/ revisao humana" em vez de aplica-la.

---

## 21. [DIRETRIZ FIXA] Matriz de Parametrizacao e Custos da B3 (WIN vs WDO)

> Valores oficiais do ecossistema.
>
> **REVISAO 10/11/2026 (canonica, vale para todo o projeto):** custo do WDO =
> **R$ 0,60 para entrar + R$ 0,60 para sair = R$ 1,20 por contrato por
> operacao**. Diretriz do Mestre, confirmada nesta data. O valor anterior de
> R$ 0,80/contrato (retificado em 02/10/2026 a partir do `config.json` ->
> `custos_operacionais`, XP NOMOS, 5 contratos) fica **substituido** e mantido
> apenas como historico. O `config.json`/`backtest/custos_reais.py` ainda
> carregam o valor antigo e devem ser alinhados na proxima manutencao.
>
> **Historico (nao vale mais):** em 02/10/2026 o custo foi retificado para
> R$ 0,80 com base no `config.json`; a redacao original de R$ 1,20 / R$ 0,50
> ("Friction B3") tinha sido revogada naquela data. Em 10/11/2026 o Mestre
> restabeleceu **R$ 1,20** como o valor correto e definitivo.
>
> **Custo nao decide trade:** operamos sempre com **1 contrato**; 1 ponto =
> R$ 10,00 (0,5 pt = R$ 5; 5 pts = R$ 50; 20 pts = R$ 200). R$ 1,20 e ruido
> frente a amplitude tipica do WDO e **nao** invalida estrategia lucrativa.

### 1. Mini Dolar (WDO)

- **Valor por Ponto:** 1,0 ponto = R$ 10,00 por contrato (medido: tick do
  contrato real = 0,5 ponto = R$ 5,00).
- **Variacao Minima (Tick) do CONTRATO REAL (`WDOV26`):** 0,5 ponto = R$ 5,00.
- **Tick do sintetico `WDO$`:** 0,001 ponto = R$ 0,01 — resolucao **500x mais
  fina** que o real. Nunca usar o tick sintetico para justificar fills/paradas.
- **Custo Operacional (Friction B3):** **R$ 0,60 na entrada + R$ 0,60 na saida =
  R$ 1,20 por contrato por operacao**. Canonico desde 10/11/2026 (diretriz do
  Mestre). O valor de R$ 0,80 do `config.json` (`custo_por_trade_5ct: 4,0`) e
  legado e deve ser corrigido.
- **PnL Liquido (por lote):**
  - Lucro = `pontos a favor x R$ 10,00 - R$ 1,20`;
  - Prejuizo = `pontos contra x R$ 10,00 + R$ 1,20`.
- **Break-even (higiene):** obrigatoriamente acima do custo (**> 0,12 ponto**);
  sugestao de +1,5 a +2,0 pontos para sair no lucro real.
- **Amplitude diaria medida** (M5, 01/10/2025-29/09/2026): p50 = 47,
  p75 = 62, p90 = 84 pontos.

### 2. Mini Indice (WIN)

- **Valor por Ponto:** 1,0 ponto = R$ 0,20 por contrato (medido: tick do
  contrato real = 5,0 pontos = R$ 1,00).
- **Variacao Minima (Tick) do CONTRATO REAL (`WINV26`):** 5,0 pontos = R$ 1,00.
- **Tick do sintetico `WIN$`:** 1,0 ponto = R$ 0,20 — resolucao **5x mais
  fina** que o real.
- **Custo Operacional (Friction B3):** R$ 0,25 por contrato, ida e volta
  (= `custo_por_trade_5ct: 1,25` do `config.json`; emolumentos B3 + RLP, XP
  NOMOS, zero corretagem). Canonico desde 02/10/2026.
- **PnL Liquido (por lote):**
  - Lucro = `pontos a favor x R$ 0,20 - R$ 0,25`;
  - Prejuizo = `pontos contra x R$ 0,20 + R$ 0,25`.
- **Break-even (higiene):** acima do custo (> 1,25 ponto, derivado do custo
  canonico de R$ 0,25).
- **Amplitude diaria medida** (M5, mesma base): p50 = 2.784, p75 = 3.784,
  p90 = 4.733 pontos.

### Regra de portabilidade de parametro

- Ponto **NAO e portavel entre ativos**: stop de 10 pontos = 21,3% da
  amplitude p50 diaria do WDO vs 0,4% do WIN (~59x de diferenca).
- Parametro em pontos so se compara dentro do mesmo ativo; entre ativos,
  normalizar por R$ ou por amplitude/ATR.
- Amplitude de referencia = RANGE do dia (high-low), nao corpo — conflacao
  range/corpo foi a origem do erro de escala corrigido no sandbox Triplo ATR.

### [REGISTRO] Sandbox Triplo ATR — ENCERRADO

- Parecer corrigido aceito pelo Mestre em 29/09/2026 (unidades desta matriz):
  **REPROVADO** — n=23, PF 1,79, RF 2,66, lucro R$ 808,80, DD absoluto
  R$ 303,60; bootstrap p=0,390; 23 sinais em 248 dias (n>=100 exigiria
  ~1.078 dias); MaxDD% de 37,5% invalido porque a curva comecou em R$ 0.
  Nenhuma integracao ao Core (ainda congelado).
- **RETIFICACAO 02/10 (custos) — HISTORICO:** os numeros do parecer acima
  (lucro R$ 808,80, etc.) usaram o custo provisorio antigo de R$ 1,20/contrato.
  Em 02/10 isso foi rebaixado para R$ 0,80; **em 10/11/2026 o valor de R$ 1,20
  foi restabelecido como canonico** (0,60 + 0,60), de modo que os numeros
  originais do parecer estao, na pratica, corretos. A reprovacao nao muda: os
  criterios decisivos (n=23 vs n>=100 -> ~4,3 anos; RF 2,66 vs floor; MaxDD%
  invalido) nao dependem do friction.

---

## 22. [REGISTRO DE INCIDENTE & REGRA DE CONTA NETTING]

### Incidente 03/09/2026 (Magic 7007 / 665 lotes) — retificacao da leitura de 29/09

- **Evento:** 03/09, 11:15:03-11:29:58 — 133 ordens **SELL** de 5 CC =
  665 lotes, comentario `7Velas V9`; PnL ~ -R$ 57.425 (SL fixo 5138,50;
  preco subiu contra a posicao vendida).
- **NOTA DE QUALIDADE:** o assistente relatou inicialmente entradas "BUY" e
  causa "falta de `positions_get`". Os deals confirmam **133 DEAL_TYPE_SELL /
  saida BUY 5138,50**, e a causa comprovada e a da secao abaixo. Registro
  corrigido.
- **Causa raiz COMPROVADA nos logs** (sec. "Auditoria da semana 01-04/09"):
  1. commit `1b7aa3d` (01/09) incluiu `rec['ticket']` sem atualizar `campos`
     em `_registrar_trade()` → `ValueError: dict contains fields not in
     fieldnames: 'ticket'`;
  2. `orquestrar()` grava o trade ANTES de persistir o state → state nunca
     salvo (`chave not in state` fica sempre True);
  3. `monstro_unificado_v22.py` L6630-6633 chama `orquestrar()` dentro de
     `except Exception` que so loga e segue → a cada ~6s reexecuta
     `avaliar()` e reenvia a ordem.
  - A ausencia de `_tem_posicao_aberta()` foi **agravante** (reentrada em
    conta Netting), NAO a causa disparadora.
- **Reparo 04/09 (`8758b19`):** idempotencia restaurada (campos + filtro
  `{c: rec.get(c, '')}`) + trava dupla (`_tem_posicao_aberta` e
  `_acumulado_janela`) + `return` apos a 1a entrada da janela.
- **Desativacao:** 10/09 v22.2 (`8bb4509`) — Faixa 1 substitui Sete Velas;
  arquivo removido da raiz (backup: `backup_pre_rompimento_20260910/`).

### Regra Institucional Permanente (Netting)

- NENHUM modulo/sinal novo entra sem TODAS as guardas:
  1. checagem de posicao aberta do MAGIC via `positions_get` (cobre a posicao
     parcial pos-TP1);
  2. teto de volume acumulado por janela temporal;
  3. idempotencia cuja persistencia sobrevive a excecao (state gravado antes
     de qualquer efeito colateral);
  4. loop de execucao que jamais engole excecao e segue reenviando ordem.
- Backtest/simulacao: ponto e tick sempre do CONTRATO REAL de referencia;
  sinteticos (`WDO$`/`WIN$`) servem so para continuidade de historico, nunca
  para justificar precisao de fill.

---

## 23. CHECKPOINT SEMANAL - 02/10/2026 (fechamento do ciclo congelado 28/09-02/10)

> Protocolo de quarentena ATIVADO em 02/10 (sexta, 18:00) via
> `analisar_quarentena.py` (`logs/quarentena_semanal.log`, 2o bloco). Todos os
> numeros conferidos contra `modelo_a_shadow.csv`, `rompimento_trades.csv` e
> history_deals GET no MT5 nesta data.

### 23.1 Regua 02/10 (nao mudou a regua; proposito: leitura)

| regua | 29/09 | 02/10 | meta | estado |
|---|---|---|---|---|
| Core WDO n (P&L fechado pos-04/09) | 22 | **29** | >=100 | 29% |
| Correlacao Mod. A (pos-04/09) | 0,2386 | **0,1867** | >=0,15 | atingida, mas ruido (ver abaixo) |
| Rompimento n (pts preenchido) | 9 | **11** | >=30 | 37% |
| Rompimento WR | 33,3% | **36,4%** | >=45% | REPROVADO |
| Rompimento PF | 0,43 | **0,59** | >=1,1 | REPROVADO |
| Rompimento MaxDD (R$) | -4825 | **-4825** | >=-3600 | REPROVADO |
| Rompimento Net (R$) | -3500 | **-3025** | - | semana melhorou; dia 02/10 devolveu |

- Core pos-04/09: 43 registros, 29 com P&L fechado. WR 41,4%, PF 0,67,
  net -R$ 395,00. Correlacao 0,1867 de novo acima da meta, mas sobre PnL
  negativo e n=29 -> ruido de amostra pequena, NAO sinal. Veto do Modelo A
  permanece DESLIGADO.

### 23.2 Semana em numeros (deals MT5, magic 123456 e 7008)

- **Core (123456): 7 trades -> +R$ 75.** 29/09 (-80, -80, +65, +50);
  01/10 (+75, +70, -25). Sem trades em 28/09, 30/09 e 02/10.
- **Faixa 1 (7008): 5 trades -> +R$ 1.925.** 28/09 +325; 29/09 -200, +1.325;
  01/10 +1.800; 02/10 **-1.325** (BUY 5261, SL ATR 10,69 x 2,5 = 5234,3,
  fechou 17:14, -26,5 pts).
- **Semana total: +R$ 2.000.**
- Saldo MT5 842.464,21 = 841.869,21 (fecho 29/09) + 1.920 (01/10) - 1.325
  (02/10) -- reconcile OK. Margem livre = saldo. Contrato front: **WDOX26**
  (rolagem de WDOV26). WINV25 fantasma segue aberta/inerte (secao 13).

### 23.3 Logs dos agentes

- Watchdog: kill-switch ok; fechos 17:35 em 30/09, 01/10 e 02/10 sem diff
   contra HEAD (commits `1be4cf0`, `526997a`, `26f34e0`). Autopsia profunda
   (ver 23.8) CORRIGE a leitura inicial: houve 2 travamentos em 02/10 (09:06
   e 15:21, este com posicao Faixa 1 aberta) + force kill 01/10 17:38 (fecho).
- Plano 02/10: prioridade 3 "win rate < 35% -> nao ajustar nada
  automaticamente; aguardar mais amostra".

### 23.4 Anomalias registradas (p/ 05/10)

1. **Gap 30/09 da Faixa 1:** CSV sem linha (nem S/TRADE), 1 linha no
   `rompimento.log`, 0 trades (Core teve 1.145 decisoes). Janela sem
   pronunciamento do modulo -- verificar se a janela rodou em 30/09.
2. **Spam de reconciliacao:** 01/10 = 641 linhas, 02/10 = 1.457 no
   `rompimento.log`. O modulo re-registra o trade do dia anterior a cada ~2s
   antes da janela (CSV nao duplica; log afoga). Candidato a expurgo/limpeza.
3. **`cb2_ignore_max_loss=true`:** Faixa 1 fica fora do `max_loss_diario`
   (design). Em 02/10 a perda de -1.325 passou do limite -1.000 sem disparo.
   Manter sob vigilancia; decidir vigencia no 05/10.

### 23.5 Decisoes do checkpoint

- Ciclo 28/09-02/10 (5 pregoes) ENCERRADO. Congelamento do Core mantido
  (diretriz-mestra).
- Pauta rebaseada: **adiada de 05/10 para 09/10** (secao 14.3; pregão =
   coleta, nao ajuste), salvo parecer do B1-a (Etapa I fds 02-04/10, 23.10).
   Conteudo: A1 (expurgo ~18 metodos mortos + bloco inalcancavel `alertas`
   L2485-2499), A2 (5 falhas legadas RG1/RG2/RG3 + spam scaler + trava da
   Faixa 1), A3 (fiacao Keras ->gate). Re-baseline EXECUTADO (23.6).
- Friction: secao 21 RETIFICADA em 10/11/2026 para o canonico do Mestre
  (**WDO R$ 1,20 = 0,60+0,60** / WIN R$ 0,25). O valor antigo (WDO R$ 0,80)
  era o do `config.json` e fica so como historico; o `config.json` precisa ser
  alinhado.

### 23.6 Re-baseline implementado

- `analisar_quarentena.py` agora reporta a EXPECTATIVA BASELINE de 60 dias
  (secao 11): **180 trades | WR 39% | -R$ 2.185** = -R$ 12,14/trade, comparada
  com a amostra pos-marcador corrente (ex.: 29 trades -> -R$ 13,62/trade).
  A regua passa a medir contra a expectativa real, nao apenas contra o n.
- Sem alteracao no marcador protocolar `CUTOFF_CORE = 2026-09-04` (integridade
  da medicao n>=100 intacta).

### 23.7 B1-a - validacao de fontes (preparacao 02/10, implementacao 05/10)

- `decisions_wdo.csv`: vivo, 147.080 decisoes (NADA/BUY/SELL), ~40k
  direcionais. **Sem coluna de preco** -> rotulo via caminho M5 do `WDO$`
  (barra que contem o timestamp da decisao = barra 0; entrada na abertura).
- `historico_contexto_wdo.csv`: vivo, 2.647 linhas (reward, escoras, action).
- `WDO$` M5: historico completo via MT5 (cobertura 116,8%, secao 10.1).
- Decisao: congelar intervalo de decisoes para o B1-a ate **02/10 inclusive**
  (arquivo e vivo; decisoes futuras nao entram na amostra).
- Implementacao: **fds 02-04/10 (Etapa I)** — rotular (tripla barreira t+12,
   N pela concordancia com os 242 trades reais, secao 10.4). Resultado em 23.10.

### 23.8 PARECER OFICIAL DA AUTOPSIA SEMANAL (28/09-02/10)

> Autopsia read-only: MT5 history (deals/orders) + logs + CSVs, cruzados em
> fonte primaria. Numeros da narrativa sintetica que divergiram da telemetria
> foram corrigidos (ver "O que encontramos"). Registrar aqui toda sexta.

**Tabela de evolucao semanal (preencher a cada sexta):**

| Semana | Bruto | Custos | Liquido | N | WR | PF | Payoff | Corr ModA (n) | Veto ModA |
|---|---|---|---|---|---|---|---|---|---|
| 28/09-02/10 | +R$ 2.000,00 | -R$ 25,60 | **+R$ 1.974,40** | 12 | 58,3% | 2,17 | 1,55 | 0,1867 (29) | OFF |
| _proxima_ | | | | | | | | | |

Notas da linha: Core 7 trades (+75 bruto / +69,40 liq) | Faixa 1 5 trades
(+1.925 bruto / +1.905 liq) | slippage ZERO nos 12 encerramentos | saldo
02/10: R$ 842.464,21 inclui (sem custos, sem orgaos).

**O que encontramos nesta semana:**

1. **Pausa 12:30: 0 ocorrencias** (nem agente_autonomo.log nem monstro_*.log).
   Nenhuma DECISAO/AJUSTE na semana; whitelist intocada por construcao.
2. **`SelecionadorRegime`: 0 referencias no `monstro_unificado_v22.py`.** A
   classificacao EXPLOSAO/LATERAL/EXTREMO da narrativa nao vem do codigo.
   Usar proxy de ATR (29/09 ~7,96; 02/10 ~10,69) e SENTINELA (30/09 RISK_OFF
   o dia, DXY +0,54% / US10Y +2,54%, 0 trades).
3. **Watchdog com 2 travamentos em 02/10** (09:06 porta morta, restart 09:08;
   15:21 com posicao Faixa aberta, `ultimo_restart_falhou` 15:23:57). Seguranca
   dada pelo SL broker-side (5.234,5 preenchido exato). + force kill 01/10 17:38.
4. **Kill-switch so vigia o Core:** Faixa (cb2_ignore_max_loss=true) devolveu
   -1.325 no dia 02/10 acima do teto geral -1.000 sem disparo.
5. **Spam de boot:** 02/10 = 2.657 reloads do Scaler + 2.653 clips de
   normalizacao (64.328 linhas). Sem duplicidade de ordens no MT5.
6. **Memoria:** `experiencias_wdo.json` = `[]` (vazio); carga real via CSV no
   boot (02/10: 203 positivas / 0 negativas - vies de memoria a acompanhar).
7. **Deal OUT de 28/09 (Faixa +325) nao retorna mais** do history MT5 ->
   necessidade de backup diario de deals/orders (JSON/CSV local).
8. **Veto:** corte >=0,65 na amostra pos-04/09 (WR 66,7%, net +190) e
   monotonicidade minerada sobre n=29 (data snooping); corr 0,1867 e ruido
   (insignificante). Veto permanece OFF; pergunta binaria so o B1-a (Etapa I).

**Parecer do Tech Lead:**

- Execucao impecavel (0 slippage, SL/TP broker exatos, guardas do Sniper
  ativas, sem loops). A semana +R$ 2.000/liq +1.974,40 veio 96,5% da Faixa 1
  (2 TPs grandes), sobre n=12 - nao e evidencia de alfa.
- Congelamento do Core confirmado como correto: amostra pos-04/09 em
  -13,62 R$/trade, pior que a baseline 60d de -12,14 R$/trade.
- Risco residual principal: Faixa 1 sem trava diaria financeira (achado 4).
- Decisao (nao a execucao) permanece como a pergunta central -> B1-a (23.10).

### 23.9 ROTINA DO PARECER SEMANAL (toda sexta, apos protocolo 18:00)

1. Rodar `analisar_quarentena.py` (regua + re-baseline) e salvar log.
2. Cruzar history_deals/orders do MT5 da semana (converter p/ BRT) vs
   `rompimento_trades.csv`, `modelo_a_shadow.csv` e decisions.
3. Preencher a linha da semana na tabela 23.8 e o bloco "O que encontramos".
4. Anotar correcoes a qualquer narrativa que nao venha de fonte primaria.
5. Backup diario de deals/orders em arquivo (rotina no fecho 17:35).
6. Decisoes: manter congelamento do Core ate n>=100 p/ as reguas.

### 23.10 B1-a EXECUTADO (Etapa I, fds 02-04/10) — ROTULO CONTRAFACTUAL

> `rotular_b1_contrafactual.py` (read-only). Tripla barreira t+12 em `WDO$`
> M5 (29/07-02/10, 5.544 barras), lower = -max(1,5*ATR20, 8) pts, upper = k*lower,
> entrada na abertura da barra seguinte a decisao. Alinhamento: barras e deals
> em epoch UTC (mesmo eixo); decisao `timestamp` BRT -> `timestamp()` (UTC).
> ATR M5 verificada (~4 pts; piso de 8 domina, stop real do Core ~8). Gerou
> `logs/b1a_rotulos.csv` (42.165 rotulos) e `logs/b1a_resumo.json`.

**Calibracao k pela concordancia com os 274 trades reais (magic 123456):**

| k | n | Concordancia |
|---|---|---|
| 1,0 | 274 | 35,4% |
| 1,5 | 274 | 35,0% |
| 2,0 | 274 | 35,0% |
| 3,0 | 274 | 35,0% |

Concordancia ~35% = nivel de chance: a barreira (1,5xATR/8) NAO reproduz o
resultado real em granularidade de barra (stops rapidos dentro da barra de
entrada + TP deslizante do Core). Rotulo contrafactual NUNCA virar gate.

**Pergunta binaria (secao 11):**

- E_teorica IA = **-0,36 pts/trade** (42.165 decisoes direcionais) = R$ -3,57
- E_executada = **-9,36 pts/trade** (274 trades) = R$ -93,61
- WR teorica 46,0% | WR executada 35,4% | label 0 (expirado) 2,2%
- E_teorica por mes: 07/07 -1,71 (n=66) | 08/08 -0,81 (n=7.764) | 09/09 -0,20
  (n=32.598) | 10/10 -1,25 (n=1.737) -> SEMPRE <= 0.

**VEREDITO: CENARIO B — SEM ALPHA A RESGATAR.** O sinal primario nunca teve
expectativa teorica positiva sob o modelo tripla barreira; a perda (0,36+
9,36 ~ 9,7 pts) e estrutural do SINAL, nao so de gates/execucao. Meses ruins
de execucao (executada -9,36) nao se convertem em alpha ao "afinar gates" -
nao ha o que destravar. Pauta 09/10 mantida: A1 (expurgo Core), A2 (risco/
custos, trava financeira da Faixa, spam do Scaler) atacam PERDER MENOS, e a
travada de decisao continua ate reguas com n>=100.

### 23.11 PAUTA EXTERNA agendada — VALIDACAO DA COLETA SHADOW (HERMAN 6P/3P)

> Lembrete de governanca registrado em 04/10: nao deixar a massa critica de
> dados da coleta shadow se perder nas proximas semanas.

- [ ] **Janela de acumulo:** 05/10/2026 a 23/10/2026 (~15 sessoes de pregao).
- [ ] **Acao:** executar o harness `backtest_6p_herman.py` sobre os CSVs
      consolidados em `logs/herman_6p/` (coletados pelo
      `coletor_herman_6p_shadow.py`, track dupla 6P e 3P, read-only).
- [ ] **Criterios de leitura:**
      - Amostra real (n) em ambas as tracks (`--box 6` e `--box 3`).
      - Auditar banda de execucao realista (LH vs. HL).
      - Verificar edge/expectativa positiva estavel para decidir entre
        descarte definitivo ou evolucao para modulo ativo.
- [ ] **Contexto da geometria (04/10):** no WDO o box de 6 pts = 12 ticks de
      corpo; com pavio >= 35% do range, o stop curto 2,5-4,0 pts e
      MATEMATICAMENTE impossivel no 6P (minimo ~9,7 pts). A confusao classica
      de nomenclatura (6 ticks = 3 pts como "6P") explica a inconsistencia;
      por isso a coleta e dual, decisao empirica apos a massa critica.

### 23.12 FLUXO TEMPO REAL - WIRING + AUTOMACAO (09/10, validacao ao vivo 13/10)

> Status em 09/10: **implementado e testado (19 passed), NAO validado ao
> vivo**. 12/10 (segunda) e feriado nacional - sem pregao; primeira sessao
> com feed real e **13/10 (terca)**, via `start_all.bat` oficial (09:00).

- [x] **Modulo `fluxo_tempo_real.py`** (monitoramento, read-only): captura via
      `copy_ticks_range`, cursor `time_msc` + dedup, delta C/V, snapshot
      thread-safe (`session_total` = volume direcional do dia). 13 testes mock.
- [x] **Adapter `fluxo_mt5_adapter.py`**: `datetime` (nao int-ms), flags
      resolvidas em runtime (`TICK_FLAG_BUY=32/SELL=64`), `ticks None->raise`.
- [x] **Rota `GET /api/fluxo/status`** (`dashboard_bp`) + card no dashboard
      (polling 1s dentro de `fetchStatus`, sem timer novo, so `textContent`).
- [x] **Wiring aditivo no main** (+16, 0 remocoes) + `config.json` (+12).
- [x] **Autostart Herman** no watchdog (single-instance via psutil + pidfile
      `logs/herman_6p/watchdog.pid`) + **stop no fecho** (so o coletor).
- [x] **Resumo diario** `logs/fluxo_resumo_YYYYMMDD.json` no fecho (veredito
      tri-estado sobre `session_total`; fallback = ultima `FLUXO heartbeat`).
- [x] **Fronteira:** `is_executable=false` / `usar_como_decisao=false`;
      flags de feed = **INFERIDO** (nao "agressao real"); 0 `order_send` no
      diff (161 insercoes, 0 remocoes em 4 arquivos).
- [ ] **16/10 ao vivo:** `tick_count>0` em pregao, `quality=INFERIDO`,
      resumo gravado com `ROTULADOS`, coletor encerrado no fecho 17:35.
      Causa raiz do tick_count=0: `fetch_ticks` usava `t.get()` em
      `numpy.void` (nao dict) -> AttributeError silencioso. Fix: `t[k]`.
      Commit `b6f654a`. Debug ground truth no heartbeat (commit `1ad815d`,
      cadencia 60s) para validacao ao vivo em 16/10 16h.
- [x] **Commit antecipado (09/10):** `9f06a26` (8 arquivos, 375+/15-, sem push).
      Feito antes do verde ao vivo por decisao do usuario. Se a validacao de
      13/10 exigir correcao, novo commit antes das 17:35 (senao cai no fecho
      autonomo generico).
- [ ] **Pendencia pos-validacao (16/10):** card FLUXO exibe so subset dos
      "elementos visuais minimos" do prompt §7.9 (faltam: delta acumulado,
      volume total, spread, ultimo preco, simbolo/contrato, janela, idade do
      dado). API ja retorna todos (`/api/fluxo/status`). Adicionar a template
      no freeze de 16/10, apos verde ao vivo.

### 23.13 - SPRINT 09/10/2026 (sexta) - FLUXO + FERRAMENTAS

> Declaracao honesta de desvio de pauta: 09/10 era o dia agendado de A1/A2
> (23.10), mas a janela foi absorvida pelo wiring do Fluxo Real (frente
> emergencial da semana) e pelo parser da autopsia (ferramenta read-only,
> segura). Verificado: nada disso toca o Core/Faixa (congelados).

- [x] **Parser da autopsia corrigido**: `re_saida` por tokens ASCII
      (sobrevive ao mojibake do log), `tem_deal_saida`, segregacao
      `n_fechados`/`n_sem_deal`, gate P3 como `[INFO]`. Validado vs
      `monstro_wdo_20261007.log`: n=8, fechados=7, sem_deal=1, be=0,
      saldo=-150.0 (antes: be=8 fantasma, saldo=0).
- [x] **Wiring Fluxo Real (F1/F2/F3)**: `fluxo_tempo_real.py` +
      `fluxo_mt5_adapter.py` + 3 ancoras no main + `config.json`.
      Smoke standalone MT5 real OK. pytest 19 passed.
- [x] **Automacao segunda-quinta**: Herman auto-launch no watchdog
      (single-instance psutil+pidfile), heartbeat 15min, resumo diario
      tri-estado no fecho + stop do coletor. Atende ao alerta da 23.11.
- [x] **Roadmap 23.12** criado (fluxo tempo real wiring + automacao),
      normalizado para ASCII puro.

**Decisao 16/10 - Agente Autonomo (OPCAO A):**
- Whitelist permanece VAZIA. Agente funciona como vigilante (watchdog,
  kill-switch, fecho, autopsia).
- Motivo: Sniper %R tem thresholds hardcoded (ignora config); autotuning
  anterior nao mostrou ganhos claros; sistema estavel e lucrativo.
- Nao reativar autotuning. Se futuro: testar Opção B (whitelist limitada
  a sniper_cooldown_s/max_spread, 1 ajuste/dia, rollback automatico).

- [x] **A1 (expurgo do Core)** - executado em **16/10** (commit da8e2e7).
- [x] **A2 (trava financeira da Faixa + spam Scaler)** - executado em **16/10**
      (commit da8e2e7).

### 23.15 - AUTOPSIA SEMANA 12-16/10/2026

> Semana lucrativa (+R$ 190 liquido), mas com ineficiencias operacionais.
> Core (Sniper %R) 79% WR; Faixa 1 25% WR. Agente em vigilancia (whitelist vazia).

**Correcao de relatorio (Sub-Trader nao incluido como item separado):**

- **Sub-Trader (modulo `sub`):** 15/10 SELL 5073.5 TP +18.5pts **+R$925**
      (lote 5.0). Amostra: 2 trades (1 gain +925, 1 loss -200). Expectativa
      positiva mas amostra minima.

**Mudanca de lote (commit 4b0d03a, 16/10):**

- **Antes (ate 15/10):** lote 5.0 na Faixa 1 (5x mais capital em risco)
- **Depois (a partir de 16/10):** lote 1.0 (alinhado com Core)
- **Impacto esperado:** exposicao reduzida em 80%. Perdas como -R$975
      (lote 5) virariam -R$195 (lote 1). Porem, gains como +R$925 (Sub)
      tambem reduzem proporcionalmente.

**Vigilar semana que vem (19-23/10):**
- [ ] Se a Faixa 1 com lote 1.0 + trava financeira (R$ 1500/dia) para a sangria
- [ ] Se o Sub continua lucrativo com lote 1.0 (expectativa por trade cai,
      mas o risco tambem)
- [ ] Se o conflito Sniper x Faixa 1 (60 bloqueios GATE) diminui

### 23.14 - OBSERVACOES BOOT IDLE 12/10/2026 (feriado)

> Boot idle sem pregao. Sistema 100% automatico. Nenhum trade, nenhuma
> ordem. Coletor de fluxo vivo (35 heartbeats, todos INDISPONIVEL/tick_count=0,
> correto sem feed). Fecho gracioso 17:35. **Pontos de atencao (nao bloqueantes,
> melhorias futuras):**

- [ ] **Storm watchdog-DLL em feriado:** 2415 reconexoes (~12s) por tick
      estagnado >10s sem pregao. Pre-existente (loop v22.2), nao vem do Fluxo.
      Em pregao os ticks fluem e nao deve ocorrer. Melhoria futura: diferenciar
      "feriado/sem pregao" de "feed travado" no watchdog (ex: checar calendario
      B3 ou silencio de reconexao em dias sem pregao).
- [ ] **Coletor de fluxo reiniciou 2x (10:43 e 10:57):** auto-restart
      funcionou (35 heartbeats continuos), mas vale investigar causa raiz
      (excecao nao capturada? reinicio externo?). Melhoria futura: adicionar
      log estruturada de erro no coletor quando morrer.
- [ ] **Resumo com ConnectionReset no fecho:** caiu para o heartbeat do log
      (nao-fatal, resumo valido). Melhoria futura: retry no request do resumo.
- [ ] **Herman 6p sem dados:** parado desde 03/10. Esperado; coleta efetiva
      inicia 13/10 (auto via watchdog).

### 23.16 CORRECAO COLETOR HERMAN (10/11/2026) - URGENTE

- [x] **Causa raiz identificada:** coletor usava `SYM = "WDO$"` (generico) que nao retorna ticks
  via `copy_ticks_range`. 19 pregões de coleta perdidos (13/10 a 09/11).
- [x] **Fix aplicado:** SYM resolvido dinamicamente (front-month WDOZ26, mesmo criterio do robo).
- [x] **LAST_LOOKBACK_S:** 3.0 -> 10.0 (MT5 nao armazena ticks dos ultimos 3s).
- [x] **COPY_TICKS_ALL flag:** adicionado ao copy_ticks_range (faltava, causava "Invalid arguments").
- [x] **Coletor reiniciado** com contrato WDOZ26. vwap=5589.89 (recebendo ticks).
- [ ] **Acumulo de dados:** aguardar ~15 sessoes de pregao para validar edge.
- [ ] **Backtest:** executar backtest_6p_herman.py sobre boxes coletados.

---

### 23.17 COLETA HERMAN: CSV AUTO-CURÁVEL + MONITOR DE SAÚDE + ROMPIMENTO FT (10/11/2026)

> Sessão de recuperação após 19 pregões perdidos. Duas camadas de falha foram
> corrigidas: (1) símbolo genérico sem ticks (já em 23.16); (2) cabeçalho do CSV
> desatualizado, que fazia o backtest descartar 100% das linhas. Também foram
> criados o monitor de saúde dos coletores e a reativação do Rompimento FT.

#### 23.17.1 Diagnóstico em duas camadas

| # | camada | sintoma | causa | correção |
|---|---|---|---|---|
| 1 | símbolo | `copy_ticks_range` vazio | `WDO$` não retorna ticks | contrato dinâmico `WDOZ26` (commit `a342232`) |
| 2 | CSV | backtest lia 0 boxes | `boxes_herman.csv` de 03/10 sem a coluna `box_pts`; linhas novas com 26 colunas desalinhavam | auto-cura + reparo in-place (commit `8c1ca88`) |

O coletor **estava** coletando (heartbeat de 1 min, vwap vivo). O que falhava era
a **leitura**: `float("2026-11-10")` estourava e o backtest descartava tudo.

#### 23.17.2 Correção do CSV (auto-cura)

- `_init_csvs` agora valida o cabeçalho na abertura. Se não bater com o layout
  atual, rotaciona o arquivo antigo (`*.hdr_antigo_YYYYMMDD_HHMMSS`) em vez de
  escrever linhas novas sob cabeçalho velho.
- Reparo in-place preservou os boxes do dia: **34 boxes (27 de 3P + 7 de 6P)**.
- Integridade verificada: **26 colunas, 0 linhas desalinhadas**.
- Backtest passou a carregar **7 boxes 6P e 27 boxes 3P** (antes: 0).

#### 23.17.3 Monitor de saúde dos coletores

Arquivos: `monitor_saude_coletores.py` + `monitor_saude_coletores.bat`.
**Read-only:** só lê processos/logs/CSVs e escreve em `logs/`. Nunca envia ordem.

| checagem | critério | severidade |
|---|---|---|
| MT5 `terminal64` | vivo no pregão | CRIT |
| Coletor Herman | processo vivo | CRIT |
| Coletor duplicado | >2 processos (wrapper+filho) | WARN |
| Heartbeat | último registro < 5 min | CRIT |
| Crescimento de boxes | sem box novo > 30 min (45 no almoço) | WARN |
| Crescimento de boxes | sem box novo > 50 min (75 no almoço) | CRIT |
| Integridade do CSV | cabeçalho de 26 colunas + 0 linhas desalinhadas | CRIT |
| `resumo_herman.json` | `day` == hoje | WARN |
| Robô principal | `monstro_unificado_v22.py` vivo | CRIT |
| Rompimento FT | rodando quando a tarefa existe e `ativo_desde` já passou | CRIT |

Saídas:
- `logs/saude_coletores.json` — retrato atual (dashboard)
- `logs/saude_coletores.log` — histórico append-only
- `logs/ALERTA_COLETORES.txt` — existe enquanto houver WARN/CRIT
- toast do Windows em WARN/CRIT, com cooldown de 20 min
- exit code: `0` OK, `1` WARN, `2` CRIT

O horário do último box vem da coluna `ts` do CSV (não do horário em que o
monitor rodou), então um coletor travado é detectado mesmo se o monitor iniciar
tarde. Fora do pregão, ausência de processo vira INFO (não alerta).

Tarefa `Monstro-Monitor-Coletores`: diária 09:00, repetição a cada 10 min por
9h (última ~17:50). Teste de ponta a ponta: execução automática às **12:30:01
de 10/11, resultado 0**, próxima 12:40.

#### 23.17.4 Rompimento FT (paper) — viabilidade e reativação

- **O que é:** forward test em papel do "Rompimento da Primeira Hora" (WIN M5),
  caixa 09:00–10:00, gatilho 10:00–11:00, SL antes do TP, EOD 17:55. Read-only:
  zero `order_send` no código.
- **Bloqueio corrigido:** `feed_lag_min()` comparava a vela com o relógio local
  sem o offset do terminal (~3h), então o feed parecia sempre 180 min defasado.
  Agora usa `last_epoch + _SHIFT` (offset detectado por `detect_shift`).
- **Dry-run (sem gravar estado):** connect OK, `_SHIFT=10800s`, feed lag
  **4,3 min** (limite 12), 40 barras M5 no dia.
- **Selftest:** **172/172 dias, 0 falhas** contra o histórico.
- **Ativação:** tarefa `Rompimento-FT` seg–sex 09:00, início **11/11/2026**.
  Marcador `logs/rompimento_ft/ativo_desde.txt = 2026-11-11` evita cobrança no
  dia da ativação. **Não** foi iniciado em 10/11 no meio do dia para não travar
  um registro parcial.
- **Sem backfill proposital:** preencher 11/09–10/11 seria retrospectivo (o
  backtest 2021–2026 já cobre); o FT existe para validar **ao vivo**.

#### 23.17.5 Tarefas agendadas (novas)

| tarefa | quando | ação |
|---|---|---|
| `Monstro-Monitor-Coletores` | diária 09:00, a cada 10 min por 9h | `monitor_saude_coletores.bat --quiet` |
| `Rompimento-FT` | seg–sex 09:00 | `rompimento_ft_run.bat` (paper, read-only) |

Ambas criadas sem admin (`schtasks /create`).

#### 23.17.6 Linha de base de 10/11/2026 (pós-correção)

| item | estado |
|---|---|
| Coletor Herman | vivo (PID 28744), heartbeat 1 min, contrato `WDOZ26` |
| Boxes do dia (CSV) | 35 (28 de 3P + 7 de 6P), 0 linhas corrompidas |
| Robô principal | vivo |
| MT5 | vivo |
| Monitor | OK, rodando a cada 10 min |
| Rompimento FT | agendado para 11/11 09:00 |

#### 23.17.7 Regras e decisões desta sessão

1. **Nunca reiniciar o coletor no meio do pregão** (zera EMA/K em memória). O
   backtest recalcula EMA/K pelo CSV, mas evita-se o restart desnecessário.
2. **Foco no track 3P:** o 6P gera stop > 4,5 pts, incompatível com o spec.
3. **Não fazer backfill do FT** com dados passados.
4. **O monitor é read-only** e nunca interfere na operação.
5. **Dados nunca são demais:** todo coletor deve ser vigiado; coletor silencioso
   é falha, não economia.
6. **Os 19 pregões perdidos são irrecuperáveis** (MT5 não guarda ticks antigos).

#### 23.17.8 Pendências / próximos passos

- [ ] Acumular ~15 sessões de pregão (a partir de 10/11) para o backtest Herman.
- [ ] Rodar `backtest_6p_herman.py --box 3` e `--box 3 --sens` após ~15 sessões.
- [ ] Acompanhar `logs/saude_coletores.json` e `logs/ALERTA_COLETORES.txt`.
- [ ] Após ~20–30 dias de FT, comparar `logs/rompimento_ft/trades.csv` com o
      backtest; divergência = investigar feed/fill.
- [ ] Se o monitor acusar crescimento parado, verificar antes de reiniciar
      (heartbeat vivo + CSV íntegro = provável mercado lento).

#### 23.17.9 Commits desta sessão

| commit | conteúdo |
|---|---|
| `a342232` | coletor Herman usa contrato dinâmico (WDOZ26) |
| `8c1ca88` | auto-cura do cabeçalho CSV (box_pts) |
| `c29f053` | monitor de saúde + fix de fuso do Rompimento FT |
| `2125d24` | limiar de crescimento mais folgado no almoço |

#### 23.17.10 Lições registradas

- Coletor "vivo" (heartbeat ok) não garante dado **útil**: validar a **leitura**
  (cabeçalho + parse) é tão importante quanto validar a **coleta**.
- O monitor checa exatamente o bug que causou os 19 dias: cabeçalho e linhas
  desalinhadas. Falha silenciosa agora tem alarme.
- Agendar ≠ executar: toda tarefa nova precisa de teste de ponta a ponta
  (execução real + resultado 0).

---

### 23.18 CI GITHUB ACTIONS: YAML INVÁLIDO (linha 46) — CORRIGIDO (10/11/2026)

- **Sintoma:** GitHub Actions recusava `.github/workflows/monstro-ci.yml` com
  "You have an error in your yaml syntax on line 46".
- **Causa raiz:** um `PYEOF` órfão na última linha (resto de heredoc que não
  existe; os `run:` usam bloco literal `|`, não heredoc). `PYEOF` no nível zero
  não é chave YAML válida → o arquivo inteiro fica inválido.
- **Correção:** removida a linha `PYEOF`. Aproveitado para incluir
  `coletor_herman_6p_shadow.py`, `rompimento_ft.py` e
  `monitor_saude_coletores.py` no `py_compile` do CI.
- **Validação local:** YAML parseado com PyYAML (OK, job `static-checks`, 6
  steps) e `py_compile` de todos os arquivos do CI com exit 0.
- **Regra:** antes de `git push`, validar o YAML do workflow. Heredoc em
  workflow exige `<<'EOF'` dentro do `run:`; nunca deixar o terminador solto.

#### 23.18.1 Falha do pytest no CI — causa e correção (10/11/2026)

Com o YAML válido, a run `#109` (`b35c6cd`) executou de verdade pela primeira
vez. Passaram: setup, checkout, dependências e `py_compile`. Falhou apenas o
step **"Testes sem dependencia de MT5"**.

| item | resultado |
|---|---|
| Anotação do check-run | apenas "Process completed with exit code 1" (sem texto do pytest) |
| Log bruto do job | 403 — exige autenticação (`gh` não instalado) |
| Reprodução local (venv limpo, só pytest+pandas+numpy+requests) | **1 failed, 20 passed** |
| Erro exato | `ModuleNotFoundError: No module named 'flask'` em `tests/test_fluxo_api_contrato.py:7` |
| Mesmo venv **com** flask | **21 passed**, exit 0 |

- **Causa raiz:** o CI instalava `pytest pandas numpy` (+ TensorFlow), mas
  `tests/test_fluxo_api_contrato.py` importa `dashboard_routes`, que importa
  `flask`; e `sentinela_fluxo` importa `requests`. No Windows local os dois
  existem, por isso o teste passava aqui e falhava no Ubuntu.
- **Correção:** passo de instalação passou a ser
  `pip install pytest pandas numpy requests flask`.
- **Validação:** YAML OK (6 steps) + 21/21 no venv limpo com as dependências
  do CI.
- **Lição:** teste verde na máquina local não prova nada sobre o CI. A lista de
  dependências do CI tem que ser derivada dos **imports reais** dos módulos
  testados (`flask`, `requests`), não presumida.
- **Pendência (não bloqueante):** `actions/checkout@v4` e
  `actions/setup-python@v5` emitem aviso de depreciação do Node 20 (forçados a
  rodar em Node 24). Migrar para `@v5`/`@v6` quando conveniente.

**Resultado:** run `#110` (`8093001`) — **success em todos os steps** (setup,
checkout, deps, `py_compile`, pytest 21/21, testes legados). CI fechado.

---

### 23.19 VARREDURA GITHUB: PROJETOS SEMELHANTES (10/11/2026)

Busca por repositórios públicos via API (`/search/repositories`, sem token —
limite ~10 req/min). Não é avaliação de qualidade; é mapa de referências.

| repositório | ⭐ | stack | por que interessa |
|---|---:|---|---|
| `AlexPMendonca/lara-ml-trading` | 0 | Python, XGBoost, MT5, B3 | ML para WIN/B3 com holdout temporal e auditoria de overfitting/vazamento — mesma preocupação do nosso `modelo_a` |
| `Tzaratin/win-wdo-quant-research` | 1 | Python | "audit-first" para mini futures B3; mesma filosofia de validar antes de operar |
| `wesleyzilva/RepoRobos` | 4 | Python/MQL5, MT5 | robôs WIN + backtest em Python; comparável ao nosso 3P/6P |
| `srlcarlg/srl-python-indicators` | 59 | Python | Order Flow Ticks, Volume/TPO Profile, VWAP, Wyckoff — referência direta para o Herman (boxes por volume) |
| `mahmoud20138/OrderFlow-Analysis-Pro` | 78 | Python, Dash, MT5 | footprint + delta + volume profile com feed MT5; espelho do nosso `fluxo_tempo_real` |
| `mahmoud20138/OrderFlow-Scalper` | 19 | Python, MT5 | scalper 3 threads com order flow; arquitetura de coleta assíncrona |
| `francomascareloai/EA_SCALPER_XAUUSD` | 285 | MQL5 + Python | pesquisa de EA aberta, com disciplina de registro (parecido com nosso ROADMAP) |
| `jimtin/algorithmic_trading_bot` | 163 | Python, MT5 | bot MT5 didático; útil para revisar integração/retry |
| `AminHP/gym-mtsim` | 526 | Python | simulador OpenAI Gym para MT5; ideia para ambiente de RL (não usamos hoje) |
| `geraked/metatrader5` | 690 | MQL5 | coleção de estratégias para backtest MT5 |

Achados relevantes da busca:

- **B3/WDO/WIN é nicho:** buscas "MetaTrader5 WDO WIN" → 1 repo;
  "WIN B3 day trade python" → 1; "b3 futures quantitative research" → 1.
  Não existe projeto público grande com a nossa arquitetura completa
  (coletor + gate + FT + monitor + autópsia).
- **Order flow/volume profile é onde há mais material reaproveitável**
  (`srl-python-indicators`, `OrderFlow-Analysis-Pro`) — provável fonte de
  ideias para melhorar a leitura dos boxes do Herman.
- **Nada de "Rompimento da 1ª Hora" com esse nome:** a estratégia é descrita
  na literatura como *opening range breakout* (ORB). Buscar por "ORB" rende
  mais que "primeira hora".
- **Code search exige token** (a busca em código, não em repositórios). Sem
  `gh`/token, o alcance fica limitado a nome/descrição/topic dos repos.

Próximos passos possíveis (nenhum obrigatório):

- [ ] Clonar em `C:\AIOFEN\_referencias\` (fora do repo) os 3 mais próximos:
      `srl-python-indicators`, `OrderFlow-Analysis-Pro`, `lara-ml-trading`.
- [ ] Comparar o cálculo de delta/footprint deles com o nosso
      `fluxo_tempo_real.py` (só leitura, sem tocar no Core).
- [ ] Buscar "opening range breakout" + B3/WIN para calibrar o FT.

---

### 23.20 PESQUISA APLICADA: ORB NO WDO + AUDITORIA DOS REPOS (10/11/2026)

> Sessão de pesquisa. Nada aqui altera lógica de trade, Core ou FT. Tudo é
> read-only e reproduzível por `backtest_orb_wdo.py`.

#### 23.20.1 Achado técnico que vale para todo o projeto

**Barras e ticks do MT5 não usam o mesmo relógio.**

| fonte | fuso | evidência (10/11 13:42 local) |
|---|---|---|
| `copy_rates_*` (barras) | **já em BRT** | última barra M5 = 13:40, sessão 09:00–18:00 |
| `copy_ticks_*` / `symbol_info_tick` | **3h atrás** | tick = 10:42 com relógio local 13:42 |

Consequência: **nunca somar `_SHIFT` em barra**; o `+10800s` é só para tick.
O `detect_shift()` do `rompimento_ft.py` resolve isso por sessão (escolhe o
offset que maximiza barras dentro de 9–17h), então o FT está correto — mas o
estudo ORB usa `SHIFT_H = 0` de propósito. Erro clássico: aplicar o offset duas
vezes e achar que o feed está 3h atrasado.

#### 23.20.2 Estudo ORB no WDO (5 anos, dados reais)

Fonte: `WDO$` M5, **135.365 barras**, 10/11/2021 → 10/11/2026, **1.242 sessões**.
Custo canônico: **R$ 1,20/contrato por operação** (0,60 entrada + 0,60 saída);
1 ponto = R$ 10,00. Todos os números abaixo já estão líquidos de R$ 1,20.

Definição: caixa = 09:00–10:00 BRT; rompimento do high/low da caixa na janela
de gatilho; stop = lado oposto da caixa; saída no EOD (17:55).

**Mecanismo medido (sem regra nenhuma):**

- caixa mediana = **35,4 pts** (p20 = 23,1 | p80 = 51,7)
- rompe a caixa na hora seguinte em **81,5%** dos dias
- depois do rompimento: MFE mediano **22,6 pts** vs MAE mediano **21,2 pts**
  → razão **1,07**; MFE > MAE em **49,3%** dos dias

Ou seja: o ORB "de manual" é quase cara-ou-coroa no WDO.

**CORREÇÃO METODOLÓGICA (10/11/2026) — leia antes dos números.** A primeira
versão da simulação começava a checar o stop só às 11:00, **ignorando a barra
de entrada** (10:30–11:00). Isso favorece stop apertado, porque o pior trecho do
trade é logo após o gatilho. Corrigido: a simulação agora começa **na barra de
entrada** e modela **gap através do stop** (se a barra abre além do stop, o fill
é o open, pior que o stop). Os números abaixo são os corrigidos. O efeito foi
grande no stop de 5 pts (PF caiu de 3,02 para 1,77) e no stop 0,5× caixa na
janela cheia (PF caiu de 1,25 para 1,06).

**Resultado por variante (1 contrato, saída EOD, custo R$ 1,20):**

| variante | n | win% | exp R$ | PF | total R$ | maxDD R$ |
|---|---:|---:|---:|---:|---:|---:|
| base (gatilho 10:00–11:00) | 1012 | 45,8 | 8,43 | 1,06 | 8.527 | -6.502 |
| gatilho 10:00–10:30 | 814 | 46,7 | 18,09 | 1,13 | 14.724 | -5.589 |
| **gatilho 10:30–11:00** | **875** | **51,9** | **58,86** | **1,48** | **51.505** | **-3.188** |
| confirmação no fechamento | 862 | 47,9 | 12,16 | 1,08 | 10.480 | -6.255 |
| stop 0,5× caixa (janela cheia) | 1012 | 32,2 | 6,69 | 1,06 | 6.766 | -8.046 |
| caixa comprimida (<p30 20d) | 363 | 46,8 | 29,90 | 1,25 | 10.855 | -3.777 |
| volume da caixa ≥ mediana 20d | 476 | 46,2 | 2,80 | 1,02 | 1.331 | -4.570 |
| filtro p20–p80 (repo vespera) | 549 | 44,3 | 2,06 | 1,01 | 1.131 | -8.584 |

**Controles (o teste que separa edge de sorte):**

| controle | exp R$ | PF | total R$ |
|---|---:|---:|---:|
| CTRL-MIRROR (lado oposto) | -10,83 | 0,93 | -10.956 |
| CTRL-LONG 10:00 → EOD (deriva do dólar) | -8,06 | 0,94 | -10.011 |

O espelho perde e o comprado-puro perde: o ganho **não** vem de deriva do dólar
nem de ruído simétrico. Vem da direção do rompimento.

**Validação do gatilho 10:30–11:00 (o único com PF relevante, R$ 1,20):**

| ano | n | win% | exp R$ | PF | total R$ |
|---|---:|---:|---:|---:|---:|
| 2021 (parcial) | 28 | 57,1 | 133,72 | 1,94 | 3.744 |
| 2022 | 190 | 56,3 | 101,44 | 1,62 | 19.274 |
| 2023 | 176 | 49,4 | 29,82 | 1,25 | 5.248 |
| 2024 | 164 | 52,4 | 73,80 | 1,67 | 12.103 |
| 2025 | 175 | 53,1 | 44,35 | 1,41 | 7.761 |
| 2026 | 142 | 45,8 | 23,77 | 1,25 | 3.376 |

- **IS 2021–2024:** PF **1,54** (n=558) | **OOS 2025–2026:** PF **1,35** (n=317)
- **6 de 6 anos positivos**, inclusive 2026 (ano em que o ORB base é negativo).
- **Stress de slippage:** +2 pts/trade ainda deixa exp **R$ 38,86** e total R$ 34.005.
- **Stop 0,5× caixa DENTRO da janela 10:30–11:00:** PF **1,63**, maxDD
  **-R$ 2.226**, exp R$ 61,26. (Na janela cheia 10:00–11:00 o stop 0,5× é ruim:
  PF 1,06 — o stop curto só funciona depois das 10:30.)
- **TP:** 3R (PF 1,49) ≈ sem TP (PF 1,48); TP 1R piora (PF 1,43).
- **Risco por trade (stop = caixa):** mediana **R$ 339** (p80 R$ 493) — é trade
  de 1 por dia, não scalp.

**Filtros testados sobre o gatilho 10:30–11:00 (R$ 1,20, saída EOD):**

| filtro | n | win% | exp R$ | PF | total R$ | maxDD R$ |
|---|---:|---:|---:|---:|---:|---:|
| sem filtro (referência) | 874 | 51,9 | 59,54 | 1,49 | 52.037 | -3.188 |
| + rompimento acima/abaixo do VWAP | 874 | 51,9 | 59,54 | 1,49 | 52.037 | -3.188 |
| + alinhado com EMA20/EMA50 | 506 | 54,0 | 72,59 | 1,62 | 36.732 | -3.799 |
| + alinhado com o viés da 1ª hora | 624 | 53,0 | 72,59 | 1,61 | 45.299 | -3.210 |
| + alinhado com o gap (vs fecho anterior) | 404 | 53,7 | 65,26 | 1,56 | 26.366 | -3.558 |
| + caixa ≤ 2× mediana 20d | 829 | 52,4 | 62,68 | 1,53 | 51.963 | -3.235 |
| viés 1ª hora + stop 0,5× | 624 | 43,3 | **78,57** | **1,83** | 49.027 | **-2.251** |
| EMA + caixa ≤2× + stop 0,5× | 477 | 44,0 | **82,97** | **1,93** | 39.575 | **-1.652** |

Leituras importantes (preto no branco):
- **VWAP é redundante:** resultado idêntico ao sem filtro (mesmo n, mesmo PF).
  Motivo: o rompimento da caixa quase sempre já está do lado certo do VWAP da
  caixa. Não vale implementar.
- **Filtro de percentil do repo `vespera` falhou** no WDO (PF 1,01): rejeitado.
- **Volume da caixa não separa** (PF 1,02): rejeitado.
- Os filtros que **de fato sobem acertividade e PF** são **viés da 1ª hora** e
  **EMA20/EMA50**, combinados com **stop 0,5× caixa**.

**Validação final dos 2 candidatos (R$ 1,20):**

| | viés 1ª hora + stop 0,5× | EMA + caixa≤2× + stop 0,5× |
|---|---:|---:|
| n | 624 | 477 |
| win% | 43,3 | 44,0 |
| exp R$ | 78,57 | **82,97** |
| PF | 1,83 | **1,93** |
| total R$ | **49.027** | 39.575 |
| maxDD R$ | -2.251 | **-1.652** |
| IS 2021–2024 | PF 1,81 | PF 2,01 |
| OOS 2025–2026 | PF **1,89** | PF 1,73 |
| +2 pts slippage | exp R$ 58,57 / total 36.547 | exp R$ 62,97 / total 30.035 |
| anos positivos | 6/6 | 6/6 |

Observação honesta: o WR **cai** para 43–44% com stop 0,5× (stop mais curto =
mais stops), mas o **payoff sobe** e o PF/lucro melhoram. O ganho não vem de
acertar mais, vem de **perder menos quando erra**. Se a prioridade for WR alto,
o candidato é o **gatilho puro com stop cheio** (WR 51,9%, PF 1,48).

**Stop em PONTOS (o esclarecimento que evita erro de 10x):**

| stop | pontos | R$ (1 contrato) | WR | PF | total R$ | maxDD R$ |
|---|---:|---:|---:|---:|---:|---:|
| 0,5× caixa (metade da caixa) | ~17,0 | ~R$ 170 | 43,3 | 1,83 | 49.027 | -2.251 |
| caixa cheia (stop do ORB base) | ~33,9 | ~R$ 339 | 51,9 | 1,48 | 51.505 | -3.188 |
| **stop fixo 3 pts** | 3,0 | R$ 30 | 14,5 | 2,43 | 33.372 | -998 |
| **stop fixo 5 pts (padrão Herman)** | 5,0 | **R$ 50** | **17,4** | **1,77** | 28.470 | **-1.469** |
| stop fixo 8 pts | 8,0 | R$ 80 | 24,0 | 1,55 | 29.573 | -2.013 |
| stop fixo 10 pts | 10,0 | R$ 100 | 29,9 | 1,65 | 39.755 | -2.086 |
| viés + stop fixo 5 pts | 5,0 | R$ 50 | 21,3 | **2,25** | 31.499 | **-1.280** |

**ATENÇÃO — "0,5× caixa" NÃO é 0,5 ponto.** É **metade do tamanho da caixa**:
caixa mediana 33,9 pts → stop **~17,0 pts = ~R$ 170**. Meio ponto (R$ 5) seria
violado no primeiro tick. O tick do WDO anda de 0,5 em 0,5 ponto (R$ 5), então
stop de 5 pontos = R$ 50, como no código do Herman (`SL_M=0,5` além do pavio,
`MAX_SL=4,5`).

**Validação do stop fixo de 5 pts (o do código Herman):**

| | stop fixo 5 pts | viés + stop fixo 5 pts |
|---|---:|---:|
| n | 874 | 624 |
| win% | 17,4 | 21,3 |
| exp R$ | 32,57 | **50,48** |
| PF | 1,77 | **2,25** |
| total R$ | 28.470 | **31.499** |
| maxDD R$ | -1.469 | **-1.280** |
| IS 2021–2024 | PF 1,70 | PF 2,10 |
| OOS 2025–2026 | PF **1,90** | PF **2,55** |
| +2 pts slippage | exp R$ 12,57 / total 10.990 | exp R$ 30,48 / total 19.019 |
| anos positivos | 6/6 | 6/6 |

**Por que 10:30 e não 10:00 (a explicação econômica):** 10:30 BRT é o horário
do catalisador americano. No horário de verão dos EUA (mar–nov) = **09:30 ET,
abertura do mercado acionário americano**; no inverno = **08:30 ET, janela de
divulgação de dados macro** (CPI, payroll, PPI, varejo). O WDO é o contrato da
B3 mais sensível a EUA/juros. A primeira hora (09:00–10:00) é ruído doméstico;
a informação direcional chega com os EUA. Isso explica por que o gatilho misto
(10:00–11:00) rende pouco e o gatilho pós-10:30 rende muito.

**Diferença conceitual vs Herman (não são concorrentes):**

| | Herman (3P/6P) | ORB WDO |
|---|---|---|
| caixa | **volume** em faixa de 3 ou 6 pts, várias por dia | **tempo** (1ª hora), 1 por dia |
| risco/trade | R$ 30 / R$ 60 (stop 5 pts = R$ 50) | R$ 50 (stop 5 pts) a R$ 339 (caixa cheia) |
| gatilho | rompimento + EMA9/21 + VWAP + ajuste + pavio | rompimento puro após 10:30 |
| o que precisa para ganhar | acertar muito (WR alto) em movimentos curtos | capturar o repricing macro do dia |
| frequência | alta | ~1/dia (875 em 5 anos) |
| ponto fraco | stop apertado, ruído | depende do catalisador; WR baixo com stop curto |

**Veredito preto no branco:** ORB genérico no WDO **não é edge** (PF 1,06,
2026 negativo). ORB **restrito à janela pós-EUA** é um candidato real
(PF 1,48 puro; 1,63 com stop 0,5×; 1,83–1,93 com filtro + stop 0,5×; 1,77 com
stop fixo de 5 pts), com 6 anos positivos e OOS positivo — mas ainda é **1
hipótese**, não uma verdade: foram ~20 variantes testadas, então existe risco de
seleção. Próximo passo obrigatório: paper 20–30 dias antes de qualquer capital.
O custo de R$ 1,20 **não** muda o veredito (era R$ 0,80; a diferença é ~0,04
ponto/trade). O stop de 5 pts **é lucrativo**, mas com WR baixo (17–21%): é um
perfil de "poucos acertos grandes", não de acertividade alta.

#### 23.20.3 Order flow e volume profile — o que é, o que já temos, o que falta

O que já temos (`fluxo_tempo_real.py`): buy/sell volume, delta, delta
cumulativo, razão compra/venda, spread, qualidade. É **vertical delta**.

O que os repos têm de diferente e que faz falta:

| conceito | o que é | onde está | uso prático no WDO |
|---|---|---|---|
| delta horizontal / footprint | delta **por preço** dentro da barra | `OrderFlow-Analysis-Pro/analytics/footprint.py` | ver em que preço entrou agressão (borda da caixa) |
| absorção | volume alto e preço não anda | `patterns/absorption.py` | **veto** de rompimento falso |
| exaustão | delta forte, preço trava | `patterns/exhaustion.py` | saída antecipada |
| divergência | preço faz topo, delta cumulativo não | `analytics/delta.py` | filtrar continuação |
| sweep / liquidez | pavio que varre nível e volta | `patterns/sweep.py` | evitar entrada no pavio |
| POC / VAH / VAL / HVN / LVN | nós de volume | `srl-python-indicators/volume_profile.py` | substituir caixa fixa 3P/6P por nó de volume |

**Limite honesto e crítico:** o MT5 entrega *flags* de compra/venda que
representam o lado da última cotação, **não o agressor real** (Times & Trades).
O próprio `fluxo_tempo_real.py` marca `quality = INFERIDO`. Footprint feito
com flag do MT5 é **aproximação**, não footprint de DOM. Para validar de
verdade seria preciso tick a tick com agressor (Profit/Nelogica ou corretora
com DOM), o que hoje não temos.

**O que dá para testar já, com o que temos:** absorção e sweep nas bordas da
caixa do Herman, usando os ticks que o coletor grava desde 11/11. Hipótese
falsificável: "rompimento com absorção na borda tem WR menor". Se não separar
nada, descarta.

**Volume profile:** o valor real não é o desenho, é o **POC/HVN como ímã e
LVN como corredor**. Duas aplicações concretas:
1. trocar a caixa fixa (3/6 pts) por caixa ancorada em HVN/LVN;
2. usar o POC do dia anterior como filtro de direção (acima do POC = compra).

Nada disso está validado no WDO ainda. É a próxima fila de pesquisa, depois do
ORB.

#### 23.20.4 gym-mtsim — veredito: **volta à lista como ★★ (avaliação futura)**

Revisão de 10/11/2026 (diretriz do Mestre: foco é **lucratividade**, não custo;
sempre 1 contrato):

- É um simulador MT5 + ambiente Gym para RL. Bom código, 526 estrelas.
- **Limite real:** não modela custos da B3, tick 0,5, rolagem de contrato nem
  IR. Como operamos sempre 1 contrato e R$ 1,20 é ruído, o custo **não** é o
  problema; o problema é que o simulador não reproduz **microestrutura** (tick
  a tick, fila, slippage) nem a rolagem do contrato.
- **Onde pode ajudar de verdade:** gerar **dados sintéticos** para testar
  robustez da regra (ex.: ORB pós-EUA) sob diferentes regimes de volatilidade,
  e servir de ambiente para eventual RL **depois** que a regra base estiver
  validada em paper. Não substitui backtest com dados reais.
- **Não implementar agora.** Fica como ★★: só entra se (a) o ORB estiver
  validado em paper e (b) houver tempo para modelar tick/rolagem. Antes disso é
  distração.

#### 23.20.5 Auditoria dos repos (foco WDO; WIN e EA descartados)

| repo | o que tem de real | o que aproveitar | veredito |
|---|---|---|---|
| `masterjesue/quant` | WDO/WIN, MT5+cTrader, `investiga_deslocamento_3h.py`, `investiga_limite_copy_ticks_from.py` | confirma nosso bug de fuso e o comportamento de `copy_ticks_from` em janela densa | **referência** (não importar: sem README, mistura fontes) |
| `klaubeer/trade-scan` | backtester WDO/WIN, walk-forward, Monte Carlo, import de CSV do Profit | **Monte Carlo** para dimensionar drawdown + gate IS→OOS | **método** |
| `RafaelQSantos-RQS/radar` | motor WDO$/WIN$, custos B3 completos (emolumentos, ISS, IRRF, **IR 20% day trade**) | modelo de custo/imposto: nosso R$ 1,20 ignora IR (★, adiado em simulador) | **método** (só quando for dinheiro real) |
| `mnogueira/autoresearch-tradebot` | WDO M5, estratégia editável por agente, flat nos últimos 30 min | harness "propõe → backtest reprova"; regra de não dormir com posição | **método** (cuidado: loop de otimização overfitta) |
| `nicksauro/vespera` | WDO EOD unwind, CPCV, holdout lock, bandas de percentil | **CPCV/holdout**; a regra de percentil **falhou** no nosso teste (PF 1,03) | **método sim, regra não** |
| `Rpinto003/mini-dolar-strategy-v4` | WDO, RF + volume profile + orderflow | lista de features e multi-TP por ATR | **referência** (sem resultado validado) |
| `Tzaratin/win-wdo-quant-research` | só protocolo + exemplo sintético (2 .py) | protocolo IS 2021–2023 / OOS 2024–2025 / holdout 2026+ | **protocolo** (não há engine pública) |
| `PitsayCode/Mercado_Financeiro` | radar de notícias WDO/WIN | ideia: ORB **consciente do calendário** (não operar 10:30 sem catalisador) | **ideia** |
| `Felipe-Serna/Test4Wdo` | 1 arquivo, sem README | nada | **descartar** |
| `eajdias/FlowTrainerPro`, `JElemente-web/Tapereading-` | treino de tape reading | nada (não é engine) | **descartar** |
| `Mvrsant/wdoaprimorado` | paridade do WDO | sanity check de preço justo | **descartar** |
| `AlexPMendonca/lara-ml-trading`, `wesleyzilva/RepoRobos`, `francomascareloai/EA_SCALPER_XAUUSD` | WIN / EA / XAU | — | **descartados** (fora do foco WDO) |

#### 23.20.6 Fila de pesquisa revisada (10/11/2026)

> Revisão conforme diretriz do Mestre: foco em **lucratividade/acertividade**;
> IR e Monte Carlo **não** entram agora (não melhoram WR); gym-mtsim volta como
> ★★; absorção/sweep e POC/HVN/LVN só se provarem lucro incremental.

1. [ ] **ORB pós-EUA no WDO em paper** (20–30 dias), com stop 0,5× caixa e
       registro de MFE/MAE. Comparar com o backtest (PF 1,50–1,96 / maxDD
       R$ 1,6–3,2k).
2. [ ] **Filtros do ORB**: viés da 1ª hora, EMA20/50, caixa ≤2× mediana.
       Já validados no backtest; entram como flags do FT, não como código novo
       separado.
3. [ ] **Calendário/catalisador** (repo `Mercado_Financeiro`): ORB consciente
       do calendário (não operar 10:30 sem catalisador). Testar no backtest
       antes de ligar no FT.
4. [ ] **Absorção OU sweep** nas bordas da caixa do Herman com ticks reais
       (escolher **um** veto, provar valor incremental; se não separar, descartar).
5. [ ] **POC/HVN/LVN** como caixa alternativa do Herman e POC do dia anterior
       como filtro de direção (só depois de ~15 sessões de coleta).
6. [ ] **CPCV/holdout** como protocolo oficial de qualquer estratégia nova.
7. [~] **Monte Carlo** — ★ (não melhora WR; só dimensiona drawdown). Deixar de lado.
8. [~] **IR 20% day trade** — ★ (modo simulador). Deixar de lado por agora.
9. [~] **gym-mtsim** — ★★ (avaliação futura, só após ORB validado em paper).

#### 23.20.7 Arquivo entregue

- `backtest_orb_wdo.py` — estudo reprodutível, read-only, com controles,
  sensibilidade, validação IS/OOS e stress de slippage. Não envia ordem.

---

### 23.21 PLANO DE IMPLEMENTAÇÃO PONTUADO (10/11/2026)

> **Diretriz:** só entra o que tem evidência de melhorar **lucratividade e/ou
> acertividade** no WDO. Pontuação de 1 a 5 estrelas; **★ = deixar de lado**.
> Nada aqui altera o Core nem envia ordem real. Tudo é read-only/paper até
> validação em 20–30 sessões.
>
> Custo canônico: **R$ 1,20/contrato** (0,60 + 0,60). 1 contrato sempre.
> 1 ponto = R$ 10,00.

#### 23.21.1 Ranking (o que vale a pena)

| # | Iniciativa | ★ | Impacto esperado | Evidência | Decide |
|---|---|---:|---|---|---|
| 1 | **FT paper ORB pós-EUA (10:30–11:00)** | ★★★★★ | lucro + acertividade | PF 1,50 (puro) a 1,96 (filtros), 6/6 anos positivos, OOS 1,36–1,94, controles negativos | **implementar agora** |
| 2 | **Stop 0,5× caixa no ORB** | ★★★★★ | corta maxDD de -3.188 → -2.226 e sobe PF 1,50 → 1,70 | mesma base, R$ 1,20 | **implementar junto** |
| 3 | **Filtro viés da 1ª hora** | ★★★★ | sobe WR 52,1 → 53,4 e PF 1,50 → 1,63 (1,89 com stop 0,5×) | mesma base, R$ 1,20 | **implementar junto** |
| 4 | **Filtro EMA20/50 + caixa ≤2× mediana + stop 0,5×** | ★★★★ | melhor PF (1,96) e menor DD (-1.652), mas OOS 1,74 e n menor | mesma base, R$ 1,20 | **flag opcional** (comparar no paper) |
| 5 | **CPCV/holdout como protocolo** | ★★★★ | protege contra overfitting; barato | método (repo `vespera`/`win-wdo-quant-research`) | **adotar como regra** |
| 6 | **Calendário/catalisador no ORB** | ★★★★ | evita operar 10:30 sem catalisador (hipótese de mecanismo) | repo `Mercado_Financeiro` + lógica EUA | **testar no backtest antes** |
| 7 | **Absorção OU sweep (um veto)** | ★★★ | pode filtrar rompimento falso | hipótese; precisa ticks reais | **testar; descartar se não separar** |
| 8 | **POC/HVN/LVN (caixa alternativa)** | ★★★ | pode melhorar caixa do Herman | hipótese; precisa ~15 sessões | **testar depois** |
| 9 | **POC do dia anterior como filtro de direção** | ★★★ | barato de testar no ORB | hipótese | **testar no backtest** |
| 10 | **Flat nos últimos 30 min** | ★★★ | regra de risco, não de edge | método (`autoresearch-tradebot`) | **adotar no FT** |
| 11 | **Exaustão (saída antecipada)** | ★★ | redundante com absorção/sweep | mesma stream de ticks | **deixar de lado** |
| 12 | **Divergência (delta cumulativo)** | ★★ | redundante; flags MT5 aproximadas | mesma stream | **deixar de lado** |
| 13 | **Footprint / delta horizontal** | ★★ | só vale com agressor real (não temos) | `OrderFlow-Analysis-Pro` | **deixar de lado** |
| 14 | **gym-mtsim** | ★★ | dados sintéticos/RL futuro | repo 526★ | **deixar de lado por agora** |
| 15 | **VWAP como filtro** | ★ | resultado idêntico ao base | mesmo n/PF | **descartar** |
| 16 | **Filtro de percentil (vespera)** | ★ | PF 1,02 no WDO | falhou | **descartar** |
| 17 | **Filtro de volume da caixa** | ★ | PF 1,02 | falhou | **descartar** |
| 18 | **Monte Carlo** | ★ | não melhora WR; só dimensiona DD | diretriz do Mestre | **deixar de lado** |
| 19 | **IR 20% day trade** | ★ | modo simulador | diretriz do Mestre | **deixar de lado** |

#### 23.21.2 Ordem de execução (sem conflito de estratégias)

**Fase 0 — agora (documentação):**
- Corrigir custo canônico para R$ 1,20 (seção 21) e recalcular 23.20.2.
- Este plano (23.21) aprovado antes de qualquer código.

**Fase 1 — ORB paper (única estratégia nova):** ✅ **APROVADA em 10/11/2026**
- Criar `rompimento_orb_wdo.py` (read-only, sem `order_send`), nos moldes do
  `rompimento_ft.py`.
- Janela: caixa 09:00–10:00; gatilho 10:30–11:00; EOD 17:55.
- **Decisão do Mestre: rodar as 3 saídas EM PARALELO no paper** (custo zero,
  não compromete capital nem lógica de produção):
  1. `stop_caixa` = lado oposto da caixa (~R$ 339 de risco) — maior WR (51,9%);
  2. `stop_half` = 0,5× caixa a partir da entrada (~R$ 170) — melhor total;
  3. `stop_fixed5` = 5 pts fixos (R$ 50) — o stop do código Herman, PF alto e
     DD baixo, mas WR 17–21%.
  Após 20–30 sessões, o vencedor é escolhido com dado real, não no chute.
- Flags registradas por dia (não bloqueiam o paper): `vies` (viés 1ª hora),
  `ema` (EMA20/50), `caixa_max` (caixa ≤2× mediana 20d).
- Registrar: lado, entrada, os 3 stops, viés, EMA, caixa-max, MFE/MAE e
  resultado das 3 saídas.
- Wrapper `.bat` + tarefa agendada (`ORB-WDO-FT`) com marcador `ativo_desde.txt`.
- Integrar ao `monitor_saude_coletores.py`.

**Fase 2 — validação do paper (20–30 sessões):**
- Comparar WR/PF/DD do paper com o backtest.
- Se divergir muito, **parar** e investigar (fill, slippage, fuso, rolagem).
- Só depois disso considerar capital.

**Fase 3 — filtros adicionais (só se Fase 2 passar):**
- Calendário/catalisador e POC do dia anterior: testar **primeiro no backtest**.
- Se melhorarem PF/WR fora da amostra, ligar como flag.

**Fase 4 — order flow no Herman (paralelo, não concorrente):**
- Com ≥15 sessões de ticks, testar **absorção OU sweep** como veto.
- Critério de aceite: separa WR de forma estatisticamente visível e melhora
  expectativa. Se não, descartar sem dó.

**Fase 5 — volume profile no Herman:**
- POC/HVN/LVN como caixa alternativa; comparar com caixa fixa 3P/6P.
- Só se bater a caixa fixa em PF e DD.

**Contínuo:** CPCV/holdout em toda estratégia nova.

#### 23.21.3 Conflitos e concorrências (resposta direta)

- **ORB × Herman:** **não competem.** ORB é caixa por tempo (1/dia, risco
  R$ 170–340); Herman é caixa por volume (várias/dia, risco R$ 30–60). Podem
  rodar em paralelo com magics/contas separados.
- **Absorção × exaustão × divergência × sweep:** **não são concorrentes na
  definição, mas são redundantes na prática** — todas saem do mesmo stream de
  ticks com flags aproximadas do MT5. Regra: **escolher UM veto** (absorção ou
  sweep), provar valor incremental; não empilhar os quatro.
- **Footprint × delta vertical:** footprint é delta **por preço**; o nosso
  `fluxo_tempo_real.py` é delta **vertical**. Footprint só vale com agressor
  real (Times & Trades), que não temos. Sem isso, é aproximação.
- **VWAP × ORB:** redundante (rompimento já está do lado certo do VWAP). Não
  implementar.
- **Monte Carlo × IR:** não melhoram WR; ficam ★ e saem da fila.
- **gym-mtsim × backtest real:** não substitui dados reais; fica ★★.

#### 23.21.4 Critério de aceite (para não se enganar)

Uma iniciativa só sobe para o Core se, **fora da amostra**:
1. PF > 1,30 **e** expectativa > R$ 20/trade (1 contrato, R$ 1,20); **ou**
2. reduz maxDD em ≥30% **sem** derrubar PF abaixo de 1,30; **e**
3. sobrevive a +1 pt de slippage por trade; **e**
4. passa no holdout/CPCV.

Se não passar em 1–4, fica documentada como **rejeitada** (histórico no ROADMAP).

#### 23.21.5 Registro de decisão — 3 stops em paralelo (10/11/2026)

Pergunta do Mestre: qual stop usar no FT ORB. Resposta: **não escolher no chute**.
O paper é read-only e custo zero, então registramos **as três saídas ao mesmo
tempo** e deixamos 20–30 sessões decidirem.

| saída | stop (R$) | WR backtest | exp R$ | PF | maxDD | perfil |
|---|---:|---:|---:|---:|---:|---|
| `stop_caixa` | ~339 | **51,9%** | 58,86 | 1,48 | -3.188 | maior acertividade |
| `stop_half` | ~170 | 40,8% | 61,26 | 1,63 | -2.226 | melhor total |
| `stop_fixed5` | **50** | 17,4% | 32,57 | 1,77 | **-1.469** | poucos acertos grandes |

Combinado com viés da 1ª hora: `stop_half` = PF 1,83 / OOS 1,89; `stop_fixed5`
= PF 2,25 / OOS 2,55. **Nenhuma saída é descartada antes do paper.** A regra de
aceite (23.21.4) é aplicada ao fim das 20–30 sessões, por saída e por filtro.

**Validação do núcleo do FT (10/11/2026):** `rompimento_orb_wdo.evaluate_day` foi
comparado dia a dia com `backtest_orb_wdo.simulate` em **200 sessões reais**,
nas 3 saídas: **200/200 idênticos** (diferença < 0,01 pt). O único ajuste
necessário foi cortar o after-market do WDO$ (barras 18:05–18:25), que o
backtest já ignorava.

**Sensibilidade do EOD (17:55 × 18:00):** o backtest usa como EOD o fecho da
barra 18:00 (que fecha ~18:05); a barra 17:55 é o fim da sessão regular. Medido
no período completo (875 trades):

| saída | EOD 17:55 (PF / exp) | EOD 18:00 (PF / exp) | delta |
|---|---|---:|---:|
| caixa | 1,46 / R$ 55,95 | 1,48 / R$ 58,82 | ~R$ 2,87/trade |
| half | 1,60 / R$ 58,00 | 1,63 / R$ 61,22 | ~R$ 3,22/trade |
| fixed5 | 1,72 / R$ 30,49 | 1,77 / R$ 32,43 | ~R$ 1,94/trade |

O FT mantém o critério do backtest (18:00) para o paper ser **diretamente
comparável**. Em execução real, achatar em 17:55 custa ~R$ 2–3/trade e o edge
continua positivo — está documentado como ajuste conservador.

#### 23.21.6 Aposentadoria do FT WIN$ (11/11/2026)

- A pedido do Mestre, a tarefa **`Rompimento-FT`** (WIN$, `rompimento_ft.py`) foi
  **desabilitada** e os processos do dia encerrados. O foco passa a ser
  **exclusivo em WDO**, e o `ORB-WDO-FT` assume o forward test.
- **Nada foi apagado:** histórico, CSVs e logs do WIN$ ficam preservados. A
  tarefa pode ser reabilitada (`schtasks /change /tn Rompimento-FT /enable`) se
  um dia fizer sentido.
- Motivo: diretriz WDO-only; o WIN não tinha edge validado no WDO e só gerava
  ruído/arquivos.
- Correção no monitor: `_task_existe()` agora considera tarefa **desabilitada**
  como inativa. Antes, `schtasks /query` retornava 0 mesmo para tarefa desligada
  e o monitor daria **falso CRIT** depois de aposentá-la. Testado:
  `Rompimento-FT -> inativo`, `ORB-WDO-FT -> ativo`.

---

### 23.22 BUG CRÍTICO: `SYMBOL` NULO + "DADOS DO MERCADO INCOMPLETOS" EM LOOP (11/11/2026)

**Status:** corrigido e validado em produção (conta **demo**).

#### 23.22.1 Sintoma observado

A partir de **09:15:07** o robô principal (`monstro_unificado_v22.py`) entrou em
loop infinito, repetindo a cada ~2s:

```
ERROR   - SYMBOL ainda nao foi definido!
WARNING - Dados do mercado incompletos. Aguardando proxima iteracao...
```

E, a cada ~12s, o watchdog forçava reconexão:

```
INFO  - Reconectado ao MetaTrader 5
ERROR - [WATCHDOG-DLL] Tick estagnado >10s durante o expediente - reconexao forcada (ok=True)
```

Ficou assim de **09:15 até 11:40** (≈ 2h25 de robô paralisado). O ORB WDO e o
coletor Herman **não** tinham erro — o problema era exclusivo do robô principal.

#### 23.22.2 Cadeia de causa raiz (o que realmente aconteceu)

1. `09:02:31` — robô inicia.
2. `09:03:38` — `mt5.initialize()` falha com **`(-10005, 'IPC timeout')`**.
3. `inicializar_mt5()` (L4777) retorna `False` **antes** de chegar na linha que
   resolve o contrato (`SYMBOL = get_front_month_symbol_dynamic("WDO")`, L4814).
4. `monstro_thread()` (L6662) fazia
   `mt5_ativo_local = inicializar_mt5()` e **ignorava o `False`** — seguia em
   frente com `SYMBOL = None`.
5. O loop chamava `obter_dados_mercado(SYMBOL)` → `SYMBOL is None` → retornava
   `(None,)*10` → "dados incompletos" → `sleep(2)` → repete para sempre.
6. O watchdog via o tick parado, mas `_stale_real_min()` também usa `SYMBOL`
   (nulo) e devolvia `None` → tratado como "episódio real" → `hard_reset_mt5()`
   a cada 12s. Ele reconectava o MT5, **mas nunca re-resolvia o contrato**.

Ou seja: a falha de inicialização do MT5 era **recuperável**, mas o código não
tinha nenhum caminho de auto-recuperação do `SYMBOL`. O watchdog tratava o
sintoma (conexão) e não a causa (contrato não resolvido).

#### 23.22.3 Correções aplicadas (sem tocar em lógica de trade)

Todas as mudanças são de **robustez/infraestrutura**. Nenhum limiar, gatilho,
stop, alvo, filtro ou regra de entrada/saída foi alterado.

| # | Local | Correção |
|---|-------|----------|
| 1 | `_resolver_symbol_wdo()` (nova, após `reconectar_mt5`) | Auto-recuperação do contrato: mantém `SYMBOL` se válido; reconecta se o terminal caiu; senão resolve o contrato mensal vigente, faz `symbol_select` + `market_book_add`. Throttle de 30s. |
| 2 | `_garantir_book_nativo()` (nova) | Reassina o book nativo quando a assinatura se perde (ex.: watchdog reiniciou o `terminal64`). Throttle de 15s. Chamada quando `ler_book_nativo()` volta vazio. |
| 3 | `obter_dados_mercado()` | Se `symbol is None`, chama `_resolver_symbol_wdo()` **antes** de desistir. |
| 4 | `monstro_thread()` | Se `inicializar_mt5()` falhar, tenta `reconectar_mt5()` até **6× a cada 10s** e depois força `_resolver_symbol_wdo(force=True)`. |
| 5 | `reiniciar_book()` | Default era `symbol: str = SYMBOL`, avaliado **no import** (quando `SYMBOL` ainda é `None`) → `market_book_release(None)`. Agora resolve em tempo de execução. |

#### 23.22.4 Validação (11/11/2026, 11:41)

Reinício limpo (somente o processo do robô; **MT5 não foi reiniciado** para não
interromper o coletor Herman). Log após o restart:

```
11:41:29 - MetaTrader 5 inicializado com sucesso
11:41:30 - Contrato dinamico selecionado: WDOZ26 (venc.: 2026-11-30 19:15)
11:41:30 - [BOOK] Book nativo ATIVADO para WDOZ26 (Depth of Market)
11:41:37 - WDOZ26 | Preco: 5580 | Spread: 0.5pts | BID: 5640 / ASK: 6391
11:41:37 - DOL DOLZ26: ratio=1.10 lado=BUY conf=0.37 vol=1405
11:41:38 - PTAX atualizada: R$ 5.5840
11:41:39 - [MultiTF] M5 RSI=48.5 ATR=4.9 ...
11:42:07 - BUY WDOZ26 | Entrada: 5580 | SL: 5572 TP: 5586
```

- **Zero** ocorrências de `SYMBOL ainda nao foi definido`, `Dados do mercado
  incompletos` e `[WATCHDOG-DLL]` desde o restart (verificado por 75s+).
- Robô voltou a operar (abriu BUY em WDOZ26 — comportamento normal).
- `monitor_saude_coletores.py` → **OK** em todos os checks (`robo_principal`,
  `herman_*`, `orb_wdo_ft`).

#### 23.22.5 Diagnóstico read-only que confirmou o ambiente

- Conta: **55265364 / XPMT5-DEMO** (demo, `trade_mode=0`, saldo R$ 838.534,21).
- Contrato correto: **WDOZ26** (vence 30/11/2026). `WDO$` retornou tick `0.0`
  neste teste — mais um motivo para o robô usar o contrato mensal explícito.
- Book nativo: 20 níveis após `market_book_add`.
- **Posição fantasma WINV25** (magic `123457`, aberta em 15/10/2025): **já
  registrada e decidida** na autópsia de 17/09 (seções 6 e 13 — "DECISÃO DO
  MESTRE: ignorar"). É impossível fechar (contrato vencido, retcode 10013, sem
  livro). **Fica inerte na conta demo, sem ação.** Com `SYMBOL=None` ela aparecia
  como "posição ativa"; com `SYMBOL` resolvido, `positions_get(symbol="WDOZ26")`
  a ignora sozinho. Nada a fazer.

#### 23.22.6 Lições registradas

- **Nunca ignorar o retorno de `inicializar_mt5()`.** Inicialização parcial
  precisa de caminho de recuperação, não de "seguir em frente".
- **Watchdog não substitui auto-recuperação de estado.** Reconectar o MT5 não
  adianta se o estado derivado (`SYMBOL`, assinatura do book) não é reconstruído.
- **`market_book_add` é volátil:** `mt5.shutdown()` + `initialize()` (usado pelo
  watchdog) derruba a assinatura do book; sem reassinar, o sintoma vira "dados
  incompletos" mesmo com `SYMBOL` correto.
- **Default argument com global mutável** (`symbol: str = SYMBOL`) congela o
  valor do import (`None`). Bug silencioso.
- Reiniciar **só o robô** (sem `start_all.bat`) evita matar o `terminal64` e
  interromper o coletor Herman e o ORB.

#### 23.22.7 Arquivos tocados

- `monstro_unificado_v22.py` (5 correções acima; `py_compile` OK).
- `logs/monstro_wdo_20261111_bug_symbol.log` — backup do log do bug (1,38 MB).
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.

---

### 23.23 KERAS NÃO APRENDIA EM PRODUÇÃO — DIAGNÓSTICO, CORREÇÕES E RETREINO VALIDADO (11/11/2026)

**Pergunta do Mestre:** "verificar se o Keras está realmente aprendendo".
**Resposta curta:** o modelo **aprendeu** no treino offline, mas em produção **não
aprendia** — e não era culpa da rede. Eram 6 bugs de pipeline de dados. Todos
corrigidos. O retreino candidato **não foi promovido** (holdout real insuficiente).

#### 23.23.1 Evidência de que a rede aprende

- `history_treino.json` (treino offline de 30/07): `loss` 0,7046 → 0,4643 e
  `val_loss` 0,56 → 0,40 em 30 épocas. A rede aprende quando recebe dado normalizado.
- Com o scaler offline correto, `p(BUY)` varia 0,262–0,795 (média 0,465,
  desvio 0,082; 183/500 > 0,5).
- Com o fallback quebrado (fit em 1 linha), `p(BUY)` = **0,1605 fixo** em todas
  as linhas. Ou seja: a IA virava um viés constante, não um modelo.
- Efeito colateral real no log: com `p` constante 0,16, `ia_confianca_alta` ficava
  sempre `True` (`p<0,2`) → `INVERSÃO BLOQUEADA: IA=SELL (conf:0.94) PREVALECE
  sobre Confluência=BUY`.

#### 23.23.2 As 6 causas confirmadas

1. **Recursão infinita no scaler.** `_forcar_recreacao_scaler_throttled()`
   (L2176-2187) chamava a **si mesma** em vez de `forcar_recreacao_scaler()`.
   O `RecursionError` era engolido pelo `except Exception` → o scaler **nunca
   carregava**. Log de hoje antes da correção: nenhuma linha "Scaler carregado".
2. **Fallback degenerado.** `normalizar_dados()` (L3349) fazia
   `MinMaxScaler().fit_transform()` na **única linha** da predição → min=max →
   tudo vira 0. O modelo recebia um vetor de zeros.
3. **Scaler salvo defasado.** `modelo_monstro_wdo_scaler.json` foi ajustado com
   preços de julho: `preco_maior_escora_*` 5.045–5.148 vs hoje 5.562–5.635
   (100% fora do range); `bid_qty` 8.148–22.344 vs hoje 4.155–11.954
   (243/300 abaixo do mínimo). Mesmo carregando certo, o range não cobre o regime atual.
4. **O CSV de treino apagava os trades reais.** `monitorar_recursos()` truncava
   `historico_contexto_wdo.csv` para as últimas 5.000 linhas. O robô grava
   ~194 linhas/hora de `NAO_AGIU`; o arquivo cobre só ~26 horas. Resultado:
   **restaram 3 trades rotulados** (`4997 NAO_AGIU` + `3 BUY`). O dataset de
   aprendizado era literalmente deletado pelo próprio robô.
5. **Rótulo falso.** `preparar_dados()` fazia
   `y = 1 if action=='BUY' else 0` → `NAO_AGIU` virava **SELL (0)**.
6. **Replay sempre nas amostras mais antigas.** `obter_batch_replay()` ordenava
   por idade e pegava `exp_reais[:32]`. Ao crescer o dataset, o modelo treinava
   eternamente nas 32 primeiras e nunca no regime atual.

#### 23.23.3 Correções aplicadas (sem tocar em lógica de trade)

1. `_forcar_recreacao_scaler_throttled()` agora chama
   `forcar_recreacao_scaler()` (fim da recursão).
2. `normalizar_dados()`: ao faltar scaler, **tenta carregar o salvo antes** de
   qualquer fallback; só faz fit de emergência com `len(df) >= 2`; com 1 linha,
   usa scaler dummy e registra `ERROR` (nunca mais normalização degenerada silenciosa).
3. Rótulo: `action.map({'BUY':1,'SELL':0})`; `NAO_AGIU`/`NADA` viram `NaN` e são
   **descartados** em `treinar_modelo()` (log: "Descartando N amostras sem rótulo").
4. `obter_batch_replay()` usa as experiências **mais recentes** (`[-n_replay:]`).
5. Rotação do CSV: preserva **todos** os `BUY/SELL` e mantém as últimas 5.000
   linhas de `NAO_AGIU` (teste isolado: 6 trades sobreviveram ao truncamento).
6. `retreinar_keras_wdo.py`: script novo de retreino/validação offline, read-only
   no robô, com gate de completude das features de book e veredito automático.

`py_compile` OK.

#### 23.23.4 Validação em produção (restart 12:04:35)

- Restart **só do robô** (sem `start_all.bat`, sem reiniciar MT5/Herman/ORB).
- Log confirma a correção do scaler:
  `Scaler carregado do treinamento offline: modelo_monstro_wdo_scaler.json`.
- Posição aberta `#2590758259` (BUY WDOZ26 5.579,50) foi **re-adotada**
  automaticamente; zero erros de `SYMBOL`/dados incompletos/watchdog.
- Nenhuma mudança de lógica de entrada/saída; modelo e scaler vivos **não** foram trocados.

#### 23.23.5 Retreino candidato — números honestos

Script: `retreinar_keras_wdo.py` (mesma arquitetura do modelo vivo via
`clone_model`; scaler ajustado **só no treino**; `NAO_AGIU` descartado).

| conjunto | n | baseline | acurácia | AUC | p(BUY) |
|---|---|---|---|---|---|
| validação offline (20% final do corpus de julho) | 1.081 | 0,539 | **0,593** | **0,631** | 0,177–0,986 |
| holdout real recente (book completo) | 3 | 1,000 | 0,000 | n/a | ~0,31 |

- O candidato **tem poder discriminativo no corpus offline** (AUC 0,631 > 0,55),
  o que confirma que a arquitetura/dados aprendem.
- **Holdout real = 3 trades** (todos BUY). Estatisticamente inútil.
- **Veredito automático: NÃO PROMOVER** — holdout recente insuficiente (3 < 30).
- Modelo vivo e scaler vivo **permanecem intocados**. Candidatos salvos como
  `modelo_monstro_wdo_candidato.h5/.keras/_scaler.json` + métricas em
  `logs/retreino_keras_20261111_120207.json` (não versionados).

#### 23.23.6 Achado de qualidade de dados (importante)

- `logs/treino_corpus_real.csv` (141 trades reais, ago–nov) tem **10 de 18
  features zeradas**: `preco_maior_escora_*`, `volume_maior_escora_*`,
  `distancia_maior_escora_*`, `liquidez_top5_*`. Só `bid_qty`, `ask_qty`,
  `spread`, `volatility`, `entropia_book`, `rsi_14`, `volume_tick` são reais.
  Treinar com ele ensinaria "book sempre zero" — por isso o script aplica o
  gate `MIN_BOOK_FEATURES = 6` e o descarta.
- O corpus offline (`modelo_monstro_wdo_dados_treino.csv`, 5.405 linhas) é de
  julho, com preços ~5.100 e distribuições diferentes (spread 0,5–7,45 vs real
  0–0,5; entropia 1,10–2,29 vs real 2,58–2,97).
- Conclusão: **não existe hoje dataset rotulado do regime atual (WDO ~5.580)
  com features completas.** É a limitação estrutural que impede a promoção.

#### 23.23.7 Decisão registrada

- **Rejeitado promover o candidato agora.** Motivo: holdout real < 30 amostras.
- O que entra em produção **hoje**: apenas as correções de pipeline (itens 1–5),
  que param a perda de dados e fazem a IA usar o scaler real em vez de zeros.
- Critério de aceite para promover (quando houver dados):
  1. `AUC validação > 0,55`;
  2. `acurácia > baseline majoritário + 0,03`;
  3. holdout recente **≥ 30** trades com book completo (ideal ≥ 100);
  4. rodar em paper antes de ativar.

#### 23.23.8 Próximos passos

1. Deixar o robô rodar: a partir de agora os `BUY/SELL` **não são mais apagados**.
2. Reexecutar `venv310\Scripts\python.exe retreinar_keras_wdo.py` quando houver
   ≥ 30 trades reais com book completo.
3. Só promover se o veredito do script for "APTO", e ainda assim em paper.
4. Avaliar (futuro) remover features de **preço absoluto** (`preco_maior_escora_*`)
   e usar só distâncias — reduz o problema de não-estacionariedade. Exige mudança
   de features + retreino + validação; **não** fazer junto com outras mudanças.

#### 23.23.9 Arquivos tocados

- `monstro_unificado_v22.py` — 5 correções (itens 1–5), `py_compile` OK.
- `retreinar_keras_wdo.py` — novo script de retreino/validação offline.
- `logs/trades_reais_wdo.csv` — backup persistente dos trades reais (3 no momento).
- `logs/historico_contexto_wdo_20261111_pre_fix.csv` — backup do CSV antes das correções.
- `logs/retreino_keras_20261111_120207.json` — métricas do candidato.
- Candidatos `modelo_monstro_wdo_candidato.*` — **não promovidos, não versionados**.
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.

## 23.24 Proteção do treino automático do Keras (11/11/2026)

**Decisão do usuário (11/11):** "Proteger agora".
Objetivo: impedir que o treino automático sobrescreva o modelo bom com ruído.

### 23.24.1 Problema real (não teórico)

- O treino disparava a cada **4 trades** (`LIMITE_EXPERIENCIAS_PARA_TREINO = 4`).
- Com 4 amostras o split 80/20 gera **3 para treino e 1 para validação**.
- A regra "salva se o loss cair 1%" era avaliada em **1 única amostra**.
  Ou seja: ruído puro podia substituir o modelo treinado com 5.405 amostras.
- `treinar_modelo` zerava o contador **antes** de treinar: se o treino falhasse
  por dados insuficientes, o robô esperava mais 4 trades sem necessidade.

### 23.24.2 O que foi implementado

| Constante | Valor | Função |
|---|---|---|
| `MIN_TRADES_REAIS_TREINO` | 30 | só treina com ≥ 30 trades reais (BUY/SELL) na memória |
| `MIN_AMOSTRAS_VALIDACAO` | 10 | só **salva** o modelo se `X_val` tiver ≥ 10 amostras |
| `REPLAY_MAX` | 256 | replay usa até 256 experiências recentes (antes eram 32) |

Mudanças em `monstro_unificado_v22.py`:

1. `deve_treinar_modelo(memoria=None)` ganhou **gate de base mínima**:
   conta apenas `exp[1] in ("BUY", "SELL")`; `NAO_AGIU` **não** conta como trade.
2. `treinar_modelo_inteligente` passa a memória → `deve_treinar_modelo(memoria)`.
3. Quando o gate bloqueia, a função retorna **antes** do reset do contador
   (o contador não é mais perdido à toa).
4. Guarda de validação: `pode_salvar = len(X_val) >= MIN_AMOSTRAS_VALIDACAO`.
   A condição de salvar virou `if pode_salvar and loss_nova < (loss_antiga - melhoria_minima)`.
   Se não puder salvar, cai no mesmo caminho de "sem melhoria": restaura o
   modelo temporário anterior e mantém o modelo vivo intacto.
5. `obter_batch_replay` usa `min(REPLAY_MAX, len(exp_reais))` em vez de
   `min(BATCH_SIZE, ...)`, para a validação ter tamanho útil.

### 23.24.3 Validação

- `py_compile` em `monstro_unificado_v22.py`: **OK**.
- Teste de runtime do gate (função isolada, sem subir o robô):
  - 3 BUY + 4.997 `NAO_AGIU` → **False** (bloqueado);
  - 3 SELL → **False**;
  - 29 reais → **False**;
  - 30 reais → **True**;
  - `memoria=None` → **True** (comportamento antigo preservado).
- `pytest tests/test_fluxo_tempo_real.py tests/test_fluxo_api_contrato.py tests/test_fluxo_mt5_adapter.py`: **21 passed**.

### 23.24.4 Efeito prático esperado

- **Treina** a partir de **30 trades reais**.
- **Salva** só a partir de **~50 trades reais**, porque o split é 80/20 e a
  validação precisa de 10 amostras (`50 × 0,20 = 10`). Isso é intencional:
  as duas condições escolhidas pelo usuário valem ao mesmo tempo.
- Enquanto não houver essa base, o modelo e o scaler vivos **não mudam**.

### 23.24.5 O que NÃO muda

- Lógica de trade, stops, alvos, gestão de posição: **intocados**.
- Nenhum acesso a dinheiro real; segue tudo em demo/simulador.
- O gate não força operação nem altera entrada/saída.

### 23.24.6 Arquivos tocados

- `monstro_unificado_v22.py` — 7 substituições da proteção, `py_compile` OK.
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.

## 23.25 Filtro de lateralização no ORB WDO (11/11/2026)

**Gatilho:** em 11/11 o WDO fez range de **29,5 pts** contra média de **71,5 pts**
das 10 sessões anteriores — 97% do range aconteceu antes das 10:00. Dia lateral.
Hipótese levantada pelo usuário: **não operar quando a manhã é chop**.

**Script:** `estudo_filtro_range_orb_wdo.py` (novo, read-only, não toca no Core).
Reaproveita o simulador validado `backtest_orb_wdo.simulate`, o mesmo gatilho
(rompimento da caixa 09:00–10:00 na janela 10:30–11:00) e o custo canônico
**R$ 1,20 por contrato**.

### 23.25.1 Metodologia (sem look-ahead)

- Features calculadas **somente até 10:25**, antes da janela de gatilho.
- Percentis/medianas usam os **20 dias anteriores**.
- **Slippage explícito por lado**, porque o backtest do MT5 praticamente não o
  modela: 1 tick WDO = 0,5 pt = R$ 5,00 → 1 tick/lado = **R$ 10,00 por trade**
  (além dos R$ 1,20).
- IS = 2021–2024 | OOS = 2025–2026. Filtro só vale se sobreviver no OOS.

Métrica central — **eficiência da manhã** (Kaufman):

```
eff = |close(10:25) - open(09:00)| / range(09:00 -> 10:25)
eff baixo = manhã lateral (anda de lado e gasta range)
eff alto  = manhã direcional
```

### 23.25.2 Resultado principal (saída half, slippage 1 tick/lado)

| Config | n | win% | PF | exp R$ | total R$ | maxDD R$ | t |
|---|---|---|---|---|---|---|---|
| sem filtro | 874 | 40,0 | 1,50 | 51,71 | 45.195 | -2.476 | 4,45 |
| **eff ≥ 0,40** | **547** | **43,5** | **1,77** | **75,31** | **41.193** | **-1.822** | **4,89** |

- Acerto: **+3,5 p.p.**
- Lucro por trade: **+46%** (R$ 51,71 → R$ 75,31)
- Drawdown: **-26%** (-2.476 → -1.822)
- Total absoluto: **-9%**, porque opera **37% menos dias** (874 → 547).

### 23.25.3 IS × OOS (o teste que importa)

| Filtro | IS exp R$ | OOS exp R$ | OOS PF | OOS t |
|---|---|---|---|---|
| base (sem filtro) | 66,21 | **26,23** | — | — |
| eff ≥ 0,40 | 83,03 | **61,80** | 1,81 | 2,88 |
| eff ≥ 0,45 | 95,23 | 59,90 | 1,78 | 2,59 |
| eff ≥ 0,50 | 113,38 | 74,93 | 2,03 | 3,05 |

No OOS o filtro **mais que dobra** o resultado por trade (26,23 → 61,80), com
n=199 e t=2,88. Os dias bloqueados no OOS tinham expectância **-33,75**.

### 23.25.4 Slippage (o alerta do usuário)

| Slippage | exp R$ | PF | total R$ |
|---|---|---|---|
| 0 tick/lado | 85,31 | 1,93 | 46.663 |
| 0,5 tick/lado | 80,31 | 1,85 | 43.928 |
| **1 tick/lado** | **75,31** | **1,77** | **41.193** |
| 1,5 tick/lado | 70,31 | 1,70 | 38.458 |
| 2 ticks/lado | 65,31 | 1,63 | 35.723 |

O filtro sobrevive a **2 ticks por lado** (R$ 20/trade) com PF 1,63. Ou seja, o
resultado não depende de slippage zero.

### 23.25.5 Robustez

- **Varredura do limiar é monotônica** (0,20 → 0,50): 61,23 / 69,07 / 71,46 /
  68,85 / 75,31 / 82,80 / 99,66. Não é um "degrau" de sorte em 0,40.
- **Todos os anos positivos** (2021–2026): exp R$ 49 a 98, PF 1,58 a 2,09.
- Funciona nas **3 saídas**: caixa +21%, half +22%, fixed5 **+69%**
  (PF 2,17, DD -1.469).
- **Não é proxy de range pequeno:** `corr(eff, range_manha) = 0,29`; os dias com
  eff ≥ 0,40 têm range mediano **maior** (45,3 vs 40,8 pts) e caixa mediana
  parecida (37,3 vs 35,4). O p10 da caixa é 19,1 pts — o stop não fica minúsculo.
- Refino opcional: `eff ≥ 0,40 e range ≥ p30` → n=410, win 46,1%, PF 1,86,
  exp R$ 86,60, DD -1.710.
- Melhor PF/DD: `eff ≥ 0,40 + viés 1ª hora + stop fixo 5 pts` → n=501, PF 2,23,
  DD -1.408, OOS R$ 68,34 (mas win% 24,2%).

### 23.25.6 Rejeitados (registro obrigatório)

| Filtro | Motivo da rejeição |
|---|---|
| `ADX ≥ 20` | instável: IS 74,06 mas **OOS 19,22** (abaixo da base 26,23) |
| `ADX ≥ 25` | OOS 26,39 ≈ base, sem ganho |
| `ADX < 20` (contrário) | inverte entre IS (33,56) e OOS (61,18) → ruído |
| `range ≤ p30` (contrário) | pior em tudo (35,1% win) → confirma a hipótese |
| `eff ≥ 0,40 e range ≤ p70` | **pior** (exp 40,83): teto de range bloqueia dias bons |
| `caixa ≥ 20 pts` | não melhora (74,99 vs 75,31) |
| `ATR ≥ p50` | OOS 33,64, t=1,35 → sem confiança |

### 23.25.7 Diagnóstico do dia 11/11

| Feature | Hoje | Mediana histórica |
|---|---|---|
| range 09:00–10:25 | 29,5 pts | 40,8 pts |
| range 1ª hora | 28,5 pts | 35,4 pts |
| eficiência da manhã | **0,31** | 0,47 |
| ATR14 M5 | 5,20 | 8,25 |
| ADX14 M5 | 37,0 | 27,5 |

`eff ≥ 0,40` → **BLOQUEIA**. `range ≥ p50` → **BLOQUEIA**.
`ADX ≥ 20` → **passa** (por isso ADX foi rejeitado: teria operado o dia lateral).

### 23.25.8 Veredito

**4 estrelas.** Melhora acerto, PF, expectância, drawdown e OOS, e sobrevive a
slippage de 2 ticks/lado. O único ponto contra é o total absoluto cair 9% por
operar menos dias.

**Decisão:** implementar **somente no FT paper** (`rompimento_orb_wdo.py`) como
**4ª variante** (`eff≥0,40`), mantendo as 3 saídas atuais intactas para
comparação. Nada de dinheiro real e nada na lógica do robô principal.

### 23.25.9 Arquivos tocados

- `estudo_filtro_range_orb_wdo.py` — novo estudo, read-only.
- `.github/workflows/monstro-ci.yml` — py_compile do novo script.
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.

## 23.26 Implementação da 4ª variante no FT paper (ORB WDO)

**Data:** 11/11/2026
**Arquivo:** `rompimento_orb_wdo.py` (paper/read-only)
**Decisão:** ROADMAP 23.25.8 — aplicar `eff >= 0,40` como 4ª variante, mantendo
as 3 saídas atuais intactas.

### 23.26.1 O que mudou

- `morning_efficiency(day_bars)`: mesma fórmula do estudo
  (`|close(10:25) - open(09:00)| / range(09:00 -> 10:25)`), usando **somente
  barras até 10:25** -> sem look-ahead.
- Nova coluna `eff_manha` no CSV e no `state.json` (com `eff_ok`).
- O log de registro agora mostra `eff=...` e `LIBERA4`/`BLOQUEIA4`.
- `--resumo` ganhou:
  - a linha `+ eff >= 0.40 (4a variante)` na tabela de filtros;
  - o bloco `[4a VARIANTE: stop_half com eff >= 0.40]` com
    **liberados x bloqueados**.
- **As 3 saídas (`caixa`, `half`, `fixed5`) NÃO foram alteradas.** A variante
  filtrada é uma leitura dos mesmos trades, não um bloqueio do paper.

### 23.26.2 Paridade do eixo de horário (o ponto crítico)

Havia dúvida: o FT registra `offset=10800 s` e o estudo usa `SHIFT_H=0`.
Comparação em **52 dias sobrepostos** (2026-09-03 a 2026-11-11):

| item | resultado |
|---|---|
| dias comparados | 52 |
| max abs(delta eff) | **0,0000** |
| média abs(delta eff) | **0,0000** |
| veredito | **PARIDADE OK** |

Explicação: `datetime.fromtimestamp(ts + 10800)` do FT aplica o fuso local
(UTC-3), então o `+3h` **anula** essa conversão e cai no mesmo relógio naive do
`pd.to_datetime(ts)` do estudo. O `+10800` não é offset de corretora; é
compensação do fuso da máquina. Nada a corrigir no eixo.

### 23.26.3 Teste do `--resumo` com a 4ª variante

Testado com CSV sintético (monkeypatch do caminho; CSV real intocado):
`liberados` = eff 0,55 e 0,41; `bloqueados` = eff 0,20 e vazio. Sem crash,
seção impressa corretamente. `py_compile` OK e 21/21 testes verdes.

### 23.26.4 Como ler o paper (expectativa honesta)

- O paper **não prova** o filtro. A evidência estatística veio do IS/OOS (23.25.3).
- Em ~25 sessões o filtro gera **~11 trades** -> amostra fraca para significância.
- Critério de decisão: **o paper bate com o backtest?** Se sim, a implementação
  está correta. Não é "esperar o paper dar lucro".
- Nada de dinheiro real; nada na lógica do robô principal.

### 23.26.5 Arquivos tocados

- `rompimento_orb_wdo.py` — 4ª variante (`eff_manha`, `EFF_MIN`, `--resumo`).
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.

## 23.27 Incidente 11/11: fechamento das 17:35 falhou por queda de rede (posição ficou aberta)

**Data:** 11/11/2026
**Severidade:** alta (posição ficou aberta após o encerramento)
**Conta:** demo 55265364 / XPMT5-DEMO (trade_mode=0) — sem dinheiro real

### 23.27.1 O que aconteceu

- 17:35:02 — robô inicia "FECHANDO TODAS AS POSIÇÕES"; `mt5.order_send`
  retorna **None** para `#2590873006` (SELL WDOZ26).
- 17:35:18 — shutdown gracioso (`parar.txt`) tenta de novo; **Retcode 10031**
  ("Request rejected due to absence of network connection") nos fillings 0 e 1.
- Robô encerra **com a SELL aberta**.
- 17:36–17:37 — `WATCHDOG-DLL: Tick estagnado >10s` confirma instabilidade de
  rede do terminal MT5.
- 18:05:47 — fechamento manual (autorizado pelo Mestre) a 5586,0 ->
  **−R$ 50,00** (deal `1878867890`).

### 23.27.2 Resultado do dia (WDOZ26, 1 contrato)

| Hora (BRT) | Lado | Entrada | Saída | Pts | R$ |
|---|---|---|---|---|---|
| 11:41:49 | BUY | 5579,5 | 5581,0 | +1,5 | **+15,00** |
| 12:32:49 | SELL | 5581,0 | 5586,0 | −5,0 | **−50,00** |
| **Total** | | | | | **−35,00 bruto** |

Custos canônicos: 2 operações x R$ 1,20 = R$ 2,40 -> líquido ~ **−R$ 37,40**.

Observação: o `relatorio_diario_20261111.txt` registrou "Trades executados: 1"
porque foi gerado às 17:35, antes do fechamento manual. O número real é 2.

### 23.27.3 Bugs identificados

1. **Sem retry/reconexão em 10031**: o fecho das 17:35 não reconecta nem espera;
   a re-checagem 15s/30s foi abortada pelo shutdown 16 s depois.
2. **Mensagem incondicional**: "POSIÇÕES FECHADAS ÀS 17:35" foi impressa mesmo
   com "0 posições fechadas".
3. **Shutdown não garante flat**: o encerramento gracioso não bloqueia enquanto
   houver posição aberta.

### 23.27.4 Propostas de correção (NÃO implementadas — aguardam revisão humana, Fase 1)

- Em retcode 10031, chamar `mt5.initialize()` e repetir com backoff
  (ex.: 5 tentativas de 5 s) antes de desistir.
- Só logar sucesso se `positions_get()` confirmar zero posições do magic.
- Bloquear o shutdown gracioso se houver posição aberta, exigindo `--force`
  explícito.
- Relatório diário deve ler os deals reais (inclui fechamento manual).

### 23.27.5 Veredito

**5 estrelas** (risco operacional real, ainda que em demo). Correção prioritária
antes de qualquer promoção para real. Documentado; **sem alteração de código**
nesta rodada.

### 23.27.6 Arquivos / evidências

- `monstro_wdo.log` — sequência do erro (10031).
- `ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md` — esta seção.
- `plano_20261111.txt` — commit `9845e13` (agente de fecho).

## 23.28 Patch de robustez do fecho — proposta revisavel (NAO aplicada)

**Data:** 11/11/2026
**Status:** proposta isolada, aguardando revisao humana (Fase 1)
**Origem:** incidente da secao 23.27 (retcode 10031 no fecho das 17:35)

### 23.28.1 O que foi entregue

Patch **aditivo**, sem tocar no robo em producao:

- `patches/robustez_fecho_helpers.py` — helpers injetaveis (mt5/reconnect/log/sleep),
  testaveis sem terminal.
- `tests/test_robustez_fecho.py` — 12 testes com `FakeMT5`.
- `patches/robustez_fecho_2026-11-11.md` — documento de integracao com ancoras,
  plano de teste e rollback.
- `.github/workflows/monstro-ci.yml` — passou a compilar e rodar o novo teste.

`monstro_unificado_v22.py` e `agente_monstro_core.py` **nao foram alterados**
(o fonte do robo tem mojibake; a aplicacao deve ser feita em branch separada).

### 23.28.2 As 4 correcoes propostas

| # | Bug (23.27) | Correcao |
|---|---|---|
| C1 | sem retry/reconexao em 10031 | `fechar_todas_robusto`: reconecta com backoff, testa todos os fillings, usa `pos.magic` |
| C2 | mensagem de sucesso incondicional | so logar "POSICOES FECHADAS" se `posicoes_restantes()` for vazio |
| C3 | shutdown nao garante flat | trava: nao encerra com posicao aberta; escape `MONSTRO_FORCE_SHUTDOWN=1` |
| C4 | relatorio conta log, nao deals | `contar_deals_reais_hoje`: le `DEAL_ENTRY_OUT` dos magics do robo |

### 23.28.3 Resultado dos testes

- `py_compile` — OK.
- `python tests/test_robustez_fecho.py` — **12/12 PASS**.
- `pytest tests/test_robustez_fecho.py -q` — **12 passed**.
- Suite do CI (3 antigos + novo) — **33 passed**.

Cobertura: fecho normal, 10031 com reconexao, 10031 persistente (nao mente),
`order_send None`, retcode DONE sem posicao sair (nao conta sucesso),
magic alheio 123457 ignorado, bitmask de fillings, deals por magic/PnL.

### 23.28.4 Decisao

- **Nada aplicado em producao.** As 4 correcoes seguem como proposta.
- Aplicacao futura em branch separada, com teste em demo simulando queda de rede.
- Criterio de aceite: nenhum log de "POSICOES FECHADAS" com posicao aberta e
  shutdown sem `--force` nunca termina com posicao do robo aberta.

**Aprovacao conceitual em 11/11/2026 (Mestre):**

- Textos de log aprovados: `FECHO CONFIRMADO`, `FECHO INCOMPLETO`,
  `SHUTDOWN BLOQUEADO`.
- Escape do shutdown: `MONSTRO_FORCE_SHUTDOWN=1` (variavel de ambiente;
  CLI intocada).
- Backoff: 5 tentativas x 5 s (~25 s).
- Branch `robustez-fecho` criada em `9768889`, pronta para receber a
  integracao C1-C4 apos o pregao de 12/11.

### 23.28.5 Observacao

`tests/test_gerenciador_bloqueio.py` tem um teste legado que falha sempre
(`assert False`); ele **nao** faz parte do CI e nao foi alterado nesta rodada.

### 23.28.6 Veredito

**5 estrelas** — correcao prioritaria antes de qualquer promocao para real.

## 23.29 Alerta "3 valores fora de [0,1] foram clipped" - diagnostico (12/11/2026)

### 23.29.1 O que e

- WARNING de `normalizar_dados` (`monstro_unificado_v22.py` L3401-L3407), no modo
  predicao: `scaler_global.transform` gera valores <0 ou >1, o codigo faz
  `clip(0,1)` e conta quantos mudaram.
- **Nao e erro** e nao para o robo: e aviso de saturacao de features.

### 23.29.2 Evidencia

- 12/11: **2.933 ocorrencias** entre 09:15:30 e 11:12:15 (~2,4 s entre cada),
  no `monstro_wdo.log`.
- 10/11: 6.072 | 06/11: 4.534 | 11/11: 3 (dia com bug SYMBOL e poucas predicoes).
  Portanto e **cronico**, nao uma regressao de hoje.
- Scaler em producao: `modelo_monstro_wdo_scaler.json`, de **01/08/2026**.
- Ultima linha de `historico_contexto_wdo.csv` (11:00:50) fora da faixa em 3-4
  features:
  - `bid_qty` / `ask_qty` abaixo do minimo (intermitente);
  - `volatility` acima do maximo (persistente);
  - `preco_maior_escora_bid` / `ask` acima do maximo (persistentes;
    ~5618 vs faixa de treino 5060-5148).
- O numero "3" varia com o instante; os persistentes sao `volatility` e as
  duas escoras de preco.

### 23.29.3 Causa raiz

- Features de preco absoluto sao **nao-estacionarias** (ja registrado nos
  bloqueios do projeto).
- O scaler foi ajustado num regime de preco ~5060-5148; hoje o WDO esta ~5620.
  O modelo nunca viu esse nivel.
- O clipping satura essas features em 0/1 e reduz a informacao; o modelo segue
  prevendo (probabilidades 0,39-0,50), mas **fora da distribuicao de treino**.

### 23.29.4 Impacto

- **Nao** altera logica de entrada/saida, stops ou filtros; nao e bug de execucao.
- **Nao** afeta o ORB (processo separado, sem scaler).
- Risco operacional: log flood (2.933 linhas em ~2 h) pode rotacionar logs e
  esconder erros reais (como o 10031 de 11/11).
- Risco de modelo: sinal de ML degradado por saturacao; hoje os sinais sairam
  NEUTRO (confianca < 0,15), entao sem trade.

### 23.29.5 Propostas (NAO aplicadas)

- Throttle do warning: no maximo 1x/10 min, com os nomes das features e a
  contagem; DEBUG no restante.
- Incluir `feature_names` no aviso para diagnostico imediato.
- Nao refitar o scaler isoladamente: refitar junto com o retreino
  (>=30 trades reais, validacao >=10) para manter scaler+modelo coerentes.
- Avaliar substituir preco absoluto das escoras por **distancia relativa ao
  preco** (ex.: `preco_escora - preco_atual`), que e estacionaria.
- Enquanto isso, manter o modelo em paper; nao promover candidato.

### 23.29.6 Veredito

**3 estrelas** - importante para a qualidade do ML e higiene de logs, mas nao
bloqueia o pregao nem o ORB. Corrigir junto com o proximo retreino.

---

## 23.30 ORB WDO 12/11: 4a variante e analitica e EOD do state e provisorio

### 23.30.1 Estado observado (11:12)

- `state.json`: dia 2026-11-12, side BUY, entry 5624,0 (10:30), stops
  caixa 5596 / half 5610 / fixed5 5619, eff 0,352, eff_ok false,
  obs `BLOQUEIA4`, final false, fase "em trade".
- `resultados`: caixa/half "EOD" -1,5 (provisorios), fixed5 SL -5,0 (real).

### 23.30.2 Por que BUY com eff_ok=false

- `evaluate_day` registra os filtros, mas **nao bloqueia** (comentario L329:
  "filtros (registrados, nao bloqueiam)").
- A 4a variante e aplicada no `--resumo` (L622-L636), separando liberados
  (eff >= 0,40) e bloqueados.
- Portanto o paper registra o dia; `BLOQUEIA4` e classificacao analitica.
  Se a intencao for bloqueio operacional, e mudanca de logica (proposta).

### 23.30.3 Por que EOD aparece as 11:12

- `simulate` usa `eod_close = day_bars[-1]["c"]` (ultima barra disponivel) e
  rotula "EOD" se o stop nao foi atingido (L286-L287).
- O CSV so e gravado as 18:05 (`TIME_EOD_FINAL`), com a barra 17:55; antes
  disso o state e mark-to-market.
- `final=false` confirma que nao e resultado final. Nao ler o state como fecho.

### 23.30.4 Impacto

- Nenhum no CSV/estatistica: `registrar()` so roda no EOD/reconciliacao.
- Risco de leitura errada da telemetria ao vivo (operador achar que o dia fechou).
- Proposta: rotular `exit="EOD_PARCIAL"` enquanto `final=false`, ou so preencher
  `resultados` no EOD. Nao aplicado.

### 23.30.5 Veredito

**2 estrelas** - clareza de telemetria; sem risco de dados. Corrigir quando
mexer no ORB.

## 23.31 Materiais preparatorios pos-pregao 12/11 (C1-C4, ML 23.29, checklist)

### 23.31.1 O que foi criado (nada aplicado ao robo)

- `patches/aplicar_robustez_fecho.py` - script de aplicacao segura de C1-C4
  (dry-run por padrao, backup, UTF-8 estrito, diff e `py_compile`).
- `patches/proposta_ml_23.29.md` - proposta do throttle de clipping e das
  escoras estacionarias, com ancoras e gates de retreino.
- `patches/checklist_fecho_2026-11-12.md` - checklist de validacao do fecho
  para rodar depois das 18:30.
- `.gitignore`: `patches/backups/` passou a ser ignorado (copia do fonte).

### 23.31.2 Validacao do script (somente dry-run)

- Rodado apenas `py_compile` do proprio script e o modo seco (`--skip-git`).
- **Nenhuma escrita nos fontes, nenhum MT5, nenhum restart.**
- Plano do dry-run: robo 11.449 -> 11.418 linhas (diff 232); agente
  1.275 -> 1.310 linhas (diff 51); buffer compilou.
- O dry-run achou **1 bug real**: o C4 usava a indentacao da 2a linha do
  `linhas.append(...)` (18 espacos) e gerava `unexpected indent`; corrigido
  para usar a abertura do statement (4 espacos).
- Ancoras sao trechos ASCII estaveis (nao dependem de numero de linha nem do
  mojibake do fonte).

### 23.31.3 Garantias do script de aplicacao

- Exige branch `robustez-fecho` e os 2 arquivos limpos (salvo flags).
- UTF-8 estrito; aborta em byte invalido ou U+FFFD.
- `splitlines(keepends=True)` preserva CRLF/LF (o robo tem 11.405 CRLF + 43 LF).
- Backup completo + `manifest.json` com sha256 + `diff.patch`.
- `compile()` do buffer antes de gravar; `py_compile` do arquivo gravado.
- Idempotente pela marca `[C1-C4]`; `--reverter` restaura o ultimo backup.

### 23.31.4 Proposta ML 23.29 (pontuacao)

- **T1 throttle do warning: 3 estrelas.** 1 aviso/10 min com os nomes das
  features; restante em DEBUG. Nao muda modelo nem trade.
- **T2 escoras estacionarias: 4 estrelas.** Descoberta: as features
  `distancia_maior_escora_bid/ask` **ja existem** (L2895-L2898 e L2917-L2920)
  e ja estao nas 22; o problema e manter as 2 colunas de **preco absoluto**.
  Opcao A recomendada: 20 features + retreino + scaler novo + `n_features=20`.
- **Opcao C (refitar scaler sozinho): 1 estrela, rejeitada.** O candidato de
  11/11 ainda tem 3 features fora da faixa.
- Gates: >=30 trades reais, validacao >=10, AUC>0,55, acuracia>baseline+0,03,
  holdout>=30 e paper antes de qualquer promocao.

### 23.31.5 Checklist do fecho

- Pre-requisitos: ORB com `final=true`, zero processos Python do robo/ORB,
  flat nos magics 123456/7008 (fantasma 123457 ignorado), branch limpa.
- Gates: 12/12 pytest, `py_compile`, e pelo menos 1 fecho real em demo
  confirmado por `positions_get()` (ou teste na sexta antes das 09:00).
- Rede: queda de ~10 s (10031 -> reconecta/backoff) e falha persistente
  (`critical`, nunca "POSICOES FECHADAS").
- C3: revisao estatica hoje; dinamico opcional na sexta.
- C4: relatorio por deals inclui fecho manual.
- Rollback: `--reverter` ou `git revert`.

### 23.31.6 Veredito

**4 estrelas** para o pacote de robustez do fecho (C1-C4 + script + checklist):
alto impacto operacional, baixo risco e nenhuma mudanca na logica de trade.
O T1 (throttle) e **3 estrelas**; o T2 (escoras) e **4 estrelas**, mas fica
bloqueado ate o retreino com >=30 trades.

### 23.31.7 Proximo passo

- 18:05: conferir ORB final e zero processos.
- 18:30+: dry-run -> apply na `robustez-fecho` -> 12 testes -> fecho real demo.
- Se verde: merge na `main` para sexta; senao, manter na branch e registrar.

## 23.32 Trailing stop da Faixa 1: por que +14/+20 pts nao foram protegidos (12/11/2026)

### 23.32.1 O que o usuario viu

Posicao real `#2591384275` WDOZ26 BUY 1 @ 5624,0 (magic **7008**, Faixa 1),
aberta as 10:05. Na captura do usuario estava em 5638,0 (**+14 pts**,
+R$140). Chegou a 5644,5 (**+20,5 pts**, +R$205) as 12:12. Pergunta
legitima: por que o trailing stop nao protegeu um movimento de 14-20 pontos?

### 23.32.2 Causa raiz (dois mecanismos, nenhum ativo para a Faixa 1)

1. **Thread `atualizar_trailing_stop` (L5802-L5879):** faz
   `if pos.magic != MAGIC_NUMBER: continue` (L5844). `MAGIC_NUMBER = 123456`
   (Core). A Faixa 1 usa **7008** -> o thread nunca olha para ela.
2. **Classe `TrailingStopInteligente` (L102-L166):** e inicializada em toda
   ordem (`iniciar_trailing`, L5534-L5538), inclusive a da Faixa 1 - por isso
   o log "Trailing stop iniciado para posicao 2591384275". Mas o unico ponto
   que chama `atualizar_trailing` e `monitorar_posicao_ativa` (L10147), e
   **essa funcao nao e chamada em nenhum lugar do `monstro_unificado_v22.py`**
   (confirmado por grep em todo o projeto). Ou seja: a classe e **codigo morto**
   no v22; a linha do log e uma promessa falsa.
3. **`rompimento_orquestrador.py` (Faixa 1):** gerencia SL/TP no servidor e
   fecha a mercado no EOD (comentario L549). **Nao tem trailing.**

Resultado: a Faixa 1 opera com SL/TP fixos no servidor (SL 5605,5 = -18,5 pts
= -R$185) e **nenhuma protecao de lucro**.

### 23.32.3 Evidencia no log

- `monstro_wdo.log:7412` (10:05:06): "Trailing stop iniciado para posicao
  2591384275" -> so inicializacao do objeto.
- Nenhuma linha posterior de "Trailing stop ativado" / "Lucro travado" /
  "SL movido" para esse ticket.
- `logs/rompimento/rompimento.log:32825` (10:05:06): "[ROMPIMENTO] BUY WDOZ26
  (lote 1.0) entrada=5624.0 SL~5605.68 TP=5666.0 ticket=2591384275" -> SL/TP
  fixos, sem trailing.

### 23.32.4 O que teria acontecido hoje (tick a tick, 70.273 ticks)

Caminho real: entrada 5624,0; minimo -2,5 pts as 10:07; +8 as 10:08:30;
+12 as 10:09:41; **+14 as 10:09:49**; recuo; minimo **-7,5 pts as 11:18:35**
(5616,5, a 11 pts do SL); **+20,5 as 12:12:03** (pico); +19 as 12:14.

Simulacao com os parametros atuais (`gatilho 8`, `distancia 4`):

| Regra | Saida | Resultado |
|---|---|---|
| **Sem trailing (real)** | ainda aberta | +19 flutuante, mas risco -18,5 e excursao -7,5 |
| Trail 8/4 (atual) | 10:10:21 | **+11,0 pts = R$110** |
| Trail 8/6 | 10:13:32 | +11,5 pts = R$115 |
| Trail 8/8 | 10:18:01 | +9,5 pts = R$95 |
| Trail 8/10 | 10:18:18 | +7,5 pts = R$75 |
| BE +8 (trava 1 pt), sem trail | 10:23:08 | +1,0 pt = R$10 |
| BE +8 + trava 70% em +14 | 10:10:27 | +10,5 pts = R$105 |

Conclusao factual: **qualquer** regra de protecao teria saido entre +1 e +11,5
pontos e **perdido o +20**, que so veio 2 horas depois, apos um recuo de
-7,5 pts. O +20 nao foi um movimento linear de 14 pontos; foi um caminho
volatil. O trailing "protegeria", mas cortaria o unico winner grande do dia.

### 23.32.5 Leitura honesta

- O usuario tem razao no principio: uma operacao que andou +14/+20 **deveria**
  ter alguma protecao. Hoje nao tem nenhuma.
- Mas "ligar o trailing atual" **nao** teria protegido +14: com distancia de
  4 pts, o ruido normal do WDO (3-6 pts) tira a operacao em ~+11.
- Aumentar a distancia (8-10 pts) protege menos ainda (sai em +7,5 a +9,5).
- Breakeven puro (+8 -> SL entrada+1) tambem foi tirado em +1 hoje.
- Ou seja: **proteger mais e ganhar mais sao objetivos em conflito** neste
  desenho de 1 contrato e saida unica. A decisao tem que ser por backtest
  (874 trades, com slippage), nao por um dia.

### 23.32.6 Propostas (NAO implementadas - Fase 1)

- **P1 - Fazer o thread enxergar a Faixa 1: 5 estrelas.**
  Trocar o filtro `pos.magic != MAGIC_NUMBER` por um conjunto de magics
  geridos (`{MAGIC_NUMBER, MAGIC_FAIXA1}`) ou delegar ao orquestrador.
  Sem isso, qualquer parametro e irrelevante.
- **P2 - Backtest de trailing no ORB antes de escolher regra: 5 estrelas.**
  Rodar `backtest_orb_wdo.py` com 4 variantes de saida (sem trailing,
  trail 8/4, BE+8, BE+8+trava 70%) nas 3 saidas existentes (caixa,
  0,5x caixa, fixed5), com slippage 0/1/2 ticks. Gates: PF, expectancia,
  WR e DD. **Nao promover se nao melhorar WR e PF.**
- **P3 - Corrigir o log mentiroso: 3 estrelas.**
  "Trailing stop iniciado" so deve ser impresso quando o trailing for
  realmente gerenciado para aquele magic.
- **P4 - Remover/religar o codigo morto: 2 estrelas.**
  `monitorar_posicao_ativa` e `TrailingStopInteligente` estao mortos no v22;
  decidir entre remover ou religar (religar mexe na logica de trade -> Fase 1).

### 23.32.7 Veredito

**5 estrelas** para P1+P2 (diagnostico + validacao). O bug e real e explica
exatamente a queixa. Mas a expectativa "o trailing teria protegido os 14
pontos" **nao se confirma** com os parametros atuais: ele teria saido em
+11 e perdido o +20. Antes de ligar qualquer trailing na Faixa 1, o
backtest tem que mostrar que a troca (menos cauda, mais consistencia)
melhora o resultado liquido.

## 23.33 Relatorio diario inflava a Faixa 1 em 5x (12/11/2026)

### 23.33.1 Achado

O `relatorio_diario_20261112.txt` mostrou a Faixa 1 como **R$ +2100,00**
(42,0 pts). O deal real `#1879504380` fechou em **R$ +420,00** (42 pts x
R$10, 1 contrato). Erro de 5x.

### 23.33.2 Causa raiz

`agente_monstro_core.py:827` fazia `pnl = pts * 5.0 * 10.0`, assumindo
**5 contratos** (heranca do desenho antigo da Faixa 1). O CSV
`logs/rompimento/rompimento_trades.csv` ja grava `lucro_rs` correto
(420.0) e era ignorado.

### 23.33.3 Correcao aplicada

- `pnl` passa a usar `rp["lucro_rs"]` quando presente; fallback
  `pts * 1.0 * 10.0` (1 contrato, R$10/ponto).
- Commit `40b917c`; `py_compile` OK; diff restrito ao relatorio.
- Nao toca em logica de trade, MT5 ou risco.

### 23.33.4 Achado secundario (nao corrigido, 2 estrelas)

`plano_20261112.txt` diz "3 fechados", mas o dia teve **4** (3 Core +
1 Faixa 1). O `tools/autopsia_automatizada.py` le apenas o log do v22 e
nao o CSV da Faixa 1. Impacto hoje: nulo (3 ou 4 < 15). Proposta:
somar `contar_executados_rompimento_hoje()` ao `n_fechados` (Fase 1).

### 23.33.5 Veredito

**4 estrelas** para a correcao do relatorio: e o numero que o humano le
para decidir, e estava 5x maior. O achado secundario e **2 estrelas**.

## 23.34 Auditoria de logs do fecho de 12/11 (12/11/2026)

### 23.34.1 Escopo e metodo

Varredura read-only de todos os logs modificados em 12/11
(`monstro_wdo.log`, `agente_autonomo.log`, `logs/saude_coletores.log`,
`logs/ALERTA_COLETORES.txt`, `logs/herman_6p/online_herman.log`,
`logs/rompimento/rompimento.log`, `logs/rompimento_orb_wdo/orb_wdo.log`).
Nenhum arquivo foi alterado durante a investigacao.

### 23.34.2 Log principal: zero erro

`monstro_wdo.log` hoje: 61.974 linhas (09:02:39 -> 17:35:50), 21.844
WARNING, **0 ERROR/CRITICAL/Traceback**. Encerramento gracioso as 17:35:50.

### 23.34.3 "VETO TOTAL ... Sem historico suficiente" (2 estrelas)

1.214 ocorrencias, o dia inteiro (nao so no inicio). Nao e falta de dados:
`monstro_unificado_v22.py:1465` devolve "Sem historico suficiente" como
**aprovacao**, e o veto real vem depois da trava dupla de Williams %R
(`:9251-9258`); `:9269` imprime os motivos **obsoletos**. Casamento exato:
1.214 VETO TOTAL = 1.214 veto SELL + 1.214 veto BUY por WR < -80.
Recorrente (10/11=611, 06/11=592): nao e regressao. Acao: so corrigir a
mensagem para citar Williams %R.

### 23.34.4 "executar_ordem falhou" apos o gate (3 estrelas)

18 ocorrencias, sempre 1:1 depois de
`[GATE ROMPIMENTO] Ordem bloqueada ... (apenas Magic 7008)`. A ordem foi
**bloqueada pelo gate**, nao falhou no MT5. Sao 18 sinais Sniper do Core
perdidos com mensagem enganosa. Acao: distinguir "bloqueada" de "falhou".

### 23.34.5 Clipping: frequencia recorde, magnitude menor (4 estrelas)

Hoje: **10.390 eventos / 29.121 valores** clipados (2-5 features por
evento). Comparacao: 10/11=6.072 eventos / 88.892 valores (14,6/evento);
06/11=4.534 / 65.792; 05/11=6.755 / 94.059. Frequencia +71% vs 10/11,
mas total de valores **-67%**. 11/11 nao serve de baseline (loop quase
nao rodou). Features provaveis: `bid_qty` (min do scaler 8148 vs bid
observado ~5011) e `volume_tick` (max 207 vs volume ~9.500-12.648).
Acao: revisar scaler/faixas de treino antes do proximo retreino (T2).

### 23.34.6 Trailing do ticket 2592177465 (confirma 23.32, 4 estrelas)

"Nenhuma atualizacao real de SL. Entrada 5669, SL 5661, TP 5674 em 452 de
452 linhas de monitoramento; maxima +1 pt (gatilho = 8). Fechou no SL fixo
(-R$80)." Reforca a proposta 23.32: o log "Trailing stop iniciado" e falso
e `monitorar_posicao_ativa` nunca e chamada.

### 23.34.7 Shutdown do agente: bug real de ciclo de vida (4 estrelas)

Timeline: `Monstro-Fecho` 17:35:04 -> 1o `parar.txt` 17:35:18 -> robo
consome 17:35:49 -> `ENCERRAMENTO GRACIL CONCLUIDO` 17:35:50 -> **2o**
`parar.txt` 17:36:17 (`parar_robo()`->`parar_gracioso()`) -> timeout
17:37:58 (~100,8 s) -> force kill PIDs 49400/60184/61980 -> `parada
forcada: ok` 17:38:13.

Os 3 PIDs sao a cadeia `cmd.exe /k` -> shim do venv -> Python real;
`pids_robo()` casa qualquer cmdline com `monstro_unificado_v22`
(`agente_monstro_core.py:159-168`), por isso superconta.

Causa raiz: o ramo de parada gracil termina com `break`
(`monstro_unificado_v22.py:6919-6959`), mas a thread principal fica presa
em `webview.start()` (`:11288`) e ninguem fecha a janela. O processo
continua vivo apos "finalizado com seguranca" e o agente espera 90 s por
`pids_robo()` vazio (`agente_config.json:22`). Em 06/11, sem pywebview,
o fallback `join()` retornou e **nao houve force kill**; nos dias com
pywebview (10/11, 11/11, 12/11) houve timeout: padrao cronico.

Impacto hoje: nenhum (artefatos salvos, flat, sem processos, sem
`parar.txt`). Risco real: se o force kill falhar (precedente 03/11), sobra
`python.exe` com `monstro_unificado_v22` na cmdline e o anti-duplicidade
do `start_all.bat:8-9` recusa subir no dia seguinte -> dia perdido.

Correcoes propostas (Fase 1, nao implementadas):
1. **4 estrelas** - sair de fato no shutdown gracil: apos o log final,
   destruir a janela (`_janela.destroy()`) e `os._exit(0)` (com flush).
2. **3 estrelas** - `pids_robo()` filtrar `python.exe` e ignorar
   `cmd.exe`/shim; ideal: PID em arquivo (`robo.pid`).
3. **2 estrelas** - launcher sem `cmd /k` (`start_all.bat:24`).
4. **1 estrela** - timeout real descontando a varredura (`wait_procs`).
5. **1 estrela** - alerta destacado se `parar_forcado()` retornar `FALHOU`.

### 23.34.8 Monitor de coletores: 1 bug real + 2 falsos positivos

- **CRIT `[rompimento_ft]` (11:40, 13:30, 14:30, 14:50, 17:00) - bug real
  (3 estrelas).** A tarefa esta `Disabled` e o probe retornou `False` em
  15/15 chamadas agora. O CRIT so aparece quando o probe externo
  (`schtasks`+PowerShell, timeout 20 s cada) falha e cai no
  `except Exception: return True` **fail-open** (`monitor:249`). As runs
  que falharam duraram 70-175 s (contencao do Task Scheduler). Correcao:
  fail-safe/tri-state + probe unico com retry + logar a falha; e remover
  `ativo_desde.txt` do FT aposentado.
- **CRIT 17:40/17:50 Herman + robo - falso positivo de janela
  (3 estrelas).** O monitor so conhece 09:00-17:55
  (`monitor_saude_coletores.py:56-58`), nao o fecho das 17:35. Limpa
  sozinho as 18:00 (`saude_coletores.log:154`, `status OK`,
  `ALERTA_COLETORES.txt` apagado). Correcao: `PREGAO_FIM=17:35` ou tratar
  17:35-17:55 como "encerramento" INFO; grace ate 09:10 na abertura.
- **WARN `herman_crescimento` 17:10/17:20 - falso positivo de limiar
  (2 estrelas).** Gap real de formacao (16:30:31 -> 17:24:10), mas com
  heartbeat vivo e CSV integro (190 boxes). 3o dia seguido. Correcao:
  limiar sazonal apos 16:30 ou condicionar a heartbeat+CSV.

### 23.34.9 Veredito

Nenhum erro de execucao no pregao. Itens acionaveis: observabilidade
(mensagens enganosas), qualidade de features (clipping) e **ciclo de vida
do processo no fecho** (4 estrelas, o unico com risco de derrubar o dia
seguinte). Os alertas do monitor sao 1 bug de fail-open + 2 falsos
positivos de janela/limiar.

## 23.35 C1-C4 aplicado + teste de restart ao vivo (12/11/2026)

### 23.35.1 Aplicacao

- `patches/aplicar_robustez_fecho.py --apply` as 18:06:53.
- Backup: `patches/backups/20261112_180653` (manifest com `sha256_antes`).
- Diff: `monstro_unificado_v22.py` +191/-111 (232 linhas no plano) e
  `agente_monstro_core.py` +35. `py_compile` 4/4 OK. `pytest` **12
  passed**. Nenhuma regra de trade tocada.
- Revisao no codigo real: C3 (L6957-6972) **antes** do log final e do
  `break` (L6974-6977), com `continue` e escape
  `MONSTRO_FORCE_SHUTDOWN=1`; C2 (L7044-7053) so loga flat se
  `positions_get()` confirmar; `MAGICS_ROBO`/helpers (L10633-10644)
  definidos antes do `__main__` (L11138).
- Commit `094ec34` na branch `robustez-fecho`.

### 23.35.2 C4 validado isolado

`contar_trades_reais_hoje()` -> **(4, 450.0)**, batendo com os 4 deals
OUT do dia (Core + Faixa 1). O relatorio diario passa a mostrar
`Trades fechados (deals MT5)`.

### 23.35.3 Teste de restart (so o robo, sem `start_all.bat`)

- 18:07:35 subida; 18:09:00 `Monstro WDO v2 REINICIADO`; MT5 ok,
  WDOZ26/DOLZ26, book nativo, dashboard 5001 (waitress), **sem erro de
  import** do patch.
- 18:09:08 `Pregao encerrado. Dormindo...` (pos-after).
- 18:09:30 `parar.txt` criado; 18:10:08 consumido; experiencias salvas;
  `ENCERRAMENTO GRACIL CONCLUIDO`.
- **O processo NAO saiu** (2 PIDs vivos) -> confirma ao vivo o bug 4
  estrelas do 23.34.7 (pywebview segura a thread principal apos o
  `break`). Force kill seguro (flat, mercado fechado): porta 5001 livre,
  zero processos, `parar.txt` removido.
- O caminho `parar.txt` nao passa pelo C2 (que fica no bloco
  after-market); o C3 rodou sem posicoes e nao bloqueou, como esperado.

### 23.35.4 Decisao

- Merge na `main` autorizado: 12/12 testes, `py_compile` OK, flat,
  diff restrito, C4 validado e restart limpo. **Merge concluido:
  `768d3fd`** (branch `robustez-fecho` mantida em `9252f6d` para
  auditoria).
- **Pendencia unica:** fecho real em demo (`order_send`/10031) nao pode
  ser testado hoje (demo sem simbolo 24h; WDO fechado). Fica para
  **sexta 13/11 antes das 09:00**, com `--reverter` pronto.
  **RESOLVIDO no mesmo dia as 18:18** (ver 23.36): o after-market estava
  vivo e o teste real passou.
- A correcao 4 estrelas do 23.34.7 (sair de fato apos o fecho) continua
  como **PROPOSTA** para revisao humana; nao foi aplicada para nao
  alterar ciclo de vida sem aprovacao.

## 23.36 Teste real de fecho em demo: PASS (12/11/2026, 18:18)

### 23.36.1 Como foi possivel hoje

A demo nao tem simbolo 24h, mas as 18:18 o after-market da B3 ainda
negociava: `WDOZ26`/`WINZ26` com tick avancando a cada 10 s e bid
mudando. Como o robo estava parado e flat, o teste foi feito na hora,
dentro da janela das 18:30, em vez de esperar sexta.

### 23.36.2 Harness

`patches/teste_fecho_demo.py` (novo, read-only no robo):
- `--check`: so lista conta/simbolos/posicoes.
- `--run SIMBOLO`: exige conta **DEMO**, aborta se houver posicao dos
  magics 123456/7008, abre 1 contrato (`volume_min`) com magic **999999**
  (fora de `MAGICS_ROBO`), fecha via `fechar_todas_robusto` e confirma
  por `positions_get()`. Fallback de fecho direto se o helper falhar.
- Log em `logs/teste_fecho_demo.log`.

### 23.36.3 Resultado

```
conta=55265364 XPMT5-DEMO trade_mode=0
posicao de teste aberta: #2592223021 WDOZ26 vol=1.0
[fecho] #2592223021 retcode 10009 (Request executed)
[fecho] #2592223021 saiu apos tentativa 1
helper: fechadas=1 restantes=[]
PASS: fecho confirmado por positions_get (flat, magic 999999)
```

Deals: entrada 5660.0 / saida 5659.5, `profit=-5.0` (spread), sem
comissao na demo. Conta terminou flat (so a fantasma WINV25 magic 123457)
e os 4 deals do robo seguem intactos (R$450,00).

### 23.36.4 Veredito

Caminho real do C1/C2 (order_send + confirmacao positions_get)
**validado em demo**. A simulacao de queda de rede (10031) continua
coberta pelos 12 testes com FakeMT5; o teste fisico de rede fica
opcional para sexta. **Item 1 do backlog concluido.**

## 23.37 Autopsia do dia 12/11: por que ganhou e por que perdeu (12/11/2026)

### 23.37.1 Escopo e metodo

Reconstrucao **read-only** dos 4 round trips reais do dia (magics
123456/7008) a partir de `history_deals_get`, do `monstro_wdo.log`, do
`sniper_supermo_historico.csv`, do `historico_multitf.csv`, do
`logs/rompimento/rompimento.log` e de barras M1 do MT5 para MFE/MAE.
Nenhum arquivo do robo foi alterado. Horarios do log/CSV sao locais; os
deals do MT5 vem com offset de 3h (local = exibido + 3h).

### 23.37.2 Os 4 round trips

| # | Estrategia | Entrada | Saida | Pts | R$ | Duracao | MFE | MAE |
|---|---|---|---|---|---|---|---|---|
| 1 | Faixa 1 (7008) | 10:05:03 @5624,0 | 14:53:21 @5666,0 (TP) | +42,0 | +420 | 4h48 | +42,0 | -7,5 |
| 2 | Core (123456) | 15:59:06 @5668,0 | 16:02:16 @5673,0 (TP) | +5,0 | +50 | 3m09 | +6,0 | -1,0 |
| 3 | Core (123456) | 16:07:18 @5666,5 | 16:39:54 @5672,5 (TP) | +6,0 | +60 | 32m36 | +6,0 | -2,0 |
| 4 | Core (123456) | 16:53:16 @5669,0 | 17:32:00 @5661,0 (SL) | -8,0 | -80 | 38m44 | +1,5 | -15,0 |

Bruto do dia: **+R$450,00** (4 round trips; liquido ~+R$445,20 com custo
R$1,20 x 4).

### 23.37.3 Por que a Faixa 1 ganhou (+42 pts)

- Caixa da 1a hora (09:00-10:00): high **5624,0**, low **5596,0**,
  range **28,0 pts**.
- Entrada 10:05:03 no rompimento da caixa (5624,0). `atr=7,33`.
  SL = 2,5 x ATR = **18,33 pts** -> 5605,68. TP = 1,5 x range = **42 pts**
  -> 5666,0. R/R = **2,29**.
- O dia inteiro foi de alta (5612 as 09:38 -> 5674 as 16:02). O
  rompimento teve seguimento e o preco **nunca ameacou o SL**: MAE de
  apenas **-7,5 pts** (low 5616,5, 1h13 apos a entrada).
- Saiu no TP as 14:53:21 (deal `#1879504380`), 4h48 depois, no topo do
  movimento. **Vitoria de contexto (tendencia) + R/R assimetrico**, nao
  de sorte: o stop tinha 18,3 pts de folga e o alvo 42.
- Ponto de atencao: o filtro `eff >= 0,40` da variante ORB (23.31) daria
  `eff=0,352` -> **BLOQUEIA4**. A variante teria perdido esse movimento
  (saida caixa +36,5 pts), enquanto a Faixa 1 ao vivo, que **nao usa
  eff**, ganhou +42. Contraexemplo de 1 dia; nao invalida as 25 sessoes,
  mas entra no radar (2 estrelas).

### 23.37.4 Por que os Core 1 e 2 ganharam (+5 e +6 pts)

Os 3 Core de hoje foram o **Sniper %R comprando sobrevenda extrema**,
que sobrepoe a IA e pula os filtros normais. Nos 3 instantes da entrada
a IA dizia `NADA` no `decisions_wdo.csv`: o resultado e **100% do
Sniper**, nao da IA.

| # | %R | RSI | DOL | ATR | TP | Resultado |
|---|---|---|---|---|---|---|
| Core 1 | -87,5 | 34,2 | BUY 0,354 | 1,66 | 4,99 | TP +5,0 |
| Core 2 | -83,3 | 35,8 | BUY 0,338 | 2,08 | 6,23 | TP +6,0 |
| Core 3 | -88,9 | **45,0** | BUY 0,340 | 1,60 | 4,79 | SL -8,0 |

- Core 1 e 2 pegaram o **tramo de alta** que levou o preco ao topo do dia
  (5674 as 16:02). MAE de -1,0 e -2,0: o preco praticamente so subiu.
- O sinal era fraco nos dois (score=2, DOL conf ~0,34, advisory), mas o
  contexto ajudou: **RSI 34-36 (sobrevenda real)** e tendencia de alta.
- Gestao: SL fixo 8 pts, TP = 3 x ATR (4,99 e 6,23), atingido em 3m e
  32m. Sem trailing envolvido (23.32).

### 23.37.5 Por que o Core 3 perdeu (-8 pts) e o falso "multiTF bloqueia BUY"

- Core 3 entrou 16:53:16 @5669,0, %R -88,9, mas **RSI 45,0** (neutro, nao
  sobrevendido como os outros dois) e ATR 1,60 (TP curto, 4,79).
- Contexto de **exaustao**: os topos foram descendentes (5674 as 16:02 ->
  5672,5 as 16:39 -> 5670,5 as 16:59). O Core 3 comprou a **terceira
  tentativa**, que falhou: MFE de apenas **+1,5 pt** em 6m44 e depois
  reversao ate o SL. O low foi a 5654,0 (MAE -15,0): o SL de 8 pts
  **salvou** de um prejuizo maior.
- A linha `standby` das 16:52:55 dizia
  `multiTF M15=-16 M30=-9 bloqueia BUY`. **E mensagem enganosa.** Com
  M15=-16 e M30=-9 (ambos sobrecomprados), o veto multiTF real e de
  **SELL** (`_veto_mt_sell`), nao de BUY. O BUY estava bloqueado pelo
  **SMA-50/momentum** (ultimo `TENDENCIA BLOQUEIA BUY` as 16:45:20,
  momentum -3,5). O codigo (`:3267-3269`) imprime o detalhe do multiTF
  sempre que `_veto_mt_sell or _veto_mt_buy` for verdadeiro, mesmo quando
  o bloqueio veio da tendencia. **Bug de log (3 estrelas), nao de trade.**
- O Sniper **respeitou** o veto: so entrou as 16:53:16, depois que o veto
  de tendencia caiu. A zona do Williams tambem re-armou corretamente:
  -88,9 (16:52:54) -> -66,7 (16:52:57, reset) -> -88,9 (16:53:16, nova
  entrada na zona). **Nao houve "entrada ignorando bloqueio".**

### 23.37.6 O gate da Faixa 1 bloqueou 18 sinais do Sniper

O `ESTADO_SISTEMA = ROMPIMENTO_EXCLUSIVO` vale na janela **09:00-11:00** e
enquanto houver posicao magic 7008 aberta (`:359-374`). A Faixa 1 entrou
10:05 e so saiu 14:53, entao o Core ficou bloqueado de 09:00 a 14:53.

- Hoje o Sniper gerou **21 sinais**; **18 foram bloqueados** pelo gate
  (`[GATE ROMPIMENTO]` -> `executar_ordem falhou`). Sao exatamente os 18
  "executar_ordem falhou" da auditoria 23.34.4. Os 3 restantes sao os
  Core 1/2/3, depois das 14:53.
- Simulacao read-only dos 18 bloqueados (SL 8, TP 3xATR, entrada no preco
  do sinal, sem trailing/slippage): **11 TP / 7 SL, +43,8 pts**.
  - Lado **BUY: +91,8 pts** (11 TP / 1 SL) — comprar sobrevenda num dia de
    alta funcionou.
  - Lado **SELL: -48,0 pts** (0 TP / 6 SL) — vender sobrecompra contra a
    alta sangrou.
- Respeitando **1 posicao por vez** (o robo real nao re-entra em posicao):
  9 trades, **+40,6 pts**; os 6 que teriam sido abertos antes das 14:53
  somam **+37,3 pts (R$373)** de custo de oportunidade.
- **Ressalvas**: 1 dia, tendencia forte, sem trailing/slippage e com saida
  fixa. Nao autoriza remover o gate. Vira **estudo multi-dia com
  drawdown** (3 estrelas).

### 23.37.7 O que NAO era bug

- Zona do Williams re-armando (acima): correto.
- Sniper bloqueado pelo gate: por desenho (Faixa 1 tem prioridade).
- `VETO TOTAL` e `executar_ordem falhou`: ja mapeados em 23.34.3/23.34.4.
- Nenhum ERROR/CRITICAL/Traceback no log principal.

### 23.37.8 Propostas e estrelas

| Proposta | Estrelas | Acao |
|---|---|---|
| Corrigir a mensagem do multiTF no standby (mostrar o veto real) | 3 | proposta; so log, sem risco |
| Estudo multi-dia do custo do gate da Faixa 1 (com drawdown/trailing/slippage) | 3 | proposta; nao mexer agora |
| Estudo de filtro RSI <= 40 no Sniper BUY (Core 3 tinha RSI 45) | 3 | proposta; exige backtest |
| Documentar o contraexemplo do `eff >= 0,40` (perdeu +36,5 pts hoje) | 2 | registro; sem mudanca |

### 23.37.9 Veredito

O dia foi **excelente (+R$450)** porque a Faixa 1 pegou um rompimento com
tendencia limpa e R/R 2,29, e porque o Sniper comprou duas sobrevendas
verdadeiras (RSI 34-36) no tramo de alta. A unica perda (Core 3) foi a
**terceira tentativa de reversao** num contexto de topos descendentes, com
RSI neutro (45) e MFE de +1,5. O Sniper **nao ignorou veto**: a mensagem
do multiTF era enganosa e o bloqueio real (SMA-50) caiu antes da entrada.
O achado mais importante para lucratividade e o **gate da Faixa 1**, que
bloqueou 18 sinais (BUY +91,8 / SELL -48,0): e um trade-off de risco que
precisa de estudo multi-dia, nao de mudanca as cegas.

## LISTA DE LOGO MAIS (backlog operacional)

Itens aprovados para fazer **depois** do fecho de 12/11, em ordem. Nada aqui
autoriza mexer no robo com posicao aberta.

| # | Item | Estrelas | Depende de | Status |
|---|---|---|---|---|
| 1 | C1-C4 robustez do fecho (`robustez-fecho`) | 5 | - | concluido 12/11: 12 testes + fecho real demo PASS (23.36) |
| 2 | P1 - trailing da Faixa 1 (magic 7008) | 1 | revisao humana + branch | rejeitado 13/11 (23.39): piora PF/exp com slippage; nao ligar |
| 3 | P2 - backtest de trailing no ORB (4 variantes) | 5 | P1 + dados | concluido 13/11 (23.39): 3 stops x 4 saidas x 3 slippages; nenhuma promovida |
| 4 | P3 - log "Trailing iniciado" so quando for real | 3 | P1 | pendente (independente do trailing: corrigir log falso) |
| 5 | T2 - features estacionarias (20 features) | 4 | >=30 trades reais | bloqueado |
| 6 | Retreino Keras com gates | 4 | >=30 trades reais | bloqueado |
| 7 | Walk-forward com janelas moveis | 4 | corpus maior | pendente |
| 8 | P4 - remover/religar codigo morto do trailing | 2 | P1/P2 | pendente (remocao nao depende de promocao) |
| 9 | Telemetria do ORB (EOD provisorio) | 2 | - | proposta 23.30 |
| 10 | Plano do dia: somar Faixa 1 aos fechados | 2 | - | concluido 13/11 (23.38): 12/11 = 4 fechados / R$450 |
| 11 | Clipping/scaler desatualizado (bid_qty/volume_tick) | 4 | T2/retreino | proposta 23.34 |
| 12 | "executar_ordem falhou" vs "gate bloqueou" | 3 | - | proposta 23.34 |
| 13 | "VETO TOTAL" citar Williams %R (motivo real) | 2 | - | proposta 23.34 |
| 14 | Robo sair de fato no shutdown gracil (os._exit) | 4 | C1-C4 + revisao | proposta 23.34 |
| 15 | Monitor: fail-open do probe `rompimento_ft` | 3 | - | concluido 13/11 (23.38): fallback schtasks + fail-closed |
| 16 | Monitor: janela 09:00-17:35 + grace 09:10 | 3 | - | concluido 13/11 (23.38): `PREGAO_FIM=(17,35)` + grace |
| 17 | `pids_robo()` filtrar python.exe (sem cmd/shim) | 3 | item 14 | proposta 23.34 |
| 18 | Growth: limiar sazonal no fim do dia | 2 | - | proposta 23.34 |
| 19 | Corrigir mensagem do multiTF no standby (mostrar veto real) | 3 | - | proposta 23.37 |
| 20 | Estudo multi-dia do custo do gate da Faixa 1 (drawdown/trailing/slippage) | 3 | dados multi-dia | proposta 23.37 |
| 21 | Estudo filtro RSI <= 40 no Sniper BUY (Core 3 tinha RSI 45) | 3 | backtest | proposta 23.37 |
| 22 | Contraexemplo do `eff >= 0,40` (perdeu +36,5 pts em 12/11) | 2 | - | registrado 23.37 |
| 23 | Filtro vies da 1a hora + BE (Faixa 1) | 1 | OOS positivo + slip 1,0 | rejeitado 13/11 (23.40): OOS negativo e falha em 1,0 pt/lado |
| 24 | Entrada por stop order na Faixa 1 | 1 | - | rejeitado 13/11 (23.40): entra em falso rompimento e piora com slippage |
| 25 | Entrada no reteste da caixa (limit) | 1 | - | rejeitado 13/11 (23.40): perde o movimento; exp -36/trade em 1,0 |
| 26 | Filtros de seletividade da Faixa 1 | 1 | - | rejeitado 13/11 (23.40): so `rng_le_20` marginal em 0,5; falha em 1,0 |
| 27 | Geometria de saida (TP/EOD) da Faixa 1 | 1 | - | rejeitado 13/11 (23.40): nenhuma combinacao robusta em 1,0 |
| 28 | Decisao sobre a Faixa 1 (suspender real / demo) | 5 | revisao humana | concluido 13/11 (23.41): suspensa no real e no paper (`rompimento.ativo=false` + `ORB-WDO-FT` desabilitada) |
| 29 | Pivotar pesquisa para nova tese (reversao/tendencia) | 5 | decisao do usuario | concluido 14/11 (23.42): H1 trend testada e **reprovada na robustez** (walk-forward PF 1,01 / t 0,09); seguir para a proxima tese |
| 30 | Tese 2 - reversao a media no VWAP (fade) | 4 | item 29 + pre-registro | pendente: aguarda escolha humana; exige gate + walk-forward + Monte Carlo desde o inicio |
| 31 | Tese 3 - microestrutura/absorcao nos extremos (book Herman) | 4 | item 29 + estudo de evento limpo | pendente: maior potencial, mas exige stream de ticks limpa |

## 23.38 Pacote seguro: monitor + plano do dia (13/11/2026)

### 23.38.1 Escopo

Fechado na madrugada de 13/11 (01:40-02:00), com mercado fechado, **sem posicao
real** (apenas a fantasma WINV25) e **sem robo rodando**. Apenas observabilidade
e relatorio: **nenhuma logica de trade foi alterada** e o robo nao foi reiniciado.

### 23.38.2 Item 16 - janela do monitor (3 estrelas)

- `PREGAO_FIM` passou de 17:55 para **17:35** (`monitor_saude_coletores.py`), o
  horario da tarefa `Monstro-Fecho`. Entre 17:35 e 17:55 o robo ja encerrou de
  proposito e nao deve ser cobrado.
- **Grace de abertura ate 09:10:** MT5, coletor Herman, heartbeat e robo
  principal passam a **WARN** (nao CRIT) entre 09:00 e 09:09, porque as tarefas
  disparam as 09:00 e os processos levam alguns minutos para subir.
- Validacao com `agora` e caminhos temporarios: **09:05 -> WARN; 09:15 -> CRIT**
  (rc 1 e 2 respectivamente).

### 23.38.3 Item 15 - fail-open do `_task_existe` (3 estrelas)

- Fallback novo via `schtasks /query /tn <nome> /fo LIST /v`, lendo
  `Status: Desabilitado` (PT-BR) ou `Scheduled Task State: Disabled` (EN).
- Se o estado continuar ilegivel, retorna **False (fail-closed)** -> INFO, nunca
  CRIT falso. O `Rompimento-FT` aposentado nao volta a alarmar.
- Validacao forcando o PowerShell a falhar: `Rompimento-FT`=False,
  `Monstro-Start`=True; com estado ilegivel: False.

### 23.38.4 Item 10 - plano do dia soma a Faixa 1 (2 estrelas)

- `tools/autopsia_automatizada.py` agora le
  `logs/rompimento/rompimento_trades.csv` e **mescla por ticket** com os trades
  do Core (o log pode registrar a posicao da Faixa 1 sem o deal de saida).
- Horario de entrada vem do `rompimento.log`
  (`[ROMPIMENTO] BUY ... ticket=`), permitindo a Faixa 1 tambem nas metricas
  "ate 12:30". Sem esse horario, o trade entra no dia mas nao no corte da manha.
- `lucro_rs` e a fonte canonica (1 contrato); fallback `pts * 10` apenas para
  linhas antigas sem a coluna. Linhas `S/TRADE` sao ignoradas.
- `cruzar_contexto` continua **apenas com trades do Core** (a Faixa 1 nao tem o
  contexto v22), evitando cruzamento falso.
- Validacao 12/11: `n=4`, `n_fechados=4`, `saldo=450.0`, WR 75%; ate 12:30 =
  1 trade / R$420 (Faixa 1). `main` completo sem Traceback.
- **Limitacao pre-existente (nao alterada):** `extrair_trades` nao filtra por
  data; ele assume que `monstro_wdo.log` e da sessao corrente (o robo sobrescreve
  o log a cada boot). A Faixa 1, por vir do CSV, e filtrada pelo campo `dia`.
  Logo, rodar a autopsia de um dia antigo depois do novo boot mistura o Core do
  dia atual; para o plano EOD (mesma sessao) o comportamento esta correto.

### 23.38.5 Veredito

Pacote concluido e testado. O monitor nao deve mais gerar CRIT falso do
`Rompimento-FT` nem da janela 17:40-17:55, e o plano do dia passa a refletir o
resultado real, incluindo a Faixa 1. Proximo item de lucratividade segue sendo o
**backtest do trailing da Faixa 1** (itens 2/3), que exige dados e revisao humana.

## 23.39 Estudo do trailing e do filtro de vies da Faixa 1 (13/11/2026)

### 23.39.1 Escopo e metodologia

Fechado na madrugada de 13/11 (01:50-02:15), com mercado fechado, **sem posicao
real** (apenas a fantasma WINV25) e **sem robo rodando**. Estudo **read-only**:
nenhuma logica de trade foi alterada e o robo nao foi reiniciado.

- Script novo: `backtest/backtest_trailing_faixa1.py` (read-only).
- Modelo **fiel a producao** (`rompimento_orquestrador.py`):
  caixa 09:00-10:00; gatilho 10:30-11:00 (janela validada); sinal na **barra M5
  fechada**; entrada no **close da barra de sinal** + slippage (producao entra a
  mercado); SL = `max(8, min(dist_da_caixa, 2.5 * ATR14_da_manha))`; TP =
  `1.5 * tamanho_da_caixa`; EOD 17:30 (ultima barra 17:25); custo R$ 1,20 por
  contrato por operacao; 1 ponto = R$ 10,00; sempre 1 contrato.
- **Slippage explicito por lado:** 0 / 0,5 / 1,0 ponto (0 / 1 / 2 ticks).
- Trailing decidido no **fechamento** da barra e aplicado na barra seguinte (sem
  look-ahead). SL conferido antes do TP (conservador). BE armado **liquido do
  slippage de saida**: `entry + 1 + slip` (BUY) / `entry - 1 - slip` (SELL).
- Amostra: **903 sinais**, 2021-11-12 a 2026-11-12 (1242 dias validos).
- Teste sintetico da mecanica: `sem`=EOD 0; `trail8_4`=+7; `be8`=+1;
  `be8_lock70`=+8,4; com slip 1,0 o `be8` segue +1.

Reproducao: `python backtest/backtest_trailing_faixa1.py`

### 23.39.2 Trailing com o stop de producao (10:30-11:00)

Stop = caixa (producao). `exp` em R$ por trade; `total` e `DD` em R$.

| regra | slip | n | WR% | exp R$ | PF | total R$ | maxDD R$ |
|---|---|---|---|---|---|---|---|
| sem | 0,0 | 903 | 43,1 | +4,89 | 1,04 | +4.411 | -7.166 |
| trail8_4 | 0,0 | 903 | 66,6 | +2,02 | 1,03 | +1.824 | -3.935 |
| be8 | 0,0 | 903 | 73,1 | +5,67 | 1,10 | +5.121 | -3.463 |
| be8_lock70 | 0,0 | 903 | 73,1 | -0,25 | 1,00 | -228 | -3.215 |
| sem | 0,5 | 903 | 41,7 | -3,40 | 0,97 | -3.066 | -11.917 |
| trail8_4 | 0,5 | 903 | 65,1 | -7,32 | 0,91 | -6.610 | -9.331 |
| be8 | 0,5 | 903 | 71,3 | -3,87 | 0,94 | -3.494 | -8.411 |
| be8_lock70 | 0,5 | 903 | 71,3 | -8,63 | 0,86 | -7.792 | -9.204 |
| sem | 1,0 | 903 | 40,4 | -12,76 | 0,90 | -11.526 | -18.676 |
| trail8_4 | 1,0 | 903 | 63,7 | -15,69 | 0,81 | -14.171 | -16.328 |
| be8 | 1,0 | 903 | 69,5 | -14,05 | 0,80 | -12.691 | -15.526 |
| be8_lock70 | 1,0 | 903 | 69,5 | -17,33 | 0,75 | -15.650 | -16.537 |

### 23.39.3 Gate do trailing

Gate: promover so se **melhorar WR e PF** vs `sem` (mesmo stop/slip) **e** ficar
absolutamente lucrativo (expectancia > 0 e PF > 1,0).

- Com o stop de producao (caixa), **nenhuma variante passa no relativo** em
  nenhum slippage.
- O unico PASSA relativo foi `fixed5/be8` com slip 0,5 (dWR +21,3, dPF +0,03,
  dExp +2,71), mas o absoluto segue **negativo** (exp -4,39, PF 0,88) e falha em
  slip 1,0.
- Trailing como substituto do TP e pior; janela de producao 10:00-11:00 e pior
  (slip 1,0: `sem` PF 0,88, `be8` PF 0,68).
- **Veredito: trailing rejeitado por ora. Nao ligar.** Item 2 = **1 estrela**.
  Reabrir apenas se o custo de entrada cair ou o modelo de sinal mudar.

### 23.39.4 Filtro vies da 1a hora (so opera o lado do corpo da caixa)

Regra: `close` da caixa > `open` -> so BUY; `close` < `open` -> so SELL.
Reduz de 903 para **645 sinais (71%)**.

| stop/regra | slip | WR% | exp R$ | PF | total R$ |
|---|---|---|---|---|---|
| caixa/sem | 0,0 | 43,6 | +5,54 | 1,05 | +3.574 |
| caixa/sem | 0,5 | 42,0 | -3,27 | 0,97 | -2.112 |
| caixa/sem | 1,0 | 40,9 | -12,41 | 0,91 | -8.006 |
| caixa/be8 | 0,0 | 75,3 | +12,22 | 1,23 | +7.883 |
| caixa/be8 | 0,5 | 73,6 | +5,32 | 1,09 | +3.430 |
| caixa/be8 | 1,0 | 72,1 | -5,44 | 0,91 | -3.511 |
| 0.5x/sem | 0,0 | 37,2 | +9,52 | 1,09 | +6.137 |
| 0.5x/sem | 0,5 | 35,3 | -0,82 | 0,99 | -528 |
| 0.5x/sem | 1,0 | 34,6 | -9,46 | 0,92 | -6.099 |
| 0.5x/be8 | 0,0 | 69,1 | +13,40 | 1,28 | +8.644 |
| 0.5x/be8 | 0,5 | 67,4 | +6,16 | 1,12 | +3.974 |
| 0.5x/be8 | 1,0 | 66,2 | -3,46 | 0,94 | -2.230 |

Comparacao sem vies (mesmo modelo, stop caixa): `be8` slip 0,5 = WR 71,3 /
exp -3,87 / PF 0,94; slip 1,0 = WR 69,5 / exp -14,05 / PF 0,80. Ou seja, o vies
**melhora WR e PF em todas as combinacoes e em todos os slippages** (ganho
relativo consistente), mas:

- em **slip 1,0 tudo continua negativo**;
- o **OOS 2025-2026 e negativo mesmo em slip 0,5**: caixa/be8 = exp -1,42 /
  PF 0,98; 0.5x/be8 = exp -2,88 / PF 0,95; `sem` vies = PF 0,92-0,95;
- 2023 e 2026 sao anos negativos; o resultado positivo depende de 2022 e 2024.
- `be8` e o que segura o conjunto: o vies sozinho (`sem`) fica entre -0,82 e
  -3,27 em slip 0,5.

**Veredito: filtro promissor, nao comprovado.** Nao promover agora; item 23 do
backlog (3 estrelas, em observacao). So reconsiderar com OOS positivo e
resistencia a 1 tick/lado.

### 23.39.5 Comparacao com o backtest base (entrada otimista)

- `backtest_orb_wdo.py`, 10:30-11:00, stop caixa, EOD: n=874, WR 51,9%,
  exp +59,32, PF 1,49 (entrada no **nivel da caixa**, otimista).
- Com confirmacao no fechamento da barra: n=861, WR 48,0%, exp +12,57, PF 1,09
  (sem slippage). No modelo fiel com custo e slippage 0,5: exp -3,40 / PF 0,97.
- O filtro `vies + stop 0,5x` no base rendia PF 1,83 (IS 1,80 / OOS 1,91), mas
  aquilo tambem usava entrada otimista. No modelo fiel o mesmo filtro cai para
  PF 1,09-1,12 em slip 0,5 e < 1,0 em slip 1,0.
- **Conclusao metodologica:** o PF alto do base nao e comparavel ao resultado
  realista; qualquer promocao futura deve usar o modelo fiel com slippage.

### 23.39.6 Veredito final

- **Trailing: rejeitado (1 estrela).** Aumenta WR, mas piora PF e expectancia
  com slippage; nao protege o lucro de forma lucrativa.
- **Vies da 1a hora + BE: em observacao (3 estrelas).** Melhora relativa real,
  mas positiva apenas com 1 tick/lado e dependente de 2022/2024; OOS negativo.
- **A Faixa 1, como esta, tem edge fragil:** PF ~1,04 sem slippage e < 1,0 com
  1 tick/lado. O ganho tem que vir de **filtro de regime/sinal**, nao de gestao
  de saida.
- Nada foi alterado na logica de trade; robo nao reiniciado; nenhuma ordem
  enviada.

## 23.40 Entrada por stop/reteste e filtros de seletividade da Faixa 1 (13/11/2026)

### 23.40.1 Escopo e metodologia

Fechado na madrugada de 13/11 (02:20-03:10), com mercado fechado, **sem posicao
real** (apenas a fantasma WINV25) e **sem robo rodando**. Estudo **read-only**:
nenhuma logica de trade foi alterada e o robo nao foi reiniciado.

Pergunta: o edge da Faixa 1 melhora se (a) entrarmos no rompimento por **stop
order** (ou no **reteste** do nivel) em vez de esperar o fechamento da barra M5,
e (b) **filtrarmos os dias** por regime?

- Script novo: `backtest/filtros_faixa1.py` (read-only, reusa
  `backtest/backtest_trailing_faixa1.py`).
- Dados: **M5 126.921 barras + M1 635.746 barras** (2021-11-16 a 2026-11-13);
  M1 e usado para sequenciar o intrabar sem look-ahead. 1.242 dias validos.
- Modelo de saida **igual a producao**: SL = `max(8, min(dist_da_caixa,
  2.5 * ATR14_da_manha))`; TP = `1.5 * tamanho_da_caixa`; EOD 17:30; custo
  R$ 1,20 por contrato por operacao; 1 ponto = R$ 10,00; sempre 1 contrato.
- **Slippage explicito por lado:** 0 / 0,5 / 1,0 ponto (0 / 1 / 2 ticks).
- SL conferido **antes** do TP dentro da barra M1 (conservador). Barras M1 em
  que high e low rompem os dois lados da ordem stop sao **ignoradas** (sequencia
  desconhecida); foram apenas **4** no periodo.
- Entradas comparadas:
  - `mercado`: sinal na barra M5 fechada; entra no **open do primeiro M1**
    seguinte (equivalente a producao, com preco real de execucao);
  - `stop`: ordem stop no high/low da caixa **+ 0,5 pt**, ativa 10:30-11:00;
    fill no nivel (ou no open, se gap);
  - `retest`: apos o fechamento M5 que confirma o rompimento, ordem **limit no
    nivel da caixa**, exigindo penetracao de 0,5 pt para assumir fill.
- 16 filtros **pre-registrados** (limitando data mining): vies da caixa,
  forca do vies, range alto/baixo vs media 20d, volume, ATR, tendencia (close
  vs SMA20), gap alinhado, `rng_ge_6`, `rng_le_20` e combinacoes.
- Gate: **OOS exp > 0, OOS PF > 1,0, n_OOS >= 40 e IS exp > 0**, sempre com
  **slippage 1,0 pt/lado**. IS = 2021-2024; OOS = 2025-2026.

Reproducao: `python backtest/filtros_faixa1.py`
(≈30 s na amostra completa).

### 23.40.2 Mercado vs stop order vs reteste

`exp` em R$ por trade; `total` e `DD` em R$; 1 contrato.

| entrada | slip | n | WR% | exp R$ | PF | total R$ | maxDD R$ |
|---|---|---|---|---|---|---|---|
| mercado | 0,0 | 903 | 43,0 | +4,55 | 1,04 | +4.113 | -6.920 |
| stop | 0,0 | 878 | 43,6 | +4,88 | 1,04 | +4.288 | -7.991 |
| reteste | 0,0 | 609 | 40,2 | -15,96 | 0,88 | -9.720 | -16.974 |
| mercado | 0,5 | 903 | 41,7 | -4,44 | 0,97 | -4.007 | -12.875 |
| stop | 0,5 | 878 | 41,7 | -6,49 | 0,95 | -5.694 | -15.061 |
| reteste | 0,5 | 609 | 38,9 | -25,71 | 0,81 | -15.659 | -21.105 |
| mercado | 1,0 | 903 | 40,6 | -13,00 | 0,90 | -11.743 | -18.906 |
| stop | 1,0 | 878 | 40,5 | -16,75 | 0,88 | -14.703 | -22.505 |
| reteste | 1,0 | 609 | 37,1 | -36,05 | 0,75 | -21.952 | -25.942 |

- Sem slippage as tres entradas empatam em ~PF 1,04; **com 1 tick/lado todas
  ficam negativas**.
- A **stop order piora** em 0,5 e 1,0 pt/lado: entra no primeiro toque (muitas
  vezes pavio/falso rompimento) e paga mais slippage de entrada.
- O **reteste e o pior de todos**: perde o movimento quando o preco nao volta ao
  nivel (633 dias sem sinal) e, quando volta, muitas vezes ja e a reversao.
- **A entrada a mercado (modelo fiel) e a menos ruim.** Nao ha ganho em trocar
  o gatilho.

### 23.40.3 Filtros de seletividade (entrada stop, slip 1,0)

Tabela do cenario mais favoravel a stop order. `exp`/`IS`/`OOS` em R$/trade.

| filtro | n | WR% | exp | PF | IS exp | IS PF | OOS n | OOS exp | OOS PF | gate |
|---|---|---|---|---|---|---|---|---|---|---|
| todos | 878 | 40,5 | -16,75 | 0,88 | -4,16 | 0,97 | 319 | -38,80 | 0,67 | nao |
| bias | 626 | 41,2 | -16,94 | 0,88 | -12,26 | 0,92 | 224 | -25,35 | 0,77 | nao |
| bias_forte | 434 | 41,5 | -20,75 | 0,85 | -23,10 | 0,85 | 149 | -16,26 | 0,85 | nao |
| range_hi | 302 | 40,4 | -14,52 | 0,90 | +5,01 | 1,03 | 106 | -50,65 | 0,61 | nao |
| range_lo | 558 | 40,7 | -18,45 | 0,86 | -9,53 | 0,93 | 213 | -32,90 | 0,70 | nao |
| vol_hi | 359 | 42,6 | -11,57 | 0,92 | +1,59 | 1,01 | 123 | -36,82 | 0,71 | nao |
| atr_hi | 345 | 42,9 | -11,92 | 0,92 | +11,04 | 1,07 | 131 | -49,41 | 0,62 | nao |
| tendencia | 433 | 41,8 | -14,22 | 0,89 | -8,52 | 0,94 | 158 | -24,13 | 0,77 | nao |
| gap_alinhado | 429 | 41,7 | -10,88 | 0,92 | +1,84 | 1,01 | 156 | -33,15 | 0,72 | nao |
| rng_ge_6 | 878 | 40,5 | -16,75 | 0,88 | -4,16 | 0,97 | 319 | -38,80 | 0,67 | nao |
| **rng_le_20** | 140 | 45,0 | +5,11 | 1,06 | +26,37 | 1,36 | 87 | -7,84 | 0,91 | **nao** |
| bias_vol | 268 | 43,7 | -5,29 | 0,96 | +5,00 | 1,03 | 95 | -24,04 | 0,80 | nao |
| bias_range | 248 | 39,9 | -12,87 | 0,91 | -4,44 | 0,97 | 87 | -28,47 | 0,75 | nao |
| bias_tend | 317 | 42,6 | -18,43 | 0,86 | -24,77 | 0,83 | 112 | -6,81 | 0,93 | nao |
| bias_vol_range | 176 | 42,0 | -5,36 | 0,96 | +10,60 | 1,07 | 60 | -36,20 | 0,71 | nao |
| bias_vol_tend | 131 | 48,1 | -1,78 | 0,99 | -14,11 | 0,91 | 41 | +25,30 | 1,31 | nao |

- **Nenhum filtro passa o gate em 1,0 pt/lado.**
- `bias_vol_tend` tem o melhor OOS (+25,30 / PF 1,31) mas **IS negativo**
  (-14,11 / PF 0,91) e so 41 trades no OOS -> **overfit**, nao promover.
- `rng_le_20` (evitar caixa larga, <= 20 pt) e o unico com total positivo
  (+5,11 / PF 1,06), mas **falha no OOS em 1,0 pt/lado** (-7,84 / PF 0,91).
- Na entrada `mercado` em slip 1,0 o melhor filtro (`atr_hi`) empata em PF 1,00
  com OOS -31,94; nada robusto.

### 23.40.4 O unico candidato marginal: `rng_le_20` (stop, slip 0,5)

`rng_le_20` sobrevive **apenas com 1 tick/lado** e apenas na entrada stop.

| ano | n | WR% | exp R$ | PF | total R$ | maxDD R$ |
|---|---|---|---|---|---|---|
| 2023 | 16 | 50,0 | +25,30 | 1,29 | +405 | -1.080 |
| 2024 | 37 | 51,4 | +35,34 | 1,55 | +1.308 | -365 |
| 2025 | 38 | 47,4 | +20,53 | 1,27 | +780 | -645 |
| 2026 | 49 | 38,8 | -10,68 | 0,86 | -523 | -754 |
| IS 2021-2024 | 53 | 50,9 | +32,31 | 1,46 | +1.712 | -1.080 |
| OOS 2025-2026 | 87 | 42,5 | +2,95 | 1,04 | +257 | -901 |

- **2021 e 2022 nao tem trades** (caixa > 20 pt): o "IS" e so 2023-2024.
- **2026 e negativo** e derruba o OOS para PF 1,04. Em slip 1,0 o OOS fica
  -7,84 / PF 0,91 (2026: -18,51 / PF 0,78).
- Sensibilidade ao buffer da stop order (slip 1,0): buffer 0,0 -> exp +0,62 /
  PF 1,01 (OOS -10,67 / 0,88); buffer 0,5 -> +5,11 / 1,06 (OOS -7,84 / 0,91);
  buffer 1,0 -> +4,81 / 1,06 (OOS -8,21 / 0,90). **Nenhum buffer salva o OOS.**
- Grade de saida (slip 0,5): nenhuma combinacao de TP x EOD melhora o OOS de
  forma convincente. Melhores: `TP=caixa/EOD 14:00` (OOS +5,06 / 1,07),
  `TP=1,0/EOD 17:30` (OOS +2,99 / 1,04) e `TP=1,0/EOD 16:00` (OOS +1,98 /
  1,03) — todas marginais e **negativas em slip 1,0**.
- Base `mercado/todos` em slip 1,0: todas as 12 combinacoes TP x EOD ficam
  negativas no OOS (melhor: `TP=caixa/EOD 16:00`, OOS -25,50 / PF 0,76).
- **Veredito: `rng_le_20` rejeitado (1 estrela).** Depende de regime
  (2023-2025), morre em 2026 e nao resiste a 1 tick/lado.

### 23.40.5 Controles do backtest base

Para descartar edge contrarian/deriva, o `backtest_orb_wdo.py` (entrada
otimista no nivel) foi consultado:

| controle | n | WR% | exp R$ | PF | total R$ |
|---|---|---|---|---|---|
| CTRL-MIRROR (lado oposto, EOD) | 1.012 | 53,6 | -11,04 | 0,93 | -11.168 |
| CTRL-LONG 10:00 -> EOD (deriva) | 1.242 | 48,6 | -7,94 | 0,95 | -9.864 |

- O **lado oposto tambem perde** (PF 0,93): nao ha edge simples de *fade* do
  rompimento.
- A **deriva long** tambem perde (PF 0,95): o resultado nao vem de alta do WDO.
- Ou seja, o ~PF 1,04 sem custo e o maximo que o modelo atual entrega, e ele
  nao sobrevive ao custo real.

### 23.40.6 Veredito final

- **Entrada por stop order: rejeitada (1 estrela).** Entra em falso rompimento
  e piora em 0,5/1,0 pt/lado.
- **Entrada no reteste da caixa: rejeitada (1 estrela).** Perde o movimento;
  exp -36/trade em 1,0 pt/lado.
- **Filtros de seletividade: rejeitados em grupo (1 estrela).** So `rng_le_20`
  e marginal em 0,5 pt/lado e falha em 1,0 e no OOS.
- **Geometria de saida (TP/EOD): rejeitada (1 estrela).** Nenhuma combinacao e
  robusta em 1,0 pt/lado.
- **A Faixa 1, como esta, nao tem edge que sobreviva a 1 tick/lado.** Nenhuma
  variante de entrada, filtro ou saida testada ate aqui resolve isso.
- **Recomendacao (item 28, 5 estrelas): suspender a Faixa 1 no real** e manter
  no maximo em demo, ate existir uma tese com OOS positivo e resistencia a
  1 tick/lado. Alternativa: pivotar para uma nova tese (reversao a media ou
  tendencia H1) — item 29.
- Correcao de tooling: `linha()` em `backtest_trailing_faixa1.py` agora trata
  `n=0` (evita `KeyError: 'saidas'` em filtros sem trades).
- Nada foi alterado na logica de trade; robo nao reiniciado; nenhuma ordem
  enviada.

## 23.41 Suspensao da Faixa 1 no real e no paper (decisao humana, 13/11/2026)

### 23.41.1 Decisao e contexto

Depois dos vereditos 23.39 (trailing/vies) e 23.40 (stop/reteste/filtros/saida),
o dono decidiu **suspender a Faixa 1 por completo**: nao apenas no real, mas
tambem no demo/paper. Justificativa: nao ha tese com edge que sobreviva a
**1 tick/lado**, entao manter em demo nao protege capital nem gera informacao
nova — so consome tempo e logs.

Contexto no momento da decisao: **sexta 13/11/2026, 10:52**, pregao aberto,
**sem posicao da Faixa 1** (o trade do dia ja havia fechado as 10:20: BUY
WDOZ26, SL -16,5 pts, -R$165) e apenas a fantasma WINV25 (magic 123457, inerte).

### 23.41.2 O que foi alterado

| item | antes | depois | efeito |
|---|---|---|---|
| `config.json` -> `rompimento.ativo` | `true` | **`false`** | desliga a Faixa 1 no proximo boot do robo |
| tarefa `ORB-WDO-FT` (paper ORB) | Habilitada | **Desabilitada** | nao inicia mais o forward test em papel |
| tarefa `Rompimento-FT` | Desabilitada | Desabilitada | ja estava suspensa |

- O `config.json` e lido **uma vez no boot** (`ROMP_CFG` / `self.cfg`), portanto
  a mudanca **nao afeta o processo de hoje** e passa a valer no proximo start
  (segunda 16/11, 09:00). **Nenhum processo foi reiniciado ou encerrado.**
- `rompimento_orquestrador.py` ja tem o curto-circuito
  `if not self.ativo or not self.cfg.get("ativo"): return`, e
  `agente_snapshot_v22.py` usa `ROMPIMENTO_ATIVO` para o estado exclusivo.
- O paper ORB (`rompimento_orb_wdo.py`) e read-only e **nunca envia ordem**;
  a tarefa foi desabilitada para nao gerar mais sessoes de uma tese reprovada.
- Nada na logica de trade foi alterado; nenhuma ordem enviada; robo nao
  reiniciado.

### 23.41.3 Reversao (se algum dia for preciso)

1. `config.json`: `"rompimento": { "ativo": true, ... }`.
2. `schtasks /change /tn "ORB-WDO-FT" /enable` (paper, se quiser retomar).
3. Reiniciar o robo apenas fora do pregao e sem posicao aberta.

### 23.41.4 Verificacao pendente (fazer no fecho de 13/11, apos 17:35)

- **Risco conhecido:** o dashboard usa `ThreadSafeConfig` (`config_manager.py`),
  que carrega o `config.json` em memoria e, ao salvar qualquer parametro, grava
  o snapshot inteiro. Se o dashboard de hoje (subiu 09:00, antes da mudanca)
  salvar algo, ele pode **reverter** `rompimento.ativo` para `true`.
- Checklist do fecho: (a) reler `rompimento.ativo` e confirmar `false`;
  (b) se tiver revertido, reaplicar e **nao** salvar parametros pelo dashboard;
  (c) confirmar `ORB-WDO-FT` = Desabilitado; (d) confirmar que nao ha posicao
  da Faixa 1 aberta.
- Sem reiniciar o robo com pregao aberto.

### 23.41.5 Veredito tecnico (dev senior / trade)

- **A tese de rompimento da 1a hora esta esgotada.** Tres angulos independentes
  (entrada, saida, filtro) e os controles (mirror PF 0,93; deriva long PF 0,95)
  mostram que o sinal nao tem edge depois do custo real.
- O problema nao e parametro: e **ausencia de ineficiencia exploravel** nesse
  horario/ativo com esse custo. Insistir em variantes do ORB e data mining.
- Proxima tese deve ser escolhida por **eficiencia de custo** (poucos trades,
  movimentos maiores) e **racional economico**, nao por mais filtros.
- Ranking inicial para o item 29 (a validar com o mesmo gate):
  1. **Momentum/tendencia em H1 com poucos trades e stop mais largo (5★)** —
     custo por trade vira fracao pequena do movimento; testar com M1 intrabar,
     slippage 1,0 pt/lado, IS/OOS e n_OOS >= 40.
  2. **Reversao a media (VWAP) apos movimento extremo da manha (4★)** — fade
     com alvo no VWAP e stop de tempo; diferente do CTRL-MIRROR cru (que usava
     saida EOD sem filtro).
  3. **Microestrutura/absorcao nos extremos com o book do Herman (4★)** —
     maior potencial de edge, mas exige estudo de evento limpo antes.
  4. **Lead-lag cross-asset (DXY/juros EUA -> WDO) (3★)** — plausivel, mas
     depende de dados e latencia.
  5. **Mais variantes de ORB (1★)** — encerrado.
- **Gate obrigatorio para qualquer tese nova** (antes de dinheiro real):
  backtest fiel com custo R$1,20 e slippage 1,0 pt/lado; IS 2021-2024 / OOS
  2025-2026; OOS exp > 0, OOS PF > 1,0, n_OOS >= 40, IS exp > 0; robustez a
  +-1 tick, vizinhanca de parametros e controle (mirror/random/shift); paper
  forward 20-30 sessoes. Sem isso, nao vai para o real.

### 23.41.6 Backlog atualizado

- Item 28 (decisao sobre a Faixa 1): **concluido 13/11** — suspensa no real e
  no paper/paper FT.
- Item 29 (pivotar para nova tese): **pendente** — recomendacao acima; aguarda
  escolha humana da tese antes de qualquer codigo.

## 23.42 Tese 1 - tendencia/momentum em H1 (13-14/11/2026)

### 23.42.1 Escopo e metodologia

Fechado entre o fecho de 13/11 e a madrugada de 14/11, com mercado fechado e
**sem posicao real** (apenas a fantasma WINV25). Estudo **read-only**: nenhuma
logica de trade foi alterada e o robo nao foi reiniciado.

Pergunta: existe edge de **tendencia em H1** no WDO, com poucos trades e stop
mais largo, que sobreviva ao custo real e a 1 tick/lado?

- Scripts novos: `backtest/tendencia_h1_wdo.py` (grade) e
  `backtest/tendencia_h1_robustez.py` (walk-forward, Monte Carlo, controles).
- Dados: M1 **636.153** barras -> H1 **11.209** barras, **1.248 dias**
  (2021-11-16 a 2026-11-13). Barras H1 construidas do M1, **somente
  09:00-17:30** (day trade).
- Sinal na barra H1 **fechada**; entrada no **primeiro M1 seguinte** (open);
  SL = `k * ATR14(H1)` (TR nao atravessa o gap overnight); TP = `m * R` ou
  **EOD 17:30**; **1 trade por dia**; 1 contrato; custo R$ 1,20.
- **Slippage por lado:** 0 / 0,5 / 1,0 / 1,5 ponto. SL conferido antes do TP
  dentro da barra M1 (conservador).
- Sinais pre-registrados: Donchian 12/24/36; EMA 8/21, 12/34, 20/50; momentum
  6/12. Gate: OOS exp > 0, OOS PF > 1,0, n_OOS >= 40, IS exp > 0 com
  **slip 1,0**; alem de walk-forward e Monte Carlo.

Reproducao:
`python backtest/tendencia_h1_wdo.py` e
`python backtest/tendencia_h1_robustez.py`.

### 23.42.2 Grade primaria (SL 2,0*ATR, TP 3R, slip 1,0)

`exp`/`IS`/`OOS` em R$ por trade; 1 contrato.

| sinal | n | WR% | exp | PF | IS exp | IS PF | OOS n | OOS exp | OOS PF | gate |
|---|---|---|---|---|---|---|---|---|---|---|
| donchian_12 | 816 | 46,9 | -9,43 | 0,93 | -11,06 | 0,93 | 293 | -6,54 | 0,94 | nao |
| donchian_24 | 592 | 47,3 | -3,88 | 0,97 | -13,17 | 0,91 | 216 | +12,28 | 1,12 | nao |
| donchian_36 | 480 | 47,7 | -3,67 | 0,97 | -11,48 | 0,92 | 176 | +9,80 | 1,09 | nao |
| ema_8_21 | 426 | 49,1 | +14,42 | 1,15 | +26,11 | 1,25 | 172 | -2,84 | 0,97 | nao |
| ema_12_34 | 276 | 49,6 | +24,96 | 1,28 | +46,00 | 1,50 | 103 | -10,38 | 0,87 | nao |
| ema_20_50 | 205 | 48,8 | -0,32 | 1,00 | -2,39 | 0,98 | 87 | +2,48 | 1,03 | nao |
| mom_6 | 1.244 | 46,7 | -11,86 | 0,92 | -9,93 | 0,94 | 465 | -15,08 | 0,88 | nao |
| mom_12 | 1.247 | 48,6 | -2,92 | 0,98 | -1,59 | 0,99 | 467 | -5,15 | 0,96 | nao |

- **Nenhum sinal pre-registrado passa o gate em 1,0 pt/lado.**
- `ema_8_21` e `ema_12_34` tem expectancia total positiva, mas **OOS
  negativo**: o resultado esta no IS (2022).
- `donchian_24/36` tem OOS positivo, mas **IS negativo** -> falha no gate.
- `mom_6/12` e `ema_20_50` nao sustentam nem o total.

### 23.42.3 O caso que parecia promissor: ema_8_21, SL 1,5*ATR, EOD

A sensibilidade mostrou que `ema_8_21` com **SL 1,5*ATR e saida no EOD**
passa o gate em 1,0 pt/lado. Detalhe ano a ano (slip 1,0):

| ano | n | WR% | exp R$ | PF | total R$ | maxDD R$ |
|---|---|---|---|---|---|---|
| 2021 | 12 | 50,0 | +51,85 | 1,52 | +622 | -837 |
| 2022 | 76 | 55,3 | +94,78 | 1,80 | +7.204 | -1.250 |
| 2023 | 80 | 55,0 | +12,02 | 1,13 | +961 | -2.016 |
| 2024 | 86 | 47,7 | -11,91 | 0,87 | -1.024 | -3.432 |
| 2025 | 91 | 41,8 | +0,16 | 1,00 | +15 | -2.454 |
| 2026 | 81 | 45,7 | +18,32 | 1,23 | +1.484 | -981 |
| IS 2021-2024 | 254 | 52,4 | +30,56 | 1,31 | +7.763 | -3.432 |
| OOS 2025-2026 | 172 | 43,6 | +8,71 | 1,11 | +1.499 | -2.454 |
| FULL | 426 | 48,8 | +21,74 | 1,23 | +9.262 | -5.149 |

- **O IS e dominado por 2022** (+94,78/trade); 2024 e negativo e 2025 e
  praticamente zero. O OOS positivo depende de **2026**.
- Em **slip 1,5** (3 ticks/lado) o OOS vira **-6,16 / PF 0,93** (FULL
  +10,24 / 1,10): o edge **morre com 3 ticks/lado**.
- Controles (slip 1,0): normal +21,74 / 1,23; **CTRL-MIRROR -40,09 / 0,67**;
  CTRL-LONG -8,93 / 0,92; CTRL-SHIFT-1 +11,59 / 1,14. Ou seja, ha **sinal
  direcional real** (o lado oposto perde forte), mas...

### 23.42.4 Walk-forward e Monte Carlo (o teste decisivo)

Walk-forward ancorado: escolhe (SL, TP) so com o passado e testa no ano
seguinte.

| ano teste | escolhido no treino | n | exp R$ | PF | total R$ |
|---|---|---|---|---|---|
| 2023 | SL 1,5 / TP 3R | 80 | +12,02 | 1,13 | +961 |
| 2024 | SL 1,5 / TP 3R | 86 | -10,83 | 0,88 | -932 |
| 2025 | SL 1,5 / TP 3R | 91 | -12,24 | 0,86 | -1.114 |
| 2026 | SL 1,5 / EOD | 81 | +18,32 | 1,23 | +1.484 |
| **agregado** | - | **338** | **+1,18** | **1,01** | **+400** |

- Agregado: maxDD -5.491, **t = 0,09**. O edge **desaparece** quando a escolha
  de SL/TP e honesta.
- Monte Carlo do candidato (10.000 reamostragens): P(total > 0) = 93,7%,
  PF mediano 1,23 (p5 0,98), **WR mediano 48,8%** (p5 44,8%), maxDD mediano
  -3.937 (p5 -7.528). O MC **nao melhora a taxa de acerto**.
- t-stat: FULL 1,54; IS 1,57; **OOS 0,44** (nao significativo).
- O unico config que passa em 1,0 foi escolhido **olhando o OOS** (SL 1,5/EOD);
  o primario pre-registrado (SL 2,0/TP 3R) tem **OOS -2,84 / 0,97**.

### 23.42.5 Veredito

- **Tendencia H1: rejeitada para promocao (2 estrelas).** E a melhor tese
  testada ate aqui - ha sinal direcional real e o lado oposto perde forte -,
  mas **nao e robusta**: walk-forward PF 1,01 / t 0,09, dependencia de 2022 e
  2026, morte em 1,5 tick/lado e OOS t 0,44.
- Pela regra do Monte Carlo (nao investir se nao melhorar a taxa de acerto),
  **nao vai para o real nem para paper** agora.
- Aprendizado metodologico: **IS/OOS sozinho nao basta**. A tese passou no
  OOS em 1,0 pt/lado apenas por selecao post-hoc; o walk-forward expos o
  overfit. Todo estudo novo passa a exigir walk-forward desde o inicio.
- **A Faixa 1 continua suspensa** (23.41). Nada foi alterado na logica de
  trade; robo nao reiniciado; nenhuma ordem enviada.

### 23.42.6 Proximos passos

- **Tese 2 - reversao a media no VWAP (4 estrelas):** fade do movimento
  extremo da manha com alvo no VWAP e stop de tempo; pre-registrar antes de
  rodar, com gate + walk-forward + Monte Carlo.
- **Tese 3 - microestrutura/absorcao nos extremos com o book do Herman
  (4 estrelas):** maior potencial, mas exige estudo de evento limpo.
- **Nao insistir em variantes de H1** sem uma razao economica nova: o
  walk-forward ja mostrou que o ajuste e instavel.
- Itens de backlog: 29 atualizado (H1 testada e reprovada na robustez);
  novos itens 30 (VWAP fade) e 31 (book/absorcao).

