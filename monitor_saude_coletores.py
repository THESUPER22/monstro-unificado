# -*- coding: utf-8 -*-
"""monitor_saude_coletores.py — VIGIA os coletores do Monstro (read-only).

Checa, durante o pregao (seg-sex 09:00-17:55):
  1. MetaTrader 5 (terminal64) vivo
  2. Coletor Herman vivo + heartbeat fresco (< 5 min)
  3. Coletor Herman CRESCENDO boxes (alerta se travar 25 min / critico 45 min)
  4. Integridade do boxes_herman.csv (cabecalho de 26 colunas + linhas alinhadas)
     -> este e' exatamente o bug que fez o backtest ler 0 boxes por 19 dias
  5. Robo principal (monstro_unificado_v22.py) vivo
  6. Rompimento FT (paper) rodando quando a tarefa agendada existe

Saidas:
  logs/saude_coletores.json   (ultimo retrato, para dashboard)
  logs/saude_coletores.log    (historico append-only)
  logs/ALERTA_COLETORES.txt   (existe enquanto houver problema)
  notificacao do Windows (toast) em WARN/CRIT, com cooldown

Uso:
  python monitor_saude_coletores.py [--no-notify] [--quiet]

Exit code: 0 = OK | 1 = WARN | 2 = CRIT
"""
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

BASE = r"C:\AIOFEN"
LOG_DIR = os.path.join(BASE, "logs")
HERMAN_DIR = os.path.join(LOG_DIR, "herman_6p")
FT_DIR = os.path.join(LOG_DIR, "rompimento_ft")
OUT_JSON = os.path.join(LOG_DIR, "saude_coletores.json")
OUT_LOG = os.path.join(LOG_DIR, "saude_coletores.log")
STATE = os.path.join(LOG_DIR, "saude_coletores_state.json")
ALERTA = os.path.join(LOG_DIR, "ALERTA_COLETORES.txt")

HEARTBEAT_LOG = os.path.join(HERMAN_DIR, "online_herman.log")
RESUMO_JSON = os.path.join(HERMAN_DIR, "resumo_herman.json")
BOXES_CSV = os.path.join(HERMAN_DIR, "boxes_herman.csv")
FT_STATE = os.path.join(FT_DIR, "state.json")
FT_ATIVO_DESDE = os.path.join(FT_DIR, "ativo_desde.txt")
ORB_DIR = os.path.join(LOG_DIR, "rompimento_orb_wdo")
ORB_STATE = os.path.join(ORB_DIR, "state.json")
ORB_ATIVO_DESDE = os.path.join(ORB_DIR, "ativo_desde.txt")

# Limiares (minutos)
HEARTBEAT_MAX_MIN = 5
GROWTH_WARN_MIN = 30
GROWTH_CRIT_MIN = 50
FT_STATE_MAX_MIN = 10
NOTIFY_COOLDOWN_MIN = 20
# Janela de pregao (hora local da maquina)
PREGAO_INI = (9, 0)
# 17:35 = horario da tarefa Monstro-Fecho; depois disso o robo ja encerrou de
# proposito e nao deve ser cobrado como "fora do ar".
PREGAO_FIM = (17, 35)

BOX_H = ["box_pts", "ts", "day", "open", "high", "low", "close", "direction",
         "range", "pavio_sup", "pavio_inf", "ratio_sup", "ratio_inf",
         "tick_volume", "n_ticks", "vwap", "ajuste", "ema9", "ema21",
         "K", "bias", "sinal", "entry", "sl", "tp_parcial", "tp_final"]


def agora():
    return datetime.now()


def em_pregao(now):
    if now.weekday() >= 5:
        return False
    hm = (now.hour, now.minute)
    return PREGAO_INI <= hm <= PREGAO_FIM


def _proc_matches(substr, so_python=False):
    """Processos cujo cmdline contem substr (case-insensitive)."""
    out = []
    try:
        import psutil
    except Exception:
        return out
    alvo = substr.lower()
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if so_python and not (p.info.get("name") or "").lower().startswith("python"):
                continue
            cl = p.info.get("cmdline") or []
            if any(alvo in (c or "").lower() for c in cl):
                out.append({"pid": p.info["pid"],
                            "name": p.info.get("name"),
                            "create_time": p.info.get("create_time")})
        except Exception:
            continue
    return out


