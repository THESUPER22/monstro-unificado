"""Contrato da rota /api/fluxo/status — sem MT5, sem servidor."""
import json
import math


def _client():
    from flask import Flask
    from dashboard_routes import dashboard_bp
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp)
    return app.test_client()


def test_fluxo_status_http200_schema_estavel():
    c = _client()
    r = c.get("/api/fluxo/status")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("schema_version", "enabled", "symbol", "contract_source",
              "last_tick_time", "data_age_ms", "quality", "capture_method",
              "buy_volume", "sell_volume", "delta", "cumulative_delta",
              "total_volume", "buy_sell_ratio", "tick_count", "bid", "ask",
              "spread", "window", "suggestion", "reason_codes", "errors",
              "updated_at"):
        assert k in d, k
    raw = json.dumps(d)
    assert "NaN" not in raw and "Infinity" not in raw
    s = d["suggestion"]
    assert s["is_executable"] is False
    assert s["source_quality"] == "INFERIDO"
    assert d["quality"] in ("INFERIDO", "ATRASADO", "INDISPONIVEL")


def test_fluxo_status_sem_mt5_por_request():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "dashboard_routes.py").read_text(encoding="utf-8")
    bloco = src.split("def api_fluxo_status")[1].split("@dashboard_bp.route")[0]
    for proib in ("symbol_info_tick", "copy_ticks", "market_book",
                  "order_send", "executar_ordem", "fechar_posicao"):
        assert proib not in bloco, proib
