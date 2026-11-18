# -*- coding: utf-8 -*-
"""Escrita atomica de arquivos (P0 17/11 #4).

Motivo: em 17/11 o agente declarou ``timeout no shutdown gracioso`` e fez
``force kill`` enquanto o robo ainda gravava artefatos. Um ``open(arquivo,'w')``
seguido de ``json.dump`` deixa o arquivo final truncado se o processo morrer no
meio. A escrita atomica elimina essa janela: grava num temporario no MESMO
diretorio (mesmo volume) e so entao troca o destino com ``os.replace``, que e
atomico no Windows/NTFS.

A extensao e preservada no temporario (``...__tmp_<pid>_<token>.json``) porque
algumas APIs (Keras) validam a extensao do caminho.

Modulo puro (sem MT5/TensorFlow), testavel em ``tests/test_escrita_atomica.py``.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Callable, TextIO

# Windows: antivirus/indexador pode segurar o arquivo por alguns ms. Sem o
# retry, um PermissionError passageiro derrubava a gravacao do artefato.
TENTATIVAS_REPLACE = 5
ESPERA_REPLACE_S = 0.1


def caminho_temporario(caminho: str) -> str:
    """Caminho temporario no mesmo diretorio do destino, com a mesma extensao.

    Unico por chamada (pid + token) para nao colidir entre processos ou entre
    duas gravacoes simultaneas do mesmo arquivo.
    """
    destino = os.path.abspath(caminho)
    pasta, nome = os.path.split(destino)
    raiz, ext = os.path.splitext(nome)
    token = f"{os.getpid()}_{uuid.uuid4().hex[:8]}"
    return os.path.join(pasta, f"{raiz}__tmp_{token}{ext}")


def _replace_com_retry(origem: str, destino: str,
                       tentativas: int = TENTATIVAS_REPLACE,
                       espera_s: float = ESPERA_REPLACE_S) -> None:
    """``os.replace`` com retry em ``PermissionError``.

    No Windows o destino pode ficar bloqueado por alguns ms (antivirus,
    indexador, outro handle de leitura). Cada falha espera ``espera_s`` e
    tenta de novo; na ultima tentativa a excecao sobe (o chamador limpa o
    temporario).
    """
    for tentativa in range(1, tentativas + 1):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa >= tentativas:
                raise
            time.sleep(espera_s)


def salvar_atomico(caminho: str,
                   escritor: Callable[[TextIO], None],
                   encoding: str = "utf-8",
                   newline=None) -> str:
    """Grava ``caminho`` via temporario + ``os.replace``.

    ``escritor`` recebe o arquivo aberto para escrita e deve apenas escrever
    (ex.: ``lambda f: json.dump(dados, f)``). Se levantar qualquer excecao, o
    arquivo final NAO e tocado e o temporario e removido.

    Retorna o caminho absoluto do destino.
    """
    destino = os.path.abspath(caminho)
    tmp = caminho_temporario(destino)
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as f:
            escritor(f)
            f.flush()
            os.fsync(f.fileno())
        _replace_com_retry(tmp, destino)
    except BaseException:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise
    return destino


def salvar_texto_atomico(caminho: str, texto: str,
                         encoding: str = "utf-8") -> str:
    """Atalho de ``salvar_atomico`` para conteudo ja serializado em texto."""
    return salvar_atomico(caminho, lambda f: f.write(texto), encoding=encoding)
