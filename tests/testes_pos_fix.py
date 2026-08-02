#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testes_pos_fix.py

Testes automatizados pós-fix (Sessão 17).
Checagens determinísticas que rodam SEM MT5 (mercado fechado / staging):
 1. mutex : CreateMutexW só deve existir dentro de if __name__ == "__main__"
 2. sys.exit: nenhum sys.exit( espalhado (só _sys.exit(0) no mutex em __main__)
 3. entropia: nenhuma comparação de entropia em escala [0,1]
 4. parada : parar.txt sempre via _caminho_dados (absoluto) - sem caminho relativo
 5. csv : integridade de decisions_wdo.csv e historico_contexto_wdo.csv

Observação: o shutdown coordenado (fechar posições + salvar dados + os._exit)
não é testável aqui (exige MT5). Deve ser validado manualmente conforme ROADMAP.
"""
import io
import os
import re
import sys
import csv

# BASE aponta para a raiz do projeto (um nível acima de tests/)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V22 = os.path.join(BASE, "monstro_unificado_v22.py")
FALHAS = []

def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print(f"[{status}] {nome}" + (f" - {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(f"{nome}: {detalhe}")

def ler_v22():
    with io.open(V22, "r", encoding="utf-8-sig") as f:
        return f.read()

def teste_mutex(src):
    idx_main = src.find('if __name__ == "__main__":')
    idx_mutex = src.find("CreateMutexW")
    dentro_main = (idx_mutex > idx_main) if idx_mutex != -1 and idx_main != -1 else False
    antes_main = src[:idx_main].count("CreateMutexW") == 0 if idx_main != -1 else True
    checar("Mutex dentro de __main__", dentro_main, f"mutex pos={idx_mutex} main pos={idx_main}")
    checar("Mutex ausente antes do __main__", antes_main)

def teste_sys_exit(src):
    # Identifica chamadas reais de sys.exit (não comentários) e permite _sys.exit(0) no __main__
    linhas = src.splitlines()
    achados = []
    for i, linha in enumerate(linhas, 1):
        if 'sys.exit' in linha and not linha.strip().startswith('#'):
            # ignora _sys.exit(0) se estiver dentro do bloco __main__ (heurística)
            if '_sys.exit(0)' in linha:
                continue
            achados.append((i, linha.strip()))
    checar("Sem sys.exit( reais espalhados", len(achados) == 0, f"achados={achados[:5]}")

def teste_entropia_escala(src):
    # procura comparações do tipo entropia < 0.x ou entropia <= 0.x
    # [<>]=? casa '<', '>', '<=', '>=' — NÃO '=' sozinho (evita atribuições como 'entropia_book = 0.0')
    padrao = re.compile(r"(entropia\w*|entropy\w*)\s*[<>]=?\s*0\.\d+")
    achados = [l for l in src.splitlines() if padrao.search(l) and not l.strip().startswith('#')]
    checar("Sem comparacoes de entropia em escala [0,1]", len(achados) == 0, f"exemplos={achados[:5]}")

def teste_parar_txt(src):
    # verifica se a função verificar_parada_gracil usa _caminho_dados("parar.txt")
    func_pos = src.find("def verificar_parada_gracil")
    if func_pos == -1:
        checar("verificar_parada_gracil presente", False)
        return
    trecho = src[func_pos: func_pos + 2000]
    relativo = 'os.path.exists("parar.txt")' in trecho
    absoluto = '_caminho_dados("parar.txt")' in trecho
    checar("parar.txt via _caminho_dados (absoluto)", absoluto and not relativo)

def teste_csv_estrutura(caminho, colunas_esperadas):
    if not os.path.exists(caminho):
        checar(f"CSV existe ({os.path.basename(caminho)})", False)
        return None
    with io.open(caminho, 'r', encoding='utf-8-sig') as f:
        leitor = csv.DictReader(f)
        headers = leitor.fieldnames or []
        linhas = list(leitor)
    checar(f"CSV colunas corretas ({os.path.basename(caminho)})", set(colunas_esperadas) <= set(headers),
          f"faltando: {set(colunas_esperadas) - set(headers)}")
    return headers, linhas

def teste_csv_dados():
    cols_decisions = ["bid_qty", "ask_qty", "entropia_book", "rsi_14", "volume_tick"]
    res = teste_csv_estrutura(os.path.join(BASE, "decisions_wdo.csv"), cols_decisions)
    if res:
        _, linhas = res
        if linhas:
            entropias = [float(l["entropia_book"]) for l in linhas if l.get("entropia_book")]
            truncadas = [e for e in entropias if 0 < e <= 1.0]
            checar("decisions_wdo: entropia NAO truncada em [0,1]", len(truncadas) == 0,
                  f"truncadas={len(truncadas)}/{len(entropias)}")
            bqs = [float(l["bid_qty"]) for l in linhas if l.get("bid_qty")]
            checar("decisions_wdo: bid_qty reais (nao todos zero)", any(b > 0 for b in bqs),
                  f"max bid_qty={max(bqs) if bqs else 0}")
    cols_hist = ["entropia_book", "bid_qty", "ask_qty", "volume_tick", "action"]
    teste_csv_estrutura(os.path.join(BASE, "historico_contexto_wdo.csv"), cols_hist)

def main():
    print("=" * 60)
    print("TESTES POS-FIX - Sessao 17 (sem MT5)")
    print("=" * 60)
    src = ler_v22()
    teste_mutex(src)
    teste_sys_exit(src)
    teste_entropia_escala(src)
    teste_parar_txt(src)
    teste_csv_dados()
    print("-" * 60)
    if FALHAS:
        print(f"RESULTADO: {len(FALHAS)} FALHA(S)")
        for f in FALHAS:
            print(f"  X {f}")
        sys.exit(1)
    print("RESULTADO: TODOS OS TESTES PASSARAM")
    sys.exit(0)

if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
"""Testes automatizados pós-fix (Sessão 17).

Checagens determinísticas que rodam SEM MT5 (mercado fechado / staging):
  1. mutex  : CreateMutexW só deve existir dentro de if __name__ == "__main__"
  2. sys.exit: nenhum sys.exit( espalhado (só _sys.exit(0) no mutex em __main__)
  3. entropia: nenhuma comparação de entropia em escala [0,1] (deve ser 2.x)
  4. parada  : parar.txt sempre via _caminho_dados (absoluto) - sem caminho relativo
  5. csv     : integridade de decisions_wdo.csv e historico_contexto_wdo.csv
                (colunas, entropia não truncada em 1.0, bid/ask reais)

O shutdown coordenado (fechar posições + salvar + os._exit) NÃO é testável aqui:
exige MT5 + mercado. Deve ser validado manualmente no checklist do ROADMAP.
"""
import csv
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V22 = os.path.join(BASE, "monstro_unificado_v22.py")

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(f"{nome}: {detalhe}")


def ler_v22():
    with io.open(V22, "r", encoding="utf-8-sig") as f:
        return f.read()


def teste_mutex(src):
    """CreateMutexW deve existir apenas DENTRO do bloco __main__."""
    idx_main = src.find('if __name__ == "__main__":')
    idx_mutex = src.find("CreateMutexW")
    dentro_main = idx_mutex > idx_main
    # Não deve haver CreateMutexW antes do main
    antes_main = src[:idx_main].count("CreateMutexW") == 0
    checar("Mutex dentro de __main__", dentro_main,
           f"mutex em {idx_mutex}, main em {idx_main}")
    checar("Mutex ausente antes do __main__", antes_main)


def teste_sys_exit(src):
    """Nenhum sys.exit( espalhado. Permitido: _sys.exit(0) do mutex em __main__."""
    # Filtra o _sys.exit(0) do mutex (linha dentro do __main__) e linhas de comentário
    reais = []
    for num, linha in enumerate(src.splitlines(), 1):
        if "_sys.exit(0)" in linha and 'if __name__ == "__main__":' in src[:src.find(linha)]:
            continue  # mutex no __main__ - permitido
        if linha.strip().startswith("#") or "sys.exit" in linha and linha.strip().startswith("#"):
            continue
        if re.search(r"\bsys\.exit\s*\(", linha):
            reais.append(f"linha {num}: {linha.strip()}")
    checar("Sem sys.exit( reais espalhados", not reais, f"{reais[:3]}")


def teste_entropia_escala(src):
    """Nenhuma comparação entropia < 0.x ou > 0.x (escala [0,1])."""
    # Ignora comentários e docstrings aproximados: remove linhas de comentário
    linhas_ok = []
    em_docstring = False
    for linha in src.splitlines():
        if '"""' in linha or "'''" in linha:
            em_docstring = not em_docstring
            continue
        if em_docstring or linha.strip().startswith("#"):
            continue
        linhas_ok.append(linha)
    body = "\n".join(linhas_ok)
    padrao = re.compile(r"(entropia\w*|entropy\w*)\s*[<>]=?\s*0\.\d+")
    achados = [l.strip() for l in body.splitlines() if padrao.search(l)]
    checar("Sem comparações de entropia em escala [0,1]", not achados,
           f"{achados[:5]}" if achados else "")


def teste_parar_txt(src):
    """verificar_parada_gracil deve usar _caminho_dados (absoluto), não relativo."""
    funcao = src[src.find("def verificar_parada_gracil"):]
    funcao = funcao[: funcao.find("\ndef ")]
    relativo = 'os.path.exists("parar.txt")' in funcao
    absoluto = '_caminho_dados("parar.txt")' in funcao
    checar("parar.txt via _caminho_dados (absoluto)", absoluto and not relativo)


def teste_csv_estrutura(caminho, colunas_esperadas):
    if not os.path.exists(caminho):
        checar(f"CSV existe ({os.path.basename(caminho)})", False)
        return
    with io.open(caminho, "r", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        headers = leitor.fieldnames or []
        linhas = list(leitor)
    checar(f"CSV colunas corretas ({os.path.basename(caminho)})",
           set(colunas_esperadas) <= set(headers),
           f"faltando: {set(colunas_esperadas) - set(headers)}")
    return headers, linhas


def teste_csv_dados():
    cols_decisions = ["bid_qty", "ask_qty", "entropia_book", "rsi_14", "volume_tick"]
    res = teste_csv_estrutura(os.path.join(BASE, "decisions_wdo.csv"), cols_decisions)
    if res:
        _, linhas = res
        if linhas:
            entropias = [float(l["entropia_book"]) for l in linhas if l.get("entropia_book")]
            truncadas = [e for e in entropias if 0 < e <= 1.0]
            checar("decisions_wdo: entropia NÃO truncada em [0,1]", len(truncadas) == 0,
                   f"{len(truncadas)}/{len(entropias)} linhas com entropia <= 1.0")
            bqs = [float(l["bid_qty"]) for l in linhas if l.get("bid_qty")]
            checar("decisions_wdo: bid_qty reais (não todos zero)",
                   any(b > 0 for b in bqs), f"max bid_qty={max(bqs) if bqs else 0}")

    cols_hist = ["entropia_book", "bid_qty", "ask_qty", "volume_tick", "action"]
    teste_csv_estrutura(os.path.join(BASE, "historico_contexto_wdo.csv"), cols_hist)


def main():
    print("=" * 60)
    print("TESTES PÓS-FIX — Sessão 17 (sem MT5)")
    print("=" * 60)
    src = ler_v22()
    teste_mutex(src)
    teste_sys_exit(src)
    teste_entropia_escala(src)
    teste_parar_txt(src)
    teste_csv_dados()
    print("-" * 60)
    if FALHAS:
        print(f"RESULTADO: {len(FALHAS)} FALHA(S)")
        for f in FALHAS:
            print(f"  X {f}")
        sys.exit(1)
    print("RESULTADO: TODOS OS TESTES PASSARAM")
    sys.exit(0)


if __name__ == "__main__":
    main()
