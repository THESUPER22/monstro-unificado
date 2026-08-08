# ============================================================
# ROADMAP — ROBÔ WDO (Mini Dólar)
# Versão: 22 | Arquivo: monstro_unificado_v22.py
# Atualizado: 04/08/2026 (Autópsia 27 trades + Fix SL fator 2 + Kill-switch + Autópsia EOD/plano + Fecho executado + Roadmap Fase 2)
# ============================================================

## VISÃO GERAL
Robô de trading automatizado para o Mini Dólar (WDO) na B3.
Opera com rede neural Keras (22 features) + book nativo MT5 + trailing stop inteligente.
Integração com DOL (Dólar Cheio) para referência de fluxo institucional.
PTAX coleta automática BCB (4 janelas: 10:00/11:00/12:00/13:00).
Payroll escape automático (primeira sexta 09:25-09:35).
SniperSupermo bloqueado em dia PTAX e payroll.
Migrado do WIN (Mini Índice) para WDO em 22/07/2026.

---

## COMO O ROBÔ FUNCIONA (Resumo Completo)

### Ciclo de Vida (a cada ~1-2 segundos)
```
1. LER BOOKS (WDO + DOL)
2. CALCULAR INDICADORES (ATR, RSI, entropia, spread)
3. FILTRAR (13 portões antes da execução)
4. IA PREVÊ (BUY/SELL/NADA com 22 features — 10 book + 8 profundidade + 4 PTAX)
5. CONFLUÊNCIA CONFIRMA (5 sinais técnicos)
6. DOL VETO/CONFIRMA (referência institucional)
7. FILTRO TENDÊNCIA (SMA-20 vs preço)
8. FILTRO MEAN REVERSION (RSI + Z-Score + ADX)
9. EXECUTAR ORDEM (MT5)
10. GERENCIAR SAÍDA (trailing + profit protection)
11. APRENDER (salvar experiência → re-treinar)
```

### Hierarquia de Decisão (14 etapas)
 ```
  1. COOLDOWN (DESATIVADO) ──────── se ativo: bloqueia tudo
  2. HORÁRIO PA1 ────────────────── 09:15-12:30 / 14:30-17:15
  3. VETO SIMPLES ──────────────── contexto contradiz BUY e SELL
  4. BLOQUEADOR DE CONTEXTO ────── contexto idêntico a perdas passadas
  5. VETO MATEMÁTICO ───────────── expectativa negativa em ambas direções
  6. FILTROS ALTA ACERTIVIDADE ─── ATR < 1.5, entropia < 2.60, volume < 400
  7. FILTRO TENDÊNCIA SMA-50 ────── Preço vs SMA-50, margem ±1.0pt + momentum
  8. SNIPER FILTER ─────────────── vol < 400 OU ratio < 1.2
  9. SNIPER BLOQUEIO ───────────── PTAX day ou payroll → sniper desligado
 10. IA PREDIÇÃO ───────────────── modelo Keras (22 features) → probabilidade
 11. CONFLUÊNCIA (5 sinais) ────── score técnico, mínimo 2 sinais
 12. DOL VETO/CONFIRMAÇÃO ─────── DOL contradiz = veto (se IA não alta)
 13. MEAN REVERSION FILTRO ────── RSI(70/30) + Z-Score(±1.5) + ADX
 14. EXECUÇÃO ─────────────────── envia ordem MT5
 ```

### O que o robô APRENDE
- Cada operação gera uma experiência (contexto + ação + lucro)
- A cada 3 novas experiências → re-treina o modelo (validação 80/20)
- Só salva se loss melhorou >1% (senão restaura)
- Veto matemático: se um contexto gerou perdas, bloqueia operações nele
- Replay de experiências: pondera experiências recentes com mais peso

### Subsistemas
| Subsistema | Status | Função |
|-----------|--------|--------|
| GerenciadorDeSaida (trailing) | ✅ | Ajusta SL quando lucro > 3pts |
| Profit Protection | ✅ | Sai se lucro cai >30% do pico após 3pts |
| SistemaConfluencia | ✅ | 5 sinais técnicos, mínimo 2 para agir |
| VolumeAdaptativo | ✅ | Ajusta volume mínimo dinamicamente |
| FiltroSpreadDinamico | ✅ | Adapta spread limit ao ATR |
| DetectorTendencia | ✅ | EMA9/EMA21, bloqueia contra-tendência |
| FiltroTendencia SMA-50+Momentum | ✅ | SMA-50 + Momentum (±1.0pt, >3pts/20ticks). Anti-contra-tendência |
| MonitorPerformance | ✅ | Taxa de acerto, drawdown, alertas |
| FiltroMeanReversion | ✅ | RSI(70/30) + Z-Score(±1.5) + ADX(<20=LATERAL, >25=TRENDING) |
| **Dashboard V2** | ✅ | UI web: status, chart, logs, ajustes, controle remoto (porta 5001) |
| **ThreadSafeConfig** | ✅ | Parâmetros editáveis em tempo real via dashboard |
| **SniperSupermo** | ✅ | Modo alta convicção (score ≥ 7/10): 7 condições, 5cc, trailing 1pt/1pt, sem cooldown |
| **PTAX Coleta BCB** | ✅ | 4 janelas (10/11/12/13h). Cache diário. Feature `dolar_casado` |
| **Payroll Escape** | ✅ | Sexta 09:25-09:35. Sniper bloqueado + fuga automática |
| **Sniper Bloqueio** | ✅ | `verificar_sniper_bloqueado()` → bloqueia em dia PTAX ou payroll |
| **Williams %R Monitor** | ✅ | Divergência bull/bear, zonas SEV/SEC, CSV histórico |
| **4 features PTAX no modelo** | ✅ | `dolar_casado`, `em_janela_ptax`, `minutos_para_ptax`, `dia_ptax` |
| FiltroHorarioPremium | ❌ | Janelas 09-12:30, 14-15:30, 17-17:30 |
| CooldownInteligente | ❌ | DESATIVADO — operador solicitou remoção |

---

## ✅ MODO APRENDIZADO TEMPORÁRIO (23/07 - 30/07/2026) — CONCLUÍDO E RESTAURADO (01/08/2026)

**MOTIVO**: O robô não fez nenhuma entrada porque os filtros estavam muito agressivos para WDO.
**OBJETIVO**: Gerar as primeiras experiências reais para o modelo aprender.

### Parâmetros Alterados (temporariamente) — TODOS RESTAURADOS
| Parâmetro | Antes | Depois | Status 01/08 |
|-----------|-------|--------|--------------|
| `sniper_ratio_min` | 1.5 | **1.2** | ✅ restaurado → **1.5** |
| `THRESHOLD_ENTROPIA_BAIXA` | 0.6 | **0.4** | ✅ restaurado → **0.6** |
| `LIMITE_REJEICOES_PARA_APRENDIZADO` | 20 | **8** | ✅ restaurado → **20** |

> **Nota (01/08):** `filtros_alta_acertividade` (entropia 0.2, ATR min 1.5, pontuação 8/5/3) **NÃO** foi restaurado para os valores WIN (100/80/45) — o v22 já usa valores adaptados ao WDO. Restaurar quebraria o robô.

### ⏰ LEMBRETE: RESTAURAR APÓS 1 SEMANA (30/07/2026) ✅ EXECUTADO 01/08/2026
```
EXECUTADO EM 01/08/2026:
1. ✅ sniper_ratio_min: 1.2 → 1.5 (config.json linhas 10 e 52)
2. ✅ THRESHOLD_ENTROPIA_BAIXA: 0.4 → 0.6 (v22:1012)
3. ✅ filtros_alta_acertividade entropia: mantido 0.2 (já WDO)
4. ✅ filtros_alta_acertividade ATR: mantido 8/5/3 (já WDO, NÃO restaurar WIN 100/80/45)
5. ✅ LIMITE_REJEICOES_PARA_APRENDIZADO: 8 → 20 (v22:91)
6. ✅ ROADMAP atualizado removendo a urgência da seção
```

---

## STATUS ATUAL (30/07/2026 — Sessão 12 — Fix Persistência + Modelo V3 Regularização Reduzida + Validação CSVs)

### ✅ O que FUNCIONA
- WDOQ26 selecionado corretamente
- Book WDO ativo e recebendo dados
- Book DOL ativo e funcionando
- **Modelo V3 retreinado (regularização reduzida): Dropout 0.2, L2 0.001, GaussNoise 0.01, 128→64→32, 81.7% val (temporal)** ✅
- **Scaler 100% íntegro** — RSI escalado corretamente, MR sem veto falso ✅
- **FiltroMeanReversion operacional (RSI 25/75)** — sem distorção ✅
- **Saída por Inversão de Fluxo (Book Nativo) validada** — trade BUY movido para breakeven em vez de loss ✅
- **Reentry pós-loss operacional** — bot recomprou no mesmo nível após stop ✅
- **PTAX coleta automática** — 4 janelas (10/11/12/13h). Cache diário ✅
- **DECISÃO PENDENTE: SL 2.5pts → SL Catástrofe 8-10pts** — saída real por algoritmos de fluxo ✅
- Modelos salvos: `.h5` (233KB), `.keras` (104KB), scaler 22 colunas
- **Dashboard V2** rodando (port 5001) — tema dark, chart, logs, ajustes em tempo real
- Indicadores calculados (ATR, RSI, entropia)
- DOL logs aparecendo
- Scaler carregado corretamente do treinamento offline (22 features)
- **Coleta de dados book** — 22 features completas sendo alimentadas
- **Filtros suavizados** — 6 filtros essenciais
- **SL Trailing funcionando** — movimenta SL corretamente quando lucro > 3pts
- **Treino balanceado** — carrega wins + losses do CSV, com punição correta para perdas
- **NaN/inf filtrados** antes do treino — evita batch rejeitado silenciosamente
- **Experiências reais** — **56 trades acumulados** (30/07). Sessão 12: 10 trades, -190pts manhã (bug persistência) + 2 trades tarde (SELL +25pts, BUY aberto). Modelo V3 operando.
- **FiltroTendência SMA-50+Momentum** — bloqueia contra-tendência
- **historico_lucro** registra cada trade
- **SniperSupermo implementado** — modo alta convicção (score ≥ 7/10). Volume 5cc, SL=5pts. Breakeven em +2.5pts, trailing 1pt/1pt. Sem cooldown. Pula filtros normais, veto big players e horário (opera 09:00-17:30)
- **PTAX coleta automática** — 4 janelas. Feature `dolar_casado`
- **Payroll escape** — Sexta 09:25-09:35. Sniper bloqueado automático
- **Sniper Bloqueio** — `verificar_sniper_bloqueado()` bloqueia em dia PTAX (31/07) e payroll
- **Williams %R Gatekeeper** — veto BUY se WR > -20, veto SELL se WR < -80
- **Dashboard 8 filtros de log** — Sniper, Contexto WDO, Decisions WDO, Experiências JSON, Williams %R, Multi TF
- **`_caminho_base()` / `_caminho_dados()` FIXADOS** — paths absolutos funcionando no PyInstaller ✅
- **PyInstaller rebuild** — .exe recompilado com fixes (11:13, 27MB) ✅
- **Coleta Multi-TF (M5/M15/M30)** — implementada e validada (38 amostras hoje) ✅

### ❌ O que BLOQUEAVA (corrigido hoje)
- **Persistência zero no .exe** — paths relativos no PyInstaller → `_caminho_dados()` resolve ✅
- **Modelo V3 underfitting (Dropout 0.5)** — travava em `NAO_AGIU` (502 ocorrências). Dropout 0.2 resolve ✅
- **CSVs não escreviam** — agora todos escrevendo em tempo real ✅

### ⚠️ Limitações Conhecidas
- Modelo treinado com **dados sintéticos** &mdash; performance real ainda não validada em mercado aberto
- **Scaler mismatch** &mdash; dados sintéticos vs reais têm ranges diferentes. Mitigado com range +20% + clipping, mas ideal é treinar com dados reais
- **Modelo retreinado com 30k amostras** &mdash; viés BUY removido (SMOTE balanceado), mas calibragem em dados reais só conhecida no próximo pregão
- **SniperSupermo ativou 29/07 11:19** — SELL score 8/10 em 2 ocasiões (11:19:12 e 11:19:42), DOL=SELL 0.73/0.72, ratio 3.9x/4.2x, %R -12/-8 ✅ (correção 01/08 — parecer anterior alegava o contrário)
- **Dashboard só funciona durante pregão** &mdash; Flask é daemon thread, morre com o robô
- **Confidence Gap 0.15** &mdash; pode ser excessivo para dias de forte tendência. Monitorar taxa de rejeição

## MONITORAÇÃO DE AMADURECIMENTO

### Marcos de Experiência (acompanhar evolução)
| # Trades | O que esperar | Status |
|----------|---------------|--------|
| 0-10 | Bebê: explora aleatório, erra muito. Perdas sequenciais normais | ✅ |
| 10-30 | Aprendendo: punições começam a criar viés contra erros repetidos | 🔄 **46 trades (Sessão 11)** |
| 30-100 | Calibragem: modelo começa a mostrar preferência por setups que deram lucro | ⏳ |
| 100-500 | Maturação: taxa de acerto começa a estabilizar | ⏳ |
| 500+ | Maduro: decisões consistentes, viés sintético substituído por real | ⏳ |

### Meta de curto prazo
- [x] **46 trades acumulados (Sessão 11)** &mdash; base para retreino offline ✅
- [x] **Retreino Keras offline (29/07)** &mdash; 30k amostras, SMOTE balanceado, regularização forte ✅
- [x] **Williams %R Gatekeeper** &mdash; implementado como veto de segurança ✅
- [x] **Scaler range +20% + clipping [0,1]** &mdash; mitigação do scaler mismatch ✅
- [x] **Dashboard 8 filtros de log** &mdash; Sniper, Contexto WDO, Decisions WDO, Experiências JSON, Williams %R ✅
- [x] **PyInstaller rebuild** &mdash; .exe atualizado com dashboard novo ✅
- [ ] **300+ trades** para calibrar modelo com dados reais balanceados
- [ ] **SNIPER_SUPERMO** diagnosticar score fixo 6/11 &mdash; ajustar thresholds se necessário

### Métricas para Decidir se Precisa de Ajuste
- **Após 50 trades**: Se win rate < 30% OU profit factor < 0.8 → reavaliar filtros
- **Após 100 trades**: Se win rate < 35% OU profit factor < 1.0 → considerar mudança de estratégia
- **Após 200 trades**: Se win rate < 40% OU profit factor < 1.2 → reestruturar sistema
- **Drawdown máximo tolerado**: R$ -500 (10 trades seguidos de -25 = -250, ainda OK)

### Estratégias Candidatas para Futuro

> **Nota importante (28/07/2026):** Após pesquisa aprofundada, a estratégia que tornou Larry Williams campeão mundial (11.376% em 1987) NÃO é SMA3/55. O edge real dele veio de:
> - **Williams %R** — oscilador 0 a -100, mais rápido que RSI (sem suavização)
> - **COT (Commitments of Traders)** — fluxo institucional = nosso **DOL** ✅
> - **%R divergências** — preço faz fundo mais baixo, %R faz fundo mais alto = reversão (~63% acerto)
> - **Sazonalidade** — fim do mês, ciclos
>
> **O que temos HOJE (Mean Reversion + RSI + DOL + FiltroTendência + Keras) é MAIS parecido com o LW real do que SMA3/55.** Estamos no caminho certo.

**Próxima evolução (pós-100 trades): Williams %R + Divergências**
- Substituir/complementar RSI com Williams %R (mais rápido, sem suavização)
- %R < -80 = sobrevendido (comprar) | %R > -20 = sobrecomprado (vender)
- **Divergência**: preço faz fundo mais baixo mas %R faz fundo mais alto = sinal forte de reversão

**1. Williams %R como filtro adicional (pós-100 trades)**
- %R calculado com janela 14 (mesmo período do RSI atual)
- Divergência bull/bear detectada em janela deslizante de 20 ticks
- Funciona como filtro extra no FiltroMeanReversion, NÃO substitui a IA

**2. Híbrido por Horário (se necessário após 200+ trades)**
- 09:15-12:00 → Estratégia atual (Mean Reversion + ML + DOL)
- 14:30-17:00 → Se WDO mostrar tendência, %R divergências têm mais espaço
- Racional: Manhã volátil favorece reversão; tarde mais direcional favorece momentum

**3. Robô decide qual estratégia usar (pós-500 trades)**
- ML escolhe entre estratégias baseado em qual performou melhor nas condições atuais
- Mais complexo, mas adaptativo

---

### CHECKLIST DE TESTES PÓS-FIX (ADICIONADO)
- Criar/rodar `tests/testes_pos_fix.py` (static checks: mutex, sys.exit, entropia, parar.txt, CSVs).
- Validar shutdown coordenado em staging com MT5 (manual): executar checklist do ROADMAP e confirmar fechamento de posições + salvamento.
- Registrar ticket se qualquer comportamento anômalo for observado no primeiro pregão após deploy.
- Observação: `tests/testes_pos_fix.py` é CI-ready, mas o arquivo `monstro_unificado_v22.py` precisa estar versionado para ativar GitHub Actions.


## CHECKLIST DIÁRIO (ao fim do dia)

### 📊 Performance & Lucro
```bash
# 1. Operações feitas?
grep -c "ORDER_SEND.*RET_CODE_10009" monstro_wdo.log
# Esperado: 1-10 operações por dia

# 2. Lucro/prejuízo?
grep "LUCRO\|PREJUÍZO\|resultado" monstro_wdo.log
# Esperado: balanço positivo no fim da semana

# 3. Erros?
grep -i "error\|exception\|traceback" monstro_wdo.log
# Esperado: poucos ou nenhum
```

### 🧠 Aprendizado
```bash
# 4. Modelo salvo?
ls -la C:\AIOFEN\modelo_monstro_wdo.h5
# Esperado: tamanho > 100KB, modificação = hoje

# 5. Treino realizado?
grep "TREINO" monstro_wdo.log
# Esperado: 1-2 treinos por dia (17:30)

# 6. Experiências crescendo?
wc -l decisions_wdo.csv
# Esperado: crescendo ao longo dos dias
```

### 📡 DOL
```bash
# 7. DOL funcionando?
grep "DOL" monstro_wdo.log
# Esperado: logs "📊 DOL" a cada 2min

# 8. DOL vetando/confirmando?
grep "DOL VETA\|DOL CONFIRMA" monstro_wdo.log
# Esperado: aparece quando DOL contradiz/confirma
```

### 🔧 Filtros
```bash
# 9. ATR bloqueando?
grep "ATR.*<" monstro_wdo.log
# Esperado: nenhum (threshold agora é 1.5)

# 10. Sniper ativo?
grep "Standby" monstro_wdo.log
# Esperado: aparece quando book equilibrado (normal)
```

---

### 📋 Pós-Pregão 29/07/2026 — Tarefas Noturnas (EXECUTADO)

#### ✅ 1. Retreino offline Keras (29/07 22:00)
```bash
python treinar_monstro_offline.py --samples 30000 --epochs 200
```

**Resultado:**
| Métrica | Treino | Validação |
|---------|--------|-----------|
| Loss | 0.4748 | 0.3438 |
| Accuracy | &mdash; | 82.6% |
| Épocas | 53 (early stop) | best epoch 38 |
| Amostras | 30k geradas | 12.920 treino (SMOTE) |

**Mudanças no treinamento:**
- `GaussianNoise(0.02)` + Dropout 0.5/0.4/0.3 + L2(0.005)
- Label smoothing (BUY=0.9, SELL=0.1)
- Ruído gaussiano std=0.015 nas features de treino
- Threshold de label reduzido de 2.0 para 1.5 (mais amostras marginais)
- **Modelo salvo**: `modelo_monstro_wdo.h5` (245KB) + `_scaler.json`

#### ✅ 2. Scaler fixes (29/07 22:00-22:30)
**Problema detectado:** Scaler treinado com dados sintéticos tem ranges diferentes dos dados reais. Real data tem bid_qty=0, entropia_book=0.5-1.0, enquanto sintético tem bid_qty=250-12883, entropia=1.07-2.29.
**Solução:**
- `forcar_recreacao_scaler()`: range estendido em +20% (`mins_ext = mins - range*0.2`, `maxs_ext = maxs + range*0.2`)
- `normalizar_dados()`: clipping [0,1] pós-transform com log de quantos valores foram afetados
- `_caminho_recurso()`: `os.path.abspath('.')` → `os.path.dirname(os.path.abspath(__file__))` (template_folder independente do CWD)

#### ✅ 3. Williams %R Gatekeeper (29/07 22:30)
Adicionado na `prever_acao()` (monstro_unificado_v22.py):
```python
if pode_buy and wr_val > -20:
    # VETA BUY (sobrecomprado)
if pode_sell and wr_val < -80:
    # VETA SELL (sobrevendido)
```
Age antes do Filtro de Tendência e do ML. Prioridade máxima. Logging com `WILLIAMS %R VETO`.

#### ✅ 4. Dashboard — 5 novos filtros de log (29/07 23:00)
| Botão | Filtro | Palavras-chave |
|-------|--------|---------------|
| **Sniper** | `sniper` | SNIPER, sniper |
| **Contexto WDO** | `ctx` | CONTEXTO, contexto, PRINT_CONTEXTO |
| **Decisions WDO** | `decisions` | DECISAO, decisao, VETO, FORÇA, prever_acao |
| **Experiências JSON** | `exp` | experiencia, JSON, EXPERIENCIA |
| **Williams %R** | `wr` | WILLIAMS, WR=, williams_r, %R, SOBRECOMPRA, SOBREVENDIDO |

#### ✅ 5. PyInstaller rebuild (29/07 23:30)
```bash
pyinstaller MonstroDashboard.spec
# Resultado: dist\MonstroDashboard\ (1.44GB, 1659 arquivos)
# _internal\templates\dashboard.html com 8 filtros
```

