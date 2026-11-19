# -*- coding: utf-8 -*-
"""Selecao e commit restrito dos artefatos do fecho (P1 17/11 #3, rev. 2.3).

Por que existe: ate 17/11 o ``git_commit_dia`` fazia ``git add -- <arquivos>``
sem ``-f``. Dois dos quatro padroes da whitelist caem no ``.gitignore``
(``relatorio_*.txt`` e ``logs/``). Como ``git add`` falha (exit 1) quando
QUALQUER caminho da lista e ignorado, a funcao desistiria inteira, em silencio.
Medido em 17/11: 71 ``relatorio_diario_*.txt`` e 26
``logs/fluxo_resumo_*.json`` no disco, ZERO no git. So os 71 ``plano_*.txt``
(unico padrao fora do ``.gitignore``) entravam - o que mascarava o problema: o
fecho parecia funcionar.

A whitelist entrou em 17/11 18:18, DEPOIS do fecho daquele dia (17:35), entao
o codigo com o bug nunca chegou a rodar: este fix pega o problema antes do
primeiro fecho com whitelist (18/11 17:35).

Correcoes, cada uma com flag propria:

  - ``add_forcado``: usa ``git add -f`` (a whitelist ja e a barreira; o
    ``-f`` so vence o ``.gitignore``).
  - ``janela_horas``: so entram arquivos modificados nas ultimas N horas
    (padrao 26). Sem isso, o primeiro fecho depois do fix publicaria de uma
    vez 170 arquivos historicos que nunca deveriam ir para o repo publico.
    26 h e nao 24 h de proposito: se um fecho falhar, o fecho do dia seguinte
    (mesmo horario) ainda alcanca o arquivo de ontem. ``None`` desliga o
    filtro.
  - ``dry_run``: ``executar_commit`` apenas informa o que seria commitado,
    sem tocar no indice nem criar commit.
  - ``verificar_sensivel``: antes do ``git add``, varre a whitelist e o indice
    (``tools/verificar_sensivel.py``). Conta, saldo em R$ ou segredo literal
    bloqueiam o commit e o chamador loga arquivo/linha/tipo, nunca o valor.

Rev. 2.3 separa a CHECAGEM (``caminhos_permitidos``, pura: so le o disco e o
relogio) da ACAO (``executar_commit``, unico ponto que chama ``git add`` /
``git commit``). Assim a checagem pode ser testada de verdade, sem placebo.

Modulo sem MT5/TensorFlow; testavel em ``tests/test_commit_dia.py`` (inclui um
repo git descartavel que reproduz o bug e prova o fix).
"""
from __future__ import annotations

import glob
import os
import subprocess
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence

from tools.verificar_sensivel import varrer as varrer_sensivel

JANELA_HORAS_PADRAO = 26.0

STATUS_OK = "ok"
STATUS_NADA_PRESENTE = "nada_presente"
STATUS_NADA_NOVO = "nada_novo"
STATUS_ADD_FALHOU = "add_falhou"
STATUS_COMMIT_FALHOU = "commit_falhou"
STATUS_COMMITADO = "commitado"
STATUS_DRY_RUN = "dry_run"
STATUS_SENSIVEL = "sensivel"


def _rel(base_dir: str, caminho: str) -> str:
    """Caminho relativo em barras normais (git usa '/' em todo lugar)."""
    return os.path.relpath(caminho, base_dir).replace(os.sep, "/")


def selecionar_arquivos(padroes: Iterable[str],
                        base_dir: str,
                        agora: Optional[datetime] = None,
                        janela_horas: Optional[float] = JANELA_HORAS_PADRAO) -> List[str]:
    """Arquivos existentes que casam com os padroes, em ordem alfabetica.

    - ignora diretorios (um padrao pode casar com pasta);
    - remove duplicatas quando dois padroes casam com o mesmo arquivo;
    - ``janela_horas`` compara o mtime com ``agora`` (horario local, que e o
      que o Agendador de Tarefas usa); ``None`` desliga o filtro.
    """
    agora = agora or datetime.now()
    limite = (agora - timedelta(hours=float(janela_horas))
              if janela_horas is not None else None)
    vistos = set()
    saida: List[str] = []
    for padrao in padroes or ():
        completo = os.path.join(base_dir, str(padrao).replace("/", os.sep))
        for caminho in sorted(glob.glob(completo)):
            if not os.path.isfile(caminho):
                continue
            rel = _rel(base_dir, caminho)
            if rel in vistos:
                continue
            if limite is not None:
                mtime = datetime.fromtimestamp(os.path.getmtime(caminho))
                if mtime < limite:
                    continue
            vistos.add(rel)
            saida.append(rel)
    return sorted(saida)


