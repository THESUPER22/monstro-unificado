# -*- coding: utf-8 -*-
"""Isola a suite dos logs de producao.

`agente_monstro_core` chama `logging.basicConfig(filename=agente_autonomo.log)`
no import. Sem isolamento, todo teste que loga (fecho, watchdog, shadow)
grava no log real do dia e contamina o aceite: medido em 18/11, linhas de
teste as 18:09/18:25 fizeram o item 4 ("encerrou graciosamente") passar por
engano.

Duas camadas:
1. `MONSTRO_AGENTE_LOG` (definida AQUI, antes da coleta importar o agente)
   aponta o FileHandler para um arquivo temporario desta sessao;
2. a fixture autouse remove o FileHandler da raiz depois da coleta e
   adiciona `NullHandler`, entao nenhum teste escreve no arquivo temporario
   nem no de producao.
"""
import logging
import os
import tempfile

import pytest

LOG_AGENTE_TESTE = os.path.join(
    tempfile.gettempdir(), f"monstro_agente_teste_{os.getpid()}.log")
# atribuicao direta: mesmo que o ambiente tenha a variavel, a suite isola.
os.environ["MONSTRO_AGENTE_LOG"] = LOG_AGENTE_TESTE


@pytest.fixture(autouse=True, scope="session")
def _nao_escrever_no_log_de_producao():
    raiz = logging.getLogger()
    for handler in list(raiz.handlers):
        if isinstance(handler, logging.FileHandler):
            raiz.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # noqa: BLE001
                pass
    raiz.addHandler(logging.NullHandler())
    yield
    try:
        os.remove(LOG_AGENTE_TESTE)
    except OSError:
        pass