def _proc_name(name):
    out = []
    try:
        import psutil
    except Exception:
        return out
    alvo = name.lower()
    if alvo.endswith(".exe"):
        alvo = alvo[:-4]
    for p in psutil.process_iter(["pid", "name"]):
        try:
            nm = (p.info.get("name") or "").lower()
            if nm.endswith(".exe"):
                nm = nm[:-4]
            if nm == alvo:
                out.append(p.info["pid"])
        except Exception:
            continue
    return out


def _ler_ultima_linha(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 4096))
            data = f.read().decode("utf-8", "replace")
        linhas = [l.strip() for l in data.splitlines() if l.strip()]
        return linhas[-1] if linhas else None
    except Exception:
        return None


def _idade_heartbeat_min(now):
    linha = _ler_ultima_linha(HEARTBEAT_LOG)
    if not linha:
        return None, None
    try:
        ts = datetime.strptime(linha.split("|")[0].strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None, linha
    return max(0.0, (now - ts).total_seconds() / 60.0), linha


def _csv_stats(hoje_str):
    """(header_ok, malformadas, total_hoje, por_track, ultimo_ts, erro)"""
    if not os.path.exists(BOXES_CSV):
        return False, 0, 0, {}, None, "arquivo nao existe"
    try:
        with open(BOXES_CSV, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
    except Exception as e:
        return False, 0, 0, {}, None, "falha ao ler: %s" % e
    if not rows:
        return False, 0, 0, {}, None, "arquivo vazio"
    header = rows[0]
    header_ok = (header == BOX_H)
    malformadas = sum(1 for r in rows[1:] if len(r) != len(header))
    por_track = {}
    total_hoje = 0
    ultimo_ts = None
    for r in rows[1:]:
        if len(r) != len(header):
            continue
        try:
            if r[2] == hoje_str:
                por_track[r[0]] = por_track.get(r[0], 0) + 1
                total_hoje += 1
                try:
                    ts = datetime.strptime(r[1].strip(), "%Y-%m-%d %H:%M:%S")
                    if ultimo_ts is None or ts > ultimo_ts:
                        ultimo_ts = ts
                except Exception:
                    pass
        except Exception:
            continue
    return header_ok, malformadas, total_hoje, por_track, ultimo_ts, None


def _carregar_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_json(path, obj):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        pass


def _notificar(titulo, msg):
    """Toast do Windows, best-effort. Nunca quebra o monitor."""
    try:
        import winsound
        winsound.MessageBeep()
    except Exception:
        pass
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
        "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        "$x = $t.GetXml(); $tx = $x.GetElementsByTagName('text'); "
        "$tx.Item(0).AppendChild($x.CreateTextNode($env:ALERT_TITLE)) > $null; "
        "$tx.Item(1).AppendChild($x.CreateTextNode($env:ALERT_MSG)) > $null; "
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($t); "
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:ALERT_APP).Show($toast)"
    )
    env = os.environ.copy()
    env["ALERT_TITLE"] = titulo[:64]
    env["ALERT_MSG"] = msg[:250]
    env["ALERT_APP"] = ("{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
                        "\\WindowsPowerShell\\v1.0\\powershell.exe")
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-WindowStyle", "Hidden", "-Command", ps],
                       env=env, capture_output=True, timeout=25)
    except Exception:
        pass


