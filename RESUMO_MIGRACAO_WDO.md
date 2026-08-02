# 🚀 RESUMO DA MIGRAÇÃO WIN → WDO

**Data:** 22/07/2026
**Usuário:** Metre Super
**Idioma:** PORTUGUÊS (SEMPRE)

---

## 📋 O QUE FOI FEITO ATÉ AGORA

### ✅ 1. Análise do Estado Atual
- Li e analisei os 3 arquivos principais:
  - `monstro_unificado_v2.py` (robô principal - 8857 linhas)
  - `monstro_unificado_v22.py` (cópia para modificar)
  - `ideia para o robo.txt` (ideias de melhoria)
- Li o roadmap oficial (`ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md`)
- Verifiquei que o robô atualmente opera WIN (Mini Índice)

### ✅ 2. Migração do Símbolo
- **Mudei** a função `get_front_month_symbol_dynamic` de `prefix="WIN"` para `prefix="WDO"`
- **Arquivo modificado:** `monstro_unificado_v22.py` linha 225

### ✅ 3. Atualização dos Parâmetros Básicos WDO

| Parâmetro | WIN (ANTES) | WDO (AGORA) | Linha |
|-----------|-------------|-------------|-------|
| Símbolo | WINQ26 | WDOM26 | 225 |
| tick_size | 0.2 | 0.5 | 544 |
| ticks_por_ponto | 10000 | 1000 | 546 |
| Volume | 5 contratos | 1 contrato | 548 |
| SL | 100 pontos | 5 pontos | 575 |
| TP | 250 pontos | 10 pontos | 577 |
| MaxLoss | -R$1000 | -R$500 | 618 |
| MaxDrawdown | -R$500 | -R$250 | 620 |
| MaxSpread | 10 pts | 5 pts | 622 |
| MinVolumeBook | 1500cc | 200cc | 627 |

### ✅ 4. Atualização dos Cálculos de Preço
- **Todas** as referências hardcoded a `0.2` (WIN) foram mudadas para `TICK_SIZE` (WDO)
- **Cálculos de lucro** agora usam TICK_SIZE global
- **Trailing stop** ajustado para WDO

### ✅ 5. Atualização dos Arquivos de Dados
- `historico_contexto_win.csv` → `historico_contexto_wdo.csv`
- `modelo_monstro_win.h5` → `modelo_monstro_wdo.h5`
- `config_win_v2.json` → `config.json` (já configurado para WDO)

### ✅ 6. Atualização das Mensagens de Log
- Todas as mensagens agora falam "WDO" em vez de "WIN"
- Comentários atualizados para refletir WDO

### ✅ 7. Atualização do Trailing Stop
- **Gatilho:** 80 pontos → 5 pontos
- **Distância:** 40 pontos → 2 pontos
- **Configuração:** `trailing_gatilho_pts: 5`, `trailing_distancia_pts: 2`

---

## 🔧 PRÓXIMAS MUDANÇAS NECESSÁRIAS

### FASE 2 - Saída Dinâmica (SEM TP FIXO)
- **Objetivo:** Keras decide quando sair do trade
- **SL** apenas como rede de segurança
- **Proteção:** entrada + R$5 para cobrir custos
- **Book:** usar escoras/iceberg para mover trailing

### FASE 3 - Melhorias Keras
- Treinar com wins E losses (não só wins)
- Validação walk-forward
- Features 16-18 para decisão de saída

---

## 📍 LOCALIZAÇÃO DO PROJETO

**Pasta:** `C:\AIOFEN`
**Arquivo principal:** `monstro_unificado_v22.py`
**Config:** `config.json` (já configurado para WDO)

---

## ⚠️ IMPORTANTE

- **SEMPRE** falar em português
- **NUNCA** usar inglês nas respostas
- **NOME DO USUÁRIO:** Metre Super (sempre usar)
- **IDIOMA:** Português do Brasil

---

**Status:** Migração Fase 1 CONCLUÍDA - Parâmetros WDO atualizados