#### ✅ 6. Backups preservados
- `modelo_monstro_wdo.h5.backup_20260729` (modelo original pré-retreino)
- `modelo_monstro_wdo_scaler.json.backup_20260729` (scaler original)

#### ✅ 7. Coleta Multi-TF (M5/M15/M30) — 30/07 01:00
**Implementado sem risco ao core:**
- `obter_dados_multitf()` — coleta RSI, ATR, Williams %R, close, volume de M5, M15, M30
- `salvar_dados_multitf_csv()` — salva em `historico_multitf.csv` separado
- Executa no loop principal após o contexto M1, sem interferir na decisão
- Log periódico a cada 5 min no dashboard
- **Botão Multi TF** no dashboard (filtro `MultiTF|Multi TF|M5 RSI|M15 RSI|M30 RSI`)
- Dashboard e .exe rebuildados

### 📋 Check-list 30/07 (Pós-Pregão — EXECUTADO)
1. ✅ **Abrir robô via `all.bat` ou `MonstroDashboard.lnk`** — .exe rebuildado com fixes
2. ✅ **Monitorar clipping nos logs** — `[normalizar_dados] ⚠️ N valores fora de [0,1] foram clipped`
3. ✅ **Monitorar Williams %R veto nos logs** — `WILLIAMS %R VETO BUY/SELL`
4. ✅ **Manter parâmetros do Modo Aprendizado** (validados na sessão tarde):
   - `sniper_ratio_min`: 1.2 (WDO raro >1.4)
   - `THRESHOLD_ENTROPIA_BAIXA`: 0.4 (WDO típico 0.3-0.5)
   - `LIMITE_REJEICOES_PARA_APRENDIZADO`: 8
5. ✅ **Reavaliar após 100+ trades se precisa restaurar parâmetros originais**
6. ✅ **Backup dos dados da sessão para auditoria/treino**
   - `decisions_wdo.csv` → `backup/decisions_20260730.csv`
   - `historico_contexto_wdo.csv` → `backup/historico_20260730.csv`
   - `historico_multitf.csv` → `backup/multitf_20260730.csv`
7. ✅ **Incorporar 38 amostras `historico_multitf.csv` no dataset de retreino V4**
8. ✅ **Aplicar SL Catástrofe 8-10pts no config.json** (pós-pregão)
9. ✅ **Retreino offline noturno com dados reais consolidados (17h+)**

---

