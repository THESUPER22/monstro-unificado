import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

mt5.initialize()
for tf, nome in [(mt5.TIMEFRAME_M5, "M5"), (mt5.TIMEFRAME_M15, "M15")]:
    r = mt5.copy_rates_range("WDOV26", tf, datetime(2018, 1, 1), datetime.now())
    if r is not None and len(r):
        df = pd.DataFrame(r)
        ini = pd.to_datetime(df["time"].min(), unit="s").date()
        print(f"{nome}: {len(r)} barras | inicio: {ini}")
    else:
        print(f"{nome}: vazio")
mt5.shutdown()
