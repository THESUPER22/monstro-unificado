import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

PARAMS = {
    "contratos": 1,
    "ema_period": 21,
    "slope_lookback": 3,
    "slope_threshold": 0.0003,
    "atr_period": 14,
    "atr_ma_period": 14,
    "breakout_ratio": 1.0,
    "consol_ratio": 0.6,
    "band_pullback_atr": 0.3,
    "stop_trend_atr": 1.5,
    "risk_reward": 1.5,
    "stop_extra_atr": 0.3,
    "candle_min_atr": 0.3,
    "breakout_manha": True,
    "breakout_almoco": True,
    "breakout_tarde": False,
}

ASSETS = {
    "WIN": {"symbol": "WIN$", "fallback": "WINV26", "pt_value": 0.20},
    "WDO": {"symbol": "WDO$", "fallback": "WDOV26", "pt_value": 10.0},
}

CUSTO_TRADE = 1.20

SESSOES = [
    ("09:10", "12:00"),
    ("14:00", "17:10"),
]


def em_sessao(t):
    for ini, fim in SESSOES:
        h1, m1 = map(int, ini.split(":"))
        h2, m2 = map(int, fim.split(":"))
        if (t.hour, t.minute) >= (h1, m1) and (t.hour, t.minute) < (h2, m2):
            return True
    return False


def breakout_habilitado(t):
    if t.hour < 12:
        return PARAMS["breakout_manha"]
    if t.hour >= 14:
        return PARAMS["breakout_tarde"]
    return PARAMS["breakout_almoco"]


def carregar_dados(symbol):
    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=365)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    d5 = df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    return d5


def calcular_indicadores(df):
    p = PARAMS
    df["ema"] = df["close"].ewm(span=p["ema_period"], adjust=False).mean()
    ref = df["ema"].shift(p["slope_lookback"])
    df["slope"] = np.where(ref != 0, (df["ema"] - ref) / ref, 0.0)

    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=p["atr_period"], adjust=False).mean()
    atr_ma = df["atr"].ewm(span=p["atr_ma_period"], adjust=False).mean()
    ratio_ref = atr_ma.shift(p["slope_lookback"])
    df["atr_ratio"] = np.where(ratio_ref > 0, df["atr"] / ratio_ref, 1.0)
    return df


def classificar_estados(df, breakout_ratio):
    p = PARAMS
    estado = np.full(len(df), 2, dtype=int)
    estado[df["atr_ratio"] >= breakout_ratio] = 3
    zona = (df["atr_ratio"] >= p["consol_ratio"]) & (df["atr_ratio"] < breakout_ratio)
    estado[zona & (df["slope"] > p["slope_threshold"])] = 0
    estado[zona & (df["slope"] < -p["slope_threshold"])] = 1
    df["estado"] = estado
    return df


NOMES_ESTADO = {0: "ALTA", 1: "BAIXA", 2: "CONSOL", 3: "BREAKOUT"}


