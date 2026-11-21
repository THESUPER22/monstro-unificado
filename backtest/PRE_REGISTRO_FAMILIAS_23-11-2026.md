# PRÉ-REGISTRO — 3 FAMÍLIAS DE BAIXA FREQUÊNCIA (escrito em 21/11/2026)

**Registro aberto antes de qualquer backtest destas famílias.** Depois deste
arquivo ser fechado, **não é permitido** ajustar parâmetros, trocar filtros,
mudar janela, trocar stop/alvo ou reescrever a hipótese para acomodar o OOS.
O que der no OOS é o veredito — inclusive "não operar".

Nenhuma linha aqui autoriza mexer no robô. Somente `backtest/` e documentação.

---

## 1. Por que esta fase existe

Sniper e ORB foram reprovados sob atrito (23.62.2/23.62.3): 112 trades ao
vivo com −0,06 pt bruto e −1,18 pt líquido; no ORB, o PF histórico vinha do
fill idealizado no nível da caixa. O `order_send` mediu ~120 ms (cauda até 4 s)
e o custo de ida e volta é ~1,2–2 pts. Portanto só faz sentido testar teses em
que o **movimento esperado por trade seja muito maior que o custo**: poucos
trades, stop largo, alvo grande.

## 2. Protocolo comum (congelado)

- **Dados:** `backtest/dados_mt5/baixa_tudo/filtrados/WDO_FULL_M5_2021_2026.csv`,
  barras M5 das 09:00 às 15:25 BRT. Sem after, leilão, 17:30 ou 17:55.
- **ATR:** Wilder(14) em M5, semente no primeiro TR (função `atr_diario` de
  `triagem_m5_sltp.py`). Sem converter para M1 nesta fase.
- **Entrada:** na **abertura da barra M5 seguinte** ao sinal, com 0,5 pt
  contra a direção (BUY = `open + 0,5`; SELL = `open − 0,5`).
- **Custo:** 0,12 pt por operação (R$ 1,20 / R$ 10,00 por ponto).
- **Slippage adicional:** 0 / 0,5 / 1,0 pt **por lado**; deduzir `2 × slip`.
- **Resultado líquido:** `bruto − 0,12 − 2 × slip`, em pontos, 1 contrato.
- **SL e TP na mesma barra M5:** usar **pessimista (SL primeiro)** como
  resultado oficial; guardar o otimista apenas como limite informativo.
- **Gap:** se a barra abrir além do nível de stop, fill no open (pior preço).
- **Sem SL/TP até 15:25:** fechar no último close disponível.
- **Períodos:** IS = 2021-01-01 a 2024-12-31; OOS = 2025-01-01 a 2026-12-31.
  2021 é informativo dentro do IS; o corte é por ano da barra.
- **Sem ajustes, sem "poda boa", sem segunda rodada.** Cada família tem
  exatamente 2 conjuntos de parâmetros, definidos abaixo.

## 3. Hipóteses e regras pré-registradas

### (a) Rompimento de volatilidade — alvo ≥ 15 pts, máx. 2 trades/dia

**Hipótese (econômica):** a expansão de volatilidade logo após a abertura tende
a continuar; exigir que o rompimento tenha folga de ATR filtra pavios de ruído.
Com alvo de 15 pts e no máximo 2 entradas por dia, o custo de ~1,2–2 pts vira
fração pequena do movimento e a estratégia deixa de ser escalping.

**Regra:** caixa = barras 09:00–09:30 (6 barras M5); `hi`/`lo` da caixa. A partir
das 09:35, primeira barra com `high ≥ hi + k×ATR` (BUY) ou `low ≤ lo − k×ATR`
(SELL). Se os dois lados romperem na mesma barra, o dia é ambíguo → sem trade.
Entrada na abertura seguinte + 0,5 contra. Stop = `m×ATR`. **Alvo fixo 15 pts.**
Saída por tempo 15:25. Máx. 2 trades/dia, com intervalo mínimo de 12 barras
(60 min) entre entradas; após stop, não reentrar no mesmo lado no mesmo dia.

| parâmetro | k (folga do gatilho) | m (stop em ATR) | alvo | máx/dia |
|---|---:|---:|---:|---:|
| V1 | 0,5 | 2,0 | 15 pts | 2 |
| V2 | 1,0 | 3,0 | 15 pts | 2 |

### (b) Reversão nos extremos do range do dia — stop largo

