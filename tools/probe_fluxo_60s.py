"""Probe read-only 60s: valida flags TICK_FLAG_BUY/SELL no feed real.

Somente leitura: initialize + symbol_select + copy_ticks_range em loop.
Nao envia ordem, nao altera config, nao escreve arquivo. Uso:
  venv310\\Scripts\\python.exe tools\\probe_fluxo_60s.py [PREFIXO] [SEGUNDOS]
Saida: contagem BUY/SELL/ambos/sem-flag por janela + veredito INFERIDO/REAL.
"""
import sys
import time

FLAG_BUY_STD = 32   # MQL5 TICK_FLAG_BUY (1<<5); confirmado via mt5 no runtime
FLAG_SELL_STD = 64  # MQL5 TICK_FLAG_SELL (1<<6); confirmado via mt5 no runtime


def main():
    prefixo = sys.argv[1] if len(sys.argv) > 1 else "WDO"
    segundos = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 indisponivel neste interpretador. Rode no venv310.")
        return 2
    if not mt5.initialize():
        print(f"MT5 initialize falhou: {mt5.last_error()}")
        return 3
    flag_buy = getattr(mt5, "TICK_FLAG_BUY", FLAG_BUY_STD)
    flag_sell = getattr(mt5, "TICK_FLAG_SELL", FLAG_SELL_STD)
    print(f"TICK_FLAG_BUY={flag_buy} TICK_FLAG_SELL={flag_sell}")
    # front-month dinamico, mesmo criterio do robo
    import re
    from datetime import datetime
    syms = mt5.symbols_get() or []
    agora = datetime.now().timestamp()
    cand = [s for s in syms
            if re.fullmatch(rf"{prefixo}[A-Z]\d{{2}}", s.name)
            and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
            and getattr(s, "expiration_time", 0) > agora]
    symbol = min(cand, key=lambda s: s.expiration_time).name if cand else f"{prefixo}$"
    mt5.symbol_select(symbol, True)
    print(f"Probe em {symbol} por {segundos}s (somente leitura)...")
    t_end = time.time() + segundos
    tot = {"buy": 0, "sell": 0, "ambos": 0, "sem": 0, "n": 0}
    last_msc = 0
    while time.time() < t_end:
        from datetime import timedelta
        dt_to = datetime.now()
        dt_from = dt_to - timedelta(seconds=3)
        ticks = mt5.copy_ticks_range(symbol, dt_from, dt_to,
                                     mt5.COPY_TICKS_ALL)
        if ticks is not None:
            for t in ticks:
                tms = int(t["time_msc"])
                if tms <= last_msc:
                    continue
                last_msc = tms
                f = int(t["flags"])
                b, s_ = bool(f & flag_buy), bool(f & flag_sell)
                tot["n"] += 1
                if b and not s_:
                    tot["buy"] += 1
                elif s_ and not b:
                    tot["sell"] += 1
                elif b and s_:
                    tot["ambos"] += 1
                else:
                    tot["sem"] += 1
        time.sleep(0.2)
    print(tot)
    rotulados = tot["buy"] + tot["sell"]
    if tot["n"] == 0:
        print("VEREDITO=SEM_FEED (mercado fechado ou simbolo sem ticks)")
    elif rotulados == 0:
        print("VEREDITO=INFERIDO (feed sem flags de lado; nao chamar de agressao real)")
    else:
        print(f"VEREDITO=FLAGS_PRESENTES buy={tot['buy']} sell={tot['sell']} "
              f"ambos={tot['ambos']} sem={tot['sem']} -> ainda tratar como "
              "INFERIDO ate provar que flag == agressor (comparar com book/T&S)")
    mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
