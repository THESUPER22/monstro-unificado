"""
SENTINELA DE FLUXO - Gatekeeper Macroeconomico

Classifica o cenario global em RISK_ON / RISK_OFF / NEUTRO usando:
- DXY (indice do dolar)
- US 10Y (treasury yield)
- USD/JPY (proxy de carry trade)

Tambem fornece cotacoes globais para o Market Ticker do dashboard.

Fonte: Yahoo Finance (query1.finance.yahoo.com) - apenas `requests`, sem
dependencia externa nova. Falha de API = NEUTRO (fail-open, sem veto).

Logica:
  DXY sobe + Juros EUA sobem + USD/JPY cai (carry unwind) = RISK-OFF
      -> Sentinela libera: so BUY no WDO (dolar forte)
  DXY cai + Juros EUA estaveis/caem + USD/JPY sobe (carry on) = RISK-ON
      -> Sentinela libera: so SELL no WDO (dolar fraco)
"""

import threading
import time
from datetime import datetime

import requests

_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range=5d"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_TIMEOUT = 10
_TTL = 60

_lock = threading.Lock()
_cache = {}

SENTINELA_SYMBOLS = {
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "usd_jpy": "JPY=X",
}

TICKER_SYMBOLS = {
    "dxy": ("DX-Y.NYB", "DXY"),
    "us10y": ("^TNX", "US 10Y"),
    "sp500": ("^GSPC", "S&P 500"),
    "wti": ("CL=F", "WTI"),
    "gold": ("GC=F", "OURO"),
    "btc": ("BTC-USD", "BTC"),
    "usdbrl": ("BRL=X", "USD/BRL"),
}

_limiares = {
    "dxy": 0.15,
    "us10y": 0.50,
    "usd_jpy": 0.15,
}


def _buscar(symbol):
    agora = time.time()
    with _lock:
        if symbol in _cache and agora - _cache[symbol][0] < _TTL:
            return _cache[symbol][1]
    try:
        r = requests.get(_YAHOO_URL.format(s=symbol), headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        meta = r.json()["chart"]["result"][0]["meta"]
        preco = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        valor = None
        if preco:
            var = ((preco / prev) - 1.0) * 100.0 if prev else 0.0
            valor = {
                "preco": float(preco),
                "variacao": round(float(var), 3),
                "atualizado": datetime.now().strftime("%H:%M:%S"),
            }
        with _lock:
            _cache[symbol] = (agora, valor)
        return valor
    except Exception:
        return None


def _pontuar(chave, var):
    if var is None:
        return 0
    lim = _limiares.get(chave, 0.15)
    if var > lim:
        return 1
    if var < -lim:
        return -1
    return 0


def classificar():
    """Retorna dict: cenario RISK_ON|RISK_OFF|NEUTRO, score, dados e detalhe."""
    dxy = _buscar(SENTINELA_SYMBOLS["dxy"])
    us10y = _buscar(SENTINELA_SYMBOLS["us10y"])
    jpy = _buscar(SENTINELA_SYMBOLS["usd_jpy"])

    if not dxy or not us10y or not jpy:
        return {
            "cenario": "NEUTRO",
            "score": 0,
            "detalhe": "Dados indisponiveis (fail-open)",
            "dados": {"dxy": dxy, "us10y": us10y, "usd_jpy": jpy},
            "atualizado": datetime.now().strftime("%H:%M:%S"),
        }

    s_dxy = _pontuar("dxy", dxy["variacao"])
    s_y10 = _pontuar("us10y", us10y["variacao"])
    s_jpy = -_pontuar("usd_jpy", jpy["variacao"])  # JPY forte = carry unwind = RISK_OFF
    score = s_dxy + s_y10 + s_jpy

    if score >= 2:
        cenario = "RISK_OFF"
        detalhe = (f"DXY {dxy['variacao']:+.2f}% | US10Y {us10y['variacao']:+.2f}% | "
                   f"USDJPY {jpy['variacao']:+.2f}% -> so BUY liberado")
    elif score <= -2:
        cenario = "RISK_ON"
        detalhe = (f"DXY {dxy['variacao']:+.2f}% | US10Y {us10y['variacao']:+.2f}% | "
                   f"USDJPY {jpy['variacao']:+.2f}% -> so SELL liberado")
    else:
        cenario = "NEUTRO"
        detalhe = (f"Score {score} (DXY {dxy['variacao']:+.2f}% | "
                   f"US10Y {us10y['variacao']:+.2f}% | USDJPY {jpy['variacao']:+.2f}%)")

    return {
        "cenario": cenario,
        "score": score,
        "detalhe": detalhe,
        "dados": {"dxy": dxy, "us10y": us10y, "usd_jpy": jpy},
        "atualizado": datetime.now().strftime("%H:%M:%S"),
    }


def obter_ticker():
    """Retorna cotacoes globais para o Market Ticker do dashboard."""
    result = {}
    for chave, (symbol, rotulo) in TICKER_SYMBOLS.items():
        valor = _buscar(symbol)
        result[chave] = {
            "simbolo": symbol,
            "rotulo": rotulo,
            "preco": valor["preco"] if valor else None,
            "variacao": valor["variacao"] if valor else None,
            "atualizado": valor["atualizado"] if valor else None,
        }
    return result


def liberar_buy(cenario):
    """Em RISK_OFF, BUY liberado e SELL bloqueado."""
    return cenario == "RISK_OFF"


def liberar_sell(cenario):
    """Em RISK_ON, SELL liberado e BUY bloqueado."""
    return cenario == "RISK_ON"


if __name__ == "__main__":
    print(classificar())
    print(obter_ticker())