def _task_existe(nome):
    """True se a tarefa existe E esta habilitada.

    `schtasks /query` retorna 0 tambem para tarefa DESABILITADA; por isso
    conferimos o State via Get-ScheduledTask. Se o PowerShell falhar, cai no
    fallback `schtasks /query /fo LIST /v` (campo Status/State). Se nada puder
    ser lido, assume DESABILITADA (fail-closed): tarefa aposentada nao pode
    gerar falso CRIT so porque o estado ficou ilegivel.
    """
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", nome],
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return False
    except Exception:
        return False

    # 1) caminho preferido: Get-ScheduledTask (State em ingles: Ready/Running/Disabled)
    try:
        q = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue).State" % nome],
            capture_output=True, text=True, timeout=20)
        state = (q.stdout or "").strip()
        if state:
            return state.lower() != "disabled"
    except Exception:
        pass

    # 2) fallback: schtasks /fo LIST /v -> "Status: Desabilitado" (PT-BR) ou
    #    "Scheduled Task State: Disabled" (EN). Evita fail-open no locale atual.
    try:
        q = subprocess.run(["schtasks", "/query", "/tn", nome, "/fo", "LIST", "/v"],
                           capture_output=True, text=True, timeout=20)
        for linha in (q.stdout or "").splitlines():
            chave, _, valor = linha.partition(":")
            chave = chave.strip().lower()
            valor = valor.strip().lower()
            if not valor:
                continue
            if "task state" in chave or chave.startswith("status") or "situa" in chave:
                return not ("desabilit" in valor or "disabled" in valor)
    except Exception:
        pass

    # 3) estado ilegivel: fail-closed -> INFO, nunca CRIT falso.
    return False


def _ft_ativo_desde():
    """Data a partir da qual o FT deve ser cobrado (evita alerta no dia da ativacao)."""
    return _ativo_desde(FT_ATIVO_DESDE)


