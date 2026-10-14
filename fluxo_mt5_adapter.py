"""Adapter MT5 read-only para fluxo_tempo_real (wiring fds).

Protocolo exigido pelo coletor: get_symbol() + fetch_ticks().
- Nenhuma ordem, nenhuma escrita, nenhuma chamada fora destas 2 funcoes.
- `import MetaTrader5` lazy dentro dos metodos (suite roda sem terminal).
- Janela via `datetime` (nao int-ms — licao do probe que deu OverflowError),
  ancorada em `symbol_info_tick().time` (server time), NAO em `datetime.now()`
  (local BRT fica ~5h fora da coordenada do MT5 e zerava os ticks).
- Flags resolvidas do proprio `mt5.TICK_FLAG_BUY/SELL` em runtime.
- Falha dura (ticks None) => raise, para o coletor registrar erro e
  NAO marcar mt5_ok. Feed vazio => ([], bid, ask).
"""
from datetime import datetime, timedelta


class FluxoMT5Adapter:
    def __init__(self, symbol_provider, janela_segundos=3):
        self._symbol_provider = symbol_provider
        self._janela = janela_segundos

    def get_symbol(self):
        try:
            return self._symbol_provider()
        except Exception:
            return None

    def fetch_ticks(self, symbol, janela_ms):
        import MetaTrader5 as mt5  # lazy: testes usam stub
        ti = mt5.symbol_info_tick(symbol)
        if ti is None or not ti.time:
            return ([], None, None)
        dt_to = datetime.fromtimestamp(ti.time)
        dt_from = dt_to - timedelta(seconds=self._janela)
        ticks = mt5.copy_ticks_range(symbol, dt_from, dt_to, mt5.COPY_TICKS_ALL)
        if ticks is None:
            raise RuntimeError(f"copy_ticks_range falhou: {mt5.last_error()}")
        fb = getattr(mt5, "TICK_FLAG_BUY", 32)
        fs = getattr(mt5, "TICK_FLAG_SELL", 64)
        out = []
        for t in ticks:
            f = int(t["flags"])
            last = float(t.get("last", 0) or 0)
            out.append({
                "time_msc": int(t["time_msc"]),
                "is_buy": bool(f & fb),
                "is_sell": bool(f & fs),
                "volume": float(t.get("volume", 0) or 0),
                "volume_real": float(t.get("volume_real", 0) or 0),
                "price": last if last > 0 else float(t.get("bid", 0) or 0),
            })
        bid = float(ti.bid) if ti.bid else None
        ask = float(ti.ask) if ti.ask else None
        return (out, bid, ask)
