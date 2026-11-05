# FASE 0 — AUDITORIA DE DIVERGÊNCIA CONFIG.JSON vs HARDCODED
# Data: 04/11/2026
# Projeto: Monstro v22 (WDO) — C:\AIOFEN

## 1. Divergência de Fonte de Verdade

### 1.1 sniper_ratio_min
| Fonte | Valor |
|-------|-------|
| config.json (top-level) | 1.5 |
| config.json (risk_management) | 1.5 |
| Código hardcoded default (L1038) | 1.5 |
| PARAM_SCHEMA (config_manager.py) | 1.2 (default) |
| **Veredito** | ✅ Alinhado (config = código). ⚠️ PARAM_SCHEMA default (1.2) diverge do código (1.5) |

### 1.2 book_ratio_min
| Fonte | Valor |
|-------|-------|
| config.json (top-level) | 1.3 |
| config.json (risk_management) | AUSENTE |
| Código hardcoded default (L7860) | 1.3 |
| PARAM_SCHEMA (config_manager.py) | 1.3 (default) |
| **Veredito** | ✅ Alinhado (config = código). ⚠️ Ausente em risk_management (gap de schema) |

### 1.3 dol_conf_min
| Fonte | Valor |
|-------|-------|
| config.json (top-level) | 0.4 |
| config.json (risk_management) | AUSENTE |
| Código hardcoded default (L7859) | 0.4 |
| PARAM_SCHEMA (config_manager.py) | 0.4 (default) |
| **Veredito** | ✅ Alinhado (config = código). ⚠️ Ausente em risk_management (gap de schema) |

### 1.4 sl_points
| Fonte | Valor |
|-------|-------|
| config.json (top-level) | 8 |
| config.json (risk_management) | 8 |
| Código hardcoded default (L1021) | 5 |
| PARAM_SCHEMA (config_manager.py) | 5 (default) |
| **Veredito** | ✅ Alinhado (config = código = 8). ⚠️ Default do código (5) diverge do config (8) — se config.json sumir, SL cai para 5 |

### 1.5 tp_points
| Fonte | Valor |
|-------|-------|
| config.json (top-level) | 0 |
| config.json (risk_management) | AUSENTE |
| Código hardcoded default (L1023) | 10 |
| PARAM_SCHEMA (config_manager.py) | 0 (default) |
| **Veredito** | ⚠️ DIVERGÊNCIA CRÍTICA: config=0 (sem TP, saída dinâmica), código default=10 (TP fixo 10pts). Se config.json sumir, TP muda de 0 para 10 pts |

### 1.6 trailing_stop
| Fonte | Valor |
|-------|-------|
| config.json (trailing_stop) | gatilho=8.0, distancia=4.0 |
| Código (monstro_unificado_v22.py L1060-1062) | TRAILING_ATIVO = config.get("trailing_stop", {}).get("ativo", True) |
| | TRAILING_INTERVALO = config.get("trailing_stop", {}).get("intervalo_segundos", 5) |
| **Veredito** | ✅ Código LÊ o bloco trailing_stop do config. Nota no config diz "O codigo NAO le este bloco" — INCORRETA, o código LÊ. |

### 1.7 Resumo da Divergência

| Parâmetro | config.json | Código default | PARAM_SCHEMA default | risk_management | Status |
|-----------|-------------|----------------|---------------------|-----------------|--------|
| sniper_ratio_min | 1.5 | 1.5 | 1.2 | 1.5 | ⚠️ PARAM_SCHEMA diverge |
| book_ratio_min | 1.3 | 1.3 | 1.3 | AUSENTE | ⚠️ Gap em risk_management |
| dol_conf_min | 0.4 | 0.4 | 0.4 | AUSENTE | ⚠️ Gap em risk_management |
| sl_points | 8 | 5 | 5 | 8 | ⚠️ Default diverge (5 vs 8) |
| tp_points | 0 | 10 | 0 | AUSENTE | 🔴 CRÍTICO: default 10 vs config 0 |
| trailing_gatilho | 8.0 | (lê do config) | 3.0 | N/A | ⚠️ PARAM_SCHEMA diverge |
| trailing_distancia | 4.0 | (lê do config) | 2.0 | N/A | ⚠️ PARAM_SCHEMA diverge |

### 1.8 Problemas Identificados

