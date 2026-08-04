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

No CI (env CI=true) os checagens de CSV são SKIPPED, pois os dados (*.csv)
são gitignored e não existem no repositório.
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
EM_CI = os.environ.get("CI") == "true"

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
        if EM_CI:
            print(f"[SKIP] CSV ausente no CI ({os.path.basename(caminho)})")
            return None
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
