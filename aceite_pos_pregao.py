# -*- coding: utf-8 -*-
"""Aceite pos-pregao (READ-ONLY) - imprime os 5 numeros do fecho.

Roda depois do fecho (17:35 BRT) e responde, com numero medido:

  1. linhas com retcode 10016 no log do dia (esperado: 0);
  2. linhas "TETO DE EXECUCAO ESTOURADO" (esperado: 0);
  3. ultimo ``[pnl_dia] MT5`` do log == soma dos deals ATE o horario
     daquela linha (o total do dia e informativo);
  4. ``parado.ok`` presente + "encerrou graciosamente" no agente_autonomo.log;
  5. commits do fecho (mensagem "fecho autonomo AAAA-MM-DD") so com
     arquivos da whitelist.

Nao envia ordem, nao escreve no repo, nao importa o robo. Usa o mesmo
``pnl_de_deals`` do P0 #3. Testes em ``tests/test_aceite_pos_pregao.py``.

Uso:
    python aceite_pos_pregao.py                 # hoje, com MT5
    python aceite_pos_pregao.py --dia 2026-11-18
    python aceite_pos_pregao.py --sem-mt5       # so log/arquivos/git
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
from datetime import date, datetime, time, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from pnl_dia import pnl_de_deals

RE_PNL = re.compile(
    r"^(?P<quando>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
    r".*?\[pnl_dia\] MT5: (?P<deals>\d+) deals, liquido "
    r"(?P<liquido>[+-]?\d+(?:\.\d+)?)"
    r"(?: \(magics \[(?P<magics>[0-9, ]*)\])?",
    re.MULTILINE)
ENTRY_OUT = 1  # mt5.DEAL_ENTRY_OUT


def _ler(caminho: str) -> str:
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def contar_10016(texto: str) -> int:
    """Linhas (nao ocorrencias) com 10016 no log do dia."""
    return sum(1 for linha in texto.splitlines() if "10016" in linha)


def contar_teto(texto: str) -> int:
    return sum(1 for linha in texto.splitlines()
               if "TETO DE EXECUCAO ESTOURADO" in linha)


def ultimo_pnl_mt5(texto: str) -> Optional[dict]:
    """Ultimo ``[pnl_dia] MT5`` do log, com magics e o horario da linha.

    O horario importa: o snapshot vale para os deals que existiam QUANDO
    ele foi logado. Comparar com o dia inteiro foi o defeito medido em
    18/11 (ultimo log 16:58:32 com +5,00; dois deals fecharam depois e o
    dia terminou em +70,00).
    """
    achados = list(RE_PNL.finditer(texto))
    if not achados:
        return None
    m = achados[-1]
    lista = [int(x) for x in re.findall(r"\d+", m.group("magics") or "")]
    return {"deals": int(m.group("deals")),
            "liquido": float(m.group("liquido")),
            "magics": lista or None,
            "quando": datetime.strptime(m.group("quando"),
                                        "%Y-%m-%d %H:%M:%S,%f")}


def encerrou_graciosamente(texto: str, dia: date) -> bool:
    """True se o AGENTE registrou o encerramento NAQUELE dia.

    A mensagem do watchdog ("watchdog: robo encerrou graciosamente...") nao
    conta: ela observa o `parado.ok`, nao confirma que o fecho concluiu.
    Medido em 18/11: as linhas de teste do watchdog fizeram o item 4 passar
    por engano; o criterio tem que ser a mensagem do `parar_gracioso`.
    """
    alvo = dia.isoformat()
    for linha in texto.splitlines():
        if alvo not in linha:
            continue
        partes = linha.split(" - ", 2)
        if len(partes) == 3 and partes[2].startswith("robo encerrou graciosamente"):
            return True
    return False


def _campo(deal, nome: str, padrao=0.0):
    valor = (deal.get(nome, padrao) if isinstance(deal, dict)
             else getattr(deal, nome, padrao))
    return padrao if valor is None else valor


def _quando_do_deal(deal) -> Optional[datetime]:
    """Horario de parede do deal, no mesmo relogio do log.

    ``deal.time`` e o epoch do servidor codificado como UTC; em 18/11 a
    ultima saida (17:23:14) coincidiu com o horario do log. Por isso a
    comparacao usa ``fromtimestamp(ts, UTC)`` sem tzinfo, igual ao
    ``pnl_dia.py``.
    """
    ts = _campo(deal, "time", None)
    if ts is None:
        return None
    return datetime.fromtimestamp(float(ts), timezone.utc).replace(tzinfo=None)


def soma_deals(deals: Iterable, dia: date, magics: Optional[Sequence[int]] = None,
               apenas_saida: bool = False,
               ate: Optional[datetime] = None) -> Tuple[float, int]:
    """Soma (cash flow) dos deals do dia; opcionalmente so as saidas.

    ``ate`` limita aos deals com horario <= ``ate`` (o horario do ultimo
    ``[pnl_dia]``). Sem ``ate``, soma o dia inteiro.
    """
    if apenas_saida:
        deals = [d for d in (deals or ()) if int(_campo(d, "entry", -1)) == ENTRY_OUT]
    if ate is not None:
        deals = [d for d in (deals or ())
                 if _quando_do_deal(d) is None or _quando_do_deal(d) <= ate]
    return pnl_de_deals(deals, dia, magics)


def permitido(caminho: str, padroes: Iterable[str]) -> bool:
    normal = caminho.replace("\\", "/")
    return any(fnmatch.fnmatch(normal, p) for p in padroes or ())


def _git(base: str, args: Sequence[str]) -> str:
    try:
        r = subprocess.run(["git", "-C", base] + list(args),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
        return r.stdout
    except Exception:  # noqa: BLE001
        return ""


def commits_do_fecho(base: str, dia: date,
                     hora: time = time(0, 0)) -> List[str]:
    """SHAs dos commits do fecho, identificados pela MENSAGEM.

    A janela de horario sozinha pegava commit manual (medido em 18/11: 4
    commits / 8 arquivos fora da whitelist). O fecho commita sempre por
    ``commit_dia.mensagem_fecho()`` -> "fecho autonomo AAAA-MM-DD (...)".
    """
    desde = datetime.combine(dia, hora).strftime("%Y-%m-%d %H:%M:%S")
    saida = _git(base, ["log", "--since", desde,
                        "--pretty=format:%H%x09%s"])
    alvo = f"fecho autonomo {dia:%Y-%m-%d}"
    shas: List[str] = []
    for linha in saida.splitlines():
        sha, _, assunto = linha.partition("\t")
        if sha.strip() and assunto.startswith(alvo):
            shas.append(sha.strip())
    return shas


def arquivos_do_commit(base: str, sha: str) -> List[str]:
    saida = _git(base, ["show", "--pretty=format:", "--name-only", sha])
    return [l.strip().replace("\\", "/") for l in saida.splitlines() if l.strip()]


def _whitelist(base: str) -> List[str]:
    try:
        with open(os.path.join(base, "agente_config.json"), encoding="utf-8-sig") as f:
            return list(json.load(f).get("git", {}).get("caminhos_permitidos", []))
    except Exception:  # noqa: BLE001
        return []


def resolver_log(base: str, dia: date) -> Tuple[str, str]:
    """Caminho do log DAQUELE dia e o motivo.

    A rotacao do robo renomeia ``monstro_wdo.log`` para
    ``monstro_wdo_AAAA-MM-DD.log`` somente na INICIALIZACAO seguinte. No dia do
    pregao o arquivo atual ainda e ``monstro_wdo.log``. Procurar so o datado
    faria o aceite ler um arquivo inexistente e reportar 0x10016 falso.

    Ordem: datado (sessao ja rotacionada) -> atual com mtime do dia -> nada.
    """
    datado = os.path.join(base, f"monstro_wdo_{dia:%Y%m%d}.log")
    if os.path.exists(datado):
        return datado, "datado"
    atual = os.path.join(base, "monstro_wdo.log")
    if os.path.exists(atual):
        mtime = datetime.fromtimestamp(os.path.getmtime(atual)).date()
        if mtime == dia:
            return atual, "atual (sessao do dia, ainda nao rotacionado)"
        return "", f"atual e de {mtime.isoformat()}, nao de {dia.isoformat()}"
    return "", "log do dia nao encontrado"


def _deals_mt5(dia: date) -> List:
    try:
        import MetaTrader5 as mt5  # noqa: PLC0415

        if not mt5.initialize():
            return []
        ini = datetime(dia.year, dia.month, dia.day)
        fim = datetime(dia.year, dia.month, dia.day, 23, 59, 59)
        return list(mt5.history_deals_get(ini, fim) or [])
    except Exception:  # noqa: BLE001
        return []


def coletar(base: str, dia: date, deals: Optional[Iterable] = None,
            log_texto: Optional[str] = None,
            agente_texto: Optional[str] = None,
            commit_info: Optional[dict] = None) -> dict:
    """Mede os 5 numeros e devolve o veredito (sem efeito colateral)."""
    log_usado, log_motivo = "", "texto fornecido"
    if log_texto is None:
        log_usado, log_motivo = resolver_log(base, dia)
        log_texto = _ler(log_usado) if log_usado else ""
    if agente_texto is None:
        agente_texto = _ler(os.path.join(base, "agente_autonomo.log"))

    n10016 = contar_10016(log_texto)
    n_teto = contar_teto(log_texto)
    pnl = ultimo_pnl_mt5(log_texto)
    log_encontrado = bool(log_texto)

    if deals is None and pnl is not None:
        deals = _deals_mt5(dia)
    deals = list(deals or ())
    magics = pnl["magics"] if pnl else None
    quando = pnl["quando"] if pnl else None
    soma_saidas, n_saidas = soma_deals(deals, dia, magics, apenas_saida=True)
    soma_todos, n_todos = soma_deals(deals, dia, magics, apenas_saida=False)
    # Invariante do item 3: o snapshot vale para os deals ATE o horario da
    # linha, nao para o dia inteiro (defeito medido em 18/11).
    soma_ate_log, n_ate_log = soma_deals(deals, dia, magics,
                                         apenas_saida=False, ate=quando)
    soma_saidas_ate_log, n_saidas_ate_log = soma_deals(
        deals, dia, magics, apenas_saida=True, ate=quando)
    pnl_igual_log = bool(pnl) and abs(pnl["liquido"] - soma_ate_log) <= 0.01
    pnl_igual_saidas = (bool(pnl)
                        and abs(pnl["liquido"] - soma_saidas_ate_log) <= 0.01)
    pnl_igual_todos = bool(pnl) and abs(pnl["liquido"] - soma_todos) <= 0.01

    parado = os.path.exists(os.path.join(base, "parado.ok"))
    encerrou = encerrou_graciosamente(agente_texto, dia)

    if commit_info is None:
        shas = commits_do_fecho(base, dia)
        arquivos: List[str] = []
        for sha in shas:
            arquivos.extend(arquivos_do_commit(base, sha))
        padroes = _whitelist(base)
        extras = sorted({a for a in arquivos if not permitido(a, padroes)})
        commit_info = {"commits": len(shas), "arquivos": sorted(set(arquivos)),
                       "extras": extras, "ok": bool(shas) and not extras}

    ok = (log_encontrado and n10016 == 0 and n_teto == 0 and pnl_igual_log
          and parado and encerrou and bool(commit_info.get("ok")))
    return {
        "dia": dia.isoformat(),
        "log_usado": log_usado,
        "log_motivo": log_motivo,
        "log_encontrado": log_encontrado,
        "retcode_10016": n10016,
        "teto_estourado": n_teto,
        "pnl_log": pnl,
        "pnl_quando": quando,
        "pnl_soma_ate_log": soma_ate_log,
        "pnl_deals_ate_log": n_ate_log,
        "pnl_soma_saidas_ate_log": soma_saidas_ate_log,
        "pnl_deals_saidas_ate_log": n_saidas_ate_log,
        "pnl_soma_saidas": soma_saidas,
        "pnl_soma_todos": soma_todos,
        "pnl_deals_saidas": n_saidas,
        "pnl_deals_todos": n_todos,
        "pnl_igual_log": pnl_igual_log,
        "pnl_igual_saidas": pnl_igual_saidas,
        "pnl_igual_todos": pnl_igual_todos,
        "parado_ok": parado,
        "encerrou_graciosamente": encerrou,
        "commit_fecho": commit_info,
        "ok": bool(ok),
    }


def imprimir(r: dict) -> None:
    print(f"ACEITE POS-PREGAO {r['dia']}")
    if r.get("log_usado"):
        print(f"  log do dia:                    {r['log_usado']}")
    else:
        print(f"  log do dia:                    AUSENTE ({r.get('log_motivo', '')})")
    print(f"  10016 (esperado 0):            {r['retcode_10016']}")
    print(f"  TETO ESTOURADO (esperado 0):   {r['teto_estourado']}")
    p = r["pnl_log"]
    if p:
        quando = r.get("pnl_quando")
        hora = f", as {quando:%H:%M:%S}" if quando else ""
        print(f"  [pnl_dia] MT5:                 {p['liquido']:+.2f} "
              f"({p['deals']} deals, magics {p['magics']}{hora})")
    else:
        print("  [pnl_dia] MT5:                 ausente no log")
    print(f"  deals ate o [pnl_dia]:         {r['pnl_soma_ate_log']:+.2f} "
          f"({r['pnl_deals_ate_log']} deals) "
          f"{'OK' if r['pnl_igual_log'] else 'DIFERENTE'}")
    print(f"  saidas ate o [pnl_dia]:        {r['pnl_soma_saidas_ate_log']:+.2f} "
          f"({r['pnl_deals_saidas_ate_log']} deals)")
    print(f"  total do dia (informativo):    {r['pnl_soma_todos']:+.2f} "
          f"({r['pnl_deals_todos']} deals)")
    print(f"  parado.ok:                     {'SIM' if r['parado_ok'] else 'NAO'}")
    print(f"  encerrou graciosamente:        "
          f"{'SIM' if r['encerrou_graciosamente'] else 'NAO'}")
    c = r["commit_fecho"]
    print(f"  commits do fecho:              {c.get('commits', 0)} "
          f"({len(c.get('arquivos', []))} arquivos) "
          f"{'OK' if c.get('ok') else 'FALHOU'}")
    if c.get("extras"):
        print(f"    FORA DA WHITELIST:           {c['extras']}")
    print(f"VEREDITO: {'OK' if r['ok'] else 'FALHOU'}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Aceite pos-pregao (read-only)")
    p.add_argument("--base", default=os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--dia", default=date.today().isoformat())
    p.add_argument("--sem-mt5", action="store_true",
                   help="nao consulta deals no MT5 (usa so o log)")
    args = p.parse_args(argv)
    dia = datetime.strptime(args.dia, "%Y-%m-%d").date()
    r = coletar(args.base, dia, deals=[] if args.sem_mt5 else None)
    imprimir(r)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