def rodar(df, pt_value, usar_consol=False, breakout_ratio=None, stop_emergencia=False):
    p = dict(PARAMS)
    if breakout_ratio is not None:
        p["breakout_ratio"] = breakout_ratio
    df = classificar_estados(df.copy(), p["breakout_ratio"])
    trades = []
    pos = 0
    entry = stop = alvo = 0.0
    origem = 0
    entry_time = None
    aguardando = 0
    regiao_armada = False
    buy_lim = sell_lim = stop_buy_c = stop_sell_c = 0.0

    n = len(df)
    idx = df.index

    def fechar(i, preco, motivo):
        nonlocal pos, origem
        pts = (preco - entry) if pos == 1 else (entry - preco)
        brl = pts * pt_value * p["contratos"] - CUSTO_TRADE
        trades.append({
            "entrada": entry_time, "saida": idx[i],
            "tipo": "COMPRA" if pos == 1 else "VENDA",
            "origem": "TEND" if origem == 1 else "CONSOL",
            "pts": round(pts, 1), "brl": round(brl, 2), "motivo": motivo,
        })
        pos = 0
        origem = 0

    for i in range(1, n):
        t = idx[i]
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        novo_dia = t.date() != idx[i - 1].date()
        if novo_dia:
            aguardando = 0
            regiao_armada = False
            if pos != 0:
                fechar(i, row["open"], "Fim Dia")

        atr = row["atr"]
        if not np.isfinite(atr) or atr <= 0 or i < 40:
            continue

        # ---------- gestao de posicao aberta ----------
        if pos == 1:
            if row["open"] <= stop:
                fechar(i, row["open"], "STOP")
            elif row["low"] <= stop:
                fechar(i, stop, "STOP")
            elif row["high"] >= alvo:
                fechar(i, alvo, "ALVO")
            elif prev["estado"] == 3 and breakout_habilitado(t) and prev["slope"] < 0:
                fechar(i, row["open"], "BRK-INV")
        elif pos == -1:
            if row["open"] >= stop:
                fechar(i, row["open"], "STOP")
            elif row["high"] >= stop:
                fechar(i, stop, "STOP")
            elif row["low"] <= alvo:
                fechar(i, alvo, "ALVO")
            elif prev["estado"] == 3 and breakout_habilitado(t) and prev["slope"] > 0:
                fechar(i, row["open"], "BRK-INV")

        dentro = em_sessao(t)
        if not dentro:
            if pos != 0:
                fechar(i, row["close"], "FIM SESSAO")
            aguardando = 0
            regiao_armada = False
            continue

        st_prev = int(prev["estado"])
        ema_b = prev["ema"]
        atr_b = prev["atr"]

        # breakout sem posicao: limpa estruturas
        if pos == 0 and st_prev == 3:
            aguardando = 0
            regiao_armada = False
            continue

        # ---------- entradas tendencia (pullback) ----------
        if pos == 0 and not regiao_armada:
            if st_prev == 0 and aguardando != 1:
                aguardando = 1
            elif st_prev == 1 and aguardando != 2:
                aguardando = 2
            if aguardando == 1 and st_prev != 0:
                aguardando = 0
            elif aguardando == 2 and st_prev != 1:
                aguardando = 0

            banda_sup = ema_b + p["band_pullback_atr"] * atr_b
            banda_inf = ema_b - p["band_pullback_atr"] * atr_b

            if aguardando == 1 and row["low"] <= banda_sup:
                fill = min(banda_sup, row["high"])
                pos = 1
                entry = fill
                entry_time = t
                origem = 1
                risco = p["stop_trend_atr"] * atr_b
                stop = fill - risco
                if stop_emergencia:
                    stop = min(stop, row["low"] - 2.0 * atr_b)
                alvo = fill + (fill - stop) * p["risk_reward"]
                aguardando = 0
            elif aguardando == 2 and row["high"] >= banda_inf:
                fill = max(banda_inf, row["low"])
                pos = -1
                entry = fill
                entry_time = t
                origem = 1
                risco = p["stop_trend_atr"] * atr_b
                stop = fill + risco
                if stop_emergencia:
                    stop = max(stop, row["high"] + 2.0 * atr_b)
                alvo = fill - (stop - fill) * p["risk_reward"]
                aguardando = 0

        # ---------- entradas consolidacao (regiao limite) ----------
        if usar_consol and pos == 0 and not regiao_armada and st_prev == 2:
            candle = max(prev["high"] - prev["low"], p["candle_min_atr"] * atr_b)
            buy_lim = prev["low"]
            sell_lim = prev["high"]
            stop_buy_c = buy_lim - 2 * candle - p["stop_extra_atr"] * atr_b
            stop_sell_c = sell_lim + 2 * candle + p["stop_extra_atr"] * atr_b
            regiao_armada = True

        if regiao_armada and pos == 0:
            if st_prev != 2:
                regiao_armada = False
            else:
                tocou_buy = row["low"] <= buy_lim
                tocou_sell = row["high"] >= sell_lim
                if tocou_buy:
                    fill = min(buy_lim, row["high"])
                    pos = 1
                    entry = fill
                    entry_time = t
                    origem = 2
                    stop = stop_buy_c
                    risco = fill - stop
                    alvo = fill + risco * p["risk_reward"]
                    regiao_armada = False
                elif tocou_sell:
                    fill = max(sell_lim, row["low"])
                    pos = -1
                    entry = fill
                    entry_time = t
                    origem = 2
                    stop = stop_sell_c
                    risco = stop - fill
                    alvo = fill - risco * p["risk_reward"]
                    regiao_armada = False

    return pd.DataFrame(trades)


