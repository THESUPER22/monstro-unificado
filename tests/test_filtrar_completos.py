# -*- coding: utf-8 -*-
"""Testes do filtro PRE-REGISTRADO da coleta shadow (P1 18/11).

Regra congelada: ``completo is True`` E ``max_gap_s <= 10``. O SHA-256 de
``filtrar_completos.py`` fica aqui e no ROADMAP; alterar o filtro depois de
ver resultado invalida a analise.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import filtrar_completos as f  # noqa: E402

T0 = 1794996000.0   # 2026-11-18 10:00:00 UTC
TS = datetime.fromtimestamp(T0, tz=timezone.utc).isoformat()

# Congelado em 18/11 ANTES de qualquer leitura da coleta.
SHA256_ESPERADO = "c16fd90f2633bc02da1178f84f41ef2deabeaf143a9c6404d85fbcb8fa55f8f8"


def _sinal(**kw):
    base = {
        "ts": TS, "duracao_s": 2.0, "sinal": "BUY", "operado": True,
        "sl_pts": 8.0, "tp_pts": 8.0, "atr": 2.5, "magic": 123456,
        "symbol": "WDOZ26", "preco": 5798.0,
        "path": [[T0, 5797.5, 5798.0], [T0 + 1, 5797.5, 5798.0]],
        "n": 2, "completo": True,
    }
    base.update(kw)
    return base


def test_hash_congelado():
    caminho = os.path.join(BASE, "filtrar_completos.py")
    with open(caminho, "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == SHA256_ESPERADO


def test_mantem_completo_e_sem_buraco():
    assert f.decidir(_sinal()) == (True, "ok")


def test_descarta_incompleto():
    assert f.decidir(_sinal(completo=False)) == (False, "incompleto")


def test_completo_precisa_ser_true_booleano():
    assert f.decidir(_sinal(completo="true")) == (False, "incompleto")
    assert f.decidir(_sinal(completo=1)) == (False, "incompleto")


def test_limite_do_gap_e_inclusivo():
    assert f.decidir(_sinal(max_gap_s=10.0))[0] is True
    assert f.decidir(_sinal(max_gap_s=10.001)) == (False, "gap")


def test_calcula_buraco_do_path_quando_campo_ausente():
    s = _sinal(duracao_s=31.0,
               path=[[T0, 1, 2], [T0 + 1, 1, 2], [T0 + 31, 1, 2]])
    assert f.max_gap_s(s) == 30.0
    assert f.decidir(s) == (False, "gap")


def test_cauda_curta_reprova():
    """Path que para antes da janela nao pode passar como completo."""
    s = _sinal(duracao_s=1800.0)
    assert f.decidir(s) == (False, "gap")


def test_campo_nao_esconde_buraco_do_path():
    """Fail-closed: vale o MAIOR entre campo gravado e path."""
    s = _sinal(max_gap_s=1.0, duracao_s=60.0,
               path=[[T0, 1, 2], [T0 + 60, 1, 2]])
    assert f.max_gap_s(s) == 60.0
    assert f.decidir(s) == (False, "gap")


def test_sem_path_e_invalido_mesmo_com_campo():
    s = _sinal(max_gap_s=1.0)
    s.pop("path")
    assert f.decidir(s) == (False, "invalido")


def test_linha_ilegivel_nao_derruba_o_arquivo():
    texto = "\n".join([json.dumps(_sinal()), "{quebrado",
                       json.dumps(_sinal(completo=False))])
    mantidos, estat = f.filtrar(texto)
    assert len(mantidos) == 1
    assert estat == {"total": 3, "mantidos": 1, "incompleto": 1,
                     "gap": 0, "invalido": 1}


def test_preserva_a_linha_original():
    linha = json.dumps(_sinal(), ensure_ascii=False)
    mantidos, _ = f.filtrar(linha + "\n")
    assert mantidos == [linha]


def test_array_json_vira_jsonl():
    texto = json.dumps([_sinal(), _sinal(completo=False)])
    mantidos, estat = f.filtrar(texto)
    assert len(mantidos) == 1 and estat["incompleto"] == 1
    assert json.loads(mantidos[0])["completo"] is True


def test_cli_grava_saida_e_resume(tmp_path, capsys):
    entrada = tmp_path / "in.jsonl"
    saida = tmp_path / "out.jsonl"
    entrada.write_text("\n".join([json.dumps(_sinal()),
                                  json.dumps(_sinal(completo=False))]) + "\n",
                       encoding="utf-8")
    assert f.main(["--entrada", str(entrada), "--saida", str(saida)]) == 0
    linhas = saida.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1
    assert "mantidos=1" in capsys.readouterr().err


def test_gap_do_coletor_e_o_do_filtro():
    """A definicao do coletor e a do filtro tem que ser a mesma."""
    import shadow_sltp

    path = [[T0, 1, 2], [T0 + 2, 1, 2], [T0 + 4, 1, 2]]
    assert shadow_sltp.max_gap_s(T0, path, 5.0) == f.max_gap_s(
        {"ts": TS, "duracao_s": 5.0, "path": path})