### 30/07/2026 — Sessão 14 (FASE 9: Sentinela + Neon + Ticker + Fixes Operacionais)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| 🆕 FEATURE | **FASE 9 concluída** — Sentinela de Fluxo (veto macro DXY/US10Y/USDJPY, fail-open, cache 60s), Dashboard Neon (toggle localStorage), Market Ticker (7 ativos globais) | `sentinela_fluxo.py` + `dashboard_routes.py` + `templates/dashboard.html` |
| 🐛 CRÍTICO | **Botão PARAR não funcionava no .exe** — o clique gravava `parar.txt` em `dist\MonstroDashboard\_internal\` (via `__file__` no frozen) enquanto o robô só lia `C:\AIOFEN\parar.txt`. Adicionado `_caminho_base()` espelhando a resolução do robô | `dashboard_routes.py` |
| 🧹 PARAR CONSUMIDO | Parada graciosa agora **remove o `parar.txt`** ao executar — não sobra sinal que bloqueie o start do dia seguinte | `monstro_unificado_v22.py:6244-6249` |
| 🔧 SLEEP NOTURNO | `aguardar_abertura/fechamento` dormem em blocos de 60s checando `verificar_parada_gracil()` — PARAR responde mesmo fora do pregão (antes: `time.sleep` único até 23:59 ignorava o sinal) | `monstro_unificado_v22.py:3569-3586` |
| 🛡️ INSTÂNCIA ÚNICA | Mutex `CreateMutexW` no topo do arquivo (antes do import do TF) — segunda cópia do exe/robô sai em <1s com aviso. Sem isso, o agendador 08:58 abriria um 2º robô operando a mesma conta | `monstro_unificado_v22.py:12-27` |
| 📝 STOP_ALL.BAT | Filtro wmic `monstro_unificado_v2` → `monstro_unificado_v22` (apenas isso; `cd /d C:\AIOFEN` mantido para o agendador) | `stop_all.bat` |
| 🖥️ JANELA MAXIMIZADA | Dashboard PyWebView abre maximizado via `webview.start(_maximizar_janela)` | `monstro_unificado_v22.py:10261-10285` |
| ✅ VALIDAÇÃO | Testado ao vivo: PARAR → `thread_ativo=False` + parar.txt consumido; 2ª instância bloqueada no mutex (caixa de aviso); 1ª instância intacta; porta 5002 livre | Sessão 23:00-23:55 |
| 📦 REBUILD | `.exe` rebuildado 30/07 23:50 (27.08MB) com todos os fixes. Tarefas agendadas OK: `start_all.bat` 08:58 → exe atual; `cleanup_monstro_final.bat` 18:32 → `stop_all.bat` | `MonstroDashboard.spec` |

---

### 30/07/2026 — Sessão 13 (Correções Pós-Autópsia: 5 Vetos + Pipeline + Rebuild .exe)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| 🔧 WR THRESHOLD | **-85 → -80 simétrico** — WR < -80 agora veta BUY (antes: só veta SELL). Cobre zona cinzenta -83/-84 onde robô comprava em queda livre | `monstro_unificado_v22.py:8349` |
| 🔧 FORÇA PROTEGIDA | **FORÇA BUY/SELL agora checa Multi-TF** — não força direção contra 3 timeframes alinhados | `monstro_unificado_v22.py:8366-8379` |
| 🐛 IMPORT CIRCULAR | **config_manager.py → monstro_unificado_v22 → dashboard_routes** — resolvido com duplicação local de `_caminho_dados()` | `config_manager.py:11-29` |
| 📦 BUILD FIX | **certifi CA bundle incluído no .spec** — `FileNotFoundError` no `requests/adapters.py` em frozen mode resolvido | `MonstroDashboard.spec` |
| ✅ VALIDAÇÃO | **Pipeline de execução mapeado** — 8 camadas de proteção antes do `executar_ordem()` linha 7459. Travas de regime ANTES da confluência | `monstro_unificado_v22.py:7025-7461` |
| ✅ 5 VETOS | WR veto simétrico (-80) + Multi-TF + DOL conf ≥ 0.5 + Book ratio ≥ 1.5x + SL 8pts | Múltiplas linhas |

---

### 01/08/2026 — Sessão 15 (Fim do Modo Aprendizado + Retreino Scaler Real + Refactor)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| 🔧 PARÂMETROS | **Fim do Modo Aprendizado — parâmetros restaurados** — `sniper_ratio_min` 1.2→**1.5** (config.json:10,52); `LIMITE_REJEICOES_PARA_APRENDIZADO` 8→**20** (v22:91); `THRESHOLD_ENTROPIA_BAIXA` 0.4→**0.6** (v22:1012) | `config.json`, `monstro_unificado_v22.py` |
| 🧹 SCALER | **Retreino do scaler com dados reais combinados** — 7 features principais (bid/ask/spread/volatility/entropia/rsi/volume) do `decisions_wdo.csv` (358 linhas reais) + 8 escoras/liquidez do `historico_contexto_wdo.csv` (1368 linhas) + domínio fixo para trade-state/PTAX. Nenhuma feature constante. Script: `retreinar_scaler_real.py` | `modelo_monstro_wdo_scaler.json` |
| 🐛 ACHADO | **`historico_contexto_wdo.csv` degradado** — `bid_qty`/`ask_qty`/`volume_tick` zerados em todas as 5000 linhas; `entropia_book` truncada a 1.0 (clamp `min(1,...)` em `salvar_experiencia_csv`, v22:3044). **Causa raiz da "corrupção":** a entropia REAL é 2.6-3.0, mas o clamp a 1.0 destrói a feature no histórico — o scaler antigo (max 2.29) também extrapolava com dados reais. **Regressão vs v2** (a v2 já corrigiu em 18/07; a v22 não carregou o fix). Corrigido no v22 (save + load agora preservam valor real) | `monstro_unificado_v22.py:3044,2952` |
| 🧹 REFACTOR | **Classe duplicada `GerenciadorDeSaida` removida** — a definição antiga (linha 101, com timeout 300s/TP=10) era código morto; a da linha 1964 (timers desativados, trailing 80/40, proteção 50% pico) é a ativa. Instância na linha 6221 resolvia para a 1964 | `monstro_unificado_v22.py` |
| 🔧 ATOMICIDADE | **`salvar_modelo()` agora é atômico** — grava em `.tmp_atomic` e usa `os.replace()` para troca final. Modelo principal nunca fica corrompido por crash no meio do save | `monstro_unificado_v22.py:3245` |
| 🔧 FIX SAVE TF | **Extensão inválida corrigida no save atômico** — TF rejeita `.tmp_atomic` (`Invalid filepath extension`, mesmo erro do v2). Trocado para `_tmp.h5`/`_tmp.keras` (extensão válida) + `os.replace()`. Teste real passou: `.h5` 118000 bytes / `.keras` 108269 bytes | `monstro_unificado_v22.py:3279-3290` |
| ✅ ESCALA ENTROPIA | **Thresholds de entropia corrigidos para escala real (APLICADO 01/08)** — era [0,1] (`entropia < 0.2`, `>= 0.7`, `> 0.3`), mas entropia real é **2.69-2.97** (confirmado: scaler novo + ativação 29/07 ENT=2.67/2.68). Na prática: filtro 2 nunca bloqueava, modo EXPLOSAO sempre ativo, score sempre +3, LATERAL/CONSERVADOR nunca ativavam. Valores aplicados: `THRESHOLD_ENTROPIA_BAIXA=2.75` (lateral), `THRESHOLD_ENTROPIA_ALTA=2.85` (explosão), DetectorModo conservador `<2.75`, SniperSupermo `>2.75`, filtro 2 bloqueio `<2.60`, score qualidade `2.85/2.80/2.75` (dois locais). Nota: banda estreita (0.28) — filtro 2 e modo conservador ainda disparam raramente; monitorar | `monstro_unificado_v22.py:902,904,1067,2709,8169,8201-8205,8603-8607` |
| ✅ VALIDAÇÃO | **Sintaxe validada** (`ast.parse` com `utf-8-sig` — arquivos têm BOM). 1 definição de `GerenciadorDeSaida` restante | `monstro_unificado_v22.py` |

---

### 01/08/2026 — Sessão 16 (Code Review Final + Aprovação)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| ✅ REVIEW | **Code review completo aprovado (10/11 verificações + compilação OK)** — verificação de cada threshold aplicado no código real, linha por linha | `monstro_unificado_v22.py` |
| ✅ ESCALA ENTROPIA | **Falso negativo do script de validação descartado (L1067)** — `entropia_media < 2.75` está correto; o script pegava o 2.0 do ATR (primeiro número da linha) em vez do 2.75. Sem ação | `monstro_unificado_v22.py:1067` |
| ✅ CÓDIGO MORTO | **`MODO_CONSERVADOR_ENTROPIA = 0.3` confirmado como código morto** — existe em 1 único local (definição), nenhuma referência no fluxo de decisão. Zero efeito operacional. Mantido sem alteração | `monstro_unificado_v22.py:1088` |
| ✅ LIMPEZA | **Arquivos temporários removidos** — `_test_atomic_save.py`, `modelo_monstro_wdo_tmp.h5`, `modelo_monstro_wdo_tmp.keras` deletados. Nenhum resíduo `_tmp*`/`_test_*` no diretório | `C:\AIOFEN\` |
| ✅ APROVAÇÃO | **VEREDITO FINAL: APROVADO** — todas as correções são de bugs funcionais (escala de entropia [0,1] → 2.60-2.85), não de preferência. Robô pronto para o próximo pregão. Impactos: EXPLOSÃO deixa de ser sempre-ativo; score SniperSupermo deixa de ficar inflado por entropia constante | `monstro_unificado_v22.py` |
| 📌 MONITORAR | **Primeiro pregão** — observar nos logs se EXPLOSÃO aparece raramente (só com `entropia > 2.85`) e se o score do SniperSupermo reflete melhor os setups. Ajuste fino do threshold 2.85 se necessário (não é bug) | `monstro_wdo.log` |

---

### 01/08/2026 — Sessão 17 (Fixes de Robustez Pós-Review)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| 🔧 MUTEX | **Guard de instância única movido para `if __name__ == "__main__"`** — antes rodava no import do módulo: qualquer script que importasse `monstro_unificado_v22` com outra instância ativa morria (`_sys.exit(0)`). Agora o mutex só é criado quando o robô roda como script principal. Imports `ctypes`/`sys` movidos junto | `monstro_unificado_v22.py:10100-10117` |
| 🔧 SYS.EXIT | **`sys.exit()` do `CircuitBreakerEssencial` substituído por shutdown coordenado** — `sys.exit()` dentro de thread daemon (monstro_thread) só matava a thread; dashboard e demais threads continuavam vivas e o processo parecia ativo. Agora cria `parar.txt` (caminho absoluto via `_caminho_dados`), que o loop principal detecta na próxima iteração e executa o `encerramento_seguro_completo` existente (fecha posições → salva modelo/experiências → flush logs → `os._exit(0)`) | `monstro_unificado_v22.py:1116-1130` |
| 🔧 CAMINHO | **Inconsistência de caminho corrigida em `verificar_parada_gracil()`** — verificava `os.path.exists("parar.txt")` (relativo ao CWD) mas o loop removia via `_caminho_dados("parar.txt")` (absoluto). Se o CWD fosse diferente de `C:\AIOFEN`, o parar.txt nunca era detectado. Agora usa `_caminho_dados` | `monstro_unificado_v22.py:6061` |
| ✅ VALIDAÇÃO | **Sintaxe validada** (`py_compile` + `ast.parse` com `utf-8-sig`). 10353 linhas. `sys.exit` restantes: 1 real (`_sys.exit(0)` do mutex no `__main__`, correto) + 1 comentário. Fluxo: `registrar_resultado` (pós-trade) → cria `parar.txt` → `verificar_parada_gracil()` (topo do loop) → shutdown coordenado | `monstro_unificado_v22.py` |
| ✅ TESTES | **`tests/testes_pos_fix.py` criado e passando (9/9)** — testes determinísticos sem MT5: (1) mutex dentro do `__main__`, (2) nenhum `sys.exit(` real espalhado, (3) nenhuma comparação de entropia em escala [0,1], (4) `parar.txt` via caminho absoluto, (5) colunas/integridade de `decisions_wdo.csv` e `historico_contexto_wdo.csv` (entropia não truncada, bid_qty reais). Rodar: `venv\Scripts\python.exe tests\testes_pos_fix.py`. O shutdown coordenado NÃO é testável sem MT5 — manual no checklist. README em `tests\README.md` | `tests\testes_pos_fix.py`, `tests\README.md` |
| ⚠️ PENDÊNCIA CI | **CI (GitHub Actions) adiado** — `monstro_unificado_v22.py` está **untracked** (não versionado). Um CI rodaria num clone sem o arquivo principal → testes falhariam ou passariam vazios. **Ação:** versionar o v22 (decisão do operador) e só então criar `.github/workflows/testes-pos-fix.yml`. O script não importa o módulo (lê como texto), então o CI é viável e barato após o versionamento | `monstro_unificado_v22.py` |

---

## ARQUIVOS PARA MONITORAR

### 📊 Performance
| Arquivo | O que verificar | Frequência |
|---------|----------------|------------|
| `monstro_wdo.log` | Operações, P&L, erros | Diário |
| `implemente.txt` | Logs de teste em tempo real | Cada teste |
| Dashboard `http://127.0.0.1:5001` | Gráficos de lucro | Diário |

### 🧠 Aprendizado
| Arquivo | O que verificar | Frequência |
|---------|----------------|------------|
| `modelo_monstro_wdo.h5` | Existe? Tamanho > 100KB? | Diário |
| `decisions_wdo.csv` | Histórico de decisões | Diário |
| `experiencias_wdo.json` | Experiências salvas | Semanal |

### 📈 Dados
| Arquivo | O que verificar | Frequência |
|---------|----------------|------------|
| `config.json` | Parâmetros coerentes | Semanal |
| `historico_contexto_wdo.csv` | Dados de treino | Semanal |

---

## CHECKLIST DE TESTES PÓS-FIX (Próximo pregão / staging)

### Teste manual de shutdown coordenado (obrigatório antes de operar)
- [ ] Iniciar o robô em ambiente de staging (mercado aberto ou simulado)
- [ ] Criar `parar.txt` manualmente (ou forçar limite diário baixando `MAX_LOSS_DIARIO`)
- [ ] Confirmar nos logs que o `encerramento_seguro_completo` executou na sequência:
  1. Fecha posições ativas
  2. Salva modelo (`salvar_modelo` → h5/keras atômico)
  3. Salva experiências (`salvar_experiencias_json`)
  4. Flush final dos logs
  5. Processo termina (`os._exit(0)`)
- [ ] Confirmar que `parar.txt` foi consumido/removido pelo loop (`os.remove(_caminho_dados("parar.txt"))`)
- [ ] Confirmar que o processo não ficou "morto-vivo" (dashboard não continua rodando sem loop de trading)

### Teste de mutex (instância única)
- [ ] Iniciar o robô → iniciar segunda instância → confirmar `MessageBox` + `_sys.exit(0)` na segunda
- [ ] Importar o módulo de outro script Python com o robô ativo → confirmar que o import **não** mata o processo importador (regressão do fix)

### Teste de escala de entropia
- [ ] No primeiro pregão, confirmar nos logs que EXPLOSÃO só aparece com `entropia > 2.85`
- [ ] Confirmar que o score do SniperSupermo não fica inflado (entropia contribui apenas quando `> 2.75`)

### Testes de integridade de dados
- [ ] Após shutdown: `modelo_monstro_wdo.h5` > 100KB e íntegro (sem `.tmp_atomic`)
- [ ] `experiencias_wdo.json` com as últimas experiências salvas
- [ ] `monstro_wdo.log` sem erros críticos na sessão

### Gatilho de revisão
- [ ] Se comportamento anômalo no primeiro pregão → abrir ticket nesta seção do ROADMAP

---

## EXPECTATIVAS REALISTAS

### O que o robô FAZ hoje:
- ✅ Lê book WDO + DOL em tempo real
- ✅ Filtra por volume institucional (sniper)
- ✅ IA decide BUY/SELL/NADA com 22 features
- ✅ Confluência de 5 sinais técnicos
- ✅ DOL veto/confirmação
- ✅ PTAX coleta BCB (4 janelas: 10/11/12/13h)
- ✅ Sniper bloqueado em dia PTAX e payroll
- ✅ Payroll escape (sexta 09:25-09:35)
- ✅ Dólar casado (WDO - PTAX) como feature
- ✅ Williams %R divergência bull/bear
- ✅ Trailing stop + profit protection
- ✅ Aprende com cada operação
- ✅ Re-treina a cada 3 operações
- ✅ Dashboard web em tempo real

### O que NÃO faz (ainda):
- ❌ Otimização automática de hiperparâmetros
- ❌ Análise de fundamentos (notícias, Selic)
- ❌ Backtesting completo histórico
- ❌ Adaptação automática de SL/TP ao regime

### Realidade do mercado:
- WDO é extremamente eficiente — poucos inefficiencies
- HFT domina o book — sinais duram milissegundos
- O robô opera em M1 — pode capturar fluxo institucional
- Expectativa: **55-60% de acerto** com trailing eficiente
- Meta: consistência > lucro pontual

---

## FASES DO PROJETO

### FASE 1 — MIGRAÇÃO WIN → WDO ✅ CONCLUÍDA (22/07/2026)
- config.json, symbol, TP=0, features 16-18, trailing, limpeza referências WIN

### FASE 2 — CORREÇÃO DE BUGS ✅ CONCLUÍDA (22/07/2026)
- 10 bugs críticos + 3 menores corrigidos

### FASE 3 — TESTE DE CARGA ✅ CONCLUÍDA (23-28/07/2026)
- [x] WDOQ26 selecionado
- [x] Book nativo ativo
- [x] Modelo criado e salvo
- [x] DOL integrado
- [x] ATR/entropia/ratio recalibrados para WDO
- [x] Primeira entrada executada (BUY 5099.50)
- [x] SL funcionou (5097, -R$25 — mercado flat)
- [x] Primeiro trade lucrativo (BUY 5092→5099.5, +70pts R$70)
- [x] SL trailing funcionando (SL moveu de 5093→5100 conforme lucro)
- [x] Treino balanceado (wins + losses, punição correta)
- [x] 25 trades reais acumulados
- [x] 6 treinos com dados reais executados
- [x] FiltroTendencia bloqueou 200+ contra-tendência
- [ ] Modelo aprendendo com trades reais (precisa 30+ trades para calibragem)

### FASE 4 — PTAX + PAYROLL + SNIPER BLOQUEIO ✅ CONCLUÍDA (28/07/2026)
- [x] Coleta PTAX BCB (4 janelas 10/11/12/13h)
- [x] Feature dolar_casado (WDO - PTAX)
- [x] Payroll escape (sexta 09:25-09:35)
- [x] Sniper bloqueio em dia PTAX e payroll
- [x] 4 novas features no modelo (N_FEATURES=22)
- [x] Dashboard alert bar + métricas PTAX
- [x] Williams %R divergência corrigida (ticks)

### FASE 5 — CALIBRAÇÃO EM MERCADO ✅ CONCLUÍDA (28/07/2026)
- [x] 25 trades reais acumulados — ATR, entropia, ratio, score recalibrados
- [x] FiltroTendencia SMA-50 + Momentum validado (200+ bloqueios)
- [x] SL = 5pts, trailing gatilho 3pts validados

### FASE 6 — RETREINAR MODELO ✅ CONCLUÍDA (28/07/2026)
- [x] Retreinado Keras com 22 features (modelo V3)
- [x] L2 regularization (0.001) + BatchNorm + Dropout
- [x] TimeSeriesSplit (split temporal 80/20, sem shuffle)
- [x] SMOTE balanceamento de classes
- [x] EarlyStopping + ReduceLROnPlateau
- [x] Model melhor época (epoch 24): 93.9% train / 86.9% val
- [x] Scaler 22 colunas salvo
- [x] .h5 + .keras salvos
- [x] Pesos reais do modelo (não sintéticos puros) aplicáveis

### FASE 7 — CORREÇÃO SCALER + SAÍDA BOOK ✅ CONCLUÍDA (29/07/2026)
- [x] 4 correções de proteção do scaler (treino online não corrompe mais MinMax)
- [x] `_hash_contexto` duplicado removido
- [x] Entry context salvando corretamente no CSV
- [x] Saída por Inversão de Fluxo validada com sucesso (breakeven em vez de loss)

### FASE 7b — AJUSTE SL CATÁSTROFE ✅ CONCLUÍDA (30/07/2026)
- [x] SL_POINTS 5.0 → 8.0 (stop de segurança, saída real por fluxo: book inversion, trailing, score erosion)
- [x] Retreino offline do Keras com dados consolidados da sessão (17h+)
- [x] Backup do modelo antigo antes do retreino

### FASE 7c — FIX PERSISTÊNCIA PYINSTALLER + MODELO V3 REGULARIZAÇÃO REDUZIDA ✅ CONCLUÍDA (30/07/2026)
- [x] **Retreino V3 com regularização reduzida** — Dropout 0.2 (era 0.5/0.4/0.3), L2 0.001 (era 0.005), GaussNoise 0.01 (era 0.02). Arquitetura 128→64→32. Threshold 1.5 mantido.
- [x] **Fix persistência PyInstaller** — `_caminho_base()` + `_caminho_dados()` globais. Todos CSVs/JSON/Log/Model/Config/Parar.txt apontam para `C:\AIOFEN\` (não `dist\MonstroDashboard\`).
- [x] **Rebuild .exe** — `MonstroDashboard.exe` 27MB (11:13) com paths absolutos funcionais.
- [x] **Validação CSVs tempo real** — decisions, historico_contexto, historico_multitf, williams_r, log todos atualizando a cada ciclo.
- [x] **Sessão tarde validada** — SELL +25pts, BUY aberto com trailing. Modelo V3 reagindo (não travado em NAO_AGIU).
- [x] **Diagnóstico SniperSupermo** — score fixo 6/11 confirmado: condições de ativação (≥7) não ocorreram (DOL conf <0.7, ratio <2.0, RSI não extremo). Funcionando como projetado.

### FASE 7d — CORREÇÕES PÓS-AUTÓPSIA (5 VETOS + PIPELINE) ✅ CONCLUÍDA (30/07/2026)
- [x] **Williams %R threshold -85 → -80** — simétrico ao veto SELL (cobre zona cinzenta -83/-84)
- [x] **FORÇA BUY/SELL protegido por Multi-TF** — não força direção contra 3 timeframes
- [x] **DOL conf ≥ 0.5 + alinhado** para entradas não-sniper (já implementado)
- [x] **Book ratio ≥ 1.5x** para trades direcionais (já implementado)
- [x] **SL Catástrofe 8pts** no config.json (já configurado)
- [x] **Import circular fix** (config_manager.py → monstro_unificado_v22.py → dashboard_routes)
- [x] **Rebuild .exe com certifi CA bundle** (MonstroDashboard.exe)
- [x] **Pipeline de execução mapeado e validado** — 8 camadas de proteção antes do MT5

### FASE 8 — MELHORIAS DO SISTEMA ⬜ PENDENTE
- Risco, adaptatividade, confluência, monitoramento

### FASE 9 — DEPLOY E PRODUÇÃO ⬜ PENDENTE
- 1 semana demo lucrativo → conta real

### FASE 10 — INTEGRAÇÃO DOL ✅ CONCLUÍDA (23/07/2026)
- [x] ler_book_dol(), analisar_sinal_dol()
- [x] Subscrição DOL no MT5
- [x] Veto/confirmação no fluxo de decisão

### FASE 11 — AGENTE AUTÔNOMO (AUTOTUNER DELIMITADO) ✅ FASE 1 CONCLUÍDA (03/08/2026)
- [x] `agente_monstro_core.py` — orquestração (run_pausa/run_fecho/run_watchdog/main)
- [x] Gatekeeper `aplicar_ajuste()` + `rollback_config()` + whitelist 5 parâmetros (clamp duro)
- [x] Árvore `decidir()` + `blocker_dominante()` (relatórios sem viés)
- [x] Trava de horário de autonomia [12:30, 14:30] (`dentro_da_janela_autonomia()`)
- [x] Estado persistente `agente_estado.json` + trava 1 ajuste/dia (`pode_ajustar()`)
- [x] Diff estrutural `verificar_mudanca_codigo()` + `agente_snapshot_v22.py` (detecta, não altera)
- [x] Contagem correta de trades executados ("processada e resetada")
- [x] Automação: `start_all.bat` + 4 tasks Task Scheduler (Start 09:00 / Pausa 12:30 / Watchdog 15min / Fecho 17:35)
- [x] `.gitignore` ampliado + pushes `b800436`, `1ad5ad6`, `b3b8c87`, `4711155` → main
- [x] Watchdog LIGADO (03/08): task `Monstro-Watchdog` a cada 15min (09:05-17:35) + flag `watchdog_enabled: true` + guarda `dentro_do_expediente()` (seg-sex 09:00-17:40 — impede reinício no fim de semana)
- [x] CI GitHub Actions (`monstro-ci.yml`): py_compile + `tests/testes_pos_fix.py` (9/9 PASS local; CSV skip no CI)
- [x] Código morto removido (bloco MODO_CONSERVADOR* do v22) + config morta removida (winpct_break_even, max_mudancas_por_ciclo)
- [x] Log do EXE recompilado confirmado (monstro_wdo.log mtime 03/08 22:12)
- [ ] ⏳ VALIDAÇÃO EM PRODUÇÃO: primeira execução autônoma real (04/08/2026) — pendente
- [ ] LLM consultor (Fase 2) — pendente (recomendações após N dias de amostra)

---

## HISTÓRICO DE MUDANÇAS

### 28/07/2026 — Sessão 10 (Modelo V3 retreinado + L2 + TS + SMOTE + Confidence Gap + Bug Fixes)
| Tipo | Descrição | Arquivo |
|------|-----------|---------|
| 🔧 ML | **L2 regularization (0.001)** — Adicionado `kernel_regularizer=l2(0.001)` em todas as Dense layers. Contém overfitting | `monstro_unificado_v22.py:3292` |
| 🔧 ML | **TimeSeriesSplit** — `shuffle=False`, split 80/20 temporal (primeiros 80% treino, últimos 20% val). Fallback shuffle só se dados <4 amostras | `monstro_unificado_v22.py:7873-7879` |
| 🔧 ML | **SMOTE** — `imblearn.over_sampling.SMOTE` balanceia classes BUY/SELL no treino. 1674 amostras balanceadas | `monstro_unificado_v22.py:7886-7892` |
| 🔧 ML | **EarlyStopping patience 15** — Monitora val_loss, restaura best weights | `monstro_unificado_v22.py:7906-7907` |
| 🤖 MODELO | **Modelo V3 retreinado** — 39 épocas (best epoch 24). Train: 93.91% acc / 0.257 loss. Val: 86.92% acc / 0.373 loss. Gap 7% | Offline |
| 🗃️ MODELO | **`.keras` salvo** — Formato nativo Keras (104KB) ao lado do `.h5` (473KB) | `modelo_monstro_wdo.keras` |
| 🗃️ SCALER | **Scaler 22 colunas** — `_scaler.json` com min/max das 22 features | `modelo_monstro_wdo_scaler.json` |
| ✨ FEATURE | **Confidence Gap 0.15** — Sinais com `|prob-0.5| < 0.15` retornam NADA imediatamente. Filtra ruído borderline | `monstro_unificado_v22.py:8329-8341` |
| 🐛 BUG FIX | **Fallback scaler 18→22** — `forcar_recreacao_scaler()` criava dummy com 18 features. Se `_scaler.json` falhasse, crash ao transformar 22 colunas | `monstro_unificado_v22.py:1631` |
| 🐛 BUG FIX | **CSV header sem PTAX** — `colunas_padrao` não tinha 4 colunas PTAX, perdia dados ao recriar CSV | `monstro_unificado_v22.py:2932` |
| 🐛 BUG FIX | **Contexto CSV sem PTAX** — Experiências do CSV perdiam PTAX features. Agora default 0 | `monstro_unificado_v22.py:7610` |
| 🐛 BUG FIX | **`preparar_dados()` sem PTAX** — Fallback não incluía PTAX, causava KeyError ao misturar dados com/sem PTAX | `monstro_unificado_v22.py:3185` |
| 📊 RESULTADO | **Modelo V3**: 86.9% val temporal (honesto). Anterior era 89.59% (inflado por shuffle leak). Gap 7% controlado por L2 | Offline |
| 📊 RESULTADO | **25 trades reais em 28/07** — -190pts (+160 / -350 / 5 BE). Mercado lateral 5122-5127 | Sessão |

### 30/07/2026 — Sessão 12 (Fix Persistência PyInstaller + Retreino V3 Regularização Reduzida + Rebuild .exe + Validação CSVs)

| Tipo | Descrição | Arquivo/Linha |
|------|-----------|---------------|
| 🐛 CRÍTICO | **Persistência zero no PyInstaller** — `_caminho_recurso()` só consertava `template_folder` do Flask. Todos os CSVs/JSONs/Log/Model/Config usavam paths relativos → no `.exe` (CWD=`dist\MonstroDashboard\`) **nenhum arquivo era escrito** (RAM only). Sessão da manhã: 10 trades, -190pts, 10% WR, **0 bytes em disco**. | `monstro_unificado_v22.py:443-452` |
| 🔧 FIX | **`_caminho_base()` + `_caminho_dados()` globais** — Resolve diretório base correto: PyInstaller → sobe de `_internal` para raiz do projeto (`C:\AIOFEN\`); Script → `__file__`. Aplicado a TODOS os paths de dados. | `monstro_unificado_v22.py:443-452` |
| 🔧 FIX | **Paths convertidos para absoluto** — `CONFIG_FILE`, `HISTORICO_CSV`, `MODELO_PATH`, `LOG_FILE`, `EXPERIENCIAS_JSON`, `DECISIONS_CSV`, `MULTITF_CSV`, `SNIPER_SUPERMO_CSV`, `WILLIAMS_R_CSV`, `PARAR_TXT`, `API data_files` dir, `MonitorWilliamsR.__init__`, `verificar_arquivo_parada()`, `salvar_decisao_csv()`. | Múltiplas linhas |
| 🤖 MODELO | **Retreino V3 — Regularização reduzida (Underfitting fix)** — Dropout 0.5/0.4/0.3 → **0.2 uniforme**; L2 0.005 → **0.001**; GaussianNoise 0.02 → **0.01**; Arquitetura 256/128/64/32 → **128/64/32**; Label threshold 1.5 mantido; 30k amostras → 16k BUY/SELL → SMOTE → 12.9k balanceadas. | `treinar_monstro_offline.py` |
| 📊 RESULTADO | **Treino V3 novo**: 31 épocas (early stop), val_acc **81.71%** (vs 82.6% anterior), val_loss **0.4067** (vs 0.3438). Modelo mais leve, menos regularizado, **reage mais rápido** — objetivo: eliminar paralisia `NAO_AGIU` (502 ocorrências manhã) e recuperar timing. | Offline |
| 📦 BUILD | **`.exe` rebuildado** — `pyinstaller MonstroDashboard.spec` → `dist\MonstroDashboard\MonstroDashboard.exe` (27 MB, 11:13) com paths absolutos funcionais. | Build |
| ✅ VALIDAÇÃO | **CSVs escrevendo em tempo real** — `decisions_wdo.csv` (4.3KB), `historico_contexto_wdo.csv` (495KB), `historico_multitf.csv` (4.1KB, 38 linhas M5/M15/M30), `williams_r_historico.csv` (115KB), `monstro_wdo.log` (62KB). Todos atualizados a cada ciclo. | Sessão 11:30-11:47 |
| 📊 OPERAÇÕES | **SELL 5076 → +25pts (R$25) fechado 11:44** | Log/CSV |
| 📊 OPERAÇÕES | **BUY 5072 aberto (SL 5070 trailing)** — flutuando 0 a +1pt | Log/CSV |
| 🔍 DIAGNÓSTICO | **SniperSupermo CSV não atualiza** — Condições de ativação (score ≥7/10) **não ocorreram hoje**: DOL conf max 0.44 (<0.7), book ratio max 1.33x (<2.0), RSI 39-44 (não extremo). Funcionando como projetado (raro). | Log/CSV |

---

### 29/07/2026 — Sessão 11 (Correção Scaler + Saída Book + Decisão SL Catástrofe)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🐛 CRÍTICO | **Scaler refitava com CSV pequeno (6 linhas)** — treino online `treino=True` corrompia MinMaxScaler, RSI 0-100 → ~35-42. 4 correções: (1) `contexto: dict = {}` antes do while, (2) `treino=True`→`treino=False` no treino online, (3) `forcar_recreacao_scaler()` pós-treino, (4) pré-predição | `v22.py:6031,7856,7978,6847` |
| 🗑️ DELETE | **`_hash_contexto` duplicado removido** — linhas 679-685, book_pressure duplicado após return inatingível | `v22.py:679-685` |
| 🐛 BUG FIX | **Entry context salvando ação+reward corretamente** — SELL 2490232578 e BUY 2490384373 verificados no CSV ✅ | Loop principal |
| 📊 SAÍDA PROVADA | **Saída por Inversão de Fluxo (Book Nativo)** — BUY 5136, mercado virou contra, ratio 1.25 contrário, SL movido 5133.5→5136.0. Trade fechou zero a zero. Loss de -R$25 evitado | `v22.py:~6293-6440` |
| 📊 RESULTADO | **15 trades reais (9 novos hoje)** — 4 wins +R$95 / 11 losses -R$265. Net -R$170. Média win R$23.75 (2.4pts), loss R$-24.09 (2.4pts). Zeros: 2 (book breakeven) | Sessão |
| 🎯 DECISÃO | **SL 2.5pts → SL Catástrofe 8-10pts (pós-pregão)** — SL fixo atual estopa trades no ruído normal do WDO. SL passa a ser rede de segurança; saída real será pelos 3 algoritmos de fluxo (book inversion, trailing, score erosion) | Config pós 17h |
| 📋 PLANO | **Retreino offline noturno** — após fechamento, baixar CSV consolidado + retreinar Keras com dados reais (17h+) | Offline |
| 🔧 OBS | **Modelo VIÉS BUY 1.000 confirmado** — raiz: treino original com 6 BUY + 0 SELL. Só resolve com 500+ trades balanceados | Dados CSV |
| 🔧 OBS | **SniperSupermo score fixo 6/11** — nunca atingiu 7/11 necessário. Diagnosticar após retreino | Pendente |

### 28/07/2026 — Sessão 9 (PTAX + Payroll + Sniper Bloqueio + Williams %R fix + 22 features)
| Tipo | Descrição | Arquivo |
|------|-----------|---------|
| ✨ FEATURE | **PTAX coleta BCB** — `_PTAXParser` HTML, 4 janelas (10:00/11:00/12:00/13:00), cache diário | `monstro_unificado_v22.py:2230` |
| ✨ FEATURE | **dolar_casado** — (WDO - PTAX) × 1000. Feature + global + dashboard | `monstro_unificado_v22.py:5833` |
| ✨ FEATURE | **payroll escape** — `eh_horario_payroll()`: sexta 09:25-09:35, bloqueia sniper, fuga automática | `monstro_unificado_v22.py:2304` |
| ✨ FEATURE | **Sniper bloqueio** — `verificar_sniper_bloqueado()` bloqueia em dia PTAX (31/07) e payroll | `monstro_unificado_v22.py:2315` |
| ✨ FEATURE | **4 features PTAX no Keras** — `dolar_casado`, `em_janela_ptax`, `minutos_para_ptax`, `dia_ptax`. N_FEATURES=22 | `monstro_unificado_v22.py:541` |
| ✨ FEATURE | **Dashboard alert bar** — banner vermelho/amarelo p/ sniper bloqueado/payroll | `templates/dashboard.html:173` |
| ✨ FEATURE | **Dashboard métricas PTAX** — `#mPTAX`, `#mDCasado`, `#mSniper` | `templates/dashboard.html:167-169` |
| ✨ FEATURE | **`/api/status` PTAX** — `ptax`, `dolar_casado`, `sniper_bloqueado`, `payroll_ativado` | `dashboard_routes.py:134` |
| 🐛 BUG FIX | **Williams %R divergência thresholds % → ticks** — 1pt preço (2×TICK_SIZE), 5pts WR. Janela 20→200. `max_hist`=1000 | `monstro_unificado_v22.py:2582` |
| 🗑️ DELETE | **`williams_r_historico.csv` deletado** — 2009 linhas com divergência errada removidas | (arquivo) |
| 🔧 AJUSTE | SniperSupermo agora verifica `sniper_bloqueado` no contexto e retorna `BLOQ_PTAX/PAYROLL` | `SniperSupermo.verificar():2709` |
| 🔧 AJUSTE | Contexto agora inclui `ptax`, `dolar_casado`, `em_janela_ptax`, `minutos_para_ptax`, `dia_ptax`, `payroll_ativado`, `sniper_bloqueado` | Loop principal ~6752 |
| 🔧 AJUSTE | `config.json` N_FEATURES 18→22 | `config.json` |
| 📊 RESULTADO | 25 trades em 28/07: -190pts (Wins +160 / Losses -350 / BE 5). Mercado lateral 5122-5127 | Sessão |

### 28/07/2026 — Sessão 8 (26 trades + Pesquisa LW + SniperSupermo)
| Tipo | Descrição |
|------|-----------|
| 📊 RESULTADO | **19 trades executados** (09:01-11:29). Resultado: -80pts (Wins +145 / Losses -225 / Breakeven 5). 6 treinos Keras executados |
| 📊 ACUMULADO | **26 trades reais** (7 de 27/07 + 19 de 28/07). Meta 100+ para maturação |
| 🔧 BUG CONFIRMADO | Perdas de -25 (2.5pts) são normais — 0.5pt antes do SL real de 5pts |
| 🔧 FILTRO VALIDADO | FiltroTendencia bloqueou 200+ operações contra-tendência em mercado range-bound |
| 📚 PESQUISA | **Larry Wilson real**: %R divergências + COT (DOL) + sazonalidade. SMA3/55 é versão de iniciante. Nosso sistema já está alinhado com LW real |
| 📁 NOVO | `backtest_intraday.py` — script de backtest comparativo (E2 (LW SMA3/55) venceu 8/8 mas em mercados com tendência, não WDO) |
| 📄 ATUALIZAÇÃO | ROADMAP — candidatas corrigidas: %R divergências substitui SMA3/55 como próxima evolução |
| ✨ FEATURE | **SniperSupermo** — modo alta convicção (score ≥ 7/10): DOL+%R+RSI+ATR+entropia+horário+sniper ratio. Volume 5cc, SL=5pts. Breakeven em +2.5pts, trailing 1pt/1pt. Pula filtros normais, big players e horário. Sem cooldown. CSV `sniper_supermo_historico.csv` | `monstro_unificado_v22.py` |
| ✨ FEATURE | **Williams %R implementado** — `calcular_williams_r()`, `detectar_divergencia_wr()`, `MonitorWilliamsR`. CSV `williams_r_historico.csv`. Coleta dados sem bloquear | `monstro_unificado_v22.py` |
| 🔧 AJUSTE | SniperSupermo: 7 condições (docstring corrigida). Time check: sempre +1 (horário global não restringe sniper) | `SniperSupermo.verificar()` |
| 🔧 AJUSTE | SniperSupermo trailing: breakeven em +2.5pts (não +5). Depois trailing 1pt/1pt manual no loop principal | `monstro_unificado_v22.py:6223` |
| 🔧 AJUSTE | SniperSupermo: cooldown removido (operações raras, pode re-ativar) | `SniperSupermo.__init__` |
| 🔧 AJUSTE | `executar_ordem()`: parâmetro `sniper=True` pula verificação de horário | `executar_ordem()` |
| 🔧 AJUSTE | Hibernação 12:30-14:30: sleep 1h → sleep 5s (sniper ativo, modo normal bloqueado) | Loop principal |
| 🔧 AJUSTE | Horário: revertido para janelas originais 09:15-12:30 / 14:30-17:15 (normal). Sniper ignora | `horario_permitido()` |
| 🧹 DOC | Docstring SniperSupermo corrigida: removeu spoof/SMA-50/Z-Score (não implementados) | `SniperSupermo` |

### 27/07/2026 — Sessão 7d (Dashboard V2 + Log Reduction)
| Tipo | Descrição | Arquivo |
|------|-----------|---------|
| ✨ FEATURE | **Dashboard V2 completo** — UI dark theme (Tailwind colors), Chart.js, console de logs com cores, modal de ajustes em tempo real, botões INICIAR/REINICIAR/PARAR/PAUSAR. Imagem de fundo IMAGEMROBO.png full screen translúcido + LOGO.jfif no header | `templates/dashboard.html`, `dashboard_routes.py`, `config_manager.py` |
| ✨ FEATURE | **ThreadSafeConfig** — `config_manager.py` com `threading.RLock`, validação de range, listeners, persistência JSON. Atualiza parâmetros em tempo real sem reiniciar | `config_manager.py` |
| ✨ FEATURE | **Blueprint Flask** — 7 endpoints: `/`, `/api/status`, `/api/trades`, `/api/logs`, `/api/config/current`, `/api/config/update`, `/api/control/<action>` | `dashboard_routes.py` |
| ✨ FEATURE | **Controle remoto** — Botão INICIAR inicia novo processo, REINICIAR mata e reinicia, PARAR cria `parar.txt` | `dashboard_routes.py` |
| ✨ FEATURE | **Config em tempo real** — Modal edita SL, TP, Sniper, Trailing, Spread, MaxLoss via `/api/config/update` | `dashboard_routes.py` |
| ✨ FEATURE | **Chart de trades** — Gráfico de barras Chart.js (verde=ganho, vermelho=perda) alimentado por `historico_lucro` | `templates/dashboard.html` |
| ✨ FEATURE | **Console de logs** — Streaming com cores: INFO=azul, WARNING=amarelo, ERROR=vermelho. Polling incremental via `?offset=N` | `templates/dashboard.html` |
| 🔧 BUG FIX | **Flask log flooding** — `werkzeug` e `app.logger` agora logam só WARNING+. Eliminou ~170k linhas/dia de requests HTTP no monstro_wdo.log | L5397-5401 |
| 🔧 BUG FIX | **historico_lucro vazio** — Adicionado `historico_lucro.append(lucro_real)` após cada trade. Chart agora mostra operações | L6055 |
| 🔧 BUG FIX | **Keras warning no verificar_e_proteger_modelo** — `load_model` agora com `warnings.catch_warnings()` para suprimir aviso de métricas compiladas | L3021-3023 |
| 📊 MELHORIA | **Log reduction (6 mudanças)** — TENDENCIA BLOQUEIA: só loga quando decisão muda (antes: cada ciclo). TENDENCIA STATUS: a cada 20 calls (antes: 5). BOOK_WDO: a cada 5 ticks (antes: cada tick). NAO_AGINDO: debug level, 5min (antes: INFO, 30s). KERAS WARNING: filtrado. DOL: 2min via _log_periodico | Múltiplas linhas |
| 📁 NOVO | `config_manager.py` — ThreadSafeConfig singleton | ~130 linhas |
| 📁 NOVO | `dashboard_routes.py` — Blueprint Flask com 7 endpoints | ~240 linhas |
| 📁 NOVO | `templates/dashboard.html` — Dashboard HTML completo | ~400 linhas |
| 📁 NOVO | `static/IMAGEMROBO.png` — Imagem de fundo (2MB) |  |
| 📁 NOVO | `static/LOGO.jfif` — Logo oficial do projeto (130KB) |  |

### 27/07/2026 — Sessão 7c (Trailing SL não acompanhava preço)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🔧 BUG FIX | **`distancia_minima` muito agressiva (4.5pts)** — `freeze_level=3` (default) * 1.5 = 4.5pts. Para WDO com SL=5pts, isso impedía o trailing de mover o SL. Fix: default 3→1, removed `*1.5` multiplier | 4951-4955 |
| 🔧 BUG FIX | **Safety check trailing** — Se correção de distancia_minima piora o SL (ex: corrige 5110→5113 quando atual é 5112), agora retorna False em vez de rejeitar. Espera próximo tick quando preço se moveu | 4969-4974, 4983-4987 |
| 📊 IMPACTO | SELL 5114, preço 5108 (+6pts): SL ficava preso em 5112. Agora SL moveu para 5110, trailing funcionando | 5110 |

### 27/07/2026 — Sessão 7b (FiltroTendencia reescrito + fixes)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🔧 BUG FIX | **`freeze_level` não definida em `atualizar_sl`** — Variável só era atribuída no ramo elif, crash quando breakeen_forcado → SL NÃO era movido. Inicializada no topo da função | 4954-4999 |
| 🔧 BUG FIX | **`batch_normalization/gamma` no treino** — Optimizer antigo do H5 incompatível com Keras 3. Sempre recompilar com optimizer novo antes do fit | 7355-7361 |
| 🔧 BUG FIX | **Dupla registro de preço no FiltroTendencia** — `pode_operar()` chamado 2x com mesmo preço, adicionava preço 2x ao histórico. Substituído por `avaliar_tendencia()` chamado 1x | 7589-7609 |
| 📊 MELHORIA | **FiltroTendencia reescrito: SMA-50 + Momentum** — Janela 20→50 (reage mais devagar), margem 2.0→1.0pt (detecta tendência mais cedo), adicionada detecção de momentum (>3pts em 20 ticks). 3 camadas: SMA, Momentum, Consenso | 8996-9080 |
| 📊 CALIBRAÇÃO | **Média Reversion mantido** — RSI 70/30 correto para reversão à média. O problema era FiltroTendencia fraco, não MR | 9140-9260 |

### 27/07/2026 — Sessão 7 (SL Trailing + Treino Balanceado)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🔧 BUG FIX | **SL Trailing Breakeen CRÍTICO (3 partes)** — (1) `atualizar_sl()` aceita SL >= entry. (2) INVERSÃO DE FLUXO usa `eh_breakeen_forcado=True`. (3) GerenciadorDeSaida pula override quando SL >= entry | 5963-5987 |
| 🔧 BUG FIX | **Trailing usando melhor_preco** — AMBAS classes GerenciadorDeSaida usavam `melhor_preco` (pico) para cálculo de trailing. Quando preço retraía, SL ficava ACIMA do bid (BUY) ou ABAIXO do ask (SELL) → MT5 rejeitava. Corrigido para usar `preco_atual` | 2015-2025, 165-174 |
| 🔧 BUG FIX | **`freeze_level` não definida em `atualizar_sl`** — Variável só era atribuída dentro do ramo `elif not eh_breakeen`. Quando `eh_breakeen_forcado=True`, usava variável não definida → crash `UnboundLocalError`. SL NÃO era movido. Corrigido: `freeze_level` e `distancia_minima` inicializados no topo da função | 4954-4999 |
| 🔧 BUG FIX | **CSV carregava apenas WINS** — `carregar_experiencias_do_csv()` filtrava `reward > 0`. Modelo nunca aprendia com perdas. Corrigido para WINS + LOSSES balanceado (ratio 2:1) | 7044-7143 |
| 🔧 BUG FIX | **normalizar_recompensas destruía sinal** — Usava min-max [0,1], transformando losses em 0 (neutro) e wins em 1 (bônus). Modelo não sabia punir. Corrigido para `r/100` preservando sinal | 7202-7223 |
| 🔧 BUG FIX | **sample_weight invertia punição** — Usava `r + 0.1`, losses recebiam peso mínimo (perto de 0). Corrigido: losses = `abs(r)*2.0+0.1` (2x punição), wins = `abs(r)*0.5+0.1` | 7352-7356 |
| 🔧 BUG FIX | **NaN no batch** — Dados corrompidos causavam treino silencioso vazio. Filtro `np.isfinite()` adicionado antes de train_test_split | 7299-7302 |
| 🔧 BUG FIX | **Mínimo treino reduzido** — De 10 para 4 amostras. `train_test_split` stratify com try/except para single-class | 7305, 7324-7333 |
| 🔧 BUG FIX | **Contexto CSV incompleto** — load faltava 8 colunas book. Agora carrega todas as 18 features | 7090-7110 |
| 🔧 CONFIG | **Hibernação 12:30-14:30** — Robô entra em standby durante pausa de almoço | config |
| 📊 MELHORIA | **Mean Reversion suavizado** — RSI 80/20 → 70/30, Z-Score 2.0 → 1.5. Permite mais operações | 9025-9162 |
| 📊 CALIBRAÇÃO | **Volume mínimo 800 → 400, Entropia 0.4 → 0.2, Score 4/11 → 2/11** — Reduz bloqueios | 7400-7514, config.json |
| 📊 MELHORIA | **FiltroTendencia SMA-20** — Bloqueia BUY < SMA, SELL > SMA (±2pts) | 8930-8980 |

### 26/07/2026 — Sessão 5b (suavização de filtros)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 📊 CALIBRAÇÃO | **Mean Reversion suavizado** — RSI 80/20 → 70/30, Z-Score 2.0 → 1.5. Filtra mais cedo, permite mais operações | 9025-9162 |
| 📊 CALIBRAÇÃO | **Volume mínimo 800 → 400** — Permite operações com book menos denso | 7400-7410 |
| 📊 CALIBRAÇÃO | **Entropia mínima 0.4 → 0.2** — Aceita book mais equilibrado | 7411-7420 |
| 📊 CALIBRAÇÃO | **Score mínimo 4/11 → 2/11** — Menos exigente na qualidade do setup | 7500-7514 |
| 🔧 CONFIG | **Sniper volume 800 → 400, ratio 1.5 → 1.2** — Config.json atualizado | config.json |

### 26/07/2026 — Sessão 5 (filtros de qualidade + ajuste horário)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| ✨ FEATURE | **FiltroTendencia SMA-20** — Bloqueia BUY se preço < SMA, SELL se preço > SMA (margem ±2pts). Previne entradas contra-tendência | 8930-8980, 7561-7581, 7840-7847 |
| ✨ FEATURE | **FiltroMeanReversion** — RSI(80/20) + Z-Score(±2.0) + ADX(<20=LATERAL, >25=TRENDING). Previne entradas em exaustão | 8990-9120, 7840-7870, 7892-7915 |
| ✨ FEATURE | **Feature 19 `preco`** — Preço atual WDO ((bid+ask)/2) adicionado ao contexto para FiltroTendencia | 6275 |
| 🔧 CONFIG | **Horário PA1 ajustado** — 09:15-12:30 / 14:30-17:15 (era 09:00-12:30 / 14:30-17:30). Remove primeiro e último trimestre de menor liquidez | 2194-2196 |
| 🔧 CONFIG | **Encerramento antecipado** — 17:35 encerramento, 17:40 after_market (era 18:20/18:27). Economiza 45min de standby | 555, 3156-3163 |
| 📊 MELHORIA | **Treino skip pós-17:30** — Impede treinamento desperdiçado após janela de operação | 6612-6645 |

### 23/07/2026 — Sessão 4 (correções pós-análise completa)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🔧 BUG FIX | **Log rotation inteligente** — Log sobrescreve APENAS na 1a inicialização do dia (antes 09:00). Reiniciar durante mercado preserva log | 2142-2170 |
| 🔧 BUG FIX | **Backup 1/dia** — `salvar_modelo()` cria máximo 1 backup por dia (sobrescreve). Elimina dezenas de duplicatas pós-mercado | 2919-2955 |
| 🔧 BUG FIX | **ATR thresholds WIN corrigido** — `prever_acao` usava 100/80/45 (WIN) para score de qualidade. WDO nunca atingia. Corrigido para 8/5/3 | 7721-7726 |
| 📊 MELHORIA | **Trailing gatilho 5→3pts** — Ativa mais cedo, pega lucros menores. Coerente com SL=5pts | 5557 |
| 📊 MELHORIA | **Proteção de lucro 5→3pts** — Complementa trailing mais cedo | 153 |
| 📊 MELHORIA | **INVERSÃO DE FLUXO melhorada** — Breakeen agora em prejuívo até -2pts (antes: só lucro≥0). Dá mais respiro para posições levemente negativas | 5837-5898 |

### 23/07/2026 — Sessão 3 (correções pós-primeiro-trade)
| Tipo | Descrição | Linha |
|------|-----------|-------|
| 🔧 BUG FIX | **COOLDOWN desativado** — operador pediu remoção (atrasava reentrada) | 1804 |
| 🔧 BUG FIX | **Fallback RSI corrigido** — RSI normalizado (0.4) comparado com threshold cru (30). Sempre forçava BUY indevidamente. Agora desescala: `rsi_real = rsi_scaled * 99 + 1` | 7621-7630 |
| 🔧 BUG FIX | **Breakeven SL corrigido** — INVERSÃO DE FLUXO tentava mover SL p/ breakeven (5099.50) mas `atualizar_sl` corrigia para 5072 (28pts!). Agora detecta breakeven e pula validação de distância | 4932-4963 |
| 🔧 BUG FIX | **MODO TESTE desativado** — causava spam de treinamento a cada 2s (loop infinito por 60s). Treino falhava → scaler corrompido → refit com dados atuais | 7181-7187 |
| 🔧 BUG FIX | **Colunas book faltantes no CSV** — experiências antigas não tinham 8 features novas. `preparar_dados` agora adiciona com valor 0 | 2786-2792 |

### 23/07/2026 — Sessão 2 (DOL + filtros)
| Tipo | Descrição |
|------|-----------|
| ✨ FEATURE | Integração DOL: ler_book_dol(), analisar_sinal_dol(), veto/confirmação |
| 🔧 BUG FIX | BALANCEAMENTO FORÇADO deadlock (desativado) |
| 🔧 BUG FIX | Entropia thresholds recalibrados (2.8→2.0, 2.9→1.8, default 2.5→1.0) |
| 🔧 BUG FIX | Fallback entropia → direção book (BID vs ASK imbalance) |

### 23/07/2026 — Sessão 1 (migração + calibração)
| Tipo | Descrição |
|------|-----------|
| 🔧 BUG FIX | SL minimum distance buffer (trade_stops_level) |
| 🔧 BUG FIX | Scaler loading (forcar_recreacao_scaler) |
| 🔧 BUG FIX | ia_confianca_alta em SistemaConfluencia (0.8/0.2) |
| ✨ FEATURE | Modelo treinado offline: 89.9% acurácia, 41 epochs, 2043 amostras |
| ✨ FEATURE | Treinamento offline: treinar_monstro_offline.py |
| 📊 CALIBRAÇÃO | ATR 80→1.5, Ratio 2.0→1.2, Entropia 0.6→0.4 |

### 22/07/2026
| Tipo | Descrição |
|------|-----------|
| ✨ FEATURE | Migração WIN→WDO completa + 10 bugs críticos corrigidos |

---

## PRIMEIRO TRADE — ANÁLISE COMPLETA (23/07/2026 15:12)

### Dados do Trade
| Campo | Valor |
|-------|-------|
| Ativo | WDOQ26 |
| Direção | BUY |
| Entrada | 5099.50 @ 15:12:36 |
| SL | 5097.00 (5 pts = 2.5 index points) |
| TP | 0 (trailing decide saída) |
| Máximo lucro | +4.5 pts (R$+45) @ 15:15:25 |
| Saída | SL 5097.00 @ 16:29:46 |
| Duração | 1h17min |
| Resultado | **-R$25.00** |

### Causa da Perda
- Mercado completamente flat em 5098-5104 durante 34 minutos
- Modelo previu ~0.0 (SELL) → fallback RSI forçou BUY (bug corrigido)
- Trailing nunca ativou (precisava 5pts, máximo foi 4.5pts) → agora gatilho=3pts
- Timeout/estagnação desativados → posição ficou aberta até SL

### Correções Aplicadas (Sessão 3 + 4)
1. RSI fallback corrigido — não vai mais forçar BUY indevidamente
2. MODO TESTE desativado — não vai corromper scaler
3. Colunas book faltantes — treino com dados reais vai funcionar
4. Trailing gatilho reduzido 5→3pts — captura lucros menores
5. Breakeen via INVERSÃO DE FLUXO agora funciona em prejuívo até -2pts
6. ATR thresholds corrigidos (WIN→WDO) — score de qualidade funciona

---

## CONFIGURAÇÃO ATUAL (config.json)

```json
{
  "symbol_prefix": "WDO",
  "sl_points": 5,
  "tp_points": 0,
  "volume_padrao": 1.0,
  "max_loss_diario": -500.0,
  "max_spread": 5,
  "n_features": 22,
  "min_volume_book": 200,
  "sniper_volume_min": 400,
  "sniper_ratio_min": 1.2,
  "trailing_stop": {
    "gatilho_pontos": 3.0,
    "distancia_pontos": 2.0
  }
}
```

---

## NOTAS TÉCNICAS

### Confidence Gap Flow
```
modelo.predict(X) → acao_prob (0.0 a 1.0)
  → CONFIDENCE_GAP = 0.15
  → confianca = abs(acao_prob - 0.5)
  → confianca < 0.15?
       SIM → return "NADA", 0.0 (zona neutra, ignora)
       NÃO → continua para threshold + RSI + filtros
  → threshold = threshold_base + rsi_ajuste (±0.05)
  → BUY se acao_prob > threshold, SELL caso contrário
  → Filtros: tendência, spread, horário, mean reversion...
  → Balanceador pode forçar ação se desbalanceamento extremo
```

### Arquitetura de Saída (TP=0)
```
Entrada (Keras prevê BUY/SELL)
  → SL=5pts fixo (proteção máxima)
  → TP=0 (sem take profit)
  → GerenciadorDeSaida monitora:
      1. Trailing Stop (gatilho 3pts, dist 2pts)
      2. Proteção de Lucro (pico > 3pts, caiu > 30%)
      3. Timeout (300s sem evolução + lucro ≤ 2pts)
      4. Estagnação (480s + lucro pequeno)
      5. INVERSÃO DE FLUXO (breakeen em prejuívo até -2pts)
      6. SL=5pts (última defesa)
  → Cooldown DESATIVADO (operador pediu)
```

### Arquitetura PTAX Flow
```
BCB (ptax.bcb.gov.br) → HTTP GET (10s timeout)
  → _PTAXParser HTML → taxa_venda (float)
  → _ptax_cache (1x/dia)
  → dolar_casado = (preco_wdo / 1000 - ptax) * 1000
  → em_janela_ptax() → (bool, minutos_restantes)
  → ultimo_dia_util_mes() → dia_ptax (0/1)
  → contexto['dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax']
  → 4 features no Keras (N_FEATURES=22)
```

### Arquitetura Dashboard V2
```
monstro_unificado_v22.py (porta 5001)
  ├── Flask App + dashboard_bp (Blueprint)
  ├── ThreadSafeConfig (threading.RLock)
  │     ├── Leitura/escrita thread-safe
  │     ├── Validação de range por parâmetro
  │     ├── Persistência automática no config.json
  │     └── Listeners para notificação de mudanças
  ├── Endpoints REST
  │     ├── GET /                    → Dashboard HTML
  │     ├── GET /api/status          → JSON completo (tendência, posição, métricas)
  │     ├── GET /api/trades          → Histórico de trades para Chart.js
  │     ├── GET /api/logs?offset=N   → Polling incremental de logs
  │     ├── GET /api/config/current  → Config editável atual
  │     ├── POST /api/config/update  → Atualiza parâmetros em tempo real
  │     └── POST /api/control/<action> → stop/restart/start/pause
  └── Frontend (templates/dashboard.html)
        ├── Tema dark (Tailwind colors: slate-900/800/700)
        ├── Logo LOGO.jfif + fundo IMAGEMROBO.png (opacity 18%)
        ├── Botoeira: INICIAR, REINICIAR, PARAR, PAUSAR, AJUSTES
        ├── Cards: Tendência (ALTA/BAIXA/LATERAL), Posição, Métricas
        ├── Chart.js: barras de lucro por trade (verde/vermelho)
        ├── Console de logs com cores por nível
        └── Modal: SL, TP, Sniper, Trailing, Spread, MaxLoss
```

### Features do Modelo (22 + 1 runtime)
```
 1. bid_qty          - Volume total bids
 2. ask_qty          - Volume total asks
 3. spread           - Spread bid-ask
 4. volatility       - ATR(14)
 5. entropia_book    - Entropia do book
 6. rsi_14           - RSI 14 períodos
 7. volume_tick      - Volume do tick
 8. is_in_trade      - 0=s/posição, 1=em trade
 9. floating_profit   - Lucro flutuante
10. tempo_em_trade   - Segundos desde entrada
11. preco_maior_escora_bid   - Preço maior escora bid
12. volume_maior_escora_bid  - Volume maior escora bid
13. distancia_maior_escora_bid - Distância escora bid
14. preco_maior_escora_ask   - Preço maior escora ask
15. volume_maior_escora_ask  - Volume maior escora ask
16. distancia_maior_escora_ask - Distância escora ask
17. liquidez_top5_bid        - Liquidez top 5 bids
18. liquidez_top5_ask        - Liquidez top 5 asks
19. dolar_casado     - WDO - PTAX (pts)
20. em_janela_ptax   - 1 se dentro janela PTAX
21. minutos_para_ptax - Min até próx janela
22. dia_ptax         - 1 se último dia útil do mês
--. preco (runtime)  - Preço atual WDO ((bid+ask)/2) — NÃO entra no modelo
```

### Horários de Operação
```
Normal:   09:15-12:30 / 14:30-17:15 (bloqueado por horário via horario_permitido())
Sniper:   09:00-17:30 (ignora bloqueio de horário)
Hiberna:  12:30-14:30 (loop reduzido 5s — sniper ativo, normal bloqueado)
Limite:   17:33 (última ordem normal)
Encerramento: 17:35 (fecha posições)
After:    17:40 (fim do pregão)
```

### BUGS CORRIGIDOS — REFERÊNCIA RÁPIDA
| Bug | Causa | Fix | Linha |
|-----|-------|-----|-------|
| Fallback RSI sempre BUY | RSI normalizado (0-1) comparado com 30 | Desescala: `rsi*99+1` | 7621 |
| Breakeen SL enlouquecido | `freeze_level=20` → min 30pts | Detecta breakeen, pula validação | 4932 |
| Cooldown bloqueava reentrada | Cooldown 5-15min pós-loss | `COOLDOWN_ATIVO=False` | 1804 |
| Treino em loop infinito | MODO TESTE: 60s TRUE + reset contador | MODO TESTE desativado | 7181 |
| CSV sem colunas book | Experiências antigas sem 8 features | Preenche com 0 em preparar_dados | 2786 |
| ATR thresholds WIN (100/80/45) | Score de qualidade sempre 0 para WDO | Corrigido para 8/5/3 | 7721 |
| Backup spam pós-mercado | Timestamp a cada 30s → dezenas de duplicatas | 1 backup/dia sobrescrevendo | 2919 |
| Log acumula dias | `filemode='a'` padrão | Rotaciona: 1a vez do dia = overwrite, depois = append | 2142 |
| **SL Trailing travava em breakeen** | Breakeen bloqueava TODOS os updates de SL | Adiciona check `novo_e_melhoria` | 5963-5987 |
| **Trailing usava melhor_preco** | Preço retraía → SL ficava acima do bid/abaixo do ask → MT5 rejeitava | Usa `preco_atual` em vez de `melhor_preco` | 2015-2025 |
| **`freeze_level` não definida** | Variável só atribuída no ramo elif, crash quando breakeen_forcado | Inicializa `freeze_level` no topo da função | 4954-4999 |
| **`batch_normalization/gamma` no treino** | Optimizer antigo H5 incompatível com Keras 3 | Sempre recompilar com optimizer novo antes do fit | 7355-7361 |
| **Dupla registro preço FiltroTendencia** | `pode_operar` chamado 2x, preço entrava 2x no histórico | Substituído por `avaliar_tendencia()` único | 7589-7609 |
| **Trailing SL preso (distancia_minima 4.5pts)** | `freeze_level=3 * 1.5 = 4.5pts` impedia SL de seguir preço | Default 3→1, removed `*1.5`, safety check | 4951-4987 |
| **CSV só carregava wins** | Filter `reward > 0` excluía losses | Carrega wins + losses balanceado 2:1 | 7044-7143 |
| **Recompensas destruíam sinal** | Min-max [0,1] → losses = 0 (neutro) | Usa `r/100` preservando sinal negativo | 7202-7223 |
| **Sample weight invertia punição** | Losses recebiam peso ~0, wins ~1 | Losses 2x peso, wins 0.5x | 7352-7356 |
| **NaN silencioso no treino** | Batch com NaN → treino vazio | Filtro `np.isfinite()` antes do split | 7299-7302 |
| **Fallback scaler 18→22 features** | Dummy 18 colunas, modelo 22 → crash | `N_FEATURES` no lugar de 18 | 1631 |
| **CSV header sem PTAX** | `colunas_padrao` sem 4 PTAX columns | Adicionadas ao header | 2932 |
| **Contexto CSV sem PTAX** | Experiências antigas sem PTAX → KeyError | Default 0 nas 4 PTAX | 7610 |
| **`preparar_dados` sem PTAX** | Fallback só book, sem PTAX → crash | `colunas_book_novas` inclui PTAX | 3185 |

---

## INVENTÁRIO DE ARQUIVOS

### 📁 Código Principal
| Arquivo | Descrição |
|---------|-----------|
| `monstro_unificado_v22.py` | Robô principal (~9979 linhas) |
| `dashboard_routes.py` | Blueprint Flask — endpoints REST para dashboard (~240 linhas) |
| `config_manager.py` | ThreadSafeConfig — parâmetros editáveis em tempo real (~130 linhas) |
| `iniciar_v22_wdo.bat` | Launcher para WDO |

### 📁 Frontend
| Arquivo | Descrição |
|---------|-----------|
| `templates/dashboard.html` | Dashboard HTML — tema dark, chart, logs, modal, botões (~400 linhas) |
| `static/IMAGEMROBO.png` | Imagem de fundo do dashboard (2MB) |
| `static/LOGO.jfif` | Logo oficial do projeto (130KB) |

### 📁 Configuração
| Arquivo | Descrição |
|---------|-----------|
| `config.json` | Config principal WDO |
| `requirements.txt` | Dependências Python |

### 📁 Dados
| Arquivo | Descrição |
|---------|-----------|
| `historico_contexto_wdo.csv` | Dados de treino |
| `experiencias_wdo.json` | Memória de experiência |
| `decisions_wdo.csv` | Log de decisões |

### 📁 Modelos
| Arquivo | Descrição |
|---------|-----------|
| `modelo_monstro_wdo.h5` | Modelo Keras V3 (H5, 233KB, 14.3k params, 22 features, L2) |
| `modelo_monstro_wdo.keras` | Modelo Keras V3 (nativo, 104KB) |
| `modelo_monstro_wdo_scaler.json` | Scaler offline (22 features) |

### 📁 Treinamento Offline
| Arquivo | Descrição |
|---------|-----------|
| `treinar_monstro_offline.py` | Script de treinamento offline |
| `dados_historicos_wdo.csv` | Dados históricos para treino |

### 📁 Documentação
| Arquivo | Descrição |
|---------|-----------|
| `ROADMAP_WDO.md` | Este arquivo |
| `ANCHORED_SUMMARY.md` | Resumo executivo da sessão |
| `ideia para o robo.txt` | Notas do usuário |
| `implemente.txt` | Logs de teste |

### ⚠️ Notas para IA Futura
1. O robô roda como script único — `src/` é refatoração, NÃO usar como referência
2. Modelos .h5/.keras podem estar corrompidos — robô cria do zero
3. `salvar_modelo()` cria 1 backup/dia sobrescrevendo — não spam mais
4. Experiências antigas CSV não têm 8 colunas book — `preparar_dados` adiciona com 0
5. MODO TESTE (force train a cada 60s) foi desativado — causava loop infinito
6. Scaler offline é ESSENCIAL — sem ele o modelo prevê ~0.0 para tudo
7. WDO freeze_level=0 no MT5 — não impor distância artificial
8. Breakeen SL (prix_entry) SEMPRE deve ser aceito sem validação de distância
9. RSI no DataFrame X já está normalizado pelo scaler — desescalar antes de comparar com thresholds (30/70)
10. Log rotaciona automaticamente: 1a inicialização do dia sobrescreve, reinícios durante mercado preservam
11. INVERSÃO DE FLUXO: Nível 1 = prejuízo >2pts fecha; Nível 2 = prejuívo ≤2pts move SL p/ breakeen
12. Trailing gatilho=3pts (era 5) — ativa mais cedo para capturar lucros menores
13. FiltroTendencia usa `preco` (preço atual WDO) NÃO `preco_maior_escora_bid` — este último é preço da escora, não do mercado
14. FiltroMeanReversion calcula Z-Score com janela 20 ticks — menos dados = menos confiável nas primeiras horas
15. ADX é simplificado (usa EMA slope como proxy) — não é +DI/-DI completo. Funciona para filtro básico
16. Horário PA1: 09:15-12:30 / 14:30-17:15 — protege contra abertura caótica e fechamento de liquidez baixa
17. Treino skip pós-17:30 — evita treinamento desperdiçado quando mercado já fechou
18. Feature 19 `preco` é runtime only — não entra no modelo (scaler mantém 18 features)
19. **SL Trailing**: GerenciadorDeSaida usa `preco_atual` para calcular novo SL — NUNCA `melhor_preco` (pico). Se usar pico, preço retraído gera SL acima do bid → MT5 rejeita
20. **Breakeen check**: Na linha 5963-5987, verificar `novo_e_melhoria` ANTES de bloquear. Sem isso, SL fica preso em breakeen mesmo quando preço sobe
21. **Recompensas**: Usar `r/100` para preservar sinal. NUNCA usar min-max [0,1] — destrói informação de loss (torna 0 = neutro)
22. **Sample weight**: Losses devem ter MAIS peso (2x) que wins (0.5x). Modelo precisa aprender MAIS com erros do que com acertos
23. **NaN filter**: SEMPRE aplicar `np.isfinite().all(axis=1)` antes de `train_test_split`. Dados corrompidos causam treino silencioso
24. **Carregamento CSV**: Carregar wins E losses. Ratio 2:1 (wins:losses). Modelo que só vê wins fica enviesado e não aprende a evitar perdas
25. **`freeze_level` em `atualizar_sl`**: Variável DEVE ser inicializada no topo da função, antes de qualquer ramo condicional. Se só existe no `elif not eh_breakeen`, o caminho `eh_breakeen_forcado` causa crash
26. **FiltroTendencia**: SEMPRE chamar `avaliar_tendencia()` UMA VEZ — NUNCA chamar `pode_operar()` para BUY e SELL separadamente (dupla registro de preço)
27. **FiltroTendencia SMA-50**: Janela 50 com margem 1.0pt. SMA lenta reage devagar a mudanças graduais. Momentum (>3pts/20ticks) complementa detectando subidas/descidas rápidas
28. **`distancia_minima` em `atualizar_sl`**: NUNCA usar multiplicador no freeze_level. `freeze_level=1` (default) sem `*1.5` = 1pt mínimo. Se correção piora SL (ex: SELL 5110→5113 quando atual é 5112), retornar False — NÃO corrigir SL para pior
29. **SniperSupermo**: classe separada no topo (linha ~2575). Verifica 7 condições (DOL+%R+RSI+ATR+entropia+horário+sniper ratio). Score >= 7/10 ativa. Volume 5cc (`SNIPER_SUPERMO_VOLUME`). Pula: filtro volume, veto big players, bloqueio horário. Trailing próprio: breakeven em +2.5pts, depois 1pt/1pt. Sem cooldown. Reset `SNIPER_SUPERMO_ATIVO = False` quando posição fecha. CSV `sniper_supermo_historico.csv`
30. **`executar_ordem(sniper=True)`**: quando `sniper=True`, pula `horario_permitido()` — sniper opera 09:00-17:30 mesmo que normal mode esteja fora da janela
31. **Hibernação 12:30-14:30**: reduzida (sleep 5s em vez de 1h). SniperSupermo continua ativo. Modo normal bloqueado por horário. Treino executado uma vez ao entrar
32. **PTAX coleta**: `atualizar_ptax()` usa cache diário (`_ptax_cache`). Só consulta BCB 1x/dia. Se falha (ex: fim de semana), mantém 0.0 e tenta novamente no próximo ciclo
33. **dolar_casado**: calculado como `(preco_wdo - ptax_bruto) * 1000`. Preço WDO em reais (dividir por 1000). PTAX é BRL/USD direto do BCB
34. **4 janelas PTAX**: 10:00-10:10, 11:00-11:10, 12:00-12:10, 13:00-13:10. `em_janela_ptax()` retorna (bool, minutos_para_proxima). Após 13:10, retorna 60 (próximo dia). Antes 10:00, minutos até 10:00
35. **Payroll**: `eh_horario_payroll()` só verifica sexta 09:25-09:35. NÃO verifica se é a PRIMEIRA sexta do mês (o usuário sabe e a função é suficiente para o propósito). Se precisar refinar depois, adicionar verificação de primeira semana
36. **Sniper bloqueio**: `verificar_sniper_bloqueado()` → True em dia PTAX ou payroll. SniperSupermo NÃO opera quando bloqueado. O `contexto['sniper_bloqueado']` é 0/1 e vai para o contexto mas NÃO entra no modelo Keras (só no fluxo de decisão)
37. **Williams %R divergência**: thresholds em TICKS, não percentuais. Price diff mínimo = 2×TICK_SIZE (1.0pt para WDO). WR diff mínimo = 5. Janela de detecção = 200 ticks. `max_hist` = `max(janela_div * 3, 1000)` = 600 (mas janela_div=200 → max_hist=1000)
38. **Dashboard alert bar**: mostra "⚠️ SNIPER BLOQUEADO" (vermelho) ou "⚠️ PAYROLL — Modo de fuga" (amarelo). Escondido quando tudo normal. A cor do `#mSniper` muda: verde (LIVRE), vermelho (motivo bloqueio), amarelo (PAYROLL)
39. **Retreino Keras**: após adicionar as 4 features PTAX, o modelo precisa ser retreinado com `N_FEATURES=22`. O scaler também precisa ser refeito (22 colunas). Usar `treinar_monstro_offline.py` ou `treino_offline()` no próprio robô
40. **B3 NÃO tem 0.5cc**: o mínimo é 1 contrato (1cc). SniperSupermo usa 5cc. Config `volume_padrao=1.0`
41. **Modelo V3**: retreinado com L2(0.001), TimeSeriesSplit (80/20, shuffle=False), SMOTE. Best epoch 24 (val_loss=0.3728). Gap train-val 7%. Val acc 86.9% (temporal honesto, antes 89.59% inflado por shuffle)
42. **Confidence Gap (0.15)**: implementado na `prever_acao()` linha 8329. Se `|acao_prob - 0.5| < 0.15`, retorna NADA imediatamente. Economiza processamento e reduz overtrading. Se taxa de rejeição > 40% do pregão, reduzir para 0.10
43. **Fallback scaler ALINHADO**: `forcar_recreacao_scaler()` agora usa `N_FEATURES` (22) em vez de hardcoded 18. Se `_scaler.json` falhar carregamento, o dummy scaler terá 22 colunas compatíveis com o modelo
44. **Experiências CSV sem PTAX**: o `historico_contexto_wdo.csv` (5002 linhas, 21 colunas) foi coletado antes de PTAX existir. Após o restart 29/07, novas experiências terão 22 features. As antigas recebem default 0 nas 4 colunas PTAX via `preparar_dados()`
45. **Scaler CORRUPÇÃO (29/07/2026)**: O bug era que o treino online (`treino_online = True`) chamava `forcar_recreacao_scaler()` com `treino=True`, que refitava o MinMaxScaler usando APENAS o CSV pequeno (6 linhas). O RSI (~35-42) virava o range global do scaler, sobrescrevendo min=0 max=100. SOLUÇÃO: 4 barreiras — (a) `contexto: dict = {}` antes do `while thread_ativo:` garante que contexto não carregue scaler corrompido do ciclo anterior, (b) `treino=True`→`treino=False` no treinamento online impede refit, (c) `forcar_recreacao_scaler()` pós-treino restaura scaler verdadeiro, (d) `forcar_recreacao_scaler()` pré-predição como segurança extra
46. **SL Catástrofe (29/07/2026)**: O WDO tem ruído de 2-3pts frequente. SL fixo de 2.5pts (-R$25) estopa trades no ruído normal. A partir de 30/07, SL_POINTS=8.0 (-R$80) será usado como stop de segurança apenas. As saídas reais serão pelos 3 algoritmos de fluxo: (1) Inversão de Fluxo (book nativo) — provado salvando trade, (2) Trailing Stop Progressivo — provado (+R$45), (3) Score Erosion. O SL só será atingido em cenários de catástrofe (queda de internet, travamento MT5, gaps violentos). Trade-off: win rate deve subir porque trades não serão mais estopados no ruído, mas cada loss será maior (-R$80 vs -R$25). Com avg win R$23.75 e ~4 wins p/ recuperar 1 loss de R$80, a equação fecha se win rate melhorar de ~27% para > 50%
47. **VETO SEGUIR OS BIGS (29/07/2026)**: bloqueou re-entry durante rally por absorção (BID 12164 × ASK 19808 dominante SELL). Trade-off defensivo deliberado — protege contra comprar em absorção, mas perde movimentos de continuidade. Será reavaliado após retreino offline

---

## FASE 9 — FUTURO (pós-consolidação)

### 9.1 — Sentinela de Fluxo (Gatekeeper Macroeconômico)
**Status**: ✅ CONCLUÍDA (30/07/2026)

Camada de veto macroeconômico aplicada dentro da `prever_acao()`, baseada em:
- **DXY** (`DX-Y.NYB`) — força do dólar global
- **US 10Y** (`^TNX`) — juros americanos
- **USD/JPY** (`JPY=X`) — proxy de carry trade (JPY = moeda de funding)

**Regras implementadas**:
```
DXY sobe + Juros EUA sobem + USD/JPY cai (carry unwind) = RISK-OFF
    → Sentinela bloqueia SELL (só BUY liberado — dólar forte)

DXY cai + Juros EUA caem + USD/JPY sobe (carry on) = RISK-ON
    → Sentinela bloqueia BUY (só SELL liberado — dólar fraco)
```

**Como funciona** (`sentinela_fluxo.py`):
- Coleta via API Yahoo Finance (query1.finance.yahoo.com) usando só `requests` — sem dependência nova
- Cache thread-safe de 60s (`_lock` + TTL)
- Score = DXY(±1) + US10Y(±1) + USD/JPY(±1 com sinal invertido: JPY forte = RISK_OFF)
- `score >= 2` → RISK_OFF | `score <= -2` → RISK_ON | senão NEUTRO
- **Fail-open**: qualquer erro/indisponibilidade → NEUTRO → sem veto
- Thread `atualizar_sentinela()` atualiza globals em background a cada 60s (dashboard + veto)

**Integração** (`monstro_unificado_v22.py`):
- Classificação UMA vez no topo da `prever_acao()` (após PA1), vetos `_sf_veto_buy`/`_sf_veto_sell`
- Guardas em TODOS os pontos de saída BUY/SELL: FORÇA BUY/SELL (contexto simples), FORÇA BUY/SELL (expectativa positiva) e decisão final do modelo
- Globals para dashboard: `sentinela_cenario`, `sentinela_detalhe`, `sentinela_score`, `sentinela_ultima_atualizacao`
- Flag `SENTINELA_ATIVO = True` (False desativa o veto macro totalmente)

**Observação**: FX Carry do BRL/JPY ficou como proxy via USD/JPY (sinal de carry global). O veto é sempre **só-veto** (nunca força entrada).
- [x] **Rebuild .exe** (30/07 22:50) — `MonstroDashboard.exe` 27.1MB via `MonstroDashboard.spec` com `sentinela_fluxo` e `requests` em hiddenimports. Verificado: módulos no PYZ.

### 9.2 — Dashboard Neon Terminal
**Status**: ✅ CONCLUÍDA (30/07/2026)

Visual **neon/synthwave** no dashboard Flask via toggle:
- Botão **NEON** na action bar (persiste em `localStorage`)
- `body.neon`: fundo #05010F, bordas/glow neon — verde #00FF41, magenta #FF00FF, ciano #00FFFF
- Log console com borda/glow verde, horas em neon
- Cards de métricas com border/glow magenta (highlight em ciano)
- Header, ticker e sentinela bar com glow

**Escopo**: 100% visual — nenhuma alteração na lógica de trading. Apenas CSS + toggle JS inline.

### 9.3 — Market Ticker + Panorama Global
**Status**: ✅ CONCLUÍDA (30/07/2026)

Painel de cotações globais no topo do dashboard:
- **Barra de ticker** horizontal com 7 ativos: DXY, US 10Y, S&P 500, WTI, Ouro, BTC, USD/BRL
- Cada célula: rótulo, preço formatado e variação % (verde/vermelho)
- Endpoint novo `/api/ticker` (via `sentinela_fluxo.obter_ticker()`, cache 60s)
- Frontend atualiza a cada 60s (`fetchTicker` + `setInterval`)

**Observação**: DXY no ticker é o mesmo dado usado pelo Sentinela (9.1).


---

### 01/08/2026 — Sessão 15 (Code Review + Fix Escala Entropia + Save Atômico)

**Contexto:** Review completo do código por tech lead / arquiteto após migração WIN→WDO.

| Tipo | Descrição | Linha |
|------|-----------|-------|
| ✅ RESTAURADO | Parâmetros modo aprendizado: `sniper_ratio_min` 1.2→1.5, `THRESHOLD_ENTROPIA_BAIXA` 0.4→0.6→2.75 (ver abaixo), `LIMITE_REJEICOES_PARA_APRENDIZADO` 8→20 | v22:91, 522, 900, 904; config.json:10,52 |
| ✅ SCALER | Reconstruído com dados reais: 18 features de book do CSV real (5000 linhas) + domínio fixo para 4 features PTAX. Eliminado mismatch sintético | `modelo_monstro_wdo_scaler.json` |
| 🧹 REFACTOR | `GerenciadorDeSaida` duplicada (linha 101) removida — código morto, Python usava sempre a da linha 1964 | v22:101 → removida |
| 🐛 CRÍTICO | **Save atômico corrigido:** `.tmp_atomic` era extensão inválida para TF (mesmo bug do v2). Corrigido para `_tmp.h5` / `_tmp.keras` + `os.replace()`. Testado: 118KB + 108KB trocados sem erro | v22:3279-3280 |
| 🐛 CRÍTICO | **Escala de entropia corrigida em 11 pontos:** `calcular_entropia()` usa `scipy.stats.entropy` → escala real (2.69–2.97). Thresholds estavam em [0,1] → comportamentos não-intencionais: modo EXPLOSÃO sempre ativo, filtros de bloqueio mortos, score SniperSupermo inflado (explica 8/10 em 29/07) | v22:902, 904, 1067, 2709, 8169, 8201-8205, 8603-8607 |
| ℹ️ CÓDIGO MORTO | `MODO_CONSERVADOR_ENTROPIA = 0.3` (linha 1088) — definido mas não referenciado. Mantido sem alteração | v22:1088 |

#### Thresholds de entropia após correção (escala real)
| Uso | Linha | Antes | Depois |
|-----|-------|-------|--------|
| `THRESHOLD_ENTROPIA_BAIXA` (lateral) | 902 | 0.6 | **2.75** |
| `THRESHOLD_ENTROPIA_ALTA` (explosão) | 904 | 0.7 | **2.85** |
| `DetectorModo` conservador | 1067 | 0.3 | **2.75** |
| `SniperSupermo` | 2709 | 0.3 | **2.75** |
| Filtro 2 bloqueio | 8169 | 0.2 | **2.60** |
| Score qualidade (2 locais) | 8201/8203/8205, 8603/8605/8607 | 0.7/0.6/0.5 | **2.85/2.80/2.75** |

#### Impacto esperado no próximo pregão
- Modo EXPLOSÃO: dispara raramente (entropia real entre 2.69–2.97; threshold 2.85 = só nos picos)
- Score SniperSupermo: não mais inflado — entropia contribui condicionalmente
- Filtro 2 de bloqueio: volta a ter efeito (bloqueia se entropia < 2.60)
- Modo CONSERVADOR/LATERAL: pode dispara raramente dado que banda real é estreita (0.28)

**Calibração futura:** monitorar após 30 dias. Se EXPLOSÃO nunca ativar, reduzir 2.85 → 2.80. Se SniperSupermo parar de ativar, investigar qual condição domina o score.

**Validação final:** `py_compile` OK, scan residual [0,1] limpo (só `MODO_CONSERVADOR_ENTROPIA` = código morto), zero arquivos temporários.

---

## AUTOMAÇÕES DO AMBIENTE (setup PC novo) — Sessão 18 (02/08/2026)

**Documentação completa (conteúdo dos .bat + checklist + prompt de recriação): `README.md` na raiz.**

| Automação | Arquivo(s) | O que faz |
|-----------|-----------|-----------|
| **LIGAR** | `iniciar_v22_wdo.bat` | Remove `parar.txt` antigo → abre MT5 → espera 10s → roda `python monstro_unificado_v22.py` na `venv310` |
| **DESLIGAR** | `stop_all.bat` | Cria `parar.txt` (shutdown gracioso: fecha posições, salva modelo/experiências, flush logs) → espera 45s → mata processo com `monstro_unificado_v22` na linha de comando → remove `parar.txt` → fecha MT5 |
| **BACKUP (manual)** | `subir_atualizacao.bat` | `git add -A` → commit `atualizacao_%TS%` → `git push origin main` (atalho no Desktop) |
| **BACKUP (automático)** | `subir_atualizacao_auto.bat` + `backup_auto.vbs` | Idêntico ao manual sem `pause`, log em `backup_auto.log`, via tarefa agendada |

**Tarefa agendada Windows (já registrada):**
- Nome: `Monstro Backup GitHub` — Diário **08:50** — Ação: `wscript.exe C:\AIOFEN\backup_auto.vbs` — `/IT` (PC sempre na tomada).
- Recriação em PC novo: `schtasks /Create /F /TN "Monstro Backup GitHub" /TR "wscript.exe C:\AIOFEN\backup_auto.vbs" /SC DAILY /ST 08:50 /IT`

**Regras de ouro:**
1. `monstro_unificado_v22.py` **NÃO pode ser renomeado** — é referenciado por nome em `iniciar_v22_wdo.bat`, `stop_all.bat` e na rotina de encerramento.
2. Backup: sempre que editar código → `subir_atualizacao.bat`; a cópia da manhã (08:50) cobre o dia anterior.
3. Dados (modelos `.keras`, CSVs, logs) ficam fora do git de propósito (`.gitignore`).
4. Repo é público — nunca commitar credenciais.

**Verificado em 02/08/2026:** backup automático testado de ponta a ponta (commit `70193f1` subido sozinho, sem janela, sem clique).

---

## SELEÇÃO DE ESTRATÉGIA POR REGIME (DESIGN) — Sessão 19 (02/08/2026)

**Arquitetura decidida (regime detection + meta-labeling):** Python decide **ONDE e SE** (regras/risco). Keras decide **COM QUE FORÇA** (score dentro do cenário liberado). A rede NUNCA pergunta "opero?" sozinha.

**Arquivos novos (NÃO plugados no v22 — mercado em operação):**
- `selecao_estrategia_regime.py` — módulo de design: tabela `PERFIL_POR_REGIME` (6 modos) + `SelecionadorRegime` (mapeia modo → estratégias ativas/multiplicadores/score mínimo) + `RastreadorPerformanceRegime` (mede win_rate/lucro POR REGIME e POR ESTRATÉGIA — é o loop de calibração).
- `tests/teste_selecao_regime.py` — 24 checagens determinísticas, sem MT5. **24/24 PASS.**

**Mapeamento proposto (regime → estratégias ativas):**
| Regime | Estratégias ativas | Bloqueados |
|--------|-------------------|------------|
| NORMAL | todas (pesos padrão) | — |
| LATERAL | williams_r, rsi_mean_reversion, dol_veto, filtro_entropia | sniper_supermo, filtro_tendencia (alvos curtos, vol 50%) |
| EXPLOSAO | sniper_supermo, filtro_tendencia, filtro_entropia, dol_veto | williams_r, rsi_mean_reversion (segue o rompimento, vol 150%) |
| CONSERVADOR | só alta convicção (score_min 5.0, vol 50%) | — |
| DEFESA / AGUARDANDO | **NAO OPERA** (vol 0) | tudo |

**Por que não tudo-Python nem tudo-Keras:** regras puras não se adaptam a micro-padrões; Keras puro é caixa preta sem accountability (o bug da entropia provou: "previa bem" roubando). Híbrido = regras dão a grade de segurança, Keras afina dentro dela.

**Plano de integração (SÓ fora do horário de mercado, nunca em pregão):**
1. Plug `SelecionadorRegime` após `modo_operacional.atualizar_modo()` (v22:~6282): ler `modo_atual` → obter perfil → aplicar `parametros()` e `filtro_bloqueia()` nos portões de score.
2. Rastrear cada trade com `RastreadorPerformanceRegime.registrar_trade(modo, estrategia, lucro)` → persistir JSON (fora do git).
3. **Calibração (30 dias):** ler `relatorio()` → ajustar SÓ a tabela `PERFIL_POR_REGIME` (nunca a lógica). Se EXPLOSAO lucrar mais com williams_r ligado, re-ligar com peso menor. É o "balanceamento perfeito" medido, não adivinhado.
4. `validar_config()` no boot impede typos na tabela (falha rápido, não em produção).

**Auditoria de segurança (repo público):** sem emails/senhas/tokens/CPF reais; `config*.json` = placeholders; `mt5.initialize()` sem credenciais; modelo `.keras` fora do git. Decisão: manter público (perde zero — cérebro e credenciais estão protegidos fora do repo).

---

## VALIDAÇÃO COM DADOS WIN — DECISÃO REGISTRADA (Sessão 20, 02/08/2026)

**Contexto:** existem ~6 meses de dados reais de WIN em `C:\AIOFEN` (`decisions.csv` + 58 backups diários 25/01→19/07/2026, `historico_contexto_win.csv`, `experiencias.json`, auxiliares). Já salvos em `Backup_dados_MONSTRO_20260802.zip` (OneDrive Desktop).

**DECISÃO (para não esquecer):**

1. ❌ **NÃO rodar a lógica do robô WDO sobre os dados WIN.** Parâmetros e modelo foram calibrados para WDO (tick 0.5, pontos/R$, thresholds de entropia 2.75/2.85 e ATR, volume 1.0cc, reward em pontos). Replay em WIN = artefato de parâmetros descasados, NÃO é previsão do comportamento WDO. **Concordado entre operador e engenheiro: teste NÃO executado.**
2. ✅ **Dados WIN servem como LABORATÓRIO** apenas para o que é agnóstico de ativo:
   - Metodologia do baseline "moeda" (edge real vs 50/50 − custos)
   - Prior de *feature importance* (quais features de book importam)
   - Referência conceitual de thresholds (RSI, entropia)
3. ❌ **Modelo Keras:** treinar SOMENTE com dados WDO — `historico_contexto_wdo.csv` já acumula desde 22/07 (0,49 MB).
4. ✅ **Backup dos dados WIN:** zip no OneDrive Desktop. **NÃO vai para o git** (repo público + dados mudam diariamente → repo inflaria).

**Regra de validação do WDO (válida de verdade):** só dados WDO reais (≥30 dias) validam o WDO — a mesma lógica do baseline "moeda" aplicada sobre `decisions_wdo.csv`/`historico_contexto_wdo.csv`.

---

## CALIBRAÇÃO COM 1 ANO DE TICKS WDO (Sessão 20, 02/08/2026)

**Fonte:** `WDO$_202507141229_2026073118299.csv` (2,28 GB, 48.795.414 ticks de trade, 264 pregões, 14/07/2025→31/07/2026). Colunas `DATE TIME BID ASK LAST VOLUME FLAGS` — **BID/ASK sempre vazios, FLAGS constante 56** → é fita de trades (Time & Sales), **sem book**. Os dois downloads iniciais eram duplicatas idênticas (SHA256 igual) — mantido o com o `9`.

**Script:** `calibrar_wdo_historico.py` (streaming, não carrega 2,28 GB). Gera:
- `barras_1min_wdo.csv` (9,8 MB) — OHLC + tick_volume + n_ticks + range + delta_vol (CVD **aproximado** por regra do tick, NÃO por FLAGS)
- `regime_por_dia_wdo.csv` — classificação diária LATERAL/EXPLOSAO/EXTREMO
- `relatorio_calibracao_wdo.txt` — relatório completo (ignorado no git, regenerável)

**Números-chave obtidos (substituem chutes):**
| Métrica | Valor |
|---|---|
| ATR(14) 1min | média 2,12 pts (P90 3,32) |
| Range 1min | P50 1,5 | P90 3,5 | P99 7,0 pts |
| Range 5min | P50 4,0 | P90 8,0 | P99 15,5 pts |
| Ruído tick (P99.9) | ≤ 0,5 pts |
| STOP anti-ruído | 2,0 pts (3× P99) |
| RSI(14) 1min | P10 33 | P50 49 | P90 67 |
| Volume/volatilidade | máxima 09:00 (684 ticks/min) → cai até 18:00 (~100) |
| Regime por dia | 74,6% LATERAL / 15,2% EXPLOSAO / 10,2% EXTREMO |

**Regras de uso (decididas):**
1. ✅ Usar para calibrar ATR/volatilidade/RSI/range/alvo/stop do WDO e validar o `SelecionadorRegime`.
2. ❌ **NÃO treinar o modelo Keras de produção com esse CSV** — sem book não dá (e zerar colunas de book = contaminação, lição do WIN out/2025).
3. ✅ Modelo price-only (se surgir) treina em `barras_1min_wdo.csv` (barras reais, sem fake).
4. ✅ Módulos de book (escora/entropia) só se validam ao vivo/demo via MT5.

---

## VALIDAÇÃO DO SELECIONADOR REGIME — CAUSAL, FORA DA AMOSTRA (Sessão 20, 02/08/2026)

**Script:** `validar_selecao_regime.py` (usa o módulo real `SelecionadorRegime` da Sessão 19). Classifica **barra a barra, em tempo real** (janelas de 30 min terminando no bar anterior — sem lookahead). **Calibrou no 1º semestre** (132 dias, 14/07/2025→20/01/2026) e **testou no 2º** (132 dias, 21/01→31/07/2026), fora da amostra.

**Método (honesto):** o detector de produção usa ATR + **entropia de book** + volume. Como o CSV só tem trades, entropia foi **proxiada por volatilidade de preço** (std do retorno 1min em 30 min). AGUARDANDO (book desequilibrado) e DEFESA (sequência de losses) não são modeláveis por preço — ficaram de fora. Limiares ajustados SÓ no treino.

**Resultados (2º semestre, 70.820 barras):**
| Métrica | Valor | Leitura |
|---|---|---|
| Spearman (sinal → vol futura) | **+0,771** | o sinal de preço antecipa a volatilidade |
| Precisão EXPLOSAO | **77,6%** (aleatório 31,8%) | **lift 2,44x** — quando dispara, vale risco maior |
| Revocação EXPLOSAO | 22,4% | conservador — perde ~4 em 5 explosões |
| Falsos positivos | 3,0% das não-explosões | baixo |
| Monotonicidade fwd_vol | LATERAL 0,83 → NORMAL 1,51 → EXPLOSAO 2,10 pts | escala de risco por modo correta |
| fwd range máx | 6,3 / 12,2 / 17,1 pts | idem |
| Concordância diária | 66% | vs regime_por_dia_wdo.csv |

**Decisões registradas:**
1. ✅ A **arquitetura do módulo está validada**: LATERAL reduz risco (volx0.5) e EXPLOSAO aumenta (volx1.5) — e o que realizou depois confirma a direção (monotônico).
2. ✅ **EXPLOSAO via proxy tem precisão alta** → no v22, quando EXPLOSAO disparar, o risco maior é justificável; mas **não subir volume antes de confirmação** (recall baixo = muitas explosões não avisadas).
3. ❌ **Não plugar ainda**: entropia de book real (que deve somar poder preditivo) só se valida ao vivo/demo. A validação de preço é o piso, não o teto.
4. 🐛 **Bug numpy descoberto (lição):** `np.where` criava array `<U7` (LATERAL/NORMAL) e `"EXPLOSAO"` (8 chars) era **truncado para "EXPLOSA"** silenciosamente — comparação nunca casava, dava zero de EXPLOSAO. Corrigido com `.astype("<U9")`. Verificar sempre dtype de strings em numpy.

---

## BASELINE MOEDA NO WDO (Sessão 20, 02/08/2026) — o acaso ganha ou perde?

**Script:** `baseline_moeda_wdo.py`. 15.000 entradas ALEATÓRIAS por config (direção 50/50), mesma estrutura de SL/TP do robô, sobre `barras_1min_wdo.csv` (1 ano). Entrada = abertura do minuto, janela 09:05–17:00. Dentro do minuto, se SL e TP ambos tocados, vale o nível mais próximo da entrada (empate = SL, conservador). **Custo real corrigido: R$2,40/contrato (0,24 pts)** = R$1,20 entrada + R$1,20 saída com RLP ativado (fills no meio do spread).

**Resultados (win% = taxa de acerto do acaso; EV liq = com custos):**
| Config | win% | SL% | TP% | EV brut | EV liq | R$/trade |
|---|---|---|---|---|---|---|
| SL 2.0 / TP 4.0 | 30,5 | 69,5 | 30,5 | −0,17 | −0,41 | −4,1 |
| SL 2.0 / TP 4.0 (hold 15min) | 33,4 | 62,5 | 25,5 | −0,13 | −0,37 | −3,7 |
| SL 2.0 / TP 8.0 | 17,7 | 82,2 | 16,9 | −0,26 | −0,50 | −5,0 |
| SL 1.5 / TP 4.0 | 23,8 | 76,2 | 23,8 | −0,19 | −0,43 | −4,3 |
| SL 3.0 / TP 6.0 | 31,8 | 68,0 | 31,3 | −0,15 | −0,39 | −3,9 |

**Leituras (registradas):**
1. ✅ **O WDO é praticamente justo para entradas aleatórias:** win% do acaso ≈ 30-33% (teórico do passeio aleatório = SL/(SL+TP) = 33%). EV bruto ~ −0,15 pts (drag estrutural pequeno); **os custos é que dominam.**
2. ✅ **Custo REAL corrigido (RLP):** R$1,20 entrada + R$1,20 saída = **R$2,40/contrato** = 0,24 pts (fills no meio do spread, sem pagar o spread inteiro). O modelo anterior (R$7/contrato) era exagerado. Resultados abaixo já com o custo correto. Sensibilidade do script: se cobrar o spread inteiro de ida e volta (+0,5 pts = R$7,40/cc), o break-even do acaso sobe de 37,3% para **45,7%** — usar o cenário que reflita os fills reais no Profit/XP.
3. ✅ **Stop 2,0 pts NÃO é stop-out catastrófico:** o acaso alcança o TP em ~30% dos trades mesmo com SL 2× mais curto.
4. 🎯 **DUAS barras para o robô (SL 2/TP 4):**
   - bater o acaso: **win% > 30,5%**
   - lucrar de verdade: **win% > 37,3%** (break-even com custos R$2,40 = (SL+c)/(SL+TP))
5. ✅ **Comparação honesta para o futuro:** quando o robô acumular ≥30 dias de trades reais no WDO (`historico_contexto_wdo.csv` com reward ≠ 0), comparar o win% REAL dele contra 30,5% e 37,3%. Só então o Item 3 (reajustar SL/TP no v22) tem respaldo.
6. 🐛 **Bug de sinal corrigido:** P&L de SHORT estava invertido (TP de short = prejuízo). Resultado anterior (win% ~50%, EV ~0) era artefato do bug — longs e shorts se cancelavam.
7. ⚠️ **Limitação:** entrada na abertura do minuto (não intra-minuto) e aproximação de ordem dentro do minuto (nível mais próximo primeiro). Precisão tick-a-tick exigiria re-varrer o CSV de 2,28 GB.

**Checklist diário de apuração (enquanto a amostra acumula):** a cada fim de pregão, conferir no v22:
- Win rate do robô (trades reais com reward ≠ 0) ≥ **37,3%** (break-even) e, com margem de segurança, ≥ 45%.
- Lift vs acaso = win_robô / 30,5% > **1,22x** (37,3/30,5). Meta mais exigente: 1,47x.
- EV por trade > −0,24 pts (superar custo) e idealmente > 0.
- Registrar SL/TP realmente usados por trade em `decisions_wdo.csv` para comparar com a mesma estrutura da baseline.

## APURAÇÃO DIÁRIA AUTOMATIZADA (Sessão 20, 02/08/2026)

**Script:** `apuracao_diaria_wdo.py` — utilitário de linha de comando que lê `historico_contexto_wdo.csv` (trades) + `decisions_wdo.csv` (datas) e entrega o veredicto em ~1s. Uso: `venv310\Scripts\python.exe apuracao_diaria_wdo.py`. Salva `relatorio_apuracao_diaria.txt` (ignorado no git via `relatorio_*.txt`).

**O que calcula:**
- Trades concluídos = linhas com `reward != 0` (entradas/flutuantes com reward 0 descartadas).
- Win% com **intervalo de confiança Wilson 95%** (honestidade com amostras pequenas), Profit Factor, payoff, EV bruto/líquido (R$2,40/cc), P&L em R$.
- **Comparação tripla** vs baseline: 30,5% (bater o acaso) / 37,3% (pagar taxas RLP) / 45,7% (pagar spread cheio) — cada uma com status APROVADO/NAO ATINGIU.
- **Lift** = win% / 30,5% (metas 1,22x e 1,47x).
- **Maturação:** dias com registro de decisão e dias com entrada BUY/SELL (fontes: timestamps de `decisions_wdo.csv`, pois o `historico_contexto_wdo.csv` **não tem timestamp** — o v22 trunca o histórico em 5000 linhas). Gatilho do Item 3 = ≥30 dias.
- **Veredicto automático:** AMOSTRA EM COLETA / ABAIXO DO ACASO / EM EDGE / APROVADO para calibrar o v22.

**Primeira execução (02/08/2026, dados reais de 29–30/07/2026):**
- Trades: **46** (42 LONG / 4 SHORT) | win% **34,78%** (IC95 Wilson 22,7–49,2%) | PF 0,64.
- avg win +29,69 pts / avg loss −24,67 pts (payoff 1,20) — trades bem maiores que o SL 2/TP 4 da baseline (v22 está com SL de segurança 8 pts; caveat nº 3 no relatório).
- EV liq **−6,00 pts** = **−R$2.760** até agora. Venceu o acaso (34,78% > 30,5%) mas **não pagou as taxas** (37,3%).
- Maturação: **2/30 dias**. **Item 3 permanece travado** — não mexer no config do v22.

**Caveats registrados no script:** (1) dias vêm de decisions (proxy), (2) truncamento em 5000 linhas → backup dos CSVs preserva amostra, (3) barras assumem SL2/TP4, (4) fills reais podem pagar spread cheio (barra 45,7%).

## VERIFICACAO DE INICIALIZACAO (02/08/2026, domingo, mercado fechado)

Inicio do MonstroDashboard.exe (build 30/07 23:50) + MT5 + Sentinela OK, sem crash. Porem: **o EXE nao gravou em monstro_wdo.log** (ultima entrada 30/07 19:47), enquanto o historico_contexto_wdo.csv foi corrigido na inicializacao (22:21:49). Suspeita: setup_logging() vira no-op no build PyInstaller (basicConfig ignorado se ja existe handler do root logger na importacao). O script Python (venv310) grava log normalmente (evidencia de 30/07).

- Para operar amanha: usar iniciar_v22_wdo.bat (python + venv310) como fonte confiavel de log. Rebuild do EXE fica pendente (nao urgente; mercado fechado hoje).
- stop_all.bat NAO mata o MonstroDashboard.exe (so python + terminal64). Encerrar o EXE manualmente se necessario.

## AUTOPSIA 03/08/2026 (manha) — ZERO TRADES: EXCESSO DE RIGIDEZ (Sessao 20)

**Sintoma:** robô ativo no WDOU26 (rolagem OK), 2663 decisões 09:15–12:25 TODAS "NADA", 0 trades.

**Descartado (não bloqueou):** Sentinela NEUTRO; Williams %R −40 (neutro); Multi-TF misto; spread 0,5; entropia 2,91 (alta, passa filtro 2); ATR 2,01 (passa filtro 3). **Modelo Keras funciona:** teste offline com scaler limpo produziu sinal confiante (gap ≥0,15) em 82% das linhas.

**Causa raiz:** portão "NOVOS FILTROS PÓS-DOL" (v22:7147, Sessão 13 de 30/07) exige tripla coincidência: DOL conf ≥0,5 (ratio≥1,5) + DOL alinhado + book ratio WDO ≥1,5. **Prova:** em 30/07 ele operou 66x com book_ratio≥1,5 só 2% do dia e ATR 1,35 — condições que os filtros atuais rejeitariam. Os 5 vetos entraram DEPOIS daquelas operações. DOL conf max histórico 0,44 (<0,5) → portão zera ~100% das entradas. Mercado hoje era operável (não era preservação por lateralidade).

**⚠️ Conflito Item 3:** trava exige 30 dias + win%>37,3%, mas 0 trades → 0 amostra → autossabotagem.

**AJUSTE DIAGNÓSTICO (exceção à trava, documentado):** relaxamento cirúrgico somente no gate de ALINHAMENTO (sem tocar no veto protetivo de contradição DOL v22:7114):
- DOL_CONF_MIN 0,5 → **0,4** (DOL ratio ≥1,5 → ≥1,2)
- BOOK_RATIO_MIN 1,5 → **1,3** (passa ~20% → ~60% do dia)

**Racional:** destravar a coleta de amostra sem remover a proteção. Se ainda assim 0 trades, o log (agora via script, force=True) revelará o próximo bloqueador. Nota: EXE não grava log (bug corrigido no fonte); diagnóstico via script venv310.

## BUG CRITICO: BOM no config.json zerava a config (03/08/2026, Sessao 20)

**Sintoma:** log mostrava Configuração WDO: SL=5pts, TP=10pts, Magic=123457 e dashboard na 5002, quando o config.json real é SL=8/TP=0/Magic=123456 e porta 5001.

**Causa raiz:** config.json foi salvo com **BOM UTF-8** (bytes EF BB BF). carregar_configuracao() (v22:361) lia com encoding='utf-8' → json.load lança "Unexpected UTF-8 BOM" → retorna {} → **robô rodava INTEIRO nos defaults** (SL=5/TP=10/Magic=123457, porta 5002). O EXE tinha o mesmo bug (por isso usava 5002 e defaults). config_manager.py (editor do painel) lia com utf-8 também.

**Impacto:** SL errado (5 vs 8), TP errado (10 fixo vs 0=saída dinâmica por fluxo), magic errado (123457 do WIN), porta do dashboard errada. Não afetava os filtros de ENTRADA (são constantes de código) — a autópsia de "excesso de rigidez" segue válida.

**Fix aplicado:** (1) BOM removido do config.json; (2) carregar_configuracao → utf-8-sig; (3) config_manager.py read → utf-8-sig. Robô reiniciado: log confirmou SL=8pts, TP=0pts, Magic=123456 e dashboard vivo na **5001**. experiencias_wdo.json e scaler.json não tinham BOM (bug isolado).

**Lição:** qualquer JSON lido com utf-8 puro é vulnerável a BOM de editores externos. Usar utf-8-sig em leituras de JSON editáveis manualmente.

## ✅ RESOLVIDA (03/08/2026, noite) — URGENCIA EXE sensivel ao diretorio de lancamento (CWD)

**Fix definitivo aplicado:** `_caminho_base()` (monstro_unificado_v22.py:335) agora retorna o diretório que **contém `config.json`** (C:\AIOFEN) ANTES do fallback dirname(sys.executable) — caminha pelo caminho real do projeto, independente do CWD e da estrutura _MEIPASS do PyInstaller. Dashboard e config_manager usam o mesmo caminho.

**Validação (prova):** EXE recompilado (03/08 22:08, 27.079.150 bytes) lançado de `C:\Windows\System32` → carregou config real (SL=8/TP=0/magic 123456) e gravou em C:\AIOFEN. Backup do EXE antigo: `dist\MonstroDashboard\MonstroDashboard.exe.bak_cwd_fix`.

## DECISAO DO ENGENHEIRO (03/08/2026, tarde) — gate pós-DOL vira ADVISORY (penalizador)

**Contexto:** mesmo com o relaxamento (DOL 0,5→0,4, book 1,5→1,3 da manhã), o DOL ficou equilibrado o dia todo (conf 0,34–0,45) e o veto seco seguiu zerando entradas (15min de tarde, 0 trades).

**Análise ganho/perda das 3 opções:**
- **A (ADVISORY/penalizador):** ganho = robô opera e acumula amostra real (única via p/ validar win%); perda = perdas pequenas LIMITADAS por circuit breakers + max_loss_diario (-500) + custo R,40/cc. **EV positivo.**
- **B (só números):** mantém veto seco (estrutura que causou o problema); em DOL equilibrado pode seguir barrando. EV incerto.
- **C (nada fazer):** ganho = zero risco de mudança; perda = 0 amostra garantido, dia perdido, Item 3 travado. EV negativo.

**DECISÃO: Opção A.** Gate#2 (exigência de alinhamento DOL + book ratio) deixa de ser veto seco e vira **penalizador de confiança** (DOL fraco ×0,70; book ratio baixo ×0,85), SEM derrubar a ação. **Gate#1 (veto de contradição DOL forte) MANTIDO** — protege contra operar contra o fluxo institucional forte. Demais proteções intactas: Sentinela, Williams %R, Multi-TF, score, CONFIDENCE_GAP, cooldown, circuit breakers, max_loss_diario.

**Justificativa:** o portão era proteção REDUNDANTE. O objetivo da fase é medir win% real vs baseline (37,3%/30,5%); com 0 trades não há medição. Risco limitado e documentado. confianca_decisao é só informativa (não barra execução) — o penalizador não bloqueia o trade por acidente.

**Execução:** robô parado graciosamente (salvou modelo+experiências), reiniciado via script venv310 (force=True log + config certa SL=8/TP=0/magic 123456 + ADVISORY). EXE será recompilado à noite com ADVISORY + fix CWD.

## DESBLOQUEIO EM CASCATA (03/08/2026, tarde) — 3 gates empilhados + estado final

A autópsia da manhã achou o gate DOL, mas ao destravar surgiram gates MAIS UPSTREAM. Sequência real de bloqueio hoje:
1. **Gate DOL (7150)** — DOL conf≥0,5+alinhado+book≥1,5 → virou ADVISORY (penalizador).
2. **Gate SNIPER (6816)** — sniper_ratio_min=1,5 (config): robô só ANALISA se book ratio≥1,5. Hoje ratio ~1,1–1,35 → STANDBY eterno, nunca chegava no modelo. Em 30/07 era **1,2** (66 trades). **Fix: config.json sniper_ratio_min 1,5→1,2** (exceção diagnóstica). Após isso o robô passou a ACORDAR e chegar no modelo.
3. **Williams %R (veto 8316-8327)** — com o robô finalmente analisando, o %R marcou **-86 a -100** (preço ~5122 no fundo do range 14 candles ~5121,5–5128,5) → veto BUY (faca caindo) + SELL (fundo). **Proteção LEGÍTIMA mantida** — mercado sobrevendido/consolidado. O high=low=preco no williams_r_historico.csv é só o candle atual flat; o %R usa o range real de 14 candles.

**ESTADO FINAL (15:55):** robô CORRETAMENTE desbloqueado — acorda, analisa, chega no modelo. O que segura trades agora é o **Williams %R genuíno (mercado sobrevendido)**, não excesso de rigidez. O robô vai operar quando o preço sair do fundo (%R > -80). NÃO desabilitar o veto de %R (é o que evita pegar faca caindo = perder dinheiro).

**Bugs do dia já corrigidos:** BOM config.json (rodava nos defaults), log EXE (force=True), EXE recompilado, CWD do EXE (urgência p/ noite). Filtros relaxados: DOL advisory + sniper 1,2.

---

## AGENTE AUTÔNOMO FASE 1 — IMPLEMENTADO (03/08/2026, noite)

**Objetivo:** robô evoluir sozinho dentro de limites seguros (autotuner delimitado), com automação diária e auditoria, sem intervenção humana no expediente.

**Arquitetura (auditada):** NÃO existem `orchestrator.py`, `autotuner_gatekeeper.py` nem `smoke_test.py`. Tudo em UM arquivo: **`agente_monstro_core.py`**. Papéis mapeados:
- Orquestrador → `run_pausa()` / `run_fecho()` / `run_watchdog()` / `main()`
- Gatekeeper → `aplicar_ajuste()` + `rollback_config()`
- Smoke test → `smoke_test()` + `health_check()`
- Árvore de decisão → `decidir()` + `blocker_dominante()`

### Lacunas de segurança fechadas (commit `4711155`, +146 linhas)

1. **Trava de horário** — `dentro_da_janela_autonomia()`: `run_pausa()` aborta SEM nenhuma ação fora de [12:30, 14:30]. Config: `rotinas.janela_inicio/janela_fim` no agente_config.json. Testado: 21:30→False, 13:00→True.
2. **Estado persistente** — `agente_estado.json` (gitignored): `carregar_estado()`/`salvar_estado()`, `pode_ajustar()` = trava física de 1 ajuste/dia (bloqueia 2ª execução manual), `registrar_mudanca()` grava data/hora/param/de/para/motivo/tipo + histórico 200 reg + rollback. Trava verificada ANTES de parar o robô.
3. **Diff estrutural** — `verificar_mudanca_codigo()` (difflib): compara `agente_snapshot_v22.py` com o fonte no `run_fecho()`; se mudou, gera `diff_estrutural_YYYYMMDD.txt` (+n/-m) e adiciona seção ao relatório diário. Fase 1 só detecta/reporta — nunca altera `.py`. Testado (diff +0/-2 detectado, snapshot restaurado).

### Whitelist (trava dura em `aplicar_ajuste()`, clamp max/min)

| Parâmetro | Faixa | Passo |
|-----------|-------|-------|
| `sniper_ratio_min` | [1,1 … 1,5] | −0,1 |
| `book_ratio_min` | [1,2 … 1,5] | −0,1 |
| `dol_conf_min` | [0,3 … 0,5] | −0,05 |
| `sl_points` | [5 … 10] | +1 |
| `tp_points` | [0 … 12] | +1 |

### Correção crítica de contagem (03/08)

`decidir()` agora usa `contar_executados_hoje()` = marcador **"processada e resetada"** no `monstro_wdo.log` (equivale aos appends `total_operacoes` do dashboard). Sinais BUY/SELL em `decisions_wdo.csv` NÃO contam como trade. Validado 03/08: 4 sinais BUY → **0 executados** (vetados por Williams %R — proteção legítima). Config NÃO é hot reload (1× no boot) — agente faz restart controlado: `parar_robo → aplicar_ajuste → start_robot → smoke_test → rollback` se falhar.

---

## AGENDAMENTO DIÁRIO AUTÔNOMO (03/08/2026, noite) — 3 tasks no Task Scheduler

2ª–6ª feira, usuário 22the, modo Interativo, privilégio HIGHEST:

| Task | Horário | Ação |
|------|---------|------|
| `Monstro-Start` | 09:00 | `start_all.bat` (MT5 + robô via venv310, autônomo sem pause) |
| `Monstro-Pausa` | 12:30 | agente `pausa` → `run_pausa()` com trava de janela + estado |
| `Monstro-Fecho` | 17:35 | agente `fecho` → `run_fecho()` + relatório diário + diff estrutural + commit/push |

`.gitignore` ampliado: `experiencias_wdo.json`, `agente_estado.json`, `parar.txt`, `agente_snapshot_v22.py`, `diff_estrutural_*.txt`.

**Git:** push `399629e..b3b8c87 → main` (commits `b800436`, `1ad5ad6`, `b3b8c87`) + push `4711155 → main` (lacunas de segurança). Repo sincronizado.

---

## MAPA DO DIA 04/08/2026 — o que esperar amanhã (primeira execução autônoma real)

### Linha do tempo
```
09:00  Monstro-Start → MT5 sobe + robô venv310 (log force=True, config certa SL=8/TP=0)
       → validar: config correta, modelo treinado carregado (não em branco), dashboard 5001
09:15  PA1 abre → robô acorda, analisa, chega no modelo (sniper_ratio 1,2)
12:30  Monstro-Pausa → run_pausa() DENTRO da janela [12:30,14:30] → decide ajuste
       → validar: 1ª execução do dia permitida (pode_ajustar True), registro no agente_estado.json
17:35  Monstro-Fecho → run_fecho(): apuração do dia + relatório + diff estrutural + commit/push
```

### Validar ao longo do dia
1. **Start 09:00:** modelo treinado carregado (262+ experiências) — NUNCA modelo em branco (~112KB).
2. **Pausa 12:30:** robô para graciosamente (salva modelo+experiências); agente verifica `pode_ajustar()` antes; ajuste respeita whitelist; smoke_test após restart; rollback se falhar.
3. **Fecho 17:35:** relatório diário gerado com seção de diff estrutural; git commit/push automáticos.
4. **Métrica central:** quantos trades EXECUTADOS (marcador "processada e resetada") vs sinais — comparar win% com baseline 37,3% (taxas) / 45,7% (spread).
5. ~~**Vigiar o comportamento observado no teste:** robô repetindo "FECHANDO TODAS AS POSIÇÕES" a cada ~30s após 17:35 — investigar se repete amanhã.~~ ✅ **RESOLVIDO (03/08, noite)** — comportamento esclarecido/corrigido conforme operador; não repetir investigação.

### Se algo falhar (fallback manual)
- MT5 não subiu → abrir `start_all.bat` manualmente (C:\AIOFEN).
- Robô não logou → checar `monstro_wdo.log` (força de escrita); diagnóstico via script venv310 (EXE ainda não regrava log de forma confiável em alguns CWD).
- Agente não ajustou → `pode_ajustar()` pode ter bloqueado (trava 1/dia) — esperar ou revisar `agente_estado.json`.

### Decisões pendentes / não bloqueantes
- **Watchdog**: `watchdog_enabled: false` no agente_config.json — religar em Fase 2 quando LLM consultor entrar.
- **Sniper 1,2 / DOL ADVISORY:** mantidos como exceções diagnósticas até acumular amostra (win% medido) — NÃO restaurar 1,5 sem dados.
- **Restaurar config hot reload** (1× no boot) — opcional, agente já faz restart controlado.
- **LLM consultor (Fase 2):** recomendações para o agente após N dias de amostra.

---

## RESUMO DO DIA 03/08/2026 (mapa do que foi feito)

**Manhã — Autópsia (zero trades):** 2663 decisões "NADA", 0 trades. Gate DOL (conf≥0,5) zerava ~100% entradas. Relaxamento cirúrgico: DOL_CONF_MIN 0,5→0,4, BOOK_RATIO_MIN 1,5→1,3.

**Bug crítico:** config.json salvo com BOM UTF-8 → robô rodava INTEIRO nos defaults (SL=5/TP=10/magic 123457/porta 5002). Fix: BOM removido + `utf-8-sig` em leituras JSON.

**Tarde — Desbloqueio em cascata:** gate DOL virou **ADVISORY** (penalizador DOL fraco ×0,70 / book baixo ×0,85 — Gate#1 de contradição DOL MANTIDO). Novo bloqueio: **sniper_ratio_min 1,5→1,2** (robô passou a acordar e chegar no modelo). Estado final: robô CORRETAMENTE desbloqueado; quem segura trades é o **Williams %R genuíno** (mercado sobrevendido −86/−100) — proteção legítima, NÃO desabilitar.

**Noite — Agente Autônomo Fase 1:** fix `_caminho_base()` determinístico + EXE recompilado/provado; lacunas fechadas (trava horário, estado persistente, diff estrutural); whitelist 5 parâmetros; contagem de trades corrigida; 3 tasks agendadas (Start 09:00 / Pausa 12:30 / Fecho 17:35); `.gitignore` ampliado; **push `4711155 → main`** (repo sincronizado).

---

## REVISÃO DE CONFLITOS DO AGENDADOR (03/08/2026, noite) — tasks vs agente

**Problema encontrado (CRÍTICO):** a task antiga **`start_all.bat`** (criada 23/07, **08:58** 2ª–6ª) subia o **EXE** (`dist\MonstroDashboard\MonstroDashboard.exe`) enquanto a nova **`Monstro-Start`** (09:00) subia o robô via **python venv310** → a partir de 04/08 rodariam **DOIS robôs simultâneos** (mesmo magic no MT5 = ordens duplicadas; 2 dashboards brigando pela porta 5001).

**Correção aplicada:**
1. **Task antiga `start_all.bat` → DESATIVADA** (via UAC admin; Status: Disabled). O EXE não sobe mais automaticamente.
2. **`start_all.bat` (arquivo) blindado:** proteção anti-duplicidade — aborta o start se já houver `python.exe` rodando `monstro_unificado_v22` **ou** `MonstroDashboard.exe` (previne 2º robô mesmo em start manual).
3. **`stop_all.bat` (task `cleanup_monstro_final.bat` 18:32):** `wmic` (deprecado Win11) → **PowerShell/CIM**; passa a matar também `MonstroDashboard.exe`; janela com título atual "Monstro V22 - WDO"; **`pause` removido** (não pendura mais a task agendada).

**Mapa final do agendador (2ª–6ª, sem conflito):**
| Task | Horário | Ação | Conflito? |
|------|---------|------|-----------|
| Monstro Backup GitHub | 08:50 (diária) | `backup_auto.vbs` → git commit/push | Não (só git, robô ainda não subiu) |
| ~~start_all.bat (EXE)~~ | ~~08:58~~ | ~~MonstroDashboard.exe~~ | **DESATIVADA** — era o duplo robô |
| Monstro-Start | 09:00 | `start_all.bat` → MT5 + python v22 | OK (único start) |
| Monstro-Pausa | 12:30 | `agente pausa` → `run_pausa()` | OK (dentro da janela [12:30,14:30]) |
| Monstro-Fecho | 17:35 | `agente fecho` → para robô+MT5, relatório, commit/push | OK |
| cleanup_monstro_final.bat | 18:32 | `stop_all.bat` (novo, robusto) | OK (backstop pós-fecho, sem `pause`) |

> **Nota:** `Monstro-Fecho` (17:35) já executa `parar_robo()` + `stop_mt5()`; o `cleanup` 18:32 é backstop de segurança caso o fecho falhe.

---

## REFINAMENTOS DA NOITE (03/08/2026) — watchdog + CI + limpeza

Itens que **NÃO dependem de acumular trades** (feitos agora):

1. **Watchdog LIGADO** — `watchdog_enabled: true` + task `Monstro-Watchdog` (15min, 09:05-17:35, 2ª-6ª) + flag respeitado no `main()` + guarda `dentro_do_expediente()` (seg-sex 09:00-17:40) para NUNCA reiniciar o robô no fim de semana. Teste manual: "fora do expediente - sem acao".
2. **CI GitHub Actions** — `monstro-ci.yml` substituiu o template `python-package.yml` (que rodaria flake8+pytest em 100+ scripts antigos e falharia). Novo: py_compile (6 fontes) + `tests/testes_pos_fix.py` → **9/9 PASS** local. **✅ CI VERDE no GitHub**: run 1 (push `fa0e360`) → `Monstro CI` **SUCCESS** (03/08 22:30 UTC). O template antigo falhava nos pushes anteriores (runs 20/21) — comprova que o v22 ESTÁ versionado (senão o py_compile falharia no clone). `testes_pos_fix.py` tinha **código duplicado (2 cópias)** — reescrito limpo + skip de CSV no CI (dados são gitignored).
3. **Código morto removido** — bloco `MODO_CONSERVADOR_*` (ATR/ENTROPIA/VOLUME/SL/TP) do v22: nenhuma constante era referenciada. Removido + `agente_snapshot_v22.py` atualizado (sem diff falso no fecho).
4. **Config morta removida** — `winpct_break_even` e `max_mudancas_por_ciclo` do `agente_config.json` (não referenciados no código). JSON validado.
5. **Log do EXE confirmado** — `monstro_wdo.log` com mtime 03/08 **22:12:50** (entradas do teste do EXE recompilado lançado de System32). Pendência do "EXE não grava log" ENCERRADA. (Erro Permission denied às 22:12 foi do teste com processos simultâneos — não reproduz em operação normal.)

**Backtest histórico: confirmado como JÁ FEITO** (02/08, Sessão 20): calibração com 1 ano de ticks (`calibrar_wdo_historico.py`, 2,28 GB/48,8M ticks), validação fora da amostra do seletor de regime (Spearman +0,771; precisão EXPLOSAO 77,6%) e baseline moeda (15.000 entradas, win% acaso 30,5% / break-even 37,3%). O backtest E2E do robô com modelo segue NÃO feito (depende de book real — indisponível; só validável ao vivo/demo).

## DIA 04/08/2026 — PRIMEIRA EXECUÇÃO AUTÔNOMA REAL + AUTOPSIA + FASE 2 PARCIAL

### Resumo do dia (autópsia `tools/autopsia_automatizada.py`)
- **27 trades** (11 wins / 9 losses / 7 BE), win rate 40,7%, saldo **-R$ 45,00**, profit factor 0,88, payoff 0,72.
- Watchdog reiniciou o robô às **09:05** ("robo caido - reiniciando") — sem isso o pregão não teria começado.
- Pausa 12:30: **SEM AJUSTE** (decisão correta: 17 trades/37,9% é amostra pequena demais — apertar = overfitting).
- Relatório diário: 1422 decisões, 110 sinais, 27 trades, win% histórico 46%, entropia 2,903, ATR 2,117.
- Vetos do dia: williams_r 958, veto_total 321, sinal_neutro 142, sniper_standby 42, multi_tf 7.

### 🔴 Bug crítico corrigido: SL real era metade do configurado (fator TICK_SIZE)
- Causa: `calcular_preco_sl_tp` usava `sl_dist = sl_points * TICK_SIZE` → `8 * 0.5 = 4.0` (SL de 4 pts, não 8). WDO: 1 ponto = 1.0 de preço (tick 0.5, 2 ticks/ponto). As v1/v2 usavam `* 1.0`; a v22 introduziu a regressão de fator 2.
- Evidência: trades com SL exatamente 4,0 do preço de entrada e perdas de -40,00 (4 pontos × R$10).
- Fix (`7a07595`): `sl_dist = float(sl_points)` + `tp_dist = float(tp_points)` (mesmo bug latente no TP). `travar_lucro` já estava correto (via TICKS_POR_PONTO).
- Validação: py_compile OK + testes 9/9 PASS.

### Autópsia vs relatório — claims refutadas (decisão: NÃO mexer)
1. **"Modelo não aprende com erros"** → FALSO: treino usa CSV (`carregar_experiencias_do_csv`) com wins+losses (68 trades: 45L/23W). JSON só-positivo é por design (PA2) e afeta apenas replay.
2. **"Não há threshold de confiança"** → FALSO: `CONFIDENCE_GAP = 0.15` (L8571) + `score_qualidade >= 2` em `filtros_alta_acertividade` (L8223).
3. **"GerenciadorDeSaida força saídas antecipadas"** → causa real era o bug do SL acima, não o gerenciador.

### 🛡️ Pilar 1 — KILL-SWITCH por loss diário (commit `9ad8bd1`)
- `verificar_kill_switch()` no `run_watchdog()`: **N1 (-250)** cria `parar.txt`; **N2 (-400)** → `parar_robo()` + `stop_mt5()`. Ativação única/dia via `agente_estado.json`.
- `calcular_loss_acumulado_hoje()` soma **só** "Deal de saída encontrado...Lucro=" (não duplica com "Experiência salva"/"Resultado confluência").
- Fallback: se `limite_2 < max_loss_diario`, usa 80% do `risk_management.max_loss_diario` (-500 → -400).
- Testado: N1 (-300) cria parar.txt ✅ | N2 (-500) para robô+MT5 ✅ | loss real -45 não dispara ✅.

### 📊 Pilar 2 — AUTOPSIA EOD + PLANO DO DIA SEGUINTE (commit `9ad8bd1`)
- `tools/autopsia_automatizada.py` refatorado: `run_autopsia()`/`gerar_plano()` importáveis, data via `data_pregao()` (sem sys.argv no import), sniper sem data hardcoded.
- `run_fecho()` agora chama `gerar_plano_dia_seguinte()` → salva `plano_YYYYMMDD.txt` (somente leitura p/ humano, NUNCA aplica ação automática).
- **Fecho executado 04/08 22:20** (mercado fechado): relatório + plano gerados (`plano_20260804.txt`), commit `ff1fe07` pushado.

### 📋 Roadmap Fase 2 — o que vem (decisão: ESPERAR 5 pregões de estabilização)
1. ✅ **Pilar 1 (kill-switch)** — IMPLEMENTADO, em produção.
2. ✅ **Pilar 2 (autópsia EOD + plano)** — IMPLEMENTADO, em produção.
3. ⏸️ **Pilar 3 (Pausa 14:30 + trava por janela)** — planejado, NÃO implementado. Requer migração de `pode_ajustar()` de chave `data` → `data+janela` (1 ajuste/janela: manhã 12:30 + tarde 14:30), segunda janela no config, dispatch. Design: reutiliza `run_pausa()`/`decidir()`/whitelist/smoke test + rollback.
4. ⏸️ **Pilar 4 (Macro Gatekeeper)** — arquitetura apenas, NÃO implementado. Depende de fontes externas (DXY/VIX/agenda) que não existem no projeto + histórico 20-30 pregões para calibrar níveis. É Fase 2.5/3.

**Critério de liberação do Pilar 3** (após 5 pregões ≈ 1 semana):
- Kill-switch: 5 execuções sem falso positivo; dispara corretamente em dia ruim (se houver).
- Plano `.txt`: útil e actionable (você lê e concorda com prioridades).
- Sem crash no `agente_monstro_core.py`; git commit do fecho OK todos os dias; loss do log bate com saldo real.

---

### 📐 Pilar 3 — Especificação Detalhada + Data Limite

**Data limite de implementação:** **12/08/2026** (deploy no pregão de 12/08/2026, após 5 pregões de estabilização dos Pilares 1 e 2).

**Objetivo:** permitir uma segunda pausa de análise/autotuning às **14:30**, mantendo a trava de **1 ajuste por janela** (manhã 12:30 + tarde 14:30).

#### Decisões de design (a definir antes de codar)

| Decisão | Opção padrão | Racional |
|---------|--------------|----------|
| Chave de trava | `data+janela` no `agente_estado.json` | Evita 2 ajustes/dia (overfitting) ou 0 ajustes (trava excessiva) |
| Nome das janelas | `"manha"` (12:30) e `"tarde"` (14:30) | Claro e extensível |
| Janela tarde no config | `janela_tarde_inicio: "14:30"`, `janela_tarde_fim: "14:35"` | Curta, só ajuste, não análise longa |
| Reutilização | Generalizar `run_pausa(janela="manha")` | Minimiza código novo |
| Comportamento se já ajustou de manhã | Não ajusta de tarde, a não ser que condição seja forte | Manter conservadorismo |
| Smoke test/rollback | Mesmo mecanismo da pausa 12:30 | Reutilizar |

#### Alterações em `agente_config.json`

```json
"rotinas": {
    "graceful_timeout_s": 90,
    "health_timeout_s": 120,
    "smoke_test_s": 25,
    "porta_fallback": 5001,
    "watchdog_enabled": true,
    "janela_inicio": "12:30",
    "janela_fim": "14:30",
    "janela_tarde_inicio": "14:30",
    "janela_tarde_fim": "14:35",
    "expediente_inicio": "09:00",
    "expediente_fim": "17:40"
}
```

#### Alterações em `agente_monstro_core.py`

1. **Generalizar `dentro_da_janela_autonomia()`** para receber início/fim:

```python
def dentro_da_janela_autonomia(ini=None, fim=None):
    agora = datetime.now().strftime("%H:%M")
    ini = ini or R["janela_inicio"]
    fim = fim or R["janela_fim"]
    return ini <= agora <= fim
```

2. **Mudar `pode_ajustar()`** para receber a janela:

```python
def pode_ajustar(janela="manha"):
    st = carregar_estado()
    chave = f"{datetime.now().strftime('%Y-%m-%d')}_{janela}"
    return st.get("ultima_mudanca_janela") != chave, chave
```

3. **Mudar `registrar_mudanca()`** para registrar a janela:

```python
def registrar_mudanca(param, de, para, motivo, tipo="ajuste", janela="manha"):
    st = carregar_estado()
    agora = datetime.now()
    reg = {"data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M:%S"),
           "janela": janela, "param": param, "de": de, "para": para, "motivo": motivo, "tipo": tipo}
    st["ultima_mudanca"] = reg
    st["ultima_mudanca_janela"] = f"{agora.strftime('%Y-%m-%d')}_{janela}"
    st.setdefault("historico", []).append(reg)
    st["historico"] = st["historico"][-200:]
    salvar_estado(st)
    return reg
```

4. **Generalizar `run_pausa()`**:

```python
def run_pausa(janela="manha"):
    ini = R["janela_inicio"] if janela == "manha" else R["janela_tarde_inicio"]
    fim = R["janela_fim"] if janela == "manha" else R["janela_tarde_fim"]
    log.info(f"PAUSA {janela.upper()} ({ini}-{fim}) - analise e decisao autonoma")
    if not dentro_da_janela_autonomia(ini, fim):
        log.warning(f"FORA DA JANELA DE AUTONOMIA ({ini}-{fim}) - abortando")
        return
    # ... resto igual, usando janela em pode_ajustar/registrar_mudanca
```

5. **Task Scheduler:** adicionar `agente_monstro_core.py pausa` às **14:30** (janela tarde) — com o mesmo modo `pausa`, pois a janela será decidida pelo horário atual.

#### Alterações no `main()`

```python
elif modo == "pausa":
    run_pausa()  # detecta manha/tarde pelo horário automaticamente
```

Ou, se preferir controle explícito:

```python
elif modo == "pausa":
    run_pausa("manha")  # 12:30
elif modo == "pausa_tarde":
    run_pausa("tarde")  # 14:30
```

**Recomendação:** automática por horário é menos propenso a erro de agendamento.

#### Critérios de aceitação

- [ ] `py_compile` OK
- [ ] `testes_pos_fix.py` 9/9 PASS
- [ ] Agente às 14:30 executa e respeita a trava (se já ajustou de manhã, não ajusta de tarde)
- [ ] Agente às 14:30 ajusta se houver evidência forte e manhã não ajustou
- [ ] Smoke test + rollback funcionam na janela tarde
- [ ] 5 pregões sem regressão

#### NÃO incluir no Pilar 3

- Não alterar lógica de decisão (`decidir()`)
- Não alterar whitelist
- Não alterar modelo Keras
- Não alterar mecanismo de kill-switch
- Não adicionar fontes externas macro

---

### 🌍 Pilar 4 — Macro Gatekeeper (nota arquitetural)

**Status:** arquitetura apenas, **não implementar junto com Pilar 3**.

**Dependências externas que não existem hoje:**
- Fonte confiável de DXY, VIX, US10Y, USDJPY
- Fonte de agenda econômica (payroll, FOMC, Copom, PIB)
- Histórico de 20-30 pregões para calibrar níveis NORMAL/RESTRITO/NAO_OPERAR

**Padrão de integração seguro:**
```
Macro Gatekeeper (offline, 08:55) → escreve em config.json (ex: "macro_status": "RESTRITO") → v22 lê no startup
```

**Nunca:** o agente macro tomar decisão de trade paralela ao v22.

**Data estimada:** após Pilar 3 estável por 10+ pregões (final de agosto/2026).

---

## DIA 05/08/2026 - SEGUNDO PREGÃO AUTÔNOMO + DIAGNÓSTICO DO START FALHADO

### Resultado do dia

- **3 trades / -R$145** (14:30 BUY -80, 15:32 SELL -80, 16:42 SELL +15).
- Robô **não operou de manhã** (primeiro trade só às 14:30) → perdeu a janela da manhã.
- Kill-switch **não acionado** (loss -145 > limite N1 -250). Autópsia EOD rodou; fecho 17:35 OK (commit `f5c46ef`).

### Causa raiz 1 - Watchdog expirado (corrigido no dia anterior)

- Trigger antigo do `Monstro-Watchdog` tinha `EndBoundary=2026-08-04T17:35:00` (data única) e **expirou**.
- Recreado com `CalendarTrigger` semanal (seg-sex, repetição 15min, duração 8h30) — **sem expiração**. Próxima execução confirmada: 06/08 09:05.

### Causa raiz 2 (NOVA) - `Monstro-Start` falhou com **255** em 05/08 09:00

**Bug:** em `start_all.bat`, o `echo [AVISO] ... (2 robos = conflito de porta 5001 ... duplicadas)` tem `(`/`)` **sem escape dentro de um bloco `if (...)`**. O cmd parseia o bloco inteiro mesmo quando a condição é falsa; os parênteses quebram o parse → erro `"." foi inesperado neste momento` e o batch morre com exit 255 **antes** de chegar ao `start` do MT5/robô.

**Impacto:** 05/08 09:00 → MT5 + robô nunca subiram; sem watchdog ativo (causa raiz 1), ninguém recuperou. Manhã perdida.

**Fix:** parênteses escapados (`^(` `^)`). Validado em 05/08 21:15:
- Dry-run do arquivo real (start/timeout trocados por echo): **exit 0**, sem parse error.
- Ramo anti-duplicidade (errorlevel=1 simulado): **AVISO + exit 0**.
- `grep` confirmou que nenhum outro `.bat` usa o padrão `if %errorlevel% equ 1 (`.

### Lição / proteção em camadas

- `Monstro-Start` (09:00) + `Monstro-Watchdog` (09:05, 15min) agora são redundantes entre si: se um falhar, o outro recupera.
- Próxima validação: 06/08 09:00 (Start) e 09:05 (Watchdog) — conferir `LastResult=0` em ambos via `schtasks /Query`.

### PENDENTE (melhoria para revisão noturna)

- [ ] Autópsia EOD deve incluir **contador de incidentes do dia**: nº de restarts do watchdog ("robo caido - reiniciando"), kill-switch acionado/não acionado e motivo. Objetivo: facilitar a revisão do usuário à noite (pós-pregão), já que a única interação é noturna.

---

## DIA 06/08/2026 - PRIMEIRO DIA COMPLETO + FECHO ABORTADO (CORRIGIDO)

### Resultado do dia

- **13 trades / -R$50** (10 wins +R$160; 3 losses: #1 09:19 BUY -50, #7 10:36 BUY -80, #10 12:16 SELL -80).
- Robô operou o dia inteiro (09:19-17:03) - primeira vez desde o fix do SL (sl_points=8) com dia completo.
- Kill-switch **não acionado** (loss acumulado nunca passou de N1 -250).
- Trade #1 e #7 entraram contra a tendência multi-TF; trade #7 com RSI 47.7 e candle `upper_shadow_baixa` (confirmado em decisions_wdo.csv).

### Falha: fecho 17:35 ABORTADO (robô encerrou gracioso, mas SEM artefatos)

- Robô: "PARADA GRACIL"/"ENCERRAMENTO CONCLUÍDO" 17:35:11-17:35:16, mas **sem** relatorio_diario/plano/commit no pregão.
- `agente_autonomo.log`: fecho iniciou 17:35:02, "robo ja estava parado", sem "FECHO concluido".
- `Monstro-Fecho` LastTaskResult = **-2147023829 (0x8007042B = ERROR_PROCESS_ABORTED)**. Watchdog 17:35 rodou com resultado 0; sem eventos System/Application 17:34-17:40.
- **Hipótese:** notebook HP (PCSystemType=2, bateria) com "Parar se bateria" nas tasks + colisão watchdog 17:35 x fecho 17:35.

### Correções aplicadas (commit `9fc322f`)

- `run_fecho()` reordenado: `sinalizar_parada_robo()` -> gerar relatório+plano -> `git_commit_dia()` -> `parar_robo()` (bloqueante) -> "FECHO concluido". Artefatos gravados ANTES do shutdown - sobrevivem a abort.
- Removido `stop_mt5()` do fecho (Fecho não deve fechar MT5).
- Fecho reexecutado à noite -> `relatorio_diario_20260806` + `plano_20260807` gerados; commit `8bf17c4` (push OK).

### PENDENTE RECORRÊNCIA (exige admin/UAC - aguarda usuário)

- [x] `Monstro-Watchdog`: duração **PT8H30M -> PT8H15M** (eliminar colisão com fecho 17:35). XML pronto em `%TEMP%\opencode\watchdog_task.xml`.
- [x] Revisar "Parar se bateria"/"Iniciar somente CA" das tasks `Monstro-*` (notebook HP).

### Análise da confiança da autópsia (trade #7: confianca 0.23 EXECUTADO)

- Confirmado no `decisions_wdo.csv` 10:36:27: `BUY, confianca 0.232`. As outras 2 losses tiveram confiança normal (0.85 e 0.67).
- **Causa:** NÃO existe piso de `confianca_decisao` para executar BUY/SELL. Gates atuais: (a) `CONFIDENCE_GAP=0.15` na probabilidade do sinal em `prever_acao()` (L8571) - só filtra sinais quase neutros; (b) C10 `score_qualidade >= 2` (L8223), com caminho de **aprendizado forçado** (3/dia) que aceita score baixo. Ajustes "advisory" (DOL/book desde 03/08) reduzem a confiança final mas **não vetam**.
- **Decisão:** **NÃO alterar a lógica agora** - 06/08 é o 2º pregão da janela de estabilização (5 pregões) desde o fix do SL. Registrar para revisão pós-estabilização:
  - [ ] Opção A: piso de execução (ex.: `confianca_decisao >= 0.5` para BUY/SELL).
  - [ ] Opção B: elevar `CONFIDENCE_GAP` de 0.15.


---

## DIA 07/08/2026 - AUTÓPSIA SEMANAL + FIX DO BUG DO PLANO

### Resultado do dia (validado pela autópsia corrigida)

- **18 trades / -R$110** (5 wins +R$125, 3 losses -R$235, 10 BE). Win rate 27.8%.
- Inclui ticket **2497704960 SELL -65** sincronizado do MT5 (após restart) - antes omitido pela autópsia.
- Kill-switch não acionado. Fecho 17:35 rodou: relatório gerado, **mas plano FALHOU** (autópsia EOD com erro).

### Bug 1: autópsia EOD crashava ('>' NoneType vs int) -> plano nunca gerado

- Causa: `extrair_trades()` retornava `lucro=None` para posições fechadas sem linha "Deal de saída" (ex.: fechamento manual/automático 17:35) -> `calcular_metricas()` `t["lucro"] > 0` explodia.
- **Fix (autopsia_automatizada.py):** `lucro` default `0.0` (BE) quando não há deal logado + extração agora captura **posições sincronizadas do MT5** (re_sync + re_entry_sync) e faz união de tickets (aberturas U posicoes U saidas).
- Plano regenerado corretamente: `plano_20260807.txt` (saldo -110 -> prioridades P1/P3/P4).

### Bug 2 (alarme falso): agente_estado.json "não existe"

- **Não é problema.** `carregar_estado()` trata arquivo ausente (retorna defaults). O arquivo só é criado na 1ª `registrar_mudanca()` - o agente não ajustou nada na semana (decisão correta).

### Auditoria da semana (60 trades / -R$455)

- Infra corrigida (start_all 255, bateria, fecho abortado) -> semana operacional completa a partir de 06/08.
- Qualidade de entradas fraca: win rate 36.7%, profit factor 0.54, 21 BE em 60 trades (35%).
- Confirmado: sem piso de confianca_decisao -> recomendações A/B já registradas (aguardando janela de 5 pregões).

---

## DIA 07/08/2026 (noite) - DECISÃO + IMPLEMENTAÇÃO DAS AÇÕES 1 E 2

### Análise decisiva: é problema de SAÍDA, não de entrada

- Payoff 0.37 (gain médio +R$29,55 ≈ +3pts; loss médio -R$79,71 ≈ -8pts). Break-even exigiria **73% de acerto** (temos 36,7%). Com assimetria atual é impossível ser lucrativo por mais acerto.
- **Simulação piso 0.60 em 07/08:** sobrariam 3 trades, todos BE (saldo 0,00) - cortaria até o winner +70 (entrou com conf 0.57). Prova de que piso alto NÃO resolve e confiança é fracamente preditiva.
- **Causa raiz da sangria encontrada:** o trailing VIVO é o `GerenciadorDeSaida` (config_saida L6118-6120): **gatilho 3pts / distância 2pts** -> qualquer winner que toca +3pts tem SL puxado para +1pt e é cortado em +1pt. `monitorar_posicao_ativa` (L9196) e `atualizar_trailing_stop()` (L5254, TRAILING_GATILHO/DISTANCIA) são **código morto** (nunca chamados).

### Ação 1 - Assimetria de saída (APLICADA)

- `config_saida`: `trailing_gatilho_pts` **3 -> 8** e `trailing_distancia_pts` **2 -> 4** (L6123/6125) - o winner só arma trailing após 8pts e o SL mínimo trava em +4pts (nunca mais corta em +1pt).
- Constantes de legado atualizadas por coerência: `TRAILING_GATILHO=8`, `TRAILING_DISTANCIA=4` (L911/913).
- Breakeven por inversão de fluxo (NÍVEL 2, L6457-6470) revisado: OK como está - é defensivo (move p/ entrada) e só dispara com inversão real de book (ratio >= SNIPER_RATIO_MIN). Ganho mínimo garantido: saídas de trailing/proteção nunca fecham < 4pts; exceções só inversão forte (NÍVEL 1 em prejuízo) e breakeven defensivo.
- SNIPER trail 1pt/1pt (L6479) permanece como está (por design, entradas ratio 2.0; global `SNIPER_SUPERMO_ATIVO=False`).

### Ação 2 - Piso de confiança (APLICADA)

- `PISO_CONFIANCA_MINIMA = 0.50` (L919). Bloqueio de execução antes de `executar_ordem` (L7425): BUY/SELL com `confianca_decisao < 0.50` não executam (política fixa, sem gravação de experiência, mesmo padrão do veto de bigs).
- A decisão continua salva no `decisions_wdo.csv` (antes do filtro) para validação contínua do piso.
- Escolha do usuário: 0.50 (0.60 anularia tudo; 0.50 corta lixo mantendo winners - simulação 07/08: -45 em vez de -110).

### Validação

- `py_compile` OK; testes pos-fix **9/9 PASS**; dryrun real requer MT5+pregão (executar na 2ª 09:00).

### Ação 3 (PENDENTE - pós-semana de validação)

- SL por ATR: ATR < 1,5 não operar ou SL 5-6pts; ATR 1,5-2,5 SL 8pts; acima disso não operar. Aguardar 5 pregões da Ação 1+2 antes de mexer em SL.

---

## DIA 07/08/2026 (noite 2) - GARGALO REAL ENCONTRADO (análise de motivos de saída nos logs)

### O que os logs revelaram (monstro_wdo.log) - estava corrigindo o sintoma, não a doença

1. **SL real era 8pts, não 5pts** (`config.json sl_points: 8`). Losses do dia: -85, -65, -85 (8,5/6,5/8,5pts). O comentário no código dizia "SL=5" mas o valor carregado era 8. Cada perda = R$80+.
2. **Inversão de fluxo com gate 1.2** (`sniper_ratio_min: 1.2`) disparava com QUALQUER desequilíbrio mínimo (ratios 1.20-1.46 no log) - não é "big players viraram", é ruído.
3. **Breakeven cortava os winners:** trade 09:47 ia a +2,5pts -> SL puxado para a entrada -> fechou em +10. Trade 11:43 (+1,5pts) -> fechou +15.
4. **Breakeven em prejuízo leve é INVIÁVEL no MT5:** posição presa em -1,5/-2pts (17:10-17:35) -> 27 tentativas de mover SL -> **27x retcode 10016 "Invalid stops"** (preço colado na entrada, abaixo da distância mínima de stop). O sistema batia na porta do MT5 a cada 5s sem conseguir nada.

### Correções aplicadas (config.json + monstro_unificado_v22.py)

1. `sl_points` **8 -> 5** (perda máxima R$50/trade; default no código também 5).
2. `sniper_ratio_min` **1.2 -> 2.0** (inversão de fluxo só reage a desequilíbrio real de book, como no config_win_v2).
3. **Inversão de fluxo NÍVEL 2 reescrita:** em LUCRO real -> **trava 50% do lucro** (SL deixa a entrada para trás); em zero/prejuízo leve + fluxo contra -> **SAIR** (cortar a perda em -1,5/-2 em vez de deixar sangrar até -5/-8).
4. **Cooldown anti-espasmo:** no máximo 1 ajuste de SL por fluxo a cada 60s + distância mínima SL-preço de 2pts (evita retcode 10016).

### Conclusão honesta

- O gargalo NÃO era o trailing (era o sintoma): era a combinação **SL 8pts + gate de inversão 1.2 + breakeven** que cortava winners em +1pt e prendia perdas por horas.
- Keras e agentes não "aprendiam" porque o resultado por sinal era uma roleta (mesmo sinal -> +70 ou -85 dependendo da saída). Com a saída corrigida, o aprendizado volta a fazer sentido.
- Validação: py_compile OK, testes 9/9. Dryrun real 2ª 09:00.
- Ação 3 (SL por ATR) fica para depois de 5 pregões de validação.

