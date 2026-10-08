"""
fluxo_tempo_real — Monitoramento de fluxo/agressao (SOMENTE LEITURA).

Camada de observabilidade para o Monstro v22. Captura ticks do simbolo
efetivamente operado, calcula delta comprador/vendedor e expoe snapshot
thread-safe para o dashboard.

LIMITES OBRIGATORIOS (nao remover):
- Somente monitoramento e sugestao visual. Nao participa do caminho
  de decisao de entrada/saida/stop/take/lote/trailing/filtros.
- `is_executable` e sempre False. `usar_como_decisao` e sempre False.
- Flags TICK_FLAG_BUY/SELL do feed indicam lado da ultima
  cotacao/negocio do feed, NAO agressor estilo Times&Trades
  (Profit/Nelogica). Sem prova empirica, qualidade = INFERIDO.
- Chamadas ao terminal MT5 acontecem FORA do Lock de estado.
- Nenhuma excecao do coletor pode derrubar o robo.
"""
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone

SCHEMA_VERSION = 1

# Defaults seguros. Merge com config.json, nunca reescrever o arquivo.
DEFAULT_CONFIG = {
    "ativo": True,
    "modo": "monitoramento",  # fixo: somente observacao
    "janela_curta_segundos": 30,
    "janela_candle": "M1",
    "persistencia_ativa": False,  # F1: snapshot em memoria
    "intervalo_captura_ms": 200,
    "retencao_dias": 7,
    "limiar_volume": 0,
    "limiar_delta": 100,
    "usar_como_decisao": False,  # literal obrigatorio
}

# Janela de consulta MT5 curta para nao reprocessar historico.
MT5_JANELA_SEGUNDOS = 3
MAX_TICKS_MEMORIA = 20000
STALE_MS = 5000  # acima disso => ATRASADO


