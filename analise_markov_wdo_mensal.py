import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from backtest_markov_4estados import (
    carregar_dados, calcular_indicadores, classificar_estados, rodar,
)

if not mt5.initialize():
    raise SystemExit("Falha ao inicializar MT5")

symbol = "WDO$"
if not mt5.symbol_select(symbol, True):
    symbol = "WDOV26"
    mt5.symbol_select(symbol, True)

df = carregar_dados(symbol)
mt5.shutdown()

df = calcular_indicadores(df)
df = classificar_estados(df, 1.0)
trades = rodar(df, 10.0, usar_consol=False, breakout_ratio=1.0, stop_emergencia=True)

trades["saida"] = pd.to_datetime(trades["saida"])
trades["mes"] = trades["saida"].dt.to_period("M")
trades["dia"] = trades["saida"].dt.date

print("=" * 62)
print("WDO MARKOV SO TENDENCIA (ratio=1.0) - EQUITY MES A MES")
print("=" * 62)

g = trades.groupby("mes")["brl"]
resumo = pd.DataFrame({
    "trades": g.count(),
    "wins": trades[trades["brl"] > 0].groupby("mes")["brl"].count(),
    "resultado": g.sum(),
})
resumo["wins"] = resumo["wins"].fillna(0).astype(int)
resumo["wr_%"] = (resumo["wins"] / resumo["trades"] * 100).round(1)
resumo["acum"] = resumo["resultado"].cumsum().round(2)

print(resumo.to_string())

meses_pos = (resumo["resultado"] > 0).sum()
meses_neg = (resumo["resultado"] <= 0).sum()
melhor = resumo["resultado"].max()
pior = resumo["resultado"].min()
total = resumo["resultado"].sum()

print("-" * 62)
print(f"Meses positivos : {meses_pos} | Meses negativos: {meses_neg}")
print(f"Melhor mes      : R$ {melhor:,.2f}")
print(f"Pior mes        : R$ {pior:,.2f}")
print(f"Total periodo   : R$ {total:,.2f}")

# concentracao: participacao dos 3 melhores meses e dos 3 melhores dias
top3_mes = resumo["resultado"].nlargest(3).sum()
dias = trades.groupby("dia")["brl"].sum()
top3_dias = dias.nlargest(3).sum()
lucro_bruto_pos = trades.loc[trades["brl"] > 0, "brl"].sum()

print(f"Top 3 meses     : R$ {top3_mes:,.2f} ({top3_mes/total*100:.0f}% do total)")
print(f"Top 3 dias      : R$ {top3_dias:,.2f} ({top3_dias/total*100:.0f}% do total)")
print(f"Dias operados   : {len(dias)} | Dias positivos: {(dias>0).sum()} ({(dias>0).mean()*100:.0f}%)")