**Hipótese (econômica):** os extremos da manhã concentram exaustão de liquidez;
o preço tende a voltar ao centro do range. Stop largo evita ser caçado no
pavio e alvo proporcional ao range captura a reversão sem depender de ticks.

**Regra:** range inicial = barras 09:00–09:40 (8 barras M5); `hi`/`lo`/`rng`.
A partir das 09:45, detectar toque no topo (`high ≥ hi`) ou na base
(`low ≤ lo`), atualizando `hi`/`lo` se o preço fizer novo extremo (range móvel
da manhã). Gatilho: a barra M5 seguinte **fecha de volta para dentro** do range
em pelo menos `f×rng` (topo: `close ≤ hi − f×rng`; base: `close ≥ lo + f×rng`).
Entrada na abertura seguinte **contra o extremo** (topo → SELL, base → BUY)
+ 0,5 contra. Stop = `s×rng` além do extremo. Alvo = `t×rng`, com piso de
15 pts. Saída 15:25. **Máx. 1 trade/dia** (trava após a primeira entrada).

| parâmetro | f (retorno ao range) | s (stop em range) | t (alvo em range) | máx/dia |
|---|---:|---:|---:|---:|
| R1 | 0,25 | 1,0 | 0,5 | 1 |
| R2 | 0,50 | 1,5 | 1,0 | 1 |

### (c) Continuação após a abertura (primeira hora)

**Hipótese (econômica):** o viés direcional formado na primeira hora sobrevive
ao resto da sessão porque reflete o reposicionamento doméstico antes do
catalisador externo. Esperar o fechamento da primeira hora filtra ruído; stop
largo e alvo grande deixam o custo irrelevante; 1 trade/dia evita mineração.

**Regra:** primeira hora = barras 09:00–10:00 (12 barras M5). `open0` =
abertura da primeira barra; `close10` = close da última barra da primeira hora;
`ATR` da barra das 10:00. Se `close10 − open0 ≥ k×ATR` → BUY; se
`open0 − close10 ≥ k×ATR` → SELL; senão sem trade. Entrada na abertura da barra
seguinte (10:05) + 0,5 contra. Stop = `m×ATR`. Alvo fixo `tp` pts. Saída 15:25.
**1 trade/dia.**

| parâmetro | k (força do viés) | m (stop em ATR) | alvo | máx/dia |
|---|---:|---:|---:|---:|
| C1 | 0,5 | 2,0 | 20 pts | 1 |
| C2 | 1,0 | 3,0 | 30 pts | 1 |

## 4. Correção para múltiplas comparações (congelada antes de rodar)

- Variantes desta fase: 3 famílias × 2 parâmetros = **6**.
- Variantes já testadas **nos mesmos dados** nesta investigação: Sniper
  A0/B/C/D (4) + ORB A0/B/C/D/ORB-1030 (5) = **9**.
- **Total de comparações consideradas = 15.** Usar o total acumulado (mais
  conservador), não apenas 6.
- Nível por variante: **α_adj = 0,05 / 15 = 0,00333** (Bonferroni).
- Estatística: `t = média_OOS / (desvio_padrão_OOS / √n_OOS)`, unilateral.
  Rejeitar "sem edge" somente se `t > t_{1−0,00333, n_OOS−1}`.
- Reportar `t` e `t_crit` junto com o resultado; não esconder o limiar.

## 5. Aceite (todas as condições ao mesmo tempo)

Uma variante **passa** somente se, com **slippage 1,0 pt/lado** e cenário
pessimista no OOS:

1. `expectativa_OOS > 0`;
2. `n_OOS ≥ 40`;
3. `PF_OOS > 1`;
4. `t_OOS > t_crit` (Bonferroni, α_adj = 0,00333).

Não existe "quase passa". Não existe ajuste depois de ver o OOS. Se nenhuma
passar, a conclusão do projeto é **não operar** — resultado válido e final.

## 6. Entrega prevista

Uma tabela por família (V, R, C) com IS e OOS, expectativa a 0/0,5/1,0, n, PF,
t, t_crit e `passa / não passa`; mais uma tabela-resumo das 6 variantes e a
conclusão. O script será `backtest/familias_baixa_frequencia.py`, escrito
**depois** deste arquivo e sem alterar nenhuma regra aqui.

---

**Fim do pré-registro.** Fechado em 21/11/2026. SHA-256 registrado no ROADMAP
(23.63.1) antes da primeira execução.