def caminhos_permitidos(padroes: Iterable[str],
                        base_dir: str,
                        agora: Optional[datetime] = None,
                        janela_horas: Optional[float] = JANELA_HORAS_PADRAO) -> dict:
    """Checagem PURA: quais arquivos da whitelist seriam commitados agora.

    Nao chama git e nao escreve nada. Retorna
    ``{"status": STATUS_OK | STATUS_NADA_PRESENTE, "arquivos": [...],
    "detalhe": str}``. A acao fica em ``executar_commit``.
    """
    lista = list(padroes or ())
    if not lista:
        return {"status": STATUS_NADA_PRESENTE, "arquivos": [],
                "detalhe": "whitelist vazia"}

    arquivos = selecionar_arquivos(lista, base_dir, agora, janela_horas)
    if not arquivos:
        return {"status": STATUS_NADA_PRESENTE, "arquivos": [],
                "detalhe": "nenhum arquivo permitido presente"
                            + ("" if janela_horas is None
                               else f" nas ultimas {float(janela_horas):g} h")}

    return {"status": STATUS_OK, "arquivos": arquivos, "detalhe": ""}


def _git(base_dir: str, args: Sequence[str], timeout: float = 60):
    return subprocess.run(["git", "-C", base_dir] + list(args),
                          capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def _resumo(proc) -> str:
    texto = (proc.stderr or proc.stdout or "").strip()
    return texto.replace("\n", " ")[:300]


def executar_commit(base_dir: str,
                    padroes: Iterable[str],
                    msg: str,
                    agora: Optional[datetime] = None,
                    janela_horas: Optional[float] = JANELA_HORAS_PADRAO,
                    add_forcado: bool = True,
                    dry_run: bool = False,
                    verificar_sensivel: bool = True) -> dict:
    """Faz add + commit APENAS dos caminhos permitidos.

    Retorna ``{"status": ..., "arquivos": [...], "detalhe": str}``. Nunca
    levanta por falha do git: o fecho precisa continuar (relatorio e plano ja
    foram gravados) e o motivo fica registrado no log pelo chamador.

    ``dry_run=True`` para depois da checagem: devolve ``STATUS_DRY_RUN`` com a
    lista, sem ``git add`` e sem commit (o indice fica intocado).

    ``verificar_sensivel=True`` (padrao) varre a whitelist e o indice ANTES do
    ``git add``. Achado de conta/saldo/segredo devolve ``STATUS_SENSIVEL`` com
    ``achados`` (arquivo, linha, tipo - nunca o valor) e nada e commitado.

    ``git commit -- <caminhos>`` mantem a garantia de que nada fora da
    whitelist entra, mesmo que o indice ja tenha algo staged por um humano.
    """
    selecao = caminhos_permitidos(padroes, base_dir, agora, janela_horas)
    if selecao["status"] != STATUS_OK:
        return selecao
    arquivos = selecao["arquivos"]

    if verificar_sensivel:
        achados = varrer_sensivel(base_dir, arquivos, incluir_staged=True)
        if achados:
            return {"status": STATUS_SENSIVEL, "arquivos": arquivos,
                    "detalhe": f"{len(achados)} achado(s) sensivel(is) - "
                               "nada foi adicionado nem commitado",
                    "achados": achados}

    if dry_run:
        return {"status": STATUS_DRY_RUN, "arquivos": arquivos,
                "detalhe": "dry_run: nada foi adicionado nem commitado"}

    add_args = ["add"] + (["-f"] if add_forcado else []) + ["--"] + arquivos
    add = _git(base_dir, add_args)
    if add.returncode != 0:
        return {"status": STATUS_ADD_FALHOU, "arquivos": arquivos,
                "detalhe": f"git add ({add.returncode}): {_resumo(add)}"}

    # Só os caminhos permitidos interessam: o indice pode ter outra coisa.
    if _git(base_dir, ["diff", "--cached", "--quiet", "--"] + arquivos,
            timeout=30).returncode == 0:
        return {"status": STATUS_NADA_NOVO, "arquivos": arquivos,
                "detalhe": "sem mudanca nos caminhos permitidos"}

    commit = _git(base_dir, ["commit", "-m", msg, "--"] + arquivos)
    if commit.returncode != 0:
        return {"status": STATUS_COMMIT_FALHOU, "arquivos": arquivos,
                "detalhe": f"git commit ({commit.returncode}): {_resumo(commit)}"}

    return {"status": STATUS_COMMITADO, "arquivos": arquivos, "detalhe": ""}


def mensagem_fecho(agora: Optional[datetime] = None) -> str:
    agora = agora or datetime.now()
    return f"fecho autonomo {agora:%Y-%m-%d} (agente Fase 1)"
