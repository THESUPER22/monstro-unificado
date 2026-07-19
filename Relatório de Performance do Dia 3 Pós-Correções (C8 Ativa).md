# Relatório de Performance do Dia 3 Pós-Correções (C8 Ativa)

## Análise Quantitativa
```
✅ Arquivo historico_contexto_win.csv carregado com sucesso.
✅ Arquivo experiencias.json carregado e normalizado com sucesso.

--- Análise do Histórico de Operações (Dia 3 Pós-Correção - C8 Ativa) ---

1. Estatísticas de Lucro/Prejuízo (Reward):
count    1816.000000
mean       -0.572687
std        10.132848
min       -50.000000
25%         0.000000
50%         0.000000
75%         0.000000
max        50.000000
Name: reward, dtype: float64

2. Distribuição das Ações (Total):
action
NAO_AGIU    86.942149
BUY         10.743802
SELL         2.314050
Name: proportion, dtype: float64

3. Lucro Médio por Ação:
action
BUY        -3.461538
NAO_AGIU    0.000000
SELL       -8.690476
Name: reward, dtype: float64

4. Taxa de Acerto (Trades Reais): 29.54% (Acertos: 70, Erros: 167)
📈 Gráfico 'lucro_acumulado_dia3.png' salvo.

6. Correlação de Features com Reward (Trades Reais):
reward           1.000000
rsi_14           0.064440
volatility       0.002788
volume_tick      0.001145
bid_qty               NaN
ask_qty               NaN
spread                NaN
entropia_book         NaN
Name: reward, dtype: float64

--- Análise da Memória de Experiências (Dia 3 Pós-Correção - C8 Ativa) ---

1. Estatísticas de Lucro (Reward) na Memória:
count    1000.000000
mean       -0.510000
std         6.540847
min       -35.000000
25%         0.000000
50%         0.000000
75%         0.000000
max        40.000000
Name: lucro, dtype: float64

2. Distribuição das Ações na Memória:
acao
NAO_AGIU    94.1
BUY          5.1
SELL         0.8
Name: proportion, dtype: float64

3. Proporção de Experiências na Memória:
   Positivas (lucro > 0): 1.40%
   Negativas (lucro <= 0): 98.60%

4. Lucro Médio por Ação na Memória:
acao
BUY         -7.745098
NAO_AGIU     0.000000
SELL       -14.375000
Name: lucro, dtype: float64

--- Análise do Log (Verificação do Aprendizado) ---
1. Frequência de Treinamento (C3): 0 treinos iniciados.
2. Qualidade do Treinamento: 0 melhorias detectadas, 0 sem melhoria.
3. Erros Críticos: 0 erros registrados. (NameError: 688)
4. Operações Bloqueadas (Filtros): 0 bloqueios registrados.
5. Operações Aprovadas: 0 setups aprovados.
```

## Gráfico de Lucro Acumulado
![Lucro Acumulado Dia 3](https://private-us-east-1.manuscdn.com/sessionFile/xvWSE1NrhUhqYOjM7wSPo9/sandbox/YYJmWY8XzNeSAe16TmkhDy-images_1761608825889_na1fn_L2hvbWUvdWJ1bnR1L2x1Y3JvX2FjdW11bGFkb19kaWEz.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUveHZXU0UxTnJoVWhxWU9qTTd3U1BvOS9zYW5kYm94L1lZSm1XWThYek5lU0FlMTZUbWtoRHktaW1hZ2VzXzE3NjE2MDg4MjU4ODlfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyeDFZM0p2WDJGamRXMTFiR0ZrYjE5a2FXRXoucG5nIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzk4NzYxNjAwfX19XX0_&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=eAUQ2ejmkumTWZqnUGTdFi7ErBTFi0i49jzSILxbWcvyaA0isuVM9s14L5CfpSIzUxGgOIvkT9jfW3mhMpewPwAjadMMBxy-jekx-TsXrwY8zpTNlUTI2-xp0M6NYdutDmE1yiJBM02rfNLNCxRZLTQMIdYckEXYNIoauimYu2kAUqc77z8xn65aFAKhBFIFW7591qYNjGIX2Ae5l5meAQdnVdB8FPTfCznBC7BIRel1N7zX7wW7rBoW~Y2~UGMggR85SnAGSPavLJc8rJqcQjr6dDAHIA2HecUruEgv3AMlJkgcAKVzJynxamQJPZ-5afbxi8VNVSTt4d7bd4oBcw__)

## Diagnóstico e Próximos Passos
A ser preenchido após a análise da saída.
