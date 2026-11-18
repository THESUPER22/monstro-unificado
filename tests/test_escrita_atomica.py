#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_escrita_atomica.py  (P0 17/11 #4)

Testes do modulo escrita_atomica.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\test_escrita_atomica.py) ou via pytest.
"""
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from escrita_atomica import (  # noqa: E402
    caminho_temporario, salvar_atomico, salvar_texto_atomico)


def _dir():
    return tempfile.TemporaryDirectory()


# ------------------------------------------------------- caminho_temporario -
def test_temporario_mesmo_diretorio_e_extensao():
    with _dir() as d:
        alvo = os.path.join(d, "experiencias_wdo.json")
        tmp = caminho_temporario(alvo)
        assert os.path.dirname(tmp) == os.path.abspath(d)
        assert tmp.endswith(".json")
        assert os.path.basename(tmp).startswith("experiencias_wdo__tmp_")
        assert tmp != os.path.abspath(alvo)


def test_temporarios_unicos_por_chamada():
    with _dir() as d:
        alvo = os.path.join(d, "a.json")
        assert caminho_temporario(alvo) != caminho_temporario(alvo)


def test_temporario_preserva_extensao_composta():
    with _dir() as d:
        alvo = os.path.join(d, "modelo.tar.gz")
        assert caminho_temporario(alvo).endswith(".gz")
        alvo2 = os.path.join(d, "modelo_monstro_wdo.keras")
        assert caminho_temporario(alvo2).endswith(".keras")


# ------------------------------------------------------------ salvar_texto -
def test_salva_conteudo():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        destino = salvar_texto_atomico(alvo, "linha 1\nlinha 2\n")
        assert destino == os.path.abspath(alvo)
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "linha 1\nlinha 2\n"


def test_substitui_arquivo_existente():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        with open(alvo, "w", encoding="utf-8") as f:
            f.write("antigo")
        salvar_texto_atomico(alvo, "novo")
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "novo"


def test_sem_temporario_remanescente():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        salvar_texto_atomico(alvo, "x")
        assert os.listdir(d) == ["saida.txt"]


def test_unicode_utf8_roundtrip():
    with _dir() as d:
        alvo = os.path.join(d, "acentos.txt")
        texto = "confluencia insuficiente - opera\u00e7\u00e3o encerrada\n"
        salvar_texto_atomico(alvo, texto)
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == texto


def test_json_roundtrip_com_escritor():
    with _dir() as d:
        alvo = os.path.join(d, "exp.json")
        dados = [{"acao": "BUY", "lucro": 25.0}, {"acao": "SELL", "lucro": 10.0}]
        salvar_atomico(alvo, lambda f: json.dump(dados, f, indent=2))
        with open(alvo, encoding="utf-8") as f:
            assert json.load(f) == dados
        assert os.listdir(d) == ["exp.json"]


def test_escritor_recebe_arquivo_texto_aberto():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        visto = {}

        def escritor(f):
            visto["modo"] = f.mode
            visto["encoding"] = f.encoding
            f.write("ok")

        salvar_atomico(alvo, escritor)
        assert "w" in visto["modo"]
        assert visto["encoding"].lower().replace("-", "") == "utf8"


# --------------------------------------------------------------- falhas -----
def test_falha_do_escritor_preserva_original():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        with open(alvo, "w", encoding="utf-8") as f:
            f.write("original")

        def explode(f):
            f.write("parcial")
            raise RuntimeError("falha simulada")

        try:
            salvar_atomico(alvo, explode)
        except RuntimeError:
            pass
        else:
            raise AssertionError("RuntimeError deveria propagar")

        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "original"
        assert os.listdir(d) == ["saida.txt"]      # nenhum temporario sobrou


def test_falha_em_arquivo_novo_nao_cria_destino():
    with _dir() as d:
        alvo = os.path.join(d, "novo.json")

        def explode(f):
            f.write("{parcial")
            raise ValueError("boom")

        try:
            salvar_atomico(alvo, explode)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError deveria propagar")

        assert not os.path.exists(alvo)
        assert os.listdir(d) == []


def test_diretorio_inexistente_falha_sem_lixo():
    with _dir() as d:
        alvo = os.path.join(d, "nao_existe", "saida.txt")
        try:
            salvar_texto_atomico(alvo, "x")
        except OSError:
            pass
        else:
            raise AssertionError("OSError deveria propagar")
        assert os.listdir(d) == []


# ----------------------------------------------------------- retry replace -
def _com_replace_fake(fake, fn):
    """Executa fn com escrita_atomica.os.replace/time.sleep trocados."""
    import escrita_atomica
    real_replace = escrita_atomica.os.replace
    real_sleep = escrita_atomica.time.sleep
    esperas = []

    def fake_sleep(s):
        esperas.append(s)

    escrita_atomica.os.replace = fake
    escrita_atomica.time.sleep = fake_sleep
    try:
        fn()
    finally:
        escrita_atomica.os.replace = real_replace
        escrita_atomica.time.sleep = real_sleep
    return esperas


def test_replace_retry_vence_permissionerror_temporario():
    """os.replace bloqueado 3x ainda grava (5 tentativas, 100 ms entre elas)."""
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        real = os.replace
        chamadas = {"n": 0}

        def fake(origem, destino):
            chamadas["n"] += 1
            if chamadas["n"] <= 3:
                raise PermissionError("arquivo em uso")
            return real(origem, destino)

        esperas = _com_replace_fake(
            fake, lambda: salvar_texto_atomico(alvo, "ok"))

        assert chamadas["n"] == 4
        assert esperas == [0.1, 0.1, 0.1]
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "ok"
        assert os.listdir(d) == ["saida.txt"]      # nenhum temporario sobrou


def test_replace_retry_desiste_apos_5_e_preserva_original():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        with open(alvo, "w", encoding="utf-8") as f:
            f.write("original")
        chamadas = {"n": 0}

        def fake(origem, destino):
            chamadas["n"] += 1
            raise PermissionError("bloqueado para sempre")

        try:
            _com_replace_fake(
                fake, lambda: salvar_texto_atomico(alvo, "novo"))
        except PermissionError:
            pass
        else:
            raise AssertionError("PermissionError deveria propagar na 5a")

        assert chamadas["n"] == 5
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "original"
        assert os.listdir(d) == ["saida.txt"]


def test_replace_sem_erro_nao_espera():
    with _dir() as d:
        alvo = os.path.join(d, "saida.txt")
        esperas = _com_replace_fake(
            os.replace, lambda: salvar_texto_atomico(alvo, "ok"))
        assert esperas == []
        with open(alvo, encoding="utf-8") as f:
            assert f.read() == "ok"


# ------------------------------------------------------------- integracao ---
def _fonte_robo():
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        return f.read()


def test_robo_usa_escrita_atomica_em_experiencias():
    """Guard: salvar_experiencias_json grava via salvar_texto_atomico."""
    fonte = _fonte_robo()
    assert "from escrita_atomica import salvar_texto_atomico" in fonte
    assert 'ESCRITA_ATOMICA = _ENCERRAMENTO_CFG.get("escrita_atomica", True)' in fonte
    inicio = fonte.index("def salvar_experiencias_json(")
    fim = fonte.index("\ndef ", inicio + 1)
    corpo = fonte[inicio:fim]
    assert "if ESCRITA_ATOMICA:" in corpo
    assert "salvar_texto_atomico(arquivo, texto)" in corpo
    # o open() direto so pode existir como fallback, depois do caminho atomico
    assert corpo.index("salvar_texto_atomico(") < corpo.index("with open(arquivo, 'w') as f:")


def test_robo_grava_parado_ok_depois_da_trava_c3():
    fonte = _fonte_robo()
    trava = fonte.index("SHUTDOWN BLOQUEADO: %d posicao(oes) seguem abertas")
    ok = fonte.index('_caminho_dados("parado.ok")')
    fim = fonte.index("thread_ativo = False", trava)
    assert trava < ok < fim


def test_agente_conhece_parado_ok():
    caminho = os.path.join(BASE, "agente_monstro_core.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    assert 'PARADO_OK = os.path.join(BASE_DIR, "parado.ok")' in fonte
    inicio = fonte.index("def parar_gracioso(")
    fim = fonte.index("\ndef ", inicio + 1)
    corpo = fonte[inicio:fim]
    assert "PARADO_OK" in corpo


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"[PASS] {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"[FAIL] {nome} - {e}")
    print(f"\n{'OK' if not falhas else 'FALHAS'}: {falhas}")
    sys.exit(1 if falhas else 0)
