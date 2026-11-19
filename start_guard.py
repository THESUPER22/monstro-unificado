# -*- coding: utf-8 -*-
"""Guarda do start_all.bat: robo vivo x ZUMBI.

ZUMBI = processo do robo cujo ``parado.ok`` e MAIS NOVO que o inicio do
processo. Significa que ele ja concluiu o encerramento gracioso (gravou
``parado.ok``) mas o processo nao saiu - exatamente o que aconteceu em
18/11/2026: dois ``python monstro_unificado_v22`` vivos, um segurando a
porta 5001, e o ``start_all.bat`` cancelando o dia seguinte por achar um
robo vivo.

Regra:
  - nenhum processo do robo -> 0 (pode subir);
  - algum processo vivo de verdade (``parado.ok`` ausente ou mais antigo
    que o processo) -> 10 (aborta e registra hora/PID/comparacao);
  - todos zumbis -> mata (terminate, espera, kill) e 0; se algum nao sair
    -> 10 (nao sobe com processo do robo ainda vivo);
  - erro interno -> 11 (aborta e loga; o .bat nunca sobe no escuro);
  - psutil ausente -> 12 (aborta: sem ele nao da para classificar).

``--dry-run`` decide e registra sem matar nada (e sem gravar o marcador de
inicio). Os testes em ``tests/test_start_guard.py`` usam processos falsos;
o teste de deteccao real cria um processo inofensivo com o nome no cmdline
e o encerra no fim.

Uso:
    python start_guard.py --dry-run   # so mostra a decisao
    python start_guard.py             # mata zumbis e libera a subida
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple

ALVO_PY = "monstro_unificado_v22"
ALVO_EXE = "monstrodashboard.exe"


def _fmt(epoch: Optional[float]) -> str:
    if epoch is None:
        return "ausente"
    return datetime.fromtimestamp(float(epoch)).strftime("%Y-%m-%d %H:%M:%S")


def classificar(processos: Iterable[dict],
                parado_mtime: Optional[float]) -> Tuple[List[dict], List[dict]]:
    """Separa (zumbis, vivos).

    ``processos``: dicts com ``pid``, ``nome`` e ``inicio`` (epoch).
    Zumbi quando ``parado.ok`` existe e e mais novo que o inicio do
    processo. Sem ``parado.ok`` (ou sem ``inicio``) e vivo: na duvida,
    nao mata.
    """
    zumbis: List[dict] = []
    vivos: List[dict] = []
    for p in processos:
        inicio = p.get("inicio")
        if (parado_mtime is not None and inicio is not None
                and float(parado_mtime) > float(inicio)):
            zumbis.append(p)
        else:
            vivos.append(p)
    return zumbis, vivos


def listar_processos() -> List[dict]:
    """Processos do robo (python com o script ou o dashboard EXE)."""
    try:
        import psutil  # noqa: PLC0415
    except Exception:
        return []
    achados: List[dict] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            nome = (proc.info.get("name") or "").lower()
            cmd = " ".join(proc.info.get("cmdline") or [])
            if ((nome == "python.exe" and ALVO_PY in cmd)
                    or nome == ALVO_EXE):
                achados.append({"pid": proc.info["pid"], "nome": nome,
                                "inicio": proc.info.get("create_time")})
        except Exception:  # noqa: BLE001 - processo sumiu no meio da varredura
            continue
    return achados


def matar(pid: int, espera_s: float = 5.0) -> bool:
    """terminate + espera; se nao sair, kill. True se o processo sumiu."""
    try:
        import psutil  # noqa: PLC0415
        p = psutil.Process(pid)
        p.terminate()
        try:
            p.wait(timeout=espera_s)
        except psutil.TimeoutExpired:
            p.kill()
            p.wait(timeout=espera_s)
        return not p.is_running()
    except Exception:  # noqa: BLE001
        try:
            return not psutil.pid_exists(pid)
        except Exception:
            return False


def _log(caminho: str, linha: str) -> None:
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {linha}\n")
    except Exception:
        pass


RC_OK = 0          # subida liberada (nenhum robo, ou zumbis encerrados)
RC_VIVO = 10       # robo vivo de verdade -> start abortado
RC_ERRO = 11       # erro interno do guard -> start abortado por seguranca
RC_SEM_PSUTIL = 12  # psutil ausente -> nao da para distinguir vivo de zumbi


def _psutil_ok() -> bool:
    try:
        import psutil  # noqa: F401,PLC0415
        return True
    except Exception:
        return False


def _marcar_inicio(base: str) -> None:
    """Grava o marcador lido pelo watchdog (mtime = hora do start)."""
    caminho = os.path.join(base, "logs", "robo_inicio.txt")
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    except Exception:
        pass


def _executar(args, log_path: str, listar, matar_fn) -> int:
    if not _psutil_ok():
        _log(log_path, "ABORTA | psutil ausente no venv - sem como "
                       "distinguir robo vivo de zumbi")
        return RC_SEM_PSUTIL
    processos = list(listar() or [])
    if not processos:
        if not args.dry_run:
            _marcar_inicio(args.base)
        _log(log_path, "START | nenhum robo vivo - subida liberada")
        return RC_OK

    parado = os.path.join(args.base, "parado.ok")
    parado_mtime = os.path.getmtime(parado) if os.path.exists(parado) else None
    zumbis, vivos = classificar(processos, parado_mtime)

    for proc in vivos:
        _log(log_path,
             f"VIVO | pid={proc.get('pid')} inicio={_fmt(proc.get('inicio'))} "
             f"parado.ok={_fmt(parado_mtime)} | start ABORTADO "
             f"(robo vivo de verdade)")
    if vivos:
        return RC_VIVO

    for proc in zumbis:
        if args.dry_run:
            _log(log_path,
                 f"ZUMBI | pid={proc.get('pid')} inicio={_fmt(proc.get('inicio'))} "
                 f"parado.ok={_fmt(parado_mtime)} | DRY-RUN: mataria e seguiria")
            continue
        ok = matar_fn(int(proc.get("pid")))
        _log(log_path,
             f"ZUMBI | pid={proc.get('pid')} inicio={_fmt(proc.get('inicio'))} "
             f"parado.ok={_fmt(parado_mtime)} | "
             f"{'encerrado' if ok else 'FALHA AO ENCERRAR'}")
        if not ok:
            return RC_VIVO  # zumbi que nao morreu ainda ocupa a porta 5001
    if not args.dry_run:
        _marcar_inicio(args.base)
    return RC_OK


def main(argv: Optional[Sequence[str]] = None,
         listar=listar_processos, matar_fn=matar) -> int:
    p = argparse.ArgumentParser(description="Guarda do start_all.bat")
    p.add_argument("--base", default=os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--dry-run", action="store_true",
                   help="mostra a decisao sem encerrar processo")
    args = p.parse_args(argv)

    log_path = os.path.join(args.base, "logs", "start_all.log")
    try:
        return _executar(args, log_path, listar, matar_fn)
    except Exception as e:  # noqa: BLE001 - o .bat nao pode subir no escuro
        _log(log_path, f"ERRO INTERNO | {type(e).__name__}: {e} | start ABORTADO")
        return RC_ERRO


if __name__ == "__main__":
    raise SystemExit(main())
