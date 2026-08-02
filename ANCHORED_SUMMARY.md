## Objective
- Operar robô Monstro no WDO com ML + Williams %R + PTAX + SniperSupermo, acumular 500+ trades reais para calibragem

## Important Details
- **Data**: 28/07/2026 17:15 (fim da sessão). Robô NÃO reiniciado — modificações pendentes de restart
- **Contrato**: WDOQ26 (venc. 31/07), TICK_SIZE=0.5, SL=5pts, TP=0. Só 1cc (B3 não tem 0.5cc)
- **22 features Keras** (18 originais + 4 PTAX/payroll)
- **Model V3 (22 feats)**: 91.58% train / 89.59% val (33 epochs, EarlyStopping). Pesos `.h5` (239KB) e `.keras` (104KB) (22:04)
- **Resultado 28/07**: -190pts (25 trades: +160 Wins / -350 Losses / 5 BE). Mercado lateral 5122-5127 (5pts)
- **PTAX**: 4 janelas de consulta do BC (10:00, 11:00, 12:00, 13:00). Dealers pressionam preço. Coletada via site do BCB
- **Payroll**: primeira sexta do mês 09:30 BRT. Robô foge 09:25-09:35. Próximo: 07/08
- **SniperSupermo BLOQUEADO** em dia PTAX (31/07) e payroll
- **Dólar casado** (WDO − PTAX) ≈ +6.8pts em 28/07. Novo feature + dashboard
- **Divergência Williams %R corrigida**: thresholds % → ticks (1pt preço, 5pts WR), janela 20→200 ticks
- **N_FEATURES**: 18 → 22 (adicionados `dolar_casado`, `em_janela_ptax`, `minutos_para_ptax`, `dia_ptax`)
- **Meta**: 500 trades para refinar modelo com book, PTAX, DOL, divergências

## Work State
### Completed
- **PTAX implementado**: coleta HTTP do BCB + parser HTML + cache diário. Globals `ptax_valor`, `dolar_casado`, `sniper_bloqueado`, `payroll_ativado`
- **PTAX flags no contexto**: `ptax`, `em_janela_ptax`, `minutos_para_ptax`, `dia_ptax`, `payroll_ativado`, `sniper_bloqueado`
- **4 features Keras adicionadas**: `colunas_numericas` atualizada, N_FEATURES=22
- **Sniper bloqueado em dia PTAX + payroll**: `verificar_sniper_bloqueado()` → desvia sniper automaticamente
- **Payroll fuga**: `eh_horario_payroll()` → True se sex 09:25-09:35. Bloqueia sniper + flag no contexto
- **Dashboard atualizado**: `/status` retorna ptax, dolar_casado, sniper_bloqueado, payroll. Painel PTAX + dolar_casado + alert bar adicionados ao HTML
- **`ultimo_dia_util_mes()`**: detecta automaticamente (31/07 = sim)
- **Williams %R divergência corrigida**: thresholds ticks (1pt/5pts), janela 200, `max_hist`=1000, CSV deletado (recria limpo)
- **`williams_r_historico.csv` deletado**: 2009 linhas com divergência errada removidas

### Active
- **Modelo Keras salvo**: `.h5` (109KB) + `.keras` (101KB) + scaler. Precisa retreinar com 22 features
- **CSVs operacionais**: `decisions_wdo.csv` (9463), `historico_contexto_wdo.csv` (5002), `experiencias_wdo.json`
- **SniperSupermo NUNCA ativado**: condições de score ≥ 7/10 não ocorreram
- **Log da sessão 28/07**: 25 trades executados (09:21-12:26)

### Blocked
- **SniperSupermo + PTAX + features precisam de restart**: modificações só entram em vigor quando robô reiniciado
- **Modelo retreinado com 22 features**: ✅ V3 (91.58% train / 89.59% val, 33 epochs)
- **25 trades insuficientes**: meta 500+ para calibragem real. SniperSupermo não depende do modelo

## Next Move
1. **Modelo Keras V3 retreinado com 22 features** ✅ (91.58% train / 89.59% val)
2. **Restart robô amanhã 29/07 09:00 — SniperSupermo + PTAX + 22 features ativos**
3. **Monitorar PTAX day na sexta (31/07) — sniper desligado automático**
4. **Próximo payroll (07/08) — fuga automática 09:25-09:35**

## Relevant Files
- `C:\AIOFEN\monstro_unificado_v22.py` — robô (~9979 linhas) com PTAX, payroll, sniper bloqueio, 22 features
- `C:\AIOFEN\config.json` — SL=5, TP=0, volume=1.0, trailing gatilho=3pts/dist=2pts
- `C:\AIOFEN\modelo_monstro_wdo.h5` + `.keras`: pesos V3 (239KB, 22 features, 89.59% val)
- `C:\AIOFEN\modelo_monstro_wdo_scaler.json` — scaler (22 features) atualizado 22:04
- `C:\AIOFEN\experiencias_wdo.json` — 9851 bytes de experiências
- `C:\AIOFEN\decisions_wdo.csv` — 9463 decisões
- `C:\AIOFEN\historico_contexto_wdo.csv` — 5002 linhas
- `C:\AIOFEN\templates\dashboard.html` — dashboard com painel PTAX + alert bar + dolar_casado adicionados
- `C:\AIOFEN\dashboard_routes.py` — `/api/status` com campos ptax, dolar_casado, sniper_bloqueado, payroll
- `C:\AIOFEN\iniciar_v22_wdo.bat` — launcher (start MT5 + python)
