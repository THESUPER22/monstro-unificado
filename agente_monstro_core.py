# -*- coding: utf-8 -*-
"""
AGENTE AUTONOMO DO MONSTRO - Fase 1 (offline, deterministico)
Modos de uso (via Agendador de Tarefas, privilegio elevado):
    agente_monstro_core.py pausa     -> rotina das 12:30 (analise + ajuste + restart)
    agente_monstro_core.py fecho     -> rotina das 17:35 (autopsia + relatorio + commit)
    agente_monstro_core.py watchdog  -> checagem de vida (PID + porta)
    agente_monstro_core.py dryrun    -> so analisa e mostra a decisao (NAO mexe em nada)

Autonomia delimitada: so ajusta parametros da WHITELIST (agente_config.json),
dentro de limites [min,max], 1 parametro por ciclo, com smoke test + rollback.
Nao reescreve logica do fonte em producao nesta fase.
"""
import glob
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import psutil
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "agente_config.json"), encoding="utf-8-sig"))
P = CFG["paths"]
D = CFG["decisao"]
R = CFG["rotinas"]
BASE_DIR = P["base"]
CONFIG_ROBO = os.path.join(BASE_DIR, P["config_robo"])
LOG_ROBO = os.path.join(BASE_DIR, P["log_robo"])
DECISIONS = os.path.join(BASE_DIR, P["decisions_csv"])
LOG_AGENTE = os.path.join(BASE_DIR, P["log_agente"])
ESTADO = os.path.join(BASE_DIR, P["estado_agente"])
PARAR = os.path.join(BASE_DIR, "parar.txt")

# ---------------------------------------------------------------- logging ---
logging.basicConfig(
    filename=LOG_AGENTE, level=logging.INFO, filemode="a", force=True,
    format="%(asctime)s - %(levelname)s - %(message)s")
_sh = logging.StreamHandler()
_sh.setLevel(logging.INFO)
logging.getLogger().addHandler(_sh)
log = logging.getLogger()

VETO_PATTERNS = {
    "sniper_standby": "Standby: Aguardando Big Players",
    "williams_r": "WILLIAMS %R VETO",
    "veto_total": "VETO TOTAL",
    "multi_tf": "MULTI-TF VETO",
    "tendencia": "TENDÊNCIA VETO",
    "sinal_neutro": "Sinal NEUTRO",
    "dol_veto": "VETO DOL",
    "book_ratio_veto": "VETO BOOK RATIO",
}


# ------------------------------------------------------------- config robo --
def carregar_config_robo():
    with open(CONFIG_ROBO, encoding="utf-8-sig") as f:
        return json.load(f)


def salvar_config_robo(cfg):
    with open(CONFIG_ROBO, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def get_path(obj, dotted):
    cur = obj
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def set_path(obj, dotted, value):
    cur = obj
    ks = dotted.split(".")
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    cur[ks[-1]] = value


def porta_dashboard():
    try:
        return int(carregar_config_robo().get("web_dashboard", {}).get("port", R["porta_fallback"]))
    except Exception:
        return R["porta_fallback"]


# ------------------------------------------------------ estado persistente -----
def carregar_estado():
    """Le agente_estado.json. Estrutura minima quando ausente/corrompido."""
    try:
        with open(ESTADO, encoding="utf-8") as f:
            st = json.load(f)
        if not isinstance(st, dict):
            raise ValueError("estado nao e um dict")
    except Exception:
        st = {}
    st.setdefault("ultima_mudanca", None)
    st.setdefault("historico", [])
    st.setdefault("codigo_hash", None)
    return st


def salvar_estado(st):
    try:
        with open(ESTADO, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"falha ao salvar estado: {e}")


def pode_ajustar():
    """Trava fisica: no maximo 1 mudanca de parametro por dia/ciclo.
    Retorna (permitido, ultima_mudanca_registrada)."""
    st = carregar_estado()
    um = st.get("ultima_mudanca")
    if um and um.get("data") == datetime.now().strftime("%Y-%m-%d"):
        return False, um
    return True, um


def registrar_mudanca(param, de, para, motivo, tipo="ajuste"):
    """Registra a mudanca no estado persistente e mantem historico (max 200)."""
    st = carregar_estado()
    agora = datetime.now()
    reg = {"data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M:%S"),
           "param": param, "de": de, "para": para, "motivo": motivo, "tipo": tipo}
    st["ultima_mudanca"] = reg
    st.setdefault("historico", []).append(reg)
    st["historico"] = st["historico"][-200:]
    salvar_estado(st)
    return reg


