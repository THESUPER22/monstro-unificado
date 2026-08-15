# Autopsia Diaria de Trades - Monstro WDO

Instrucao padrao para execucao ao termino de cada pregao: autopsia tecnica e
financeira completa do robo Monstro WDO (`monstro_unificado_v22.py`).

> Versao 15/08/2026 - substitui o antigo `PROMPT DIARIO .txt`.
> Script correto de inicializacao: **`monstro_unificado_v22.py`** (o
> `monstro_unificado.py` e versao antiga, nao usar).

---

## Arquivos de Entrada para Analise

1. `monstro_wdo.log` - registro bruto de execucao do robo e ordens do MT5.
   *Atencao (rotacao de logs, fix 14/08): para autopsia de um dia anterior,
   o log pode estar em `monstro_wdo_YYYYMMDD.log` (o log de hoje e sempre
   `monstro_wdo.log`).*
2. `decisions_wdo.csv` - decisoes de compra/venda, confianca e contexto direto.
3. `historico_contexto_wdo.csv` - metricas de fluxo, dolar cheio e book de ofertas.
   *O P&L por trade (reward) fica aqui; confira a soma com o relatorio diario.*
4. `historico_multitf.csv` - confluencias de M5, M15 e M30 (WR).
5. `williams_r_historico.csv` - niveis de sobrecompra e sobrevenda.
6. `sniper_supermo_historico.csv` - registros e gatilhos do modulo Sniper.
7. `agente_autonomo.log` - registro do Agente Autonomo, Kill-Switch e Watchdog.
8. `experiencias_wdo.json` - memoria e aprendizado acumulado do agente.
9. `config.json` e `agente_config.json` - parametros, travas e regras ativas.

---

## Roteiro de Execucao da Analise

### 1. Mapeamento Geral da Sessao (Tabela de Trades 1 a N)

Extraia do `monstro_wdo.log` TODAS as ordens executadas no dia, da abertura ao
fechamento do mercado, sem omitir nenhuma operacao. Monte a tabela:

| # | Ticket | Hora Abertura | Tipo (BUY/SELL) | Preco Entrada | SL | Hora Fechamento | Resultado (GAIN/LOSS/BE) | P&L (pts) |

Confira a soma dos rewards no `historico_contexto_wdo.csv` e nos relatorios
diarios (`relatorio_diario_YYYYMMDD.txt`). Resumo final do dia: total de Wins,
Losses, Breakevens e saldo liquido em pontos e R$.

### 2. Cruzamento Temporal Trade a Trade (Raio-X da Entrada)

Para cada trade da tabela, localize o timestamp nos `.csv` e monte o raio-X:
- **Confianca do Modelo** (`decisions_wdo.csv`): decisao da IA, confianca, ATR, RSI, entropia.
- **Fluxo e Book** (`historico_contexto_wdo.csv`): lado do DOL, confianca do dolar cheio, Book Ratio (Bid/Ask).
- **Multi-Timeframe** (`historico_multitf.csv`): trade a favor ou contra a tendencia primaria de M5/M15/M30?
- **Gatekeeper** (`williams_r_historico.csv`): o %R indicava exaustao, tendencia ou divergencia? Atuou ou falhou?

### 3. Diagnostico e Padroes

- **GAINS**: o que garantiu o sucesso? (confluencia WDO/DOL, alinhamento Multi-TF, momentum).
- **LOSSES**: causa raiz? (contra Multi-TF, violacao de fluxo DOL, consolidacao, ruido de fim de dia, falha de gatekeeper).

### 4. Auditoria do Sniper / Supermo

- Maiores Scores do dia em `sniper_supermo_historico.csv`.
- Eficacia do **Cooldown de 120s** (`sniper_cooldown_s` no `config.json`): reduziu o spam de sinais?
- Se nao disparou: quais filtros barraram (veto Multi-TF, tendencia, modo defesa, ja em posicao)?
- Se disparou: assertividade e precisao da operacao.

### 5. Auditoria do Agente Autonomo e Watchdog

- Verificar `agente_autonomo.log`.
- Kill-Switch acionado? O Watchdog identificou o estado corretamente:
  - processo vivo + porta morta = "robo travado" -> reiniciou (ou encerrou orfao se kill-switch ja ativado no dia);
  - NUNCA deve reiniciar se o limite diario de risco ja foi atingido.
- Confirmar subida da porta 5001 (servidor Flask) e ausencia de falsos positivos de PID.

### 6. Conclusao e Acoes Recomendadas

Resumo das principais falhas no codigo/estrategia e ajustes praticos em logica
ou parametros para o proximo pregao.

---

## Checklist de Inicializacao Diaria (segunda-feira)

1. Abrir o MetaTrader 5 com AlgoTrading/Autotrading ativo (icone verde).
2. Terminal / Prompt de Comando:
   ```
   cd C:\AIOFEN
   venv310\Scripts\activate
   python monstro_unificado_v22.py
   ```
   *(Ou iniciar o Agente Autonomo, que ja aponta para o v22 via `agente_config.json`.)*
3. Validar subida: servidor escutando na porta 5001, log inicial acusando
   Veto Multi-TF ativo, cooldown=120s e SL 8pts.
