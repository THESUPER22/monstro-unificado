"""Testes do adapter MT5 read-only — stub, sem terminal."""
import sys
import types


def _instalar_stub(ticks="ok"):
    mod = types.ModuleType("MetaTrader5")
    mod.TICK_FLAG_BUY = 32
    mod.TICK_FLAG_SELL = 64
    mod.COPY_TICKS_ALL = 0
    base = 1_700_000_000_000
    if ticks == "ok":
        mod._rows = [
            {"time_msc": base, "flags": 32, "volume": 2,
             "volume_real": 5, "last": 5177.0, "bid": 5176.5},
            {"time_msc": base + 1, "flags": 64, "volume": 1,
             "volume_real": 0, "last": 0, "bid": 5176.0},
            {"time_msc": base + 2, "flags": 0, "volume": 3,
             "volume_real": 0, "last": 5176.5, "bid": 5176.0},
        ]
    else:
        mod._rows = None
    mod.copy_ticks_range = lambda s, a, b, c: mod._rows
    mod.last_error = lambda: (1, "stub")
    tick = types.SimpleNamespace(bid=5176.5, ask=5177.0)
    mod.symbol_info_tick = lambda s: tick
    sys.modules["MetaTrader5"] = mod
    return mod


def _remover_stub():
    sys.modules.pop("MetaTrader5", None)


def test_fetch_resolve_flags_volumes_preco():
    _instalar_stub("ok")
    try:
        from fluxo_mt5_adapter import FluxoMT5Adapter
        ad = FluxoMT5Adapter(symbol_provider=lambda: "WDOX26")
        assert ad.get_symbol() == "WDOX26"
        out, bid, ask = ad.fetch_ticks("WDOX26", 3000)
        assert len(out) == 3
        assert out[0]["is_buy"] is True and out[0]["is_sell"] is False
        assert out[0]["volume_real"] == 5  # modulo prefere volume_real
        assert out[0]["price"] == 5177.0
        assert out[1]["is_buy"] is False and out[1]["is_sell"] is True
        assert out[1]["price"] == 5176.0  # last=0 => cai para bid
        assert out[2]["is_buy"] is False and out[2]["is_sell"] is False
        assert (bid, ask) == (5176.5, 5177.0)
    finally:
        _remover_stub()


def test_ticks_none_vira_raise():
    _instalar_stub("none")
    try:
        from fluxo_mt5_adapter import FluxoMT5Adapter
        ad = FluxoMT5Adapter(symbol_provider=lambda: "WDOX26")
        try:
            ad.fetch_ticks("WDOX26", 3000)
        except RuntimeError:
            return
        assert False, "deveria lancar RuntimeError"
    finally:
        _remover_stub()


def test_symbol_provider_quebrado_retorna_none():
    _instalar_stub("ok")
    try:
        from fluxo_mt5_adapter import FluxoMT5Adapter

        def ruim():
            raise ValueError("sem simbolo")

        assert FluxoMT5Adapter(symbol_provider=ruim).get_symbol() is None
    finally:
        _remover_stub()


def test_adapter_nunca_encosta_em_ordens():
    import pathlib
    txt = (pathlib.Path(__file__).resolve().parent.parent
           / "fluxo_mt5_adapter.py").read_text(encoding="utf-8")
    for proib in ("order_send", "executar_ordem", "fechar_posicao",
                  "order_check", "positions_get"):
        assert proib not in txt, proib
