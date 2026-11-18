# -*- coding: utf-8 -*-
"""Aceite pos-pregao (READ-ONLY) - imprime os 5 numeros do fecho.

Roda depois do fecho (17:35 BRT) e responde, com numero medido:

  1. linhas com retcode 10016 no log do dia (esperado: 0);
  2. linhas "TETO DE EXECUCAO ESTOURADO" (esperado: 0);
  3. ultimo ``[pnl_dia] MT5`` do log == soma dos deals de saida do dia;
  4. ``parado.ok`` presente + "encerrou graciosamente" no agente_autonomo.log;
  5. commits do fecho (>= 17:30 local) so com arquivos da whitelist.

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
    r"\[pnl_dia\] MT5: (\d+) deals, liquido ([+-]?\d+(?:\.\d+)?)"
    r"(?: \(magics \[([0-9, ]*)\])?")
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
    """Ultimo ``[pnl_dia] MT5`` do log, com magics usados pelo robo."""
    achados = RE_PNL.findall(texto)
    if not achados:
        return None
    n, valor, magics = achados[-1]
    lista = [int(m) for m in re.findall(r"\d+", magics or "")]
    return {"deals": int(n), "liquido": float(valor),
            "magics": lista or None}


def encerrou_graciosamente(texto: str, dia: date) -> bool:
    """True se o agente registrou o encerramento NAQUELE dia."""
    alvo = dia.isoformat()
    return any(alvo in linha and "encerrou graciosamente" in linha
               for linha in texto.splitlines())


def _campo(deal, nome: str, padrao=0.0):
    valor = (deal.get(nome, padrao) if isinstance(deal, dict)
             else getattr(deal, nome, padrao))
    return padrao if valor is None else valor


def soma_deals(deals: Iterable, dia: date, magics: Optional[Sequence[int]] = None,
               apenas_saida: bool = False) -> Tuple[float, int]:
    """Soma (cash flow) dos deals do dia; opcionalmente so as saidas."""
    if apenas_saida:
        deals = [d for d in (deals or ()) if int(_campo(d, "entry", -1)) == ENTRY_OUT]
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
                     hora: time = time(17, 30)) -> List[str]:
    """SHAs de commits desde ``dia hora`` (horario local do agendador)."""
    desde = datetime.combine(dia, hora).strftime("%Y-%m-%d %H:%M:%S")
    ate = datetime.combine(dia, time(23, 59, 59)).strftime("%Y-%m-%d %H:%M:%S")
    saida = _git(base, ["log", "--since", desde, "--until", ate,
                        "--pretty=format:%H"])
    return [l.strip() for l in saida.splitlines() if l.strip()]


def arquivos_do_commit(base: str, sha: str) -> List[str]:
    saida = _git(base, ["show", "--pretty=format:", "--name-only", sha])
    return [l.strip().replace("\\", "/") for l in saida.splitlines() if l.strip()]


def _whitelist(base: str) -> List[str]:
    try:
        with open(os.path.join(base, "agente_config.json"), encoding="utf-8-sig") as f:
            return list(json.load(f).get("git", {}).get("caminhos_permitidos", []))
    except Exception:  # noqa: BLE001
        return []


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
    if log_texto is None:
        log_texto = _ler(os.path.join(base, f"monstro_wdo_{dia:%Y%m%d}.log"))
    if agente_texto is None:
        agente_texto = _ler(os.path.join(base, "agente_autonomo.log"))

    n10016 = contar_10016(log_texto)
    n_teto = contar_teto(log_texto)
    pnl = ultimo_pnl_mt5(log_texto)

    if deals is None and pnl is not None:
        deals = _deals_mt5(dia)
    deals = list(deals or ())
    magics = pnl["magics"] if pnl else None
    soma_saidas, n_saidas = soma_deals(deals, dia, magics, apenas_saida=True)
    soma_todos, n_todos = soma_deals(deals, dia, magics, apenas_saida=False)
    pnl_igual_saidas = bool(pnl) and abs(pnl["liquido"] - soma_saidas) <= 0.01
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

    ok = (n10016 == 0 and n_teto == 0 and pnl_igual_saidas and parado
          and encerrou and bool(commit_info.get("ok")))
    return {
        "dia": dia.isoformat(),
        "retcode_10016": n10016,
        "teto_estourado": n_teto,
        "pnl_log": pnl,
        "pnl_soma_saidas": soma_saidas,
        "pnl_soma_todos": soma_todos,
        "pnl_deals_saidas": n_saidas,
        "pnl_deals_todos": n_todos,
        "pnl_igual_saidas": pnl_igual_saidas,
        "pnl_igual_todos": pnl_igual_todos,
        "parado_ok": parado,
        "encerrou_graciosamente": encerrou,
        "commit_fecho": commit_info,
        "ok": bool(ok),
    }


def imprimir(r: dict) -> None:
    print(f"ACEITE POS-PREGAO {r['dia']}")
    print(f"  10016 (esperado 0):            {r['retcode_10016']}")
    print(f"  TETO ESTOURADO (esperado 0):   {r['teto_estourado']}")
    p = r["pnl_log"]
    if p:
        print(f"  [pnl_dia] MT5:                 {p['liquido']:+.2f} "
              f"({p['deals']} deals, magics {p['magics']})")
    else:
        print("  [pnl_dia] MT5:                 ausente no log")
    print(f"  soma deals de saida:           {r['pnl_soma_saidas']:+.2f} "
          f"({r['pnl_deals_saidas']} deals) "
          f"{'OK' if r['pnl_igual_saidas'] else 'DIFERENTE'}")
    print(f"  soma todos os deals:           {r['pnl_soma_todos']:+.2f} "
          f"({r['pnl_deals_todos']} deals) "
          f"{'OK' if r['pnl_igual_todos'] else 'DIFERENTE'}")
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
