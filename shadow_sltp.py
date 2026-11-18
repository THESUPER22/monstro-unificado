# -*- coding: utf-8 -*-
"""Executor shadow de SL/TP (P1 17/11 #2).

Coleta, para cada sinal pos-vetos, o caminho bid/ask a 1 s por 30 min. E
READ-ONLY: nao envia ordem, nao altera o pedido e nunca bloqueia o robo.

Isolamento (requisito do ROADMAP 23.54.3):
  - thread unica daemon, separada do loop de trading;
  - ``registrar_sinal``/``marcar_operado`` so fazem ``put_nowait`` (microssegundos)
    e engolem qualquer excecao;
  - amostragem, escrita e rotacao acontecem SOMENTE na thread do coletor;
  - flag ``shadow_sltp.ativo`` no ``config.json`` desliga tudo;
  - CPU medida por ``time.thread_time()`` e exposta em ``estatisticas()``.

Formato: um JSONL por dia UTC em ``logs/shadow_sltp/shadow_sltp_AAAA-MM-DD.jsonl``,
uma linha por sinal:

    {"ts": "...+00:00", "dia": "2026-11-18", "sinal": "BUY", "operado": true,
     "ticket": 123, "sl_pts": 8.0, "tp_pts": 0.0, "atr": 2.5,
     "path": [[epoch, bid, ask], ...], "n": 1800, "completo": true}

Modulo puro (sem MT5 no import e sem chamar MT5 em producao): o preco vem do
tick que a thread ``monitorar_spread`` do robo JA le a cada 1 s, publicado por
``atualizar_preco``. Assim o shadow nao vira mais um caller concorrente do
pacote MetaTrader5 (que nao tem lock no robo). ``_preco_mt5`` fica disponivel
apenas para uso manual/teste.
Testes em ``tests/test_shadow_sltp.py``.
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

DURACAO_PADRAO_S = 1800.0   # 30 min
INTERVALO_PADRAO_S = 1.0
FILA_PADRAO = 200
VALIDADE_TICK_S = 3.0       # tick mais velho que isso NAO vira amostra
VALIDADE_TICK_MS_S = 10.0   # mesmo tick_msc por mais que isso = feed parado

# Ultimo tick publicado pelo loop principal (thread do robo -> thread do
# coletor). Dicionario pequeno e protegido por lock: escrita de 1 tupla por
# segundo, leitura na amostragem. Nenhuma chamada ao MT5.
_ULTIMO_PRECO = {}
_LOCK_PRECO = threading.Lock()


def publicar_preco(symbol, bid, ask, quando=None, tick_msc=None) -> None:
    """Guarda o ultimo (bid, ask, tick_msc) visto pelo robo. Nunca levanta."""
    try:
        t = time.time() if quando is None else float(quando)
        chave = str(symbol)
        with _LOCK_PRECO:
            anterior = _ULTIMO_PRECO.get(chave)
            if (anterior is not None and tick_msc is not None
                    and anterior[3] == tick_msc):
                t_mudanca = anterior[4]
            else:
                t_mudanca = t
            _ULTIMO_PRECO[chave] = (float(bid), float(ask), t,
                                    tick_msc, t_mudanca)
    except Exception:  # noqa: BLE001 - publicacao nao pode quebrar nada
        pass


def preco_publicado(symbol, agora=None, validade_s=VALIDADE_TICK_S,
                    validade_ms_s=VALIDADE_TICK_MS_S):
    """Ultimo (bid, ask) publicado e AINDA VALIDO, ou ``None``.

    Dois relogios independentes:
      - ``quando`` (parede): o publicador esta vivo? Tick com mais de 3 s de
        idade e descartado.
      - ``tick_msc`` (mercado): o preco realmente mudou? Se o MT5 repete o
        mesmo ``time_msc`` por mais de 10 s, o feed esta parado e o tick e
        descartado, mesmo que o publicador continue chamando.

    Sem amostra, o track termina com ``completo=false`` (sinalizado).
    """
    try:
        with _LOCK_PRECO:
            item = _ULTIMO_PRECO.get(str(symbol))
        if not item:
            return None
        bid, ask, quando, tick_msc, t_mudanca = item
        agora = time.time() if agora is None else float(agora)
        if abs(agora - quando) > float(validade_s):
            return None
        if (tick_msc is not None
                and abs(agora - t_mudanca) > float(validade_ms_s)):
            return None
        return (bid, ask)
    except Exception:  # noqa: BLE001
        return None


def max_gap_s(inicio, path, duracao_s):
    """Maior buraco (s) na linha do tempo do path, incluindo inicio e fim.

    Usado pelo filtro pre-registrado: um buraco > 10 s invalida o sinal, mesmo
    que ``completo`` seja true. Retorna ``None`` se o path for ilegivel
    (fail-closed: o filtro descarta).
    """
    if not path:
        return 0.0
    try:
        tempos = [float(p[0]) for p in path]
        buracos = [max(0.0, tempos[0] - float(inicio))]
        buracos += [max(0.0, b - a) for a, b in zip(tempos, tempos[1:])]
        buracos.append(max(0.0, float(inicio) + float(duracao_s) - tempos[-1]))
        return round(max(buracos), 3)
    except Exception:  # noqa: BLE001
        return None


def _preco_mt5(symbol: str):
    """Provedor OPCIONAL: (bid, ask) direto do MT5 (manual/teste).

    NAO e o padrao em producao: chamar o MT5 de uma segunda thread adiciona um
    caller concorrente sem lock. Use ``publicar_preco`` no loop principal.
    """
    import MetaTrader5 as mt5  # noqa: PLC0415

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return (tick.bid, tick.ask)


def notificar_seguro(objeto, metodo: str, *args, **kwargs):
    """Chama ``objeto.metodo`` sem NUNCA deixar a excecao subir.

    Usado no caminho da ordem: se o shadow estiver quebrado/desligado, a ordem
    segue exatamente como antes. Retorna o resultado do metodo ou ``None``.
    """
    if objeto is None:
        return None
    try:
        return getattr(objeto, metodo)(*args, **kwargs)
    except Exception as e:  # noqa: BLE001 - isolamento e o objetivo
        logging.debug(f"[SHADOW SL/TP] {metodo} falhou (ignorado): {e}")
        return None


class ColetorShadow:
    """Coletor em thread unica, com fila limitada e escrita por dia UTC."""

    def __init__(self, pasta: str, ativo: bool = False,
                 duracao_s: float = DURACAO_PADRAO_S,
                 intervalo_s: float = INTERVALO_PADRAO_S,
                 fila_max: int = FILA_PADRAO,
                 provedor_preco: Optional[Callable] = None,
                 relogio: Optional[Callable[[], float]] = None,
                 iniciar: bool = True):
        self.pasta = os.path.abspath(pasta)
        self.ativo = bool(ativo)
        self.duracao_s = max(1.0, float(duracao_s))
        self.intervalo_s = max(0.001, float(intervalo_s))
        self.n_max = max(1, int(round(self.duracao_s / self.intervalo_s)))
        self.fila = queue.Queue(maxsize=max(1, int(fila_max)))
        # Padrao de producao: le o tick publicado pelo loop principal (sem MT5).
        self._provedor = provedor_preco or preco_publicado
        self._relogio = relogio or time.time
        self._tracks = {}
        self._lock = threading.Lock()
        self._ultima_amostra = None
        self._parar = threading.Event()
        self._thread = None
        self._cpu_s = 0.0
        self._iter_s = 0.0
        self._hook_ms_max = 0.0
        self._inicio = self._relogio()
        self._ultimo_log = self._inicio
        self.estat = {"sinais": 0, "gravados": 0, "amostras": 0,
                      "descartes": 0, "falhas": 0}
        if iniciar and self.ativo:
            self._thread = threading.Thread(
                target=self._loop, name="shadow-sltp", daemon=True)
            self._thread.start()

    # ------------------------------------------------------------ publico --
    def atualizar_preco(self, symbol, bid, ask, tick_msc=None) -> None:
        """Publica o ultimo tick lido pelo robo (thread do loop principal).

        Chamado no maximo 1x/s. Nao chama MT5, nao bloqueia e nao levanta:
        e o unico ponto em que a thread de trading toca o shadow a cada ciclo.
        ``tick_msc`` permite detectar feed repetindo o mesmo tick.
        """
        publicar_preco(symbol, bid, ask, tick_msc=tick_msc)

    def registrar_sinal(self, **dados):
        """Enfileira um sinal pos-vetos. Retorna o id ou ``None``."""
        if not self.ativo:
            return None
        t0 = time.perf_counter()
        try:
            sid = uuid.uuid4().hex[:12]
            item = dict(dados)
            item["id"] = sid
            self.fila.put_nowait(("sinal", item))
            self.estat["sinais"] += 1
            return sid
        except queue.Full:
            self.estat["descartes"] += 1
            logging.debug("[SHADOW SL/TP] fila cheia: sinal descartado")
        except Exception as e:  # noqa: BLE001
            self.estat["falhas"] += 1
            logging.debug(f"[SHADOW SL/TP] registrar_sinal falhou: {e}")
        finally:
            # custo real do hook no caminho da ordem (microssegundos)
            ms = (time.perf_counter() - t0) * 1000.0
            if ms > self._hook_ms_max:
                self._hook_ms_max = ms
        return None

    def marcar_operado(self, sinal_id: str, ticket=None) -> None:
        """Marca que o robo realmente enviou a ordem daquele sinal."""
        if not self.ativo or not sinal_id:
            return
        try:
            self.fila.put_nowait(("operado", (sinal_id, ticket)))
        except queue.Full:
            self.estat["descartes"] += 1
        except Exception as e:  # noqa: BLE001
            self.estat["falhas"] += 1
            logging.debug(f"[SHADOW SL/TP] marcar_operado falhou: {e}")

    def estatisticas(self) -> dict:
        """Custo medido e contadores (thread-safe o bastante para leitura)."""
        wall = max(1e-9, self._relogio() - self._inicio)
        return {
            **self.estat,
            "ativos": len(self._tracks),
            "cpu_s": round(self._cpu_s, 6),
            "iter_s": round(self._iter_s, 6),
            "hook_ms_max": round(self._hook_ms_max, 4),
            "wall_s": round(wall, 3),
            "pct_cpu": round(100.0 * self._cpu_s / wall, 4),
            "pct_iter": round(100.0 * self._iter_s / wall, 4),
            "thread_viva": bool(self._thread and self._thread.is_alive()),
        }

    def parar(self, timeout: float = 3.0) -> None:
        """Encerra a thread e grava os caminhos parciais (``completo=false``)."""
        self._parar.set()
        try:
            self.fila.put_nowait(("parar", None))
        except Exception:  # noqa: BLE001
            pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout)
        self._flush_parciais()

    # ------------------------------------------------------------- worker --
    def processar_agora(self, agora: Optional[float] = None) -> None:
        """Uma iteracao do worker (drenar + amostrar + finalizar).

        Publica para testes deterministicos; a thread chama em loop.
        """
        t_iter = time.perf_counter()
        try:
            self._drenar()
            agora = self._relogio() if agora is None else agora
            self._amostrar(agora)
            self._finalizar(agora)
            if agora - self._ultimo_log >= 300:
                self._ultimo_log = agora
                logging.info(f"[SHADOW SL/TP] {self.estatisticas()}")
        except Exception as e:  # noqa: BLE001 - a thread nunca pode morrer
            self.estat["falhas"] += 1
            logging.debug(f"[SHADOW SL/TP] iteracao falhou: {e}")
        finally:
            # custo de trabalho do coletor (tempo de parede dentro da iteracao)
            self._iter_s += max(0.0, time.perf_counter() - t_iter)

    def _loop(self) -> None:
        # CPU acumulada no inicio/fim da thread (thread_time tem granularidade
        # de ~15 ms no Windows; medir por iteracao perderia os ticks parciais).
        t_cpu = time.thread_time()
        while not self._parar.is_set():
            self.processar_agora()
            self._cpu_s = max(0.0, time.thread_time() - t_cpu)
            self._parar.wait(self.intervalo_s)
        self._flush_parciais()
        self._cpu_s = max(0.0, time.thread_time() - t_cpu)

    def _drenar(self) -> None:
        while True:
            try:
                tipo, dados = self.fila.get_nowait()
            except queue.Empty:
                return
            try:
                if tipo == "sinal":
                    self._novo_track(dados)
                elif tipo == "operado":
                    sid, ticket = dados
                    with self._lock:
                        t = self._tracks.get(sid)
                        if t is not None:
                            t["operado"] = True
                            t["ticket"] = ticket
                elif tipo == "parar":
                    self._parar.set()
            except Exception as e:  # noqa: BLE001
                self.estat["falhas"] += 1
                logging.debug(f"[SHADOW SL/TP] evento {tipo} falhou: {e}")

    def _novo_track(self, dados: dict) -> None:
        with self._lock:
            self._tracks[dados["id"]] = {
                "id": dados["id"],
                # ts capturado ANTES do order_send (o enfileiramento e depois)
                "inicio": float(dados.get("ts") or self._relogio()),
                "meta": dados,
                "path": [],
                "operado": False,
                "ticket": None,
                "completo": False,
            }

    def _amostrar(self, agora: float) -> None:
        with self._lock:
            ativos = [t for t in self._tracks.values() if not t["completo"]]
        if not ativos:
            return
        if self._ultima_amostra is not None:
            delta = agora - self._ultima_amostra
            if delta < 0:
                # relogio ajustado para tras (NTP): reinicia a cadencia
                self._ultima_amostra = agora
            elif delta < self.intervalo_s * 0.9:
                return
        self._ultima_amostra = agora
        por_symbol = {}
        for t in ativos:
            por_symbol.setdefault(t["meta"].get("symbol") or "", []).append(t)
        for symbol, tracks in por_symbol.items():
            try:
                preco = self._provedor(symbol)
            except Exception as e:  # noqa: BLE001
                self.estat["falhas"] += 1
                logging.debug(f"[SHADOW SL/TP] provedor falhou ({symbol}): {e}")
                continue
            if not preco:
                continue
            try:
                bid, ask = preco
                par = [round(float(agora), 3),
                       round(float(bid), 3), round(float(ask), 3)]
            except Exception:  # noqa: BLE001
                self.estat["falhas"] += 1
                continue
            with self._lock:
                for t in tracks:
                    t["path"].append(list(par))
            self.estat["amostras"] += len(tracks)

    def _finalizar(self, agora: float) -> None:
        prontos = []
        with self._lock:
            for t in self._tracks.values():
                if t["completo"]:
                    continue
                cheio = len(t["path"]) >= self.n_max
                estourou = (agora - t["inicio"]) >= self.duracao_s + 60.0
                if cheio or estourou:
                    t["completo"] = True
                    # "completo" = cobriu a janela inteira. Na saida por tempo,
                    # tolera ate 10% de amostras perdidas (feed de 1 s com
                    # jitter nao entrega exatamente 1800); abaixo disso o
                    # sinal e marcado incompleto e NAO entra na avaliacao.
                    completo = cheio or len(t["path"]) >= 0.9 * self.n_max
                    prontos.append((t, completo))
            for t, _ in prontos:
                self._tracks.pop(t["id"], None)
        for t, completo in prontos:
            self._gravar(t, completo=completo)

    def _flush_parciais(self) -> None:
        with self._lock:
            restantes = list(self._tracks.values())
            self._tracks.clear()
        for t in restantes:
            self._gravar(t, completo=False)

    def _gravar(self, track: dict, completo: bool) -> None:
        try:
            meta = track["meta"]
            ts = datetime.fromtimestamp(track["inicio"], tz=timezone.utc)
            dia = ts.date().isoformat()
            linha = {
                "ts": ts.isoformat(),
                "dia": dia,
                "sinal": meta.get("sinal"),
                "operado": bool(track["operado"]),
                "ticket": track["ticket"],
                "sl_pts": meta.get("sl_pts"),
                "tp_pts": meta.get("tp_pts"),
                "atr": meta.get("atr"),
                "magic": meta.get("magic"),
                "symbol": meta.get("symbol"),
                "preco": meta.get("preco"),
                "path": track["path"],
                "n": len(track["path"]),
                "duracao_s": float(self.duracao_s),
                "max_gap_s": max_gap_s(track["inicio"], track["path"],
                                       self.duracao_s),
                "completo": bool(completo),
            }
            os.makedirs(self.pasta, exist_ok=True)
            caminho = os.path.join(self.pasta, f"shadow_sltp_{dia}.jsonl")
            texto = json.dumps(linha, ensure_ascii=False,
                               separators=(",", ":")) + "\n"
            with open(caminho, "a", encoding="utf-8", newline="\n") as f:
                f.write(texto)
                f.flush()
                os.fsync(f.fileno())
            self.estat["gravados"] += 1
        except Exception as e:  # noqa: BLE001
            self.estat["falhas"] += 1
            logging.warning(f"[SHADOW SL/TP] falha ao gravar: {e}")


def criar_coletor_shadow(pasta: str, cfg: Optional[dict] = None) -> ColetorShadow:
    """Cria o coletor a partir do bloco ``shadow_sltp`` do ``config.json``.

    Ausencia do bloco/``ativo`` => desligado. Qualquer erro de criacao retorna
    um coletor inativo (nunca impede o robo de subir).
    """
    cfg = cfg or {}
    try:
        coletor = ColetorShadow(
            pasta,
            ativo=bool(cfg.get("ativo", False)),
            duracao_s=float(cfg.get("duracao_s", DURACAO_PADRAO_S)),
            intervalo_s=float(cfg.get("intervalo_s", INTERVALO_PADRAO_S)),
            fila_max=int(cfg.get("fila_max", FILA_PADRAO)),
        )
    except Exception as e:  # noqa: BLE001
        logging.warning(f"[SHADOW SL/TP] config invalida, coletor desligado: {e}")
        return ColetorShadow(pasta, ativo=False, iniciar=False)
    if coletor.ativo:
        atexit.register(coletor.parar)
        logging.info(
            f"[SHADOW SL/TP] ativo | pasta={coletor.pasta} | "
            f"{coletor.duracao_s:.0f}s @ {coletor.intervalo_s:g}s")
    return coletor