def matriz_transicao(df):
    est = df["estado"].values
    m = np.zeros((4, 4))
    for a, b in zip(est[:-1], est[1:]):
        m[a][b] += 1
    tot = m.sum(axis=1, keepdims=True)
    tot[tot == 0] = 1
    return (m / tot * 100)


def relatorio(trades, nome, pt_value, df, titulo=""):
    print("=" * 58)
    print(f"BACKTEST MARKOV - {nome} {titulo} (M5, 1 contrato)")
    print("=" * 58)

    dist = df["estado"].value_counts(normalize=True).sort_index() * 100
    linha = " | ".join(f"{NOMES_ESTADO[k]}: {v:.0f}%" for k, v in dist.items())
    print(f"Distribuicao estados: {linha}")

    mt = matriz_transicao(df)
    print("Matriz de transicao (%): linhas=de, colunas=para [Alta Baixa Consol Brk]")
    for k in range(4):
        print(f"  {NOMES_ESTADO[k]:<8}: " + " ".join(f"{mt[k][j]:5.1f}" for j in range(4)))

    if trades.empty:
        print("Nenhuma operacao no periodo.")
        print()
        return

    total = len(trades)
    wins = (trades["brl"] > 0).sum()
    wr = wins / total * 100
    saldo = trades["brl"].sum()
    gp = trades.loc[trades["brl"] > 0, "brl"].sum()
    gl = abs(trades.loc[trades["brl"] <= 0, "brl"].sum())
    pf = gp / gl if gl > 0 else float("inf")
    eq = trades["brl"].cumsum()
    dd = (eq - eq.cummax()).min()

    print(f"Total trades     : {total}")
    print(f"Win rate         : {wr:.1f}% ({wins}W/{total - wins}L)")
    print(f"Resultado liquido: R$ {saldo:,.2f}")
    print(f"Profit factor    : {pf:.2f}")
    print(f"Max drawdown     : R$ {dd:,.2f}")
    for o in ["TEND", "CONSOL"]:
        sub = trades[trades["origem"] == o]
        if not sub.empty:
            w = (sub["brl"] > 0).sum()
            print(f"  [{o}] {len(sub)} trades | WR {(w/len(sub)*100):.1f}% | R$ {sub['brl'].sum():,.2f}")
    print("Motivos saida    : " + str(trades["motivo"].value_counts().to_dict()))
    print()


if __name__ == "__main__":
    if not mt5.initialize():
        print("Falha ao inicializar MT5")
        raise SystemExit

    dados = {}
    for nome, cfg in ASSETS.items():
        symbol = cfg["symbol"]
        if not mt5.symbol_select(symbol, True):
            symbol = cfg["fallback"]
            mt5.symbol_select(symbol, True)
        df = carregar_dados(symbol)
        if df is None:
            print(f"{nome}: sem dados para {symbol}")
            continue
        dados[nome] = (calcular_indicadores(df), cfg["pt_value"])

    mt5.shutdown()

    for brk in [1.0]:
        for nome, (df_base, ptv) in dados.items():
            for emerg in [False, True]:
                df_cls = classificar_estados(df_base.copy(), brk)
                trades = rodar(df_cls, ptv, usar_consol=False,
                               breakout_ratio=brk, stop_emergencia=emerg)
                titulo = f"[SO TENDENCIA | ratio={brk} | stop={'EMERGENCIA' if emerg else 'PADRAO 1.5xATR'}]"
                relatorio(trades, nome, ptv, df_cls, titulo=titulo)
