"""Testes do modulo fluxo_tempo_real — sem MT5 real (mocks)."""
import json
import math
import threading
import time

import fluxo_tempo_real as F


def _tick(ms, lado=None, vol=1, price=5177.0, is_buy=None, is_sell=None):
    t = {"time_msc": ms, "volume": vol, "price": price}
    if lado:
        t["lado"] = lado
    if is_buy is not None:
        t["is_buy"] = is_buy
    if is_sell is not None:
        t["is_sell"] = is_sell
    return t


def test_compra_e_venda():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    e.ingerir_ticks([_tick(base, "BUY", 5), _tick(base + 1, "SELL", 2)])
    s = e.snapshot()
    assert s["buy_volume"] == 5
    assert s["sell_volume"] == 2
    assert s["delta"] == 3
    assert s["suggestion"]["is_executable"] is False


def test_tick_sem_direcao_e_volume_zero():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    e.ingerir_ticks([_tick(base, "SEM_DIRECAO", 0),
                     _tick(base + 1, is_buy=False, is_sell=False, vol=3)])
    s = e.snapshot()
    assert s["buy_volume"] == 0
    assert s["sell_volume"] == 0
    assert s["total_volume"] == 0


def test_volume_real_preferido():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    e.ingerir_ticks([{"time_msc": base, "lado": "BUY",
                      "volume": 1, "volume_real": 7}])
    assert e.snapshot()["buy_volume"] == 7


def test_duplicatas_e_fora_de_ordem():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    t = _tick(base, "BUY", 4)
    e.ingerir_ticks([t, dict(t)])  # duplicata exata
    assert e.snapshot()["buy_volume"] == 4
    assert e.snapshot()["tick_count"] == 1
    e.ingerir_ticks([_tick(base - 5000, "BUY", 99)])  # regressao > 1s: ignora
    assert e.snapshot()["buy_volume"] == 4


def test_troca_de_contrato_reseta_janela():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    e.ingerir_ticks([_tick(base, "BUY", 10)], symbol="WDOX25")
    e.ingerir_ticks([_tick(base + 1, "SELL", 3)], symbol="WDOZ25")
    s = e.snapshot()
    assert s["symbol"] == "WDOZ25"
    assert s["buy_volume"] == 0
    assert s["sell_volume"] == 3


def test_feed_vazio_e_flags_ausentes():
    e = F.EstadoFluxo()
    s = e.snapshot()
    assert s["quality"] == "INDISPONIVEL"
    assert s["suggestion"]["bias"] == "DADO_INSUFICIENTE"
    base = int(time.time() * 1000)
    e2 = F.EstadoFluxo()
    e2.mt5_ok = True
    e2.ingerir_ticks([{"time_msc": base, "volume": 2}])  # sem flags/lado
    s2 = e2.snapshot()
    assert s2["buy_volume"] == 0 and s2["sell_volume"] == 0


def test_dado_atrasado():
    e = F.EstadoFluxo({"janela_curta_segundos": 3600})
    e.mt5_ok = True
    velho = int(time.time() * 1000) - 60_000
    e.ingerir_ticks([_tick(velho, "BUY", 5)])
    # forca staleness: ultimo tick ha 60s
    e._last_time_msc = velho
    s = e.snapshot()
    assert s["quality"] == "ATRASADO"
    assert s["suggestion"]["bias"] == "DADO_ATRASADO"


def test_nan_inf_serializam_null():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    e.ingerir_ticks([_tick(base, "BUY", float("nan")),
                     _tick(base + 1, "SELL", float("inf"))])
    s = e.snapshot()
    raw = json.dumps(s)
    assert "NaN" not in raw and "Infinity" not in raw
    for k in ("buy_volume", "sell_volume", "delta", "total_volume"):
        v = s[k]
        assert v is None or math.isfinite(v)


def test_alta_taxa_e_concorrencia():
    e = F.EstadoFluxo()
    e.mt5_ok = True
    base = int(time.time() * 1000)
    lote = [_tick(base + i, "BUY" if i % 2 == 0 else "SELL", 1,
                  price=5177.0 + i * 0.01) for i in range(2000)]

    def leitor():
        for _ in range(50):
            e.snapshot()

    th = threading.Thread(target=leitor)
    th.start()
    e.ingerir_ticks(lote)
    th.join()
    s = e.snapshot()
    assert s["tick_count"] == 2000
    assert s["total_volume"] == 2000


def test_schema_estavel_e_travas():
    e = F.EstadoFluxo({"ativo": False})
    s = e.snapshot()
    for k in ("schema_version", "enabled", "symbol", "contract_source",
              "last_tick_time", "data_age_ms", "quality", "capture_method",
              "buy_volume", "sell_volume", "delta", "cumulative_delta",
              "total_volume", "buy_sell_ratio", "tick_count", "bid", "ask",
              "spread", "window", "suggestion", "reason_codes", "errors",
              "updated_at"):
        assert k in s, k
    assert s["enabled"] is False
    assert s["suggestion"]["is_executable"] is False
    assert s["suggestion"]["source_quality"] == "INFERIDO"
    assert e.config["usar_como_decisao"] is False
    assert e.config["modo"] == "monitoramento"


def test_coletar_uma_passada_com_adapter_mock():
    class Ad:
        def get_symbol(self):
            return "WDOX25"

        def fetch_ticks(self, symbol, janela_ms):
            base = int(time.time() * 1000)
            return ([_tick(base, is_buy=True, is_sell=False, vol=2),
                     _tick(base + 1, is_buy=False, is_sell=True, vol=1)],
                    5176.5, 5177.0)

    e = F.EstadoFluxo()
    n = F.coletar_uma_passada(Ad(), e)
    assert n == 2
    s = e.snapshot()
    assert s["delta"] == 1
    assert s["bid"] == 5176.5


def test_adapter_com_erro_nao_lanca():
    class Bad:
        def get_symbol(self):
            raise RuntimeError("mt5 off")

        def fetch_ticks(self, s, j):
            raise AssertionError("nao deve chamar")

    e = F.EstadoFluxo()
    assert F.coletar_uma_passada(Bad(), e) == 0
    assert len(e.snapshot()["errors"]) >= 1


def test_modulo_nunca_encosta_em_ordens():
    import pathlib
    src = pathlib.Path(__file__).resolve().parent.parent / "fluxo_tempo_real.py"
    txt = src.read_text(encoding="utf-8")
    for proib in ("order_send", "executar_ordem", "fechar_posicao",
                  "usar_como_decisao\": True", "usar_como_decisao': True"):
        assert proib not in txt, proib