# ------------------------------------------------------- janela de autonomia ---
def dentro_da_janela_autonomia():
    """Ajuste de parametro SOMENTE dentro da janela [janela_inicio, janela_fim].
    Fora dela o agente aborta sem nenhuma acao (seguranca)."""
    try:
        agora = datetime.now().strftime("%H:%M")
        ini, fim = R["janela_inicio"], R["janela_fim"]
        return ini <= agora <= fim
    except Exception as e:
        log.error(f"janela: config invalida ({e}) - bloqueando ajuste por seguranca")
        return False


# ---------------------------------------------------------------- processos -
def pids_robo():
    out = []
    for pr in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cl = " ".join(pr.info.get("cmdline") or [])
            if "monstro_unificado_v22" in cl or "MonstroDashboard.exe" in cl:
                out.append(pr.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def parar_gracioso(timeout):
    try:
        with open(PARAR, "w") as f:
            f.write("PARAR")
        log.info("parar.txt criado - shutdown gracioso solicitado")
    except Exception as e:
        log.error(f"falha ao criar parar.txt: {e}")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not pids_robo():
            if os.path.exists(PARAR):
                try:
                    os.remove(PARAR)
                except Exception:
                    pass
            log.info("robo encerrou graciosamente")
            return True
        time.sleep(3)
    log.warning("timeout no shutdown gracioso")
    return False


def parar_forcado():
    for pid in pids_robo():
        try:
            psutil.Process(pid).kill()
            log.warning(f"force kill PID {pid}")
        except Exception as e:
            log.error(f"falha kill {pid}: {e}")
    t0 = time.time()
    while time.time() - t0 < 15 and pids_robo():
        time.sleep(1)
    if os.path.exists(PARAR):
        try:
            os.remove(PARAR)
        except Exception:
            pass
    ok = not pids_robo()
    log.info(f"parada forcada: {'ok' if ok else 'FALHOU'}")
    return ok


def parar_robo():
    if not pids_robo():
        log.info("robo ja estava parado")
        return True
    if parar_gracioso(R["graceful_timeout_s"]):
        return True
    return parar_forcado()


def sinalizar_parada_robo():
    """Cria parar.txt para o robo comecar o encerramento gracioso EM PARALELO
    com a geracao dos artefatos do fecho. Se o processo do fecho for abortado
    logo depois, o robo ainda encerra sozinho e os artefatos ja existem."""
    if not pids_robo():
        log.info("robo ja estava parado - sem sinal necessario")
        return
    try:
        with open(PARAR, "w") as f:
            f.write("PARAR")
        log.info("parar.txt criado - shutdown gracioso solicitado")
    except Exception as e:
        log.error(f"falha ao criar parar.txt: {e}")


def start_mt5():
    if any("terminal64" in (pr.info.get("name") or "").lower() for pr in psutil.process_iter(["name"])):
        log.info("MT5 ja estava rodando")
        return
    try:
        subprocess.Popen([P["mt5_exe"]], cwd=os.path.dirname(P["mt5_exe"]))
        log.info("MT5 iniciado, aguardando 15s")
        time.sleep(15)
    except Exception as e:
        log.error(f"falha ao iniciar MT5: {e}")


def start_robot():
    cmd = [os.path.join(BASE_DIR, P["python_venv"]), P["robo_script"]]
    subprocess.Popen(cmd, cwd=BASE_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
    log.info("robo iniciado (script venv310, CWD=C:\\AIOFEN)")


def stop_mt5():
    for pr in psutil.process_iter(["name"]):
        try:
            if "terminal64" in (pr.info.get("name") or "").lower():
                pr.kill()
                log.info("MT5 encerrado")
        except Exception as e:
            log.error(f"falha ao encerrar MT5: {e}")


def health_check(timeout):
    porta = porta_dashboard()
    url = f"http://127.0.0.1:{porta}/api/status"
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not pids_robo():
            return False, "processo do robo morreu"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and r.json().get("thread_ativo"):
                return True, f"OK porta {porta}"
        except Exception:
            pass
        time.sleep(3)
    return False, f"timeout {timeout}s aguardando porta {porta}"


# ------------------------------------------------------------------ parsing -
def parse_vetos_log():
    hoje = datetime.now().strftime("%Y-%m-%d")
    counts = {k: 0 for k in VETO_PATTERNS}
    last = {k: None for k in VETO_PATTERNS}
    if os.path.exists(LOG_ROBO):
        with open(LOG_ROBO, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.startswith(hoje):
                    continue
                ts = line[:19]
                for k, pat in VETO_PATTERNS.items():
                    if pat in line:
                        counts[k] += 1
                        last[k] = ts
    return counts, last


def parse_decisions():
    import pandas as pd
    if not os.path.exists(DECISIONS):
        return {"sinais": 0, "n_decisoes": 0}
    df = pd.read_csv(DECISIONS)
    df["ts"] = pd.to_datetime(df["timestamp"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    hoje = df[df["ts"].dt.date == datetime.now().date()]
    if len(hoje) == 0:
        return {"sinais": 0, "n_decisoes": 0}
    b = hoje["bid_qty"].clip(lower=1)
    a = hoje["ask_qty"].clip(lower=1)
    ratio = (pd.concat([b, a], axis=1).max(axis=1) / pd.concat([b, a], axis=1).min(axis=1))
    return {
        "sinais": int(hoje["acao"].isin(["BUY", "SELL"]).sum()),
        "n_decisoes": int(len(hoje)),
        "entropia_med": float(hoje["entropia_book"].median()),
        "atr_med": float(hoje["volatility"].median()),
        "spread_med": float(hoje["spread"].median()),
        "book_ratio_med": float(ratio.median()),
    }


def contar_executados_hoje():
    """Trades FECHADOS hoje (marcador 'processada e resetada' do v22).
    Corresponde aos appends de historico_lucro (= total_operacoes do dashboard).
    Sinais BUY/SELL em decisions_wdo.csv NAO sao execucao: muitos sao vetados
    por gates pos-decisao (Williams/protecao) antes de virar ordem."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    n = 0
    if os.path.exists(LOG_ROBO):
        with open(LOG_ROBO, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith(hoje) and "processada e resetada" in line:
                    n += 1
    return n


def winpct_historico():
    import pandas as pd
    hist = os.path.join(BASE_DIR, "historico_contexto_wdo.csv")
    if not os.path.exists(hist):
        return None
    df = pd.read_csv(hist, on_bad_lines="skip")
    r = pd.to_numeric(df["reward"], errors="coerce").fillna(0)
    r = r[r != 0]
    if len(r) == 0:
        return None
    return float((r > 0).mean() * 100)


# ------------------------------------------------------------------ decisao -
def blocker_dominante(counts, last):
    """Bloqueador ATUAL = o veto com a ocorrencia MAIS RECENTE no log.
    (contagem bruta nao serve: standby loga 1x/5min, williams a cada 2s)"""
    recentes = [(ts, k) for k, ts in last.items() if ts]
    if not recentes:
        return "nenhum"
    return max(recentes)[1]


def decidir(stats, counts, last):
    mercado_operavel = (stats.get("entropia_med", 0) >= D["entropia_min_operavel"]
                        and stats.get("atr_med", 0) >= D["atr_min_operavel"])
    sinais = stats.get("sinais", 0)
    exec = contar_executados_hoje()
    log.info(f"decisao: sinais={sinais} executados={exec} entropia_med={stats.get('entropia_med')} "
             f"atr_med={stats.get('atr_med')} vetos={counts} operavel={mercado_operavel}")

    if exec == 0:
        if sinais > 0:
            return None, (f"Robo gerou {sinais} sinais hoje mas 0 executados - "
                          f"gates pos-decisao (protecao legitima) estao vetando. Manter quieto.")
        b = blocker_dominante(counts, last)
        standby_persistente = counts.get("sniper_standby", 0) >= D["min_eventos_standby"]
        if b == "sniper_standby" and standby_persistente and mercado_operavel:
            return "sniper_ratio_min", "Gate SNIPER (standby) bloqueia analise AGORA com mercado operavel"
        if b == "dol_veto":
            return "dol_conf_min", "Veto DOL e o bloqueio atual com mercado operavel"
        if b == "book_ratio_veto":
            return "book_ratio_min", "Veto Book Ratio e o bloqueio atual com mercado operavel"
        if b in ("williams_r", "veto_total", "multi_tf", "tendencia"):
            return None, f"Bloqueio legitimo de protecao ATUAL ({b}) - mercado em extremo/sem padrao. Manter quieto."
        if b == "sinal_neutro":
            return None, "Modelo indeciso (confidence gap) e o bloqueio atual - revisar modelo (notificar humano)"
        return None, f"0 executados; bloqueio atual '{b}' nao exige ajuste (mercado sem oportunidade ou protecao correta). Manter."

    if exec >= D["min_trades_para_winpct"]:
        w = winpct_historico()
        if w is not None and w < D["winpct_acaso"]:
            return None, (f"win% {w:.1f}% < acaso {D['winpct_acaso']}% - NAO apertar sozinho "
                          f"(risco). Notificar humano p/ analise.")
        return None, f"Robo operou ({exec} trades executados, win% {w}). Sem ajuste automatico necessario."
    return None, f"Amostra insuficiente ({exec} trades executados). Manter."


def aplicar_ajuste(param, motivo):
    W = CFG["whitelist"].get(param)
    if not W:
        return False, None, f"{param} fora da whitelist"
    cfg = carregar_config_robo()
    atual = None
    for cam in W["caminhos"]:
        v = get_path(cfg, cam)
        if v is not None:
            atual = float(v)
            break
    if atual is None:
        return False, None, f"{param} nao encontrado no config"
    novo = round(atual + float(W["passo"]), 4)
    novo = max(float(W["min"]), min(float(W["max"]), novo))
    if abs(novo - atual) < 1e-9:
        return False, atual, f"{param} ja esta no limite ({atual})"
    for cam in W["caminhos"]:
        set_path(cfg, cam, novo)
    salvar_config_robo(cfg)
    log.info(f"AJUSTE APLICADO: {param} {atual} -> {novo} | motivo: {motivo}")
    return True, (atual, novo), f"{param} {atual} -> {novo}"


def rollback_config(param, valor_antigo):
    W = CFG["whitelist"].get(param)
    if not W:
        return
    cfg = carregar_config_robo()
    for cam in W["caminhos"]:
        set_path(cfg, cam, valor_antigo)
    salvar_config_robo(cfg)
    log.warning(f"ROLLBACK: {param} restaurado para {valor_antigo}")


# ------------------------------------------------------------------ rotinas -
def smoke_test():
    ok, msg = health_check(R["smoke_test_s"])
    if not ok:
        return False, msg
    try:
        cfg = carregar_config_robo()
        if int(cfg.get("sl_points", 0)) == 0:
            return False, "config suspeita (sl_points=0)"
    except Exception as e:
        return False, f"config invalida: {e}"
    return True, "smoke OK"


def run_pausa():
    log.info("=" * 60)
    log.info("PAUSA 12:30 - analise e decisao autonoma")
    if not dentro_da_janela_autonomia():
        log.warning(f"FORA DA JANELA DE AUTONOMIA ({R['janela_inicio']}-{R['janela_fim']}) "
                    f"- abortando SEM nenhuma acao")
        return
    stats = parse_decisions()
    counts, last = parse_vetos_log()
    param, motivo = decidir(stats, counts, last)

    if param is None:
        log.info(f"DECISAO: SEM AJUSTE. {motivo}")
        if not pids_robo():
            log.info("robo estava parado - reiniciando para a tarde")
            start_mt5()
            start_robot()
            ok, m = health_check(R["health_timeout_s"])
            log.info(f"health pos-restart: {ok} ({m})")
        else:
            log.info("robo segue rodando (sem necessidade de restart)")
        return

    permitido, um = pode_ajustar()
    if not permitido:
        log.warning(f"TRAVA 1 AJUSTE/DIA: ja houve mudanca hoje {um} - mantendo config intacta")
        return

    log.info(f"DECISAO: AJUSTAR {param}. {motivo}")
    if not parar_robo():
        log.error("NAO consegui parar o robo - abortando ajuste por seguranca")
        return
    ok, valores, msg = aplicar_ajuste(param, motivo)
    if not ok:
        log.warning(f"ajuste nao aplicado: {msg} - reiniciando robo sem mudanca")
        start_mt5()
        start_robot()
        health_check(R["health_timeout_s"])
        return

    registrar_mudanca(param, valores[0], valores[1], motivo)

    start_mt5()
    start_robot()
    ok, m = smoke_test()
    if ok:
        log.info(f"AJUSTE VALIDADO ({msg}) - robo operacional para a tarde")
    else:
        log.error(f"SMOKE TEST FALHOU ({m}) - rollback de {param}")
        parar_robo()
        rollback_config(param, valores[0])
        registrar_mudanca(param, valores[1], valores[0], f"rollback apos smoke falho: {m}",
                          tipo="rollback")
        start_mt5()
        start_robot()
        ok2, m2 = health_check(R["health_timeout_s"])
        log.info(f"apos rollback, robo: {ok2} ({m2})")


def verificar_mudanca_codigo():
    """Detecta alteracoes ESTRUTURAIS no codigo-fonte vs ultima versao conhecida.
    Gera diff unificado em Python puro (difflib) e salva diff_estrutural_YYYYMMDD.txt.
    Fase 1: apenas REPORTADA - o agente NUNCA altera o .py de producao sozinho."""
    from difflib import unified_diff
    robo = os.path.join(BASE_DIR, P["robo_script"])
    snap = os.path.join(BASE_DIR, "agente_snapshot_v22.py")
    if not os.path.exists(robo):
        return None
    try:
        atual = open(robo, encoding="utf-8-sig").read()
    except Exception as e:
        log.error(f"erro ao ler fonte p/ diff: {e}")
        return None
    if not os.path.exists(snap):
        try:
            with open(snap, "w", encoding="utf-8") as f:
                f.write(atual)
        except Exception as e:
            log.error(f"erro ao criar snapshot inicial: {e}")
        return None
    try:
        anterior = open(snap, encoding="utf-8-sig").read()
    except Exception as e:
        log.error(f"erro ao ler snapshot: {e}")
        return None
    if anterior == atual:
        return None
    diff = "\n".join(unified_diff(
        anterior.splitlines(), atual.splitlines(),
        fromfile="monstro_unificado_v22.py (ultima execucao)",
        tofile="monstro_unificado_v22.py (atual)", lineterm=""))
    if not diff.strip():
        return None
    nome = os.path.join(BASE_DIR, f"diff_estrutural_{datetime.now():%Y%m%d}.txt")
    try:
        with open(nome, "w", encoding="utf-8") as f:
            f.write(diff)
        with open(snap, "w", encoding="utf-8") as f:
            f.write(atual)
    except Exception as e:
        log.error(f"erro ao salvar diff/snapshot: {e}")
        return None
    add = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    rem = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"nome": os.path.basename(nome), "add": add, "rem": rem}


def run_fecho():
    log.info("=" * 60)
    log.info("FECHO 17:35 - autopsia e consolidacao do dia")
    # 1) Sinaliza parada IMEDIATAMENTE: robo encerra em paralelo (se o fecho
    #    for abortado, o robo ainda para sozinho).
    sinalizar_parada_robo()
    # 2) Artefatos do dia gerados cedo -> sobrevivem mesmo se o processo for
    #    morto (ex: abort 0x8007042B no pregao 06/08).
    info_diff = verificar_mudanca_codigo()
    if info_diff:
        log.info(f"MUDANCA ESTRUTURAL detectada no fonte: +{info_diff['add']}/-{info_diff['rem']} "
                 f"(diff em {info_diff['nome']})")
    else:
        log.info("codigo-fonte inalterado desde a ultima execucao")
    gerar_relatorio_diario(info_diff)
    autopsia_eod = CFG.get("autopsia_eod", {})
    if autopsia_eod.get("ativo", True):
        gerar_plano_dia_seguinte()
    git_commit_dia()
    # 3) Por ultimo: aguarda o robo encerrar e fecha o MT5.
    parar_robo()
    log.info("FECHO concluido - ambiente pronto para amanha")


def gerar_plano_dia_seguinte():
    """Pilar 2 - roda autopsia EOD e salva plano do dia seguinte (somente leitura).
    Nunca aplica acao automatica; o arquivo e consulta humana para o proximo dia."""
    try:
        sys.path.insert(0, BASE_DIR)
        from tools.autopsia_automatizada import run_autopsia
        metricas, plano, _trades = run_autopsia()
        data = datetime.now().strftime("%Y%m%d")
        plano_path = os.path.join(BASE_DIR, f"plano_{data}.txt")
        with open(plano_path, "w", encoding="utf-8") as f:
            f.write(plano)
        log.info(f"plano do dia seguinte salvo: {plano_path}")
        print(plano)
    except Exception as e:
        log.error(f"autopsia EOD falhou: {e}")


def gerar_relatorio_diario(info_diff=None):
    stats = parse_decisions()
    counts, last = parse_vetos_log()
    w = winpct_historico()
    data = datetime.now().strftime("%Y%m%d")
    linhas = []
    linhas.append("=" * 66)
    linhas.append(f"RELATORIO DIARIO MONSTRO - {datetime.now():%d/%m/%Y}")
    linhas.append("=" * 66)
    linhas.append(f"Decisoes hoje: {stats.get('n_decisoes', 0)} | Sinais BUY/SELL: {stats.get('sinais', 0)} | Trades executados: {contar_executados_hoje()}")
    linhas.append(f"win% (historico reward!=0): {w if w is not None else 'sem amostra'}")
    linhas.append(f"Entropia med: {stats.get('entropia_med')} | ATR med: {stats.get('atr_med')} | Spread med: {stats.get('spread_med')}")
    linhas.append(f"Book ratio med: {stats.get('book_ratio_med')}")
    linhas.append("")
    linhas.append("MAPA DE VETOS (bloqueios do dia):")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        if v:
            linhas.append(f"  {k:<18} {v}")
    if not any(counts.values()):
        linhas.append("  (nenhum veto registrado)")
    linhas.append("")
    cfg = carregar_config_robo()
    linhas.append("PARAMETROS ATUAIS (whitelist):")
    for p_name, W in CFG["whitelist"].items():
        v = get_path(cfg, W["caminhos"][0])
        linhas.append(f"  {p_name:<18} = {v}   (limites {W['min']}..{W['max']})")
    linhas.append("")
    st = carregar_estado()
    um = st.get("ultima_mudanca")
    if um:
        linhas.append("ULTIMA MUDANCA REGISTRADA (trava 1 ajuste/dia):")
        linhas.append(f"  {um['data']} {um['hora']} {um['tipo']}: {um['param']} {um['de']} -> {um['para']}")
        linhas.append(f"  motivo: {um['motivo']}")
        linhas.append("")
    if info_diff:
        linhas.append("MUDANCA ESTRUTURAL DETECTADA NO FONTE:")
        linhas.append(f"  +{info_diff['add']} / -{info_diff['rem']} linhas")
        linhas.append(f"  diff completo: {info_diff['nome']}")
        linhas.append("")
    linhas.append("Nota: alteracoes estruturais de codigo ficam como PROPOSTA p/ revisao humana (Fase 1).")
    texto = "\n".join(linhas)
    nome = os.path.join(BASE_DIR, f"relatorio_diario_{data}.txt")
    with open(nome, "w", encoding="utf-8") as f:
        f.write(texto)
    log.info(f"relatorio salvo: {nome}")
    print(texto)


def git_commit_dia():
    try:
        subprocess.run(["git", "-C", BASE_DIR, "add", "-A"], capture_output=True, timeout=60)
        msg = f"fecho autonomo {datetime.now():%Y-%m-%d} (agente Fase 1)"
        subprocess.run(["git", "-C", BASE_DIR, "commit", "-m", msg], capture_output=True, timeout=60)
        subprocess.run(["git", "-C", BASE_DIR, "push"], capture_output=True, timeout=120)
        log.info("git commit+push do dia concluido")
    except Exception as e:
        log.error(f"git commit falhou: {e}")


def dentro_do_expediente():
    """Seg-Sex dentro de [h_ini, h_fim] configurados em rotinas (padrao 09:00-17:40)."""
    if datetime.now().weekday() >= 5:
        return False
    h_ini, h_fim = R.get("expediente_inicio", "09:00"), R.get("expediente_fim", "17:40")
    hora_atual = datetime.now().strftime("%H:%M")
    return h_ini <= hora_atual <= h_fim


# ------------------------------------------------------------ kill switch -----
RE_DEAL_SAIDA = re.compile(r"Deal de sa.da encontrado.*?Lucro=(-?\d+\.?\d*)")


def calcular_loss_acumulado_hoje():
    """Soma os Lucro= dos Deals de saida reais do log para o dia atual.
    Conta SOMENTE 'Deal de saida encontrado' (nao 'Experiencia salva' nem
    'Resultado confluencia', que triplicariam o valor)."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    if not os.path.exists(LOG_ROBO):
        return 0.0
    try:
        with open(LOG_ROBO, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.startswith(hoje):
                    continue
                m = RE_DEAL_SAIDA.search(line)
                if m:
                    total += float(m.group(1))
    except Exception as e:
        log.error(f"erro ao calcular loss acumulado: {e}")
    return total


def kill_switch_ja_ativado():
    st = carregar_estado()
    return st.get("kill_switch_ativado", {}).get(datetime.now().strftime("%Y-%m-%d"), False)


def marcar_kill_switch_ativado():
    st = carregar_estado()
    st.setdefault("kill_switch_ativado", {})[datetime.now().strftime("%Y-%m-%d")] = True
    salvar_estado(st)


def verificar_kill_switch():
    """Pilar 1 - protege o capital: se loss diario cruza limite_1 cria parar.txt;
    se cruza limite_2 para o robo + MT5. Ativacao unica por dia. Retorna True se parou."""
    ks = CFG.get("kill_switch", {})
    if not ks.get("ativo", False):
        return False
    if kill_switch_ja_ativado():
        log.info("kill-switch: ja ativado hoje - sem nova acao")
        return False

    loss_hoje = calcular_loss_acumulado_hoje()
    limite_1 = float(ks.get("limite_1", -250))
    limite_2 = float(ks.get("limite_2", -400))
    cfg_robo = carregar_config_robo()
    max_loss = float(get_path(cfg_robo, "risk_management.max_loss_diario") or
                     cfg_robo.get("max_loss_diario", -500))
    if limite_2 < max_loss:
        limite_2 = max_loss * 0.8

    if loss_hoje <= limite_2:
        log.error(f"KILL-SWITCH NIVEL 2: loss {loss_hoje:.2f} <= {limite_2:.2f}. Parando robo e MT5.")
        marcar_kill_switch_ativado()
        parar_robo()
        stop_mt5()
        return True
    elif loss_hoje <= limite_1:
        log.warning(f"KILL-SWITCH NIVEL 1: loss {loss_hoje:.2f} <= {limite_1:.2f}. Criando parar.txt.")
        try:
            if not os.path.exists(PARAR):
                with open(PARAR, "w", encoding="utf-8") as f:
                    f.write(f"KILL-SWITCH LOSS DIARIO: {loss_hoje:.2f}")
        except Exception as e:
            log.error(f"falha ao criar parar.txt: {e}")
    else:
        log.info(f"kill-switch: loss hoje {loss_hoje:.2f} (limites {limite_1:.0f}/{limite_2:.0f}) - ok")
    return False


def run_watchdog():
    if not dentro_do_expediente():
        log.info("watchdog: fora do expediente (seg-sex 09:00-17:40) - sem acao")
        return
    if verificar_kill_switch():
        log.warning("watchdog: kill-switch parou o robo - abortando ciclo")
        return
    if not pids_robo():
        log.warning("watchdog: robo caido - reiniciando")
        start_mt5()
        start_robot()
        ok, m = health_check(R["health_timeout_s"])
        log.info(f"watchdog restart: {ok} ({m})")
    else:
        ok, m = health_check(10)
        log.info(f"watchdog: robo vivo ({m})")


def dryrun():
    stats = parse_decisions()
    counts, last = parse_vetos_log()
    print("=" * 60)
    print("DRY-RUN - analise (sem mexer em nada)")
    print("=" * 60)
    print("stats:", stats)
    print("sinais hoje:", stats.get("sinais"), "| executados hoje:", contar_executados_hoje())
    print("vetos:", counts)
    print("ultima ocorrencia de cada veto:", {k: v for k, v in last.items() if v})
    param, motivo = decidir(stats, counts, last)
    print(f"\nDECISAO: parametro={param} | {motivo}")
    if param:
        W = CFG["whitelist"][param]
        cfg = carregar_config_robo()
        atual = get_path(cfg, W["caminhos"][0])
        novo = max(W["min"], min(W["max"], round(float(atual) + float(W["passo"]), 4)))
        print(f"SIMULACAO: {param} {atual} -> {novo} (limites {W['min']}..{W['max']})")


def main():
    modo = sys.argv[1].lower() if len(sys.argv) > 1 else "dryrun"
    log.info(f"### agente iniciado no modo: {modo}")
    if modo == "pausa":
        run_pausa()
    elif modo == "fecho":
        run_fecho()
    elif modo == "watchdog":
        if not R.get("watchdog_enabled"):
            log.info("watchdog desabilitado no config (watchdog_enabled=false) - abortando")
            return
        run_watchdog()
    elif modo == "dryrun":
        dryrun()
    else:
        print(f"modo desconhecido: {modo}. Use pausa|fecho|watchdog|dryrun")


if __name__ == "__main__":
    main()
