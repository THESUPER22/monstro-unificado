"""Testes do adapter MT5 read-only — stub, sem terminal."""
import sys
import types


def _instalar_stub(ticks="ok"):
    import numpy as np
    mod = types.ModuleType("MetaTrader5")
    mod.TICK_FLAG_BUY = 32
    mod.TICK_FLAG_SELL = 64
    mod.COPY_TICKS_ALL = 0
    base = 1_700_000_000_000
    # MT5 real devolve array estruturado (linhas numpy.void), NAO dict.
    _dtype = np.dtype([
        ("time_msc", "<i8"), ("flags", "<u4"), ("volume", "<u8"),
        ("volume_real", "<f8"), ("last", "<f8"), ("bid", "<f8"),
    ])
    if ticks == "ok":
        mod._rows = np.array([
            (base, 32, 2, 5.0, 5177.0, 5176.5),
            (base + 1, 64, 1, 0.0, 0.0, 5176.0),
            (base + 2, 0, 3, 0.0, 5176.5, 5176.0),
        ], dtype=_dtype)
    else:
        mod._rows = None
    mod.copy_ticks_range = lambda s, a, b, c: mod._rows
    mod.last_error = lambda: (1, "stub")
    tick = types.SimpleNamespace(bid=5176.5, ask=5177.0, time=base // 1000)
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


def test_fetch_ancora_janela_no_server_time_do_tick():
    from datetime import datetime
    mod = _instalar_stub("ok")
    try:
        capturado = {}

        def fake_range(s, a, b, c):
            capturado["from"], capturado["to"] = a, b
            return mod._rows

        mod.copy_ticks_range = fake_range
        from fluxo_mt5_adapter import FluxoMT5Adapter
        ad = FluxoMT5Adapter(symbol_provider=lambda: "WDOX26", janela_segundos=3)
        out, _bid, _ask = ad.fetch_ticks("WDOX26", 3000)
        assert len(out) == 3
        esperado_to = datetime.fromtimestamp(mod.symbol_info_tick("WDOX26").time)
        assert capturado["to"] == esperado_to, "janela deve ancorar em symbol_info_tick().time"
        assert (esperado_to - capturado["from"]).total_seconds() == 3
    finally:
        _remover_stub()


def test_fetch_sem_tick_retorna_vazio():
    mod = _instalar_stub("ok")
    try:
        mod.symbol_info_tick = lambda s: types.SimpleNamespace(bid=0, ask=0, time=0)
        from fluxo_mt5_adapter import FluxoMT5Adapter
        ad = FluxoMT5Adapter(symbol_provider=lambda: "WDOX26")
        assert ad.fetch_ticks("WDOX26", 3000) == ([], None, None)
    finally:
        _remover_stub()