def _finito_ou_null(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _agora_iso():
    return datetime.now(timezone.utc).isoformat()


def classificar_tick(is_buy: bool, is_sell: bool) -> str:
    """Classifica um tick ja resolvido em BUY/SELL/SEM_DIRECAO.

    Recebe booleans (adapter resolve as flags do MT5). Se ambos ou
    nenhum => SEM_DIRECAO. Nunca inventa direcao.
    """
    if is_buy and not is_sell:
        return "BUY"
    if is_sell and not is_buy:
        return "SELL"
    return "SEM_DIRECAO"


def extrair_volume_tick(tick: dict) -> float:
    """Extrai volume de um dict de tick. Prefere volume_real quando > 0."""
    try:
        vr = float(tick.get("volume_real", 0) or 0)
        if vr > 0 and math.isfinite(vr):
            return vr
        v = float(tick.get("volume", 0) or 0)
        if v < 0 or not math.isfinite(v):
            return 0.0
        return v
    except (TypeError, ValueError):
        return 0.0


def sugerir_bias(delta, total_volume, data_age_ms, tick_count,
                 limiar_delta=100, tem_feed=True):
    """Gera sugestao INFORMATIVA. is_executable sempre False."""
    base = {
        "bias": "DADO_INSUFICIENTE",
        "confidence": 0.0,
        "reason_codes": [],
        "is_executable": False,
        "source_quality": "INFERIDO",
    }
    if not tem_feed or tick_count == 0:
        base["reason_codes"] = ["FEED_VAZIO"]
        return base
    if data_age_ms is not None and data_age_ms > STALE_MS:
        base["bias"] = "DADO_ATRASADO"
        base["reason_codes"] = ["DADO_ATRASADO"]
        return base
    codes = []
    if delta > 0:
        codes.append("DELTA_POSITIVO")
    elif delta < 0:
        codes.append("DELTA_NEGATIVO")
    else:
        codes.append("DELTA_ZERADO")
    if total_volume > 0:
        codes.append("VOLUME_OBSERVADO")
    else:
        codes.append("VOLUME_ZERO")
    ad = abs(delta)
    if ad >= limiar_delta * 5:
        bias = "COMPRA_FORTE" if delta > 0 else "VENDA_FORTE"
        conf = 0.9
    elif ad >= limiar_delta:
        bias = "COMPRA_MODERADA" if delta > 0 else "VENDA_MODERADA"
        conf = 0.5
    else:
        bias = "NEUTRO"
        conf = 0.1
    base.update({"bias": bias, "confidence": conf, "reason_codes": codes})
    return base


class EstadoFluxo:
    """Estado thread-safe. Lock protege apenas estruturas em memoria."""

    def __init__(self, config: dict | None = None):
        cfg = dict(DEFAULT_CONFIG)
        if config:
            for k in cfg:
                if k in config:
                    cfg[k] = config[k]
        # Travas de seguranca: nunca operar por fluxo nesta fase.
        cfg["usar_como_decisao"] = False
        cfg["modo"] = "monitoramento"
        self.config = cfg
        self._lock = threading.RLock()
        self._ticks = deque(maxlen=MAX_TICKS_MEMORIA)  # (time_msc, lado, vol)
        self._vistos = set()  # chaves dedup com teto
        self._last_time_msc = 0
        self.buy_volume = 0.0
        self.sell_volume = 0.0
        self.tick_count = 0
        self.cumulative_delta = 0.0
        self.session_total = 0.0
        self.session_data = None
        self.last_tick_time = None
        self.last_update = None
        self.bid = None
        self.ask = None
        self.symbol = None
        self.contract_source = "dinamico"
        self.errors: list = []
        self.mt5_ok = False
        self._stop = threading.Event()
        self._thread = None

    # -- ingestao (pura, sem MT5) --
    def ingerir_ticks(self, ticks: list, symbol: str | None = None,
                      bid=None, ask=None):
        """Ingere lista de dicts {time_msc, lado|flags resolvidos, volume...}.

        Aceita `lado` pronto ("BUY"/"SELL"/...) ou flags booleanas
        `is_buy`/`is_sell`. Ignora duplicatas e timestamps em regressao
        fora de tolerancia (mantem cursor monotonico).
        """
        agora_ms = int(time.time() * 1000)
        novos = 0
        novos_buy = 0.0
        novos_sell = 0.0
        with self._lock:
            if symbol:
                if self.symbol and symbol != self.symbol:
                    # troca de contrato: reseta janela curta, preserva erros
                    self._ticks.clear()
                    self.buy_volume = 0.0
                    self.sell_volume = 0.0
                    self.tick_count = 0
                self.symbol = symbol
            hoje = datetime.now().date().isoformat()
            if self.session_data != hoje:
                self.session_data = hoje
                self.session_total = 0.0
                self.cumulative_delta = 0.0
            janela_ms = int(self.config["janela_curta_segundos"] * 1000)
            for t in ticks:
                try:
                    tms = int(t.get("time_msc", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if tms <= 0:
                    continue
                lado = t.get("lado")
                if lado not in ("BUY", "SELL", "SEM_DIRECAO"):
                    lado = classificar_tick(bool(t.get("is_buy")),
                                            bool(t.get("is_sell")))
                vol = extrair_volume_tick(t)
                chave = (tms, lado, vol,
                         _finito_ou_null(t.get("price")))
                if chave in self._vistos:
                    continue  # duplicata
                if tms < self._last_time_msc - 1000:
                    continue  # fora de ordem alem da tolerancia
                self._vistos.add(chave)
                if len(self._vistos) > MAX_TICKS_MEMORIA * 2:
                    # teto: descarta metade mais antiga (chaves sem ordem,
                    # limpeza aproximada e barata)
                    drop = len(self._vistos) - MAX_TICKS_MEMORIA
                    for k in list(self._vistos)[:drop]:
                        self._vistos.discard(k)
                if tms > self._last_time_msc:
                    self._last_time_msc = tms
                self._ticks.append((tms, lado, vol))
                self.tick_count += 1
                if lado == "BUY":
                    self.buy_volume += vol
                    novos_buy += vol
                elif lado == "SELL":
                    self.sell_volume += vol
                    novos_sell += vol
                novos += 1
            # eviccao da janela curta
            corte = agora_ms - janela_ms
            while self._ticks and self._ticks[0][0] < corte:
                self._ticks.popleft()
            # recomputa janela a partir do deque (janela curta exata)
            bv = sum(v for _, l, v in self._ticks if l == "BUY")
            sv = sum(v for _, l, v in self._ticks if l == "SELL")
            self.buy_volume = bv
            self.sell_volume = sv
            if novos:
                self.cumulative_delta += novos_buy - novos_sell
                self.session_total += novos_buy + novos_sell
                try:
                    if ticks:
                        ultimo = max(int(x.get("time_msc", 0) or 0)
                                     for x in ticks)
                        self.last_tick_time = ultimo
                except (TypeError, ValueError):
                    pass
                self.last_update = _agora_iso()
            if bid is not None:
                self.bid = _finito_ou_null(bid)
            if ask is not None:
                self.ask = _finito_ou_null(ask)
        return novos

    def registrar_erro(self, msg: str):
        with self._lock:
            self.errors.append({"ts": _agora_iso(), "erro": str(msg)[:300]})
            self.errors = self.errors[-20:]

    # -- leitura (snapshot barato para o endpoint) --
    def snapshot(self) -> dict:
        with self._lock:
            bv = float(self.buy_volume)
            sv = float(self.sell_volume)
            delta = bv - sv
            total = bv + sv
            ratio = (bv / sv) if sv > 0 else (None if bv == 0 else float("inf"))
            if ratio is not None and (not math.isfinite(ratio)):
                ratio = None
            agora_ms = int(time.time() * 1000)
            age = (agora_ms - self._last_time_msc) if self._last_time_msc else None
            if not self.mt5_ok or self._last_time_msc == 0:
                quality = "INDISPONIVEL"
            elif age is not None and age > STALE_MS:
                quality = "ATRASADO"
            else:
                quality = "INFERIDO"  # flags != agressao real comprovada
            tem_feed = self._last_time_msc != 0 and self.mt5_ok
            sug = sugerir_bias(delta, total, age, self.tick_count,
                               limiar_delta=float(
                                   self.config.get("limiar_delta", 100)),
                               tem_feed=tem_feed)
            sug.update({
                "is_executable": False,
                "source_quality": "INFERIDO",
                "symbol": self.symbol,
                "window": self.config.get("janela_candle", "M1"),
                "generated_at": _agora_iso(),
                "data_age_ms": age,
            })
            spread = None
            if self.bid is not None and self.ask is not None:
                try:
                    spread = float(self.ask) - float(self.bid)
                except (TypeError, ValueError):
                    spread = None
            return {
                "schema_version": SCHEMA_VERSION,
                "enabled": bool(self.config.get("ativo", True)),
                "symbol": self.symbol,
                "contract_source": self.contract_source,
                "last_tick_time": self._last_time_msc or None,
                "data_age_ms": age,
                "quality": quality,
                "capture_method": "COPY_TICKS_FLAGS",
                "buy_volume": _finito_ou_null(bv),
                "sell_volume": _finito_ou_null(sv),
                "delta": _finito_ou_null(delta),
                "cumulative_delta": _finito_ou_null(self.cumulative_delta),
                "total_volume": _finito_ou_null(total),
                "buy_sell_ratio": ratio,
                "tick_count": int(self.tick_count),
                "bid": self.bid,
                "ask": self.ask,
                "spread": _finito_ou_null(spread) if spread is not None else None,
                "window": self.config.get("janela_candle", "M1"),
                "suggestion": sug,
                "reason_codes": sug["reason_codes"],
                "errors": list(self.errors[-5:]),
                "updated_at": self.last_update,
            }

    def health(self) -> dict:
        snap = self.snapshot()
        return {"ok": snap["enabled"] and snap["quality"] != "INDISPONIVEL",
                "quality": snap["quality"], "data_age_ms": snap["data_age_ms"],
                "tick_count": snap["tick_count"],
                "errors": snap["errors"]}


# Instancia global (importada pela rota F2, ciclo de vida no robo F4).
_estado_global: EstadoFluxo | None = None
_estado_lock = threading.Lock()


def get_estado(config: dict | None = None) -> EstadoFluxo:
    global _estado_global
    with _estado_lock:
        if _estado_global is None:
            _estado_global = EstadoFluxo(config)
        return _estado_global


def coletar_uma_passada(adapter, estado: EstadoFluxo | None = None):
    """Uma iteracao de coleta. MT5 fora do Lock; ingestao com Lock.

    `adapter` deve expor: get_symbol()->str|None,
    fetch_ticks(symbol, janela_ms)->(list[dict], bid, ask), onde cada
    dict tem time_msc/is_buy/is_sell/volume[/volume_real]/price.
    Nunca lanca excecao.
    """
    est = estado or get_estado()
    try:
        symbol = adapter.get_symbol()
    except Exception as e:  # noqa: BLE001
        est.registrar_erro(f"symbol: {e}")
        return 0
    if not symbol:
        est.registrar_erro("contrato indisponivel")
        return 0
    try:
        ticks, bid, ask = adapter.fetch_ticks(
            symbol, MT5_JANELA_SEGUNDOS * 1000)
    except Exception as e:  # noqa: BLE001
        est.registrar_erro(f"fetch: {e}")
        return 0
    try:
        n = est.ingerir_ticks(ticks or [], symbol=symbol, bid=bid, ask=ask)
        with est._lock:
            est.mt5_ok = True
        return n
    except Exception as e:  # noqa: BLE001
        est.registrar_erro(f"ingerir: {e}")
        return 0


def loop_coleta(adapter, estado: EstadoFluxo | None = None,
                intervalo_ms: int = 200):
    """Loop daemon do coletor. Chamada uma vez pelo ciclo de vida do robo."""
    est = estado or get_estado()
    intervalo = max(0.05, (intervalo_ms or 200) / 1000.0)
    while not est._stop.is_set():
        try:
            coletar_uma_passada(adapter, est)
        except Exception:  # noqa: BLE001 - nunca derrubar o robo
            pass
        est._stop.wait(intervalo)


def iniciar(adapter, estado: EstadoFluxo | None = None) -> bool:
    """Inicia thread unica do coletor. Retorna False se ja ativa."""
    est = estado or get_estado()
    if est._thread and est._thread.is_alive():
        return False
    est._stop.clear()
    intervalo = int(est.config.get("intervalo_captura_ms", 200))
    est._thread = threading.Thread(target=loop_coleta,
                                   args=(adapter, est), daemon=True,
                                   name="fluxo_tempo_real")
    est._thread.start()
    return True


def parar(estado: EstadoFluxo | None = None):
    est = estado or get_estado()
    est._stop.set()
