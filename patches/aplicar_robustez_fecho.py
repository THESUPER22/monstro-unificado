# -*- coding: utf-8 -*-
"""aplicar_robustez_fecho.py — aplica C1..C4 na branch `robustez-fecho`.

PROPOSTA / PREPARATORIO. Este script NAO roda sozinho e NAO toca no MT5.
Ele apenas edita dois arquivos-fonte, com backup, diff e validacao de sintaxe.

USO (a partir de C:\\AIOFEN):

    # 1) sempre primeiro em seco (nao grava nada)
    C:\\AIOFEN\\venv310\\Scripts\\python.exe patches\\aplicar_robustez_fecho.py

    # 2) revisar o diff e o plano impressos; depois aplicar
    C:\\AIOFEN\\venv310\\Scripts\\python.exe patches\\aplicar_robustez_fecho.py --apply

    # 3) se algo der errado, restaurar o ultimo backup
    C:\\AIOFEN\\venv310\\Scripts\\python.exe patches\\aplicar_robustez_fecho.py --reverter

O que ele faz
-------------
- Exige branch `robustez-fecho` (salvo --force-branch) e os 2 arquivos limpos
  no git (salvo --force-dirty).
- Le os arquivos em UTF-8 estrito; aborta se houver byte invalido ou U+FFFD.
- Trabalha linha a linha (splitlines keepends), preservando CRLF/LF originais.
  O robo tem 11.405 CRLF + 43 LF; nada de "salvar como" que troque encoding.
- Aplica 4 transformacoes ancoradas em trechos ASCII estaveis (nao em numero
  de linha), exigindo EXATAMENTE 1 ocorrencia por ancora.
- Gera backup completo em patches/backups/<timestamp>/ (arquivos + manifest +
  diff unificado).
- Valida cada arquivo resultante com `compile()` e `py_compile`.
- Nao inicia, nao reinicia e nao importa o robo. Nao chama MetaTrader5.

Garantias
---------
- Idempotente: se a marca `[C1-C4]` ja existir no arquivo, aborta.
- Nenhuma regra de entrada/saida, stop, alvo ou filtro e alterada.
- O unico import novo e fail-fast: se `patches/robustez_fecho_helpers.py`
  faltar, o robo nao inicia (melhor do que iniciar sem fecho robusto).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROBO = os.path.join(BASE, "monstro_unificado_v22.py")
AGENTE = os.path.join(BASE, "agente_monstro_core.py")
HELPER = os.path.join(BASE, "patches", "robustez_fecho_helpers.py")
BACKUPS = os.path.join(BASE, "patches", "backups")
MARCA = "[C1-C4]"


# ---------------------------------------------------------------------------
# leitura / escrita preservando fim de linha
# ---------------------------------------------------------------------------
def ler_arquivo(caminho: str) -> tuple[list[str], str]:
    """Le bytes, valida UTF-8 e devolve (linhas com keepends, newline padrao)."""
    with open(caminho, "rb") as f:
        bruto = f.read()
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError as e:
        raise RuntimeError(
            "%s nao e UTF-8 valido (%s). Abortando para nao corromper o fonte."
            % (caminho, e))
    if "\ufffd" in texto:
        raise RuntimeError(
            "%s contem U+FFFD (caractere de substituicao). Abortando." % caminho)
    linhas = texto.splitlines(keepends=True)
    crlf = texto.count("\r\n")
    lf = texto.count("\n") - crlf
    nl = "\r\n" if crlf >= lf else "\n"
    return linhas, nl


def escrever_arquivo(caminho: str, linhas: list[str]) -> None:
    """Grava exatamente as linhas recebidas (sem traduzir newline)."""
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.writelines(linhas)


def sha256(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for pedaco in iter(lambda: f.read(1 << 20), b""):
            h.update(pedaco)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# utilitarios de ancoragem
# ---------------------------------------------------------------------------
def _sem_nl(linha: str) -> str:
    return linha.rstrip("\r\n")


def _indent(linha: str) -> str:
    corpo = _sem_nl(linha)
    return corpo[:len(corpo) - len(corpo.lstrip(" \t"))]


def _achar_unica(linhas: list[str], agulha: str, rotulo: str,
                 inicio: int = 0, fim: int | None = None) -> int:
    """Indice da UNICA linha que contem `agulha`; erro se 0 ou >1."""
    limite = len(linhas) if fim is None else fim
    achados = [i for i in range(inicio, limite) if agulha in linhas[i]]
    if len(achados) != 1:
        raise RuntimeError(
            "[%s] esperava 1 linha contendo %r entre %d e %d; achei %d (%s)"
            % (rotulo, agulha, inicio, limite, len(achados), achados[:8]))
    return achados[0]


def _bloco(texto: str, nl: str) -> list[str]:
    """Converte um bloco de texto (\\n) em linhas com o newline do arquivo."""
    partes = texto.replace("\r\n", "\n").split("\n")
    if partes and partes[-1] == "":
        partes.pop()
    return [p + nl for p in partes]


def _ja_aplicado(linhas: list[str]) -> bool:
    return any(MARCA in ln for ln in linhas)


# ---------------------------------------------------------------------------
# C0 + C1 — import dos helpers + fechar_todas_posicoes robusto
# ---------------------------------------------------------------------------
BLOCO_C1 = '''# [C1-C4] Robustez do fecho (patch 2026-11-11, ROADMAP 23.27/23.28).
# Helpers testados em patches/robustez_fecho_helpers.py (12 testes).
# Import fail-fast de proposito: melhor nao iniciar do que iniciar sem fecho.
from patches.robustez_fecho_helpers import (
    contar_deals_reais_hoje,
    fechar_todas_robusto,
    posicoes_restantes,
)

MAGICS_ROBO = tuple(
    {MAGIC_NUMBER} | ({MAGIC_ROMPIMENTO} if ROMPIMENTO_ATIVO else set())
)


def fechar_todas_posicoes(motivo: str = "Encerramento automatico") -> int:
    """Fecha todas as posicoes do robo com reconexao/backoff (C1).

    Delega para patches/robustez_fecho_helpers.fechar_todas_robusto:
    - tenta todos os fillings aceitos pelo simbolo;
    - em retcode 10031 (ou order_send None) reconecta e espera backoff;
    - so conta como fechada o que positions_get() confirma que saiu.

    Retorna o numero de posicoes confirmadas como fechadas (int), mantendo
    compativel o contrato dos chamadores atuais.
    """
    tickets_antes = []
    try:
        for _p in (mt5.positions_get() or []):
            if _p.magic in MAGICS_ROBO:
                tickets_antes.append(_p.ticket)
    except Exception:
        pass

    try:
        fechadas, restantes = fechar_todas_robusto(
            mt5, MAGICS_ROBO,
            reconnect=reconectar_mt5,
            log=logging,
            deviation=20,
            tentativas=5,
            backoff_s=5.0,
        )
    except Exception as e:
        logging.error("Erro critico no fecho robusto (%s): %s", motivo, e)
        return 0

    # Telemetria passiva: preserva o gancho que existia no corpo antigo.
    try:
        if "_telemetria_capturar_pnl" in globals():
            for _ticket in tickets_antes:
                if _ticket not in restantes:
                    _telemetria_capturar_pnl(_ticket)
    except Exception:
        pass

    if restantes:
        logging.critical(
            "FECHO INCOMPLETO (%s): %d posicao(oes) ainda aberta(s): %s",
            motivo, len(restantes), restantes)
    else:
        logging.info(
            "FECHO CONFIRMADO (%s): %d fechada(s), flat.", motivo, fechadas)
    return fechadas
'''


def aplicar_c1(linhas: list[str], nl: str) -> list[str]:
    ini = _achar_unica(linhas, "def fechar_todas_posicoes(", "C1-inicio")
    fim = _achar_unica(linhas, "def salvar_dados_finais(", "C1-fim", ini + 1)
    # A ancora inclui "def " para nao casar com a chamada em
    # encerramento_seguro_completo (que tambem contem "salvar_dados_finais(").
    if fim <= ini:
        raise RuntimeError("[C1] ancora de fim veio antes do inicio")
    return linhas[:ini] + _bloco(BLOCO_C1, nl) + linhas[fim:]


# ---------------------------------------------------------------------------
# C2 — so loga "POSICOES FECHADAS" se positions_get() confirmar flat
# ---------------------------------------------------------------------------
def aplicar_c2(linhas: list[str], nl: str) -> list[str]:
    alvo = _achar_unica(linhas, "AGUARDANDO AFTER MARKET", "C2")
    ini = alvo
    while ini >= 0 and "logging.info(" not in linhas[ini]:
        ini -= 1
    if ini < 0 or alvo - ini != 1:
        raise RuntimeError(
            "[C2] esperava logging.info( na linha imediatamente anterior; "
            "achei distancia %d" % (alvo - ini))
    indent = _indent(linhas[ini])
    bloco = (
        f"{indent}# {MARCA} C2: so loga sucesso se positions_get() confirmar flat.\n"
        f"{indent}_restantes = posicoes_restantes(mt5, MAGICS_ROBO)\n"
        f"{indent}if _restantes:\n"
        f"{indent}    logging.critical(\n"
        f'{indent}        "POSICOES AINDA ABERTAS AS %s: %s - fecho NAO confirmado",\n'
        f"{indent}        HORARIO_ENCERRAMENTO, _restantes)\n"
        f"{indent}else:\n"
        f"{indent}    logging.info(\n"
        f'{indent}        "POSICOES FECHADAS AS %s - flat confirmado (%d)",\n'
        f"{indent}        HORARIO_ENCERRAMENTO, posicoes_fechadas)\n"
    )
    return linhas[:ini] + _bloco(bloco, nl) + linhas[alvo + 1:]


# ---------------------------------------------------------------------------
# C3 — trava de shutdown: nao encerra com posicao do robo aberta
# ---------------------------------------------------------------------------
def aplicar_c3(linhas: list[str], nl: str) -> list[str]:
    alvo = _achar_unica(linhas, "ENCERRAMENTO GRACIL CONCLU", "C3")
    ini = alvo
    while ini >= 0 and "logging.info(" not in linhas[ini]:
        ini -= 1
    if ini < 0 or alvo - ini != 1:
        raise RuntimeError(
            "[C3] esperava logging.info( na linha imediatamente anterior; "
            "achei distancia %d" % (alvo - ini))
    indent = _indent(linhas[ini])
    bloco = (
        f"{indent}# {MARCA} C3: trava de shutdown - nao encerra com posicao aberta.\n"
        f"{indent}_restantes = posicoes_restantes(mt5, MAGICS_ROBO)\n"
        f"{indent}if _restantes:\n"
        f"{indent}    logging.critical(\n"
        f'{indent}        "SHUTDOWN BLOQUEADO: posicoes abertas %s - tentando fechar",\n'
        f"{indent}        _restantes)\n"
        f'{indent}    fechar_todas_posicoes("Trava de shutdown")\n'
        f"{indent}    _restantes = posicoes_restantes(mt5, MAGICS_ROBO)\n"
        f"\n"
        f"{indent}if _restantes and not os.environ.get(\"MONSTRO_FORCE_SHUTDOWN\"):\n"
        f"{indent}    logging.critical(\n"
        f'{indent}        "SHUTDOWN BLOQUEADO: %d posicao(oes) seguem abertas. "\n'
        f'{indent}        "Processo permanece vivo. Use MONSTRO_FORCE_SHUTDOWN=1 "\n'
        f'{indent}        "para forcar.", len(_restantes))\n'
        f"{indent}    time.sleep(30)\n"
        f"{indent}    continue\n"
        f"\n"
    )
    return linhas[:ini] + _bloco(bloco, nl) + linhas[ini:]


# ---------------------------------------------------------------------------
# C4 — relatorio diario por deals reais (agente)
# ---------------------------------------------------------------------------
BLOCO_C4_FUNC = '''# [C1-C4] C4: contagem read-only por deals reais do MT5 (inclui fecho manual).
def contar_trades_reais_hoje():
    """(n_fechados, pnl_realizado) lendo deals reais. Degrada para (None, 0)."""
    try:
        import MetaTrader5 as mt5
        from patches.robustez_fecho_helpers import contar_deals_reais_hoje

        cfg = carregar_config_robo()
        magics = {int(cfg.get("geral", {}).get("magic_number", 123456))}
        try:
            magics.add(int((cfg.get("rompimento") or {}).get("magic", 7008)))
        except (TypeError, ValueError):
            pass

        if not mt5.initialize():
            return None, 0.0
        try:
            hoje = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0)
            return contar_deals_reais_hoje(mt5, magics, hoje, datetime.now())
        finally:
            mt5.shutdown()
    except Exception as e:
        log.warning(f"contar_trades_reais_hoje indisponivel: {e}")
        return None, 0.0
'''


def aplicar_c4(linhas: list[str], nl: str) -> list[str]:
    ini = _achar_unica(linhas, "def contar_executados_hoje(", "C4-funcao")
    linhas = linhas[:ini] + _bloco(BLOCO_C4_FUNC, nl) + [nl, nl] + linhas[ini:]

    alvo = _achar_unica(linhas, "Trades executados: {n_v22 + n_romp}", "C4-relatorio")
    # A marcacao esta na 2a linha do linhas.append(...); a indentacao correta
    # e' a da ABERTURA do statement (4 espacos), nao a da continuacao (18).
    ini_stmt = alvo
    while ini_stmt >= 0 and "linhas.append(" not in linhas[ini_stmt]:
        ini_stmt -= 1
    if ini_stmt < 0 or alvo - ini_stmt > 3:
        raise RuntimeError("[C4] nao achei a abertura do linhas.append do relatorio")
    indent = _indent(linhas[ini_stmt])
    bloco = (
        f"{indent}# {MARCA} C4: deals reais (inclui fecho manual fora do log).\n"
        f"{indent}n_real, pnl_real = contar_trades_reais_hoje()\n"
        f"{indent}if n_real is None:\n"
        f'{indent}    linhas.append("Trades fechados (deals MT5): indisponivel (MT5 off)")\n'
        f"{indent}else:\n"
        f"{indent}    linhas.append(\n"
        f'{indent}        f"Trades fechados (deals MT5): {{n_real}} | "\n'
        f'{indent}        f"PnL realizado: R$ {{pnl_real:+.2f}}")\n'
    )
    return linhas[:alvo + 1] + _bloco(bloco, nl) + linhas[alvo + 1:]


# ---------------------------------------------------------------------------
# git / backup / validacao
# ---------------------------------------------------------------------------
def _git(*args: str) -> str:
    r = subprocess.run(
        ["git", "-C", BASE] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("git %s falhou: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


def checar_git(forcar_branch: bool, forcar_sujo: bool) -> dict:
    info = {}
    try:
        info["branch"] = _git("rev-parse", "--abbrev-ref", "HEAD")
        info["commit"] = _git("rev-parse", "HEAD")
    except Exception as e:
        if not forcar_branch:
            raise RuntimeError("nao consegui ler o git (%s)" % e)
        info["branch"] = info["commit"] = "desconhecido"

    if info["branch"] != "robustez-fecho" and not forcar_branch:
        raise RuntimeError(
            "branch atual e %r; o patch deve ser aplicado em 'robustez-fecho'. "
            "Use --force-branch para ignorar." % info["branch"])

    sujo = _git("status", "--porcelain", "--",
                os.path.basename(ROBO), os.path.basename(AGENTE))
    if sujo and not forcar_sujo:
        raise RuntimeError(
            "arquivos-alvo com alteracoes nao commitadas:\n%s\n"
            "Commite/stash antes (ou use --force-dirty)." % sujo)
    info["sujo"] = sujo
    return info


def criar_backup(antes: dict, info_git: dict) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUPS, ts)
    os.makedirs(destino, exist_ok=False)
    for caminho in (ROBO, AGENTE):
        shutil.copy2(caminho, os.path.join(destino, os.path.basename(caminho)))
    manifest = {
        "timestamp": ts,
        "branch": info_git.get("branch"),
        "commit": info_git.get("commit"),
        "arquivos": {
            os.path.basename(c): {
                "sha256_antes": antes[c],
                "sha256_backup": sha256(os.path.join(destino, os.path.basename(c))),
            } for c in (ROBO, AGENTE)
        },
    }
    with open(os.path.join(destino, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return destino


def validar_sintaxe_texto(caminho: str, linhas: list[str]) -> None:
    """Valida o buffer em memoria, sem gravar nada (usado no dry-run)."""
    try:
        compile("".join(linhas), caminho, "exec")
    except SyntaxError as e:
        raise RuntimeError(
            "sintaxe invalida em %s: linha %s: %s" % (caminho, e.lineno, e.msg))


def validar_sintaxe_disco(caminho: str) -> None:
    """Valida o arquivo realmente gravado, com o mesmo py_compile do CI."""
    try:
        py_compile.compile(caminho, doraise=True)
    except py_compile.PyCompileError as e:
        raise RuntimeError("py_compile falhou em %s: %s" % (caminho, e))


def gerar_diff(antes: list[str], depois: list[str], nome: str) -> str:
    return "".join(difflib.unified_diff(
        antes, depois, fromfile=nome + " (antes)", tofile=nome + " (depois)",
        n=3))


def aplicar(forcar_branch: bool, forcar_sujo: bool, pular_git: bool,
            gravar: bool) -> int:
    for caminho in (ROBO, AGENTE, HELPER):
        if not os.path.exists(caminho):
            raise RuntimeError("arquivo obrigatorio ausente: %s" % caminho)

    info_git = {"branch": "n/a", "commit": "n/a"}
    if not pular_git:
        info_git = checar_git(forcar_branch, forcar_sujo)
        print("git: branch=%s commit=%s"
              % (info_git["branch"], info_git["commit"][:12]))

    linhas_robo, nl_robo = ler_arquivo(ROBO)
    linhas_agente, nl_agente = ler_arquivo(AGENTE)

    if _ja_aplicado(linhas_robo) or _ja_aplicado(linhas_agente):
        raise RuntimeError(
            "a marca %s ja existe; o patch parece aplicado. "
            "Use --reverter ou confira o git." % MARCA)

    novo_robo = aplicar_c1(linhas_robo, nl_robo)
    novo_robo = aplicar_c2(novo_robo, nl_robo)
    novo_robo = aplicar_c3(novo_robo, nl_robo)
    novo_agente = aplicar_c4(linhas_agente, nl_agente)

    # Valida o buffer em memoria ANTES de qualquer escrita.
    validar_sintaxe_texto(ROBO, novo_robo)
    validar_sintaxe_texto(AGENTE, novo_agente)

    diff_robo = gerar_diff(linhas_robo, novo_robo, "monstro_unificado_v22.py")
    diff_agente = gerar_diff(linhas_agente, novo_agente, "agente_monstro_core.py")

    print("\n=== PLANO ===")
    print("monstro_unificado_v22.py: %d -> %d linhas | diff %d linhas"
          % (len(linhas_robo), len(novo_robo), diff_robo.count("\n")))
    print("agente_monstro_core.py : %d -> %d linhas | diff %d linhas"
          % (len(linhas_agente), len(novo_agente), diff_agente.count("\n")))
    print("sintaxe do buffer: OK (compile)")
    print("\n=== TRECHOS DO DIFF (primeiras 80 linhas de cada) ===")
    print("\n".join(diff_robo.splitlines()[:80]))
    print("\n--- agente ---")
    print("\n".join(diff_agente.splitlines()[:80]))

    if not gravar:
        print("\nDRY-RUN: nada foi gravado. Use --apply para aplicar.")
        return 0

    antes = {ROBO: sha256(ROBO), AGENTE: sha256(AGENTE)}
    destino = criar_backup(antes, info_git)
    with open(os.path.join(destino, "diff.patch"), "w",
              encoding="utf-8", newline="") as f:
        f.write(diff_robo + diff_agente)

    escrever_arquivo(ROBO, novo_robo)
    escrever_arquivo(AGENTE, novo_agente)

    # Revalida o que foi realmente gravado (nao o buffer).
    validar_sintaxe_texto(ROBO, ler_arquivo(ROBO)[0])
    validar_sintaxe_texto(AGENTE, ler_arquivo(AGENTE)[0])
    validar_sintaxe_disco(ROBO)
    validar_sintaxe_disco(AGENTE)

    manifest_path = os.path.join(destino, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    for caminho in (ROBO, AGENTE):
        manifest["arquivos"][os.path.basename(caminho)]["sha256_depois"] = \
            sha256(caminho)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n=== APLICADO ===")
    print("backup + diff: %s" % destino)
    print("sha256 robo  : %s" % sha256(ROBO))
    print("sha256 agente: %s" % sha256(AGENTE))
    print("\nProximos passos (manuais):")
    print("  1) C:\\AIOFEN\\venv310\\Scripts\\python.exe -m pytest "
          "tests/test_robustez_fecho.py -q")
    print("  2) teste em demo controlada "
          "(ver patches/checklist_fecho_2026-11-12.md)")
    print("  3) git add/commit na branch robustez-fecho; "
          "merge na main so se verde")
    return 0


def reverter() -> int:
    if not os.path.isdir(BACKUPS):
        raise RuntimeError("nenhum diretorio de backup em %s" % BACKUPS)
    candidatos = sorted(
        (d for d in os.listdir(BACKUPS)
         if os.path.isdir(os.path.join(BACKUPS, d))),
        reverse=True)
    if not candidatos:
        raise RuntimeError("nenhum backup encontrado em %s" % BACKUPS)
    destino = os.path.join(BACKUPS, candidatos[0])
    for caminho in (ROBO, AGENTE):
        origem = os.path.join(destino, os.path.basename(caminho))
        if not os.path.exists(origem):
            raise RuntimeError("backup incompleto: falta %s" % origem)
        shutil.copy2(origem, caminho)
    validar_sintaxe_texto(ROBO, ler_arquivo(ROBO)[0])
    validar_sintaxe_texto(AGENTE, ler_arquivo(AGENTE)[0])
    validar_sintaxe_disco(ROBO)
    validar_sintaxe_disco(AGENTE)
    print("revertido a partir de %s" % destino)
    print("sha256 robo  : %s" % sha256(ROBO))
    print("sha256 agente: %s" % sha256(AGENTE))
    return 0


def main(argv: list[str]) -> int:
    # O fonte tem mojibake; o console do Windows pode ser cp1252. Nao deixar
    # a impressao do diff derrubar a aplicacao.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        description="Aplica/reverte o patch C1-C4 (nao toca no MT5).")
    ap.add_argument("--apply", action="store_true",
                    help="grava as alteracoes (sem isso, so dry-run)")
    ap.add_argument("--reverter", action="store_true",
                    help="restaura o backup mais recente")
    ap.add_argument("--force-branch", action="store_true",
                    help="permite rodar fora da branch robustez-fecho")
    ap.add_argument("--force-dirty", action="store_true",
                    help="permite arquivos-alvo com alteracoes nao commitadas")
    ap.add_argument("--skip-git", action="store_true",
                    help="nao consulta o git (nao recomendado)")
    args = ap.parse_args(argv)

    if args.reverter:
        return reverter()
    if not args.apply:
        print("MODO SECO (dry-run). Nada sera gravado. Use --apply para aplicar.\n")
    return aplicar(args.force_branch, args.force_dirty, args.skip_git,
                   args.apply)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print("ABORTADO: %s" % e, file=sys.stderr)
        sys.exit(2)
