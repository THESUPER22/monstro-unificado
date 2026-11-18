# -*- coding: utf-8 -*-
"""Testes do executor shadow de SL/TP (P1 17/11 #2).

Cobrem o isolamento (falha do shadow NUNCA altera a ordem), o formato do
JSONL, a rotacao diaria, a fila limitada e o custo de CPU medido.
"""
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from shadow_sltp import ColetorShadow, notificar_seguro  # noqa: E402

T0 = 1794936900.0   # 2026-11-17 17:35:00 UTC


def _iso(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


class Relogio:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


def _coletor(tmp_path, **kw):
    relogio = kw.pop("relogio", None) or Relogio()
    provedor = kw.pop("provedor_preco", None) or (lambda symbol: (5400.0, 5400.5))
    kw.setdefault("ativo", True)
    kw.setdefault("iniciar", False)
    kw.setdefault("intervalo_s", 1.0)
    kw.setdefault("duracao_s", 3.0)
    return ColetorShadow(str(tmp_path), relogio=relogio,
                         provedor_preco=provedor, **kw)


def _linhas(tmp_path):
    arquivos = sorted(os.listdir(tmp_path))
    saida = []
    for nome in arquivos:
        with open(os.path.join(tmp_path, nome), encoding="utf-8") as f:
            saida.extend(json.loads(l) for l in f if l.strip())
    return saida


# ------------------------------------------------------------- isolamento --
class _Explode:
    ativo = True

    def registrar_sinal(self, **kw):
        raise RuntimeError("shadow quebrado")

    def marcar_operado(self, *a, **k):
        raise RuntimeError("shadow quebrado")


def test_falha_do_shadow_nunca_altera_a_ordem():
    """Mesmo fluxo do robo: shadow explode, order_send acontece igual."""
    coletor = _Explode()

    def fluxo():
        sid = notificar_seguro(coletor, "registrar_sinal", sinal="BUY")
        pedido = {"enviado": False, "retcode": None}
        pedido["enviado"] = True          # equivale a mt5.order_send(request)
        pedido["retcode"] = 10009         # TRADE_RETCODE_DONE
        notificar_seguro(coletor, "marcar_operado", sid, ticket=123)
        return pedido

    pedido = fluxo()
    assert pedido == {"enviado": True, "retcode": 10009}


def test_notificar_seguro_aceita_none_e_metodo_inexistente():
    assert notificar_seguro(None, "registrar_sinal", sinal="BUY") is None
    assert notificar_seguro(_Explode(), "metodo_que_nao_existe") is None


def test_notificar_seguro_devolve_resultado():
    class Ok:
        def soma(self, a, b):
            return a + b

    assert notificar_seguro(Ok(), "soma", 2, 3) == 5


def test_flag_desligada_nao_cria_arquivo(tmp_path):
    c = _coletor(tmp_path, ativo=False)
    assert c.registrar_sinal(sinal="BUY", symbol="WDO") is None
    c.marcar_operado("abc", ticket=1)
    c.processar_agora()
    c.parar()
    assert os.listdir(tmp_path) == []


# ---------------------------------------------------------------- formato --
def test_jsonl_tem_campos_e_path_de_30_min(tmp_path):
    relogio = Relogio()
    c = _coletor(tmp_path, relogio=relogio, duracao_s=3.0)
    sid = c.registrar_sinal(sinal="BUY", sl_pts=8.0, tp_pts=0.0, atr=2.5,
                            magic=123457, symbol="WDO", preco=5400.0)
    assert sid
    for passo in range(3):
        relogio.t = T0 + passo
        c.processar_agora()
    linhas = _linhas(tmp_path)
    assert len(linhas) == 1
    d = linhas[0]
    assert d["dia"] == "2026-11-17"
    assert d["ts"].endswith("+00:00")
    assert d["sinal"] == "BUY"
    assert d["sl_pts"] == 8.0 and d["tp_pts"] == 0.0 and d["atr"] == 2.5
    assert d["operado"] is False and d["ticket"] is None
    assert d["n"] == 3 and d["completo"] is True
    assert d["path"] == [[T0, 5400.0, 5400.5],
                         [T0 + 1, 5400.0, 5400.5],
                         [T0 + 2, 5400.0, 5400.5]]


def test_operado_marcado_apos_a_ordem(tmp_path):
    relogio = Relogio()
    c = _coletor(tmp_path, relogio=relogio, duracao_s=1.0)
    sid = c.registrar_sinal(sinal="SELL", symbol="WDO")
    c.marcar_operado(sid, ticket=1882256502)
    relogio.t = T0
    c.processar_agora()
    d = _linhas(tmp_path)[0]
    assert d["operado"] is True and d["ticket"] == 1882256502


def test_dois_sinais_geram_duas_linhas(tmp_path):
    relogio = Relogio()
    c = _coletor(tmp_path, relogio=relogio, duracao_s=1.0)
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.registrar_sinal(sinal="SELL", symbol="WDO")
    c.processar_agora()
    assert len(_linhas(tmp_path)) == 2


def test_rotacao_diaria_por_utc(tmp_path):
    relogio = Relogio()
    c = _coletor(tmp_path, relogio=relogio, duracao_s=1.0)
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.processar_agora()
    dia1 = datetime(2026, 11, 18, 23, 59, 50, tzinfo=timezone.utc).timestamp()
    relogio.t = dia1
    c.registrar_sinal(sinal="SELL", symbol="WDO")
    c.processar_agora()
    dia2 = datetime(2026, 11, 19, 0, 0, 10, tzinfo=timezone.utc).timestamp()
    relogio.t = dia2
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.processar_agora()
    nomes = sorted(os.listdir(tmp_path))
    assert nomes == ["shadow_sltp_2026-11-17.jsonl",
                     "shadow_sltp_2026-11-18.jsonl",
                     "shadow_sltp_2026-11-19.jsonl"]


# ------------------------------------------------------------ robustez ----
def test_fila_cheia_descarta_sem_levantar(tmp_path):
    c = _coletor(tmp_path, fila_max=1)
    assert c.registrar_sinal(sinal="BUY", symbol="WDO")
    assert c.registrar_sinal(sinal="SELL", symbol="WDO") is None
    assert c.estatisticas()["descartes"] == 1
    c.parar()


def test_provedor_quebrado_nao_derruba_e_grava_parcial(tmp_path):
    def ruim(symbol):
        raise RuntimeError("sem tick")

    c = _coletor(tmp_path, provedor_preco=ruim, duracao_s=1800.0)
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.processar_agora()
    c.parar()
    assert c.estatisticas()["falhas"] >= 1
    d = _linhas(tmp_path)[0]
    assert d["path"] == [] and d["completo"] is False


def test_parar_grava_caminho_parcial(tmp_path):
    c = _coletor(tmp_path, duracao_s=1800.0)
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.processar_agora()
    c.parar()
    d = _linhas(tmp_path)[0]
    assert d["n"] == 1 and d["completo"] is False


def test_cpu_e_wall_medidos(tmp_path):
    c = _coletor(tmp_path, duracao_s=1.0)
    c.registrar_sinal(sinal="BUY", symbol="WDO")
    c.processar_agora()
    st = c.estatisticas()
    assert st["cpu_s"] >= 0.0
    assert st["iter_s"] > 0.0
    assert st["wall_s"] >= 0.0
    assert st["pct_cpu"] >= 0.0
    assert st["pct_iter"] >= 0.0
    assert st["gravados"] == 1


# ------------------------------------------------------- hook no robo ------
def test_hook_fica_antes_do_order_send_e_marca_depois():
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="latin-1") as f:
        txt = f.read()
    i_reg = txt.index('shadow_sltp, "registrar_sinal"')
    i_send = txt.index("resultado = mt5.order_send(request)")
    i_op = txt.index('notificar_seguro(shadow_sltp, "marcar_operado"')
    assert i_reg < i_send < i_op
    # ATR do Sniper e o mesmo usado no dimensionamento do sinal
    assert "'atr': atr," in txt
    assert "atr=atr_override" in txt
    assert "atr_override=_atr_sinal" in txt
    assert "def executar_ordem(action, lots=VOLUME_PADRAO, symbol=None, modo_operacional=None, sniper=False," in txt


def test_config_e_gitignore_tem_o_shadow():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8-sig") as f:
        cfg = json.load(f)
    bloco = cfg["shadow_sltp"]
    assert isinstance(bloco["ativo"], bool)
    assert bloco["duracao_s"] == 1800 and bloco["intervalo_s"] == 1.0
    with open(os.path.join(BASE, ".gitignore"), encoding="utf-8",
              errors="replace") as f:
        assert "logs/shadow_sltp/" in f.read()