1. **tp_points default=10 vs config=0**: Se config.json for perdido/corrompido, o robô passa a ter TP fixo de 10pts em vez de saída dinâmica (Keras). Isso muda fundamentalmente o comportamento do robô. **Risco alto.**

2. **sl_points default=5 vs config=8**: Se config.json sumir, SL cai de 8 para 5 pontos. Menos proteção.

3. **sniper_ratio_min PARAM_SCHEMA default=1.2 vs código=1.5**: Se alguém ajustar via dashboard sem especificar, o valor muda de 1.5 para 1.2, relaxando o filtro de sniper.

4. **trailing_stop nota incorreta**: O config.json diz "O codigo NAO le este bloco" mas o código LÊ (L1060-1062). A nota é enganosa.

5. **risk_management sem book_ratio_min, dol_conf_min, tp_points**: Gaps no schema de risk_management. Se o dashboard ou outro código tentar ler desses campos, obterá None.

6. **PARAM_SCHEMA defaults desalinhados do código**: sniper_ratio_min (1.2 vs 1.5), tp_points (0 vs 10), trailing_gatilho (3.0 vs 8.0), trailing_distancia (2.0 vs 4.0). Se o dashboard for usado para "resetar" parâmetros, os valores voltam para os defaults do PARAM_SCHEMA, não do código.

## 2. População de experiencias_wdo.json

### Antes
- 1 experiência (do dia 04/11/2026, 16:50:54 SELL +45.0)

### Depois
- 6 experiências (5 novas extraídas do historico_contexto_wdo.csv)
- Trades reais: 6 (5 SELL, 1 BUY) — todos de 04/11/2026
- Resultado: 1 gain (+80.0), 5 losses (-80.0 × 4 + -80.0) = -320.0 pts líquidos
- Backup criado: experiencias_wdo.json.backup_pre_fase0

### Nota
O CSV (historico_contexto_wdo.csv) tem apenas 6 trades com reward não-zero (todos de 04/11/2026).
Trades anteriores a 04/11/2026 não estão no CSV (foram perdidos no reset de 28/09).
Os campos multi-timeframe (m5/m15/m30 RSI/ATR/WR), Williams %R, DOL, PTAX, etc.
foram preenchidos com valores neutros (defaults) por não estarem disponíveis no CSV.

## 3. Conclusão da Fase 0

### Itens completados
- [x] Item 1: experiencias_wdo.json populado com 6 experiências reais
- [x] Item 2: Auditoria de divergência concluída (7 parâmetros auditados)

### Problemas críticos identificados
1. **tp_points default divergente** (10 vs 0) — risco alto se config.json sumir
2. **PARAM_SCHEMA defaults desalinhados** — dashboard pode resetar para valores errados
3. **risk_management sem book_ratio_min, dol_conf_min, tp_points** — gaps de schema
4. **trailing_stop nota incorreta** no config.json

### Recomendação
- Corrigir os defaults do código (L1021, L1023, L1038) para alinhar com config.json
- Corrigir PARAM_SCHEMA defaults (config_manager.py) para alinhar com código
- Adicionar book_ratio_min, dol_conf_min, tp_points ao risk_management no config.json
- Corrigir a nota do trailing_stop no config.json
PYEOF

---

## 4. Fase 0.2 - Correcoes de Defaults Divergentes (04/11/2026)

### Correcoes aplicadas

#### monstro_unificado_v22.py
- SL_POINTS = config.get("sl_points", 5) -> config.get("sl_points", 8)
- TP_POINTS = config.get("tp_points", 10) -> config.get("tp_points", 0)

#### config_manager.py (PARAM_SCHEMA)
- sniper_ratio_min default: 1.2 -> 1.5
- trailing_gatilho default: 3 -> 8
- trailing_distancia default: 2 -> 4
- sl_points default: 5 -> 8

#### config.json
- risk_management: adicionados book_ratio_min=1.3, dol_conf_min=0.4, tp_points=0
- trailing_stop._nota: corrigida (codigo LE o bloco, nao ignora)

### Validacao
- py_compile OK (monstro + config_manager)
- pytest 21 passed
- JSON valido

### Impacto
- tp_points default=0: restaura saida dinamica via Keras (antes era TP fixo 10pts se config sumir)
- sl_points default=8: alinhado com config (antes era 5)
- sniper_ratio_min default=1.5: alinhado com config (antes era 1.2)
- trailing defaults alinhados com config (8.0/4.0)
- risk_management agora tem book_ratio_min, dol_conf_min, tp_points
