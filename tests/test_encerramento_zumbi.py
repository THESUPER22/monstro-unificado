# -*- coding: utf-8 -*-
"""Testes estaticos do encerramento do robo (raiz do zumbi de 18/11).

O processo ficava vivo depois de "ENCERRAMENTO GRACIL CONCLUIDO" porque o
loop so fazia thread_ativo=False e break; a thread principal continuava
presa em webview.start(). Estes testes quebram se a ordem voltar atras.
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fonte():
    with open(os.path.join(BASE, "monstro_unificado_v22.py"),
              encoding="latin-1") as f:
        return f.read()


FONTE = _fonte()


def test_pnl_final_antes_do_parado_ok():
    i_pnl = FONTE.index("pnl_dia_mt5(forcar=True, logar_sempre=True)")
    i_parado = FONTE.index('with open(_caminho_dados("parado.ok")')
    assert i_pnl < i_parado


def test_ordem_parado_ok_shadow_flush_timer():
    i_parado = FONTE.index('with open(_caminho_dados("parado.ok")')
    i_chamada = FONTE.index("_encerrar_processo_de_verdade()", i_parado)
    assert i_parado < i_chamada
    corpo = FONTE[FONTE.index("def _encerrar_processo_de_verdade"):
                  FONTE.index("def encerramento_seguro_completo")]
    i_shadow = corpo.index("shadow_sltp.parar()")
    i_flush = corpo.index("handler.flush()")
    i_timer = corpo.index("threading.Timer(delay_s, os._exit, (0,))")
    assert i_shadow < i_flush < i_timer
    # daemon ANTES do start: sem isso o Timer nao segura a saida
    assert corpo.index("t.daemon = True") < corpo.index("t.start()")


def test_pnl_final_loga_sempre_mesmo_com_cache_quente():
    trecho = FONTE[FONTE.index("def pnl_dia_mt5"):]
    assert "logar_sempre=False" in trecho
    assert "if logar_sempre or _log_periodico" in trecho


def test_flag_sair_sozinho_default_true():
    assert 'SAIR_SOZINHO = _ENCERRAMENTO_CFG.get("sair_sozinho", True)' in FONTE


def _carregar_encerrar(sair_sozinho, registro):
    """Executa o corpo REAL da funcao com threading/logging falsos.

    Nao importa o robo (MT5, modelo, webview); so o trecho da funcao, num
    namespace com a flag e o Timer instrumentado. Nada de os._exit real.
    """
    corpo = FONTE[FONTE.index("def _encerrar_processo_de_verdade"):
                  FONTE.index("def encerramento_seguro_completo")]

    class TimerFalso:
        def __init__(self, delay, fn, args=()):
            self.delay = delay
            registro.append(("timer", delay, fn, args))

        def start(self):
            registro.append(("start",))

    class LogFalso:
        handlers = []

        def info(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def getLogger(self):
            return self

    ns = {
        "os": os,
        "threading": type("ThreadingFalso", (), {"Timer": TimerFalso}),
        "logging": LogFalso(),
        "shadow_sltp": None,
        "SAIR_SOZINHO": sair_sozinho,
    }
    exec(corpo, ns)
    return ns["_encerrar_processo_de_verdade"]


def test_sair_sozinho_false_nao_agenda_os_exit():
    registro = []
    fn = _carregar_encerrar(False, registro)
    fn(5.0)
    assert registro == []


def test_sair_sozinho_true_agenda_os_exit():
    registro = []
    fn = _carregar_encerrar(True, registro)
    fn(5.0)
    assert ("start",) in registro
    timers = [x for x in registro if x[0] == "timer"]
    assert len(timers) == 1
    assert timers[0][1] == 5.0
    assert timers[0][2] is os._exit
    assert timers[0][3] == (0,)