def _ativo_desde(path):
    try:
        with open(path, encoding="utf-8") as f:
            return datetime.strptime(f.read().strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _growth_limits(now):
    """Limiares (WARN, CRIT) em minutos. No almoco a volatilidade cai e um box de
    3 pts demora mais naturalmente, entao afrouxamos para nao gerar falso positivo."""
    hm = (now.hour, now.minute)
    if (12, 0) <= hm < (14, 0):
        return 45, 75
    return GROWTH_WARN_MIN, GROWTH_CRIT_MIN


def main():
    no_notify = "--no-notify" in sys.argv
    quiet = "--quiet" in sys.argv
    now = agora()
    hoje_str = now.date().isoformat()
    pregao = em_pregao(now)
    # Grace de abertura: as tarefas disparam 09:00 e os processos levam alguns
    # minutos para subir. Ate 09:10, ausencia de processo/heartbeat e' WARN.
    abertura_estavel = (now.hour, now.minute) >= (9, 10)
    crit_pregao = pregao and abertura_estavel
    warn_pregao = pregao and not abertura_estavel
    st_antigo = _carregar_state()
    checks = []
    metrics = {}

    def add(nome, nivel, detalhe):
        checks.append({"check": nome, "level": nivel, "detail": detalhe})

    # 0) meta
    add("contexto", "INFO",
        "pregao=%s | %s" % (pregao, now.strftime("%Y-%m-%d %H:%M:%S")))

    # 1) MT5
    term = _proc_name("terminal64")
    metrics["mt5_pids"] = term
    if term:
        add("mt5", "OK", "terminal64 vivo (pid %s)" % ",".join(map(str, term)))
    else:
        add("mt5", "CRIT" if crit_pregao else ("WARN" if warn_pregao else "INFO"),
            "terminal64 NAO esta rodando")

    # 2) Coletor Herman — processo
    col = _proc_matches("coletor_herman_6p_shadow.py", so_python=True)
    metrics["herman_pids"] = [c["pid"] for c in col]
    if col:
        add("herman_processo", "OK", "coletor vivo (%d processo(s))" % len(col))
        if len(col) > 2:
            add("herman_duplicado", "WARN",
                "%d processos do coletor (esperado 2: wrapper+filho) - possivel duplicata"
                % len(col))
    else:
        add("herman_processo", "CRIT" if crit_pregao else ("WARN" if warn_pregao else "INFO"),
            "coletor Herman NAO esta rodando")

    # 3) Heartbeat
    idade_hb, ultima = _idade_heartbeat_min(now)
    metrics["herman_heartbeat_min"] = None if idade_hb is None else round(idade_hb, 1)
    if idade_hb is None:
        add("herman_heartbeat", "CRIT" if crit_pregao else ("WARN" if warn_pregao else "INFO"),
            "sem heartbeat legivel em online_herman.log")
    elif idade_hb > HEARTBEAT_MAX_MIN:
        add("herman_heartbeat", "CRIT" if crit_pregao else ("WARN" if warn_pregao else "INFO"),
            "heartbeat parado ha %.0f min (limite %d)" % (idade_hb, HEARTBEAT_MAX_MIN))
    else:
        add("herman_heartbeat", "OK", "heartbeat ha %.1f min" % idade_hb)

    # 4) Integridade do CSV (o bug que zerou o backtest)
    h_ok, malformadas, total_hoje, por_track, ultimo_box_ts, err = _csv_stats(hoje_str)
    metrics["boxes_hoje"] = total_hoje
    metrics["boxes_por_track"] = por_track
    metrics["csv_malformadas"] = malformadas
    if err:
        add("herman_csv", "CRIT" if pregao else "INFO", "CSV: %s" % err)
    else:
        if not h_ok:
            add("herman_csv", "CRIT",
                "cabecalho do boxes_herman.csv NAO bate com o layout de %d colunas "
                "(risco de backtest ler 0 boxes)" % len(BOX_H))
        elif malformadas:
            add("herman_csv", "CRIT",
                "%d linha(s) com numero de colunas errado no CSV" % malformadas)
        else:
            add("herman_csv", "OK",
                "cabecalho ok | %d boxes hoje (3P=%d, 6P=%d)" %
                (total_hoje, por_track.get("3", 0), por_track.get("6", 0)))

    # 5) Crescimento de boxes (com estado persistido)
    ant_total = st_antigo.get("box_total")
    ant_change = st_antigo.get("box_change_ts")
    if st_antigo.get("day") != hoje_str:
        # primeiro run do dia: zera a referencia
        ant_total = None
        ant_change = None
    if ant_total is None or total_hoje > ant_total or total_hoje < ant_total:
        # primeiro run do dia, box novo OU CSV rotacionado/reiniciado -> reancora
        # no horario REAL do ultimo box (nao no horario em que o monitor rodou)
        change_dt = ultimo_box_ts or now
        if change_dt > now:
            change_dt = now
    else:
        # sem crescimento desde a ultima referencia: preserva o instante do ultimo box
        try:
            change_dt = datetime.fromisoformat(ant_change) if ant_change else now
        except Exception:
            change_dt = now
    parado_min = (now - change_dt).total_seconds() / 60.0
    metrics["box_parado_min"] = round(parado_min, 1)
    if pregao and now.hour >= 9 and (now.hour, now.minute) >= (9, 20):
        warn_min, crit_min = _growth_limits(now)
        if parado_min > crit_min:
            add("herman_crescimento", "CRIT",
                "sem novo box ha %.0f min (critico >%d)" % (parado_min, crit_min))
        elif parado_min > warn_min:
            add("herman_crescimento", "WARN",
                "sem novo box ha %.0f min (alerta >%d)" % (parado_min, warn_min))
        else:
            add("herman_crescimento", "OK",
                "ultimo box ha %.0f min | total hoje=%d" % (parado_min, total_hoje))
    else:
        add("herman_crescimento", "INFO",
            "fora do pregao/abertura - crescimento nao avaliado")

    # 6) Resumo JSON coerente
    try:
        with open(RESUMO_JSON, encoding="utf-8") as f:
            resumo = json.load(f)
        metrics["resumo_day"] = resumo.get("day")
        if pregao and resumo.get("day") != hoje_str:
            add("herman_resumo", "WARN",
                "resumo_herman.json ainda e' de %s" % resumo.get("day"))
        else:
            add("herman_resumo", "OK",
                "resumo day=%s boxes_3P=%s boxes_6P=%s" %
                (resumo.get("day"), resumo.get("boxes_3P"), resumo.get("boxes_6P")))
    except Exception:
        add("herman_resumo", "WARN", "resumo_herman.json ausente/ilegivel")

    # 7) Robo principal
    robo = _proc_matches("monstro_unificado_v22.py", so_python=True)
    metrics["robo_pids"] = [r["pid"] for r in robo]
    if robo:
        add("robo_principal", "OK", "monstro vivo (%d processo(s))" % len(robo))
    else:
        add("robo_principal", "CRIT" if crit_pregao else ("WARN" if warn_pregao else "INFO"),
            "monstro_unificado_v22.py NAO esta rodando")

    # 8) Rompimento FT (paper)
    ft = _proc_matches("rompimento_ft.py", so_python=True)
    ft_task = _task_existe("Rompimento-FT")
    ft_ativo = _ft_ativo_desde()
    ft_vigente = bool(ft_ativo and now.date() >= ft_ativo)
    metrics["ft_pids"] = [p["pid"] for p in ft]
    metrics["ft_task"] = ft_task
    metrics["ft_ativo_desde"] = ft_ativo.isoformat() if ft_ativo else None
    ft_state = {}
    try:
        with open(FT_STATE, encoding="utf-8") as f:
            ft_state = json.load(f)
        metrics["ft_state_day"] = ft_state.get("dia")
        metrics["ft_final"] = ft_state.get("final")
    except Exception:
        pass
    if ft:
        idade_ft = (now.timestamp() - os.path.getmtime(FT_STATE)) / 60.0 if os.path.exists(FT_STATE) else None
        if idade_ft is not None and idade_ft > FT_STATE_MAX_MIN:
            add("rompimento_ft", "WARN",
                "FT vivo mas state.json sem atualizar ha %.0f min" % idade_ft)
        else:
            add("rompimento_ft", "OK", "FT paper vivo")
    elif ft_task and ft_vigente and pregao and (now.hour, now.minute) >= (9, 10) and now.hour < 19:
        if ft_state.get("dia") == hoje_str and ft_state.get("final"):
            add("rompimento_ft", "OK", "FT finalizado hoje (%s)" % ft_state.get("saida"))
        else:
            add("rompimento_ft", "CRIT",
                "tarefa Rompimento-FT existe mas o robo NAO esta rodando")
    elif ft_task and not ft_vigente:
        add("rompimento_ft", "INFO",
            "FT agendado para comecar em %s (hoje ainda nao e' cobrado)"
            % (ft_ativo.isoformat() if ft_ativo else "-"))
    elif ft_task:
        add("rompimento_ft", "INFO", "tarefa Rompimento-FT agendada (fora da janela)")
    else:
        add("rompimento_ft", "INFO", "FT nao agendado/ativo")

    # 9) ORB WDO FT (paper, 3 saidas em paralelo)
    orb = _proc_matches("rompimento_orb_wdo.py", so_python=True)
    orb_task = _task_existe("ORB-WDO-FT")
    orb_ativo = _ativo_desde(ORB_ATIVO_DESDE)
    orb_vigente = bool(orb_ativo and now.date() >= orb_ativo)
    metrics["orb_pids"] = [p["pid"] for p in orb]
    metrics["orb_task"] = orb_task
    metrics["orb_ativo_desde"] = orb_ativo.isoformat() if orb_ativo else None
    orb_state = {}
    try:
        with open(ORB_STATE, encoding="utf-8") as f:
            orb_state = json.load(f)
        metrics["orb_state_day"] = orb_state.get("dia")
        metrics["orb_final"] = orb_state.get("final")
        metrics["orb_fase"] = orb_state.get("fase")
    except Exception:
        pass
    if orb:
        idade_orb = ((now.timestamp() - os.path.getmtime(ORB_STATE)) / 60.0
                     if os.path.exists(ORB_STATE) else None)
        if idade_orb is not None and idade_orb > FT_STATE_MAX_MIN:
            add("orb_wdo_ft", "WARN",
                "ORB FT vivo mas state.json sem atualizar ha %.0f min" % idade_orb)
        else:
            add("orb_wdo_ft", "OK", "ORB WDO paper vivo (%s)" % (orb_state.get("fase") or "-"))
    elif (orb_task and orb_vigente and pregao
          and (now.hour, now.minute) >= (10, 20) and now.hour < 19):
        if orb_state.get("dia") == hoje_str and orb_state.get("final"):
            add("orb_wdo_ft", "OK", "ORB WDO finalizado hoje")
        else:
            add("orb_wdo_ft", "CRIT",
                "tarefa ORB-WDO-FT existe mas o robo NAO esta rodando")
    elif orb_task and not orb_vigente:
        add("orb_wdo_ft", "INFO",
            "ORB WDO agendado para comecar em %s (hoje ainda nao e' cobrado)"
            % (orb_ativo.isoformat() if orb_ativo else "-"))
    elif orb_task:
        add("orb_wdo_ft", "INFO", "tarefa ORB-WDO-FT agendada (fora da janela)")
    else:
        add("orb_wdo_ft", "INFO", "ORB WDO FT nao agendado/ativo")

    # ---- consolida status ----
    niveis = [c["level"] for c in checks]
    if "CRIT" in niveis:
        status = "CRIT"
    elif "WARN" in niveis:
        status = "WARN"
    else:
        status = "OK"
    problemas = [c for c in checks if c["level"] in ("WARN", "CRIT")]

    retrato = {
        "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "pregao": pregao,
        "checks": checks,
        "metrics": metrics,
    }
    _salvar_json(OUT_JSON, retrato)

    # ---- log append ----
    try:
        with open(OUT_LOG, "a", encoding="utf-8") as f:
            if problemas:
                f.write("%s | %s | %s\n" % (
                    retrato["ts"], status,
                    " ; ".join("[%s] %s" % (p["check"], p["detail"]) for p in problemas)))
            else:
                f.write("%s | OK | boxes_hoje=%s hb=%smin robo=%s ft=%s\n" % (
                    retrato["ts"], total_hoje,
                    metrics.get("herman_heartbeat_min"), len(robo), len(ft)))
    except Exception:
        pass

    # ---- arquivo de alerta visivel ----
    try:
        if problemas:
            with open(ALERTA, "w", encoding="utf-8") as f:
                f.write("ALERTA COLETORES - %s\n\n" % retrato["ts"])
                for p in problemas:
                    f.write("[%s] %s: %s\n" % (p["level"], p["check"], p["detail"]))
        elif os.path.exists(ALERTA):
            os.remove(ALERTA)
    except Exception:
        pass

    # ---- notificacao com cooldown ----
    if problemas and not no_notify:
        ult_notif = st_antigo.get("last_notify_ts")
        pode = True
        if ult_notif:
            try:
                idade = (now - datetime.fromisoformat(ult_notif)).total_seconds() / 60.0
                pode = idade >= NOTIFY_COOLDOWN_MIN
            except Exception:
                pode = True
        if pode:
            titulo = "Monstro: %s nos coletores" % ("CRITICO" if status == "CRIT" else "atencao")
            msg = " | ".join("%s: %s" % (p["check"], p["detail"]) for p in problemas[:3])
            _notificar(titulo, msg)
            st_antigo["last_notify_ts"] = now.isoformat()

    # ---- persiste estado de crescimento ----
    _salvar_json(STATE, {
        "day": hoje_str,
        "box_total": total_hoje,
        "box_change_ts": change_dt.isoformat(),
        "last_notify_ts": st_antigo.get("last_notify_ts"),
        "last_status": status,
        "last_ts": retrato["ts"],
    })

    # ---- console ----
    if not quiet:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        print("=" * 62)
        print("MONITOR COLETORES | %s | %s" % (retrato["ts"], status))
        print("=" * 62)
        for c in checks:
            if c["level"] in ("WARN", "CRIT") or not quiet:
                print("  [%-4s] %-18s %s" % (c["level"], c["check"], c["detail"]))
        print("-" * 62)

    return 2 if status == "CRIT" else (1 if status == "WARN" else 0)


if __name__ == "__main__":
    sys.exit(main())
