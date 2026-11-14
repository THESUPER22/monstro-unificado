# -*- coding: utf-8 -*-
"""
vwap_fade_diagnostico.py — EXPLORATORIO (nao promove nada).

Motivo: a grade PRE-REGISTRADA do vwap_fade_wdo.py falhou em todas as 27
combinacoes, inclusive com slippage 0. Diagnostico para entender POR QUE:

  (a) z>=1,5 dispara em ~99,5% dos dias -> o "primeiro cruzamento" nao e um
      extremo, e ruido. Testar limiares de extremo real (z>=3/4/5).
  (b) o fade perde dinheiro; o lado OPOSTO (momentum) ganha? Rodar o mirror.
  (c) a rejeicao vem do stop curto? Testar saida so por tempo (stop ~8 sigma).

Nada aqui autoriza promocao. Qualquer coisa positiva ainda teria que passar
gate + walk-forward + Monte Carlo num pre-registro novo.

Uso:
    python backtest/vwap_fade_diagnostico.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filtros_faixa1 import load_m1  # noqa: E402
from vwap_fade_wdo import (  # noqa: E402
    avaliar, coletar, gate, preparar_dias, sinal_dia,
)
from backtest_trailing_faixa1 import linha, stats  # noqa: E402

Z_EXT = (3.0, 4.0, 5.0)
K_EXT = (2.0, 3.0, 4.0)


def main() -> None:
    m1 = load_m1("WDO$", datetime(2021, 11, 1))
    dias = preparar_dias(m1)
    print("=" * 112)
    print(f"DIAGNOSTICO VWAP FADE | dias={len(dias)} | EXPLORATORIO")
    print("=" * 112)

    print("\n--- frequencia em extremos reais ---")
    for z in (1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        n = sum(1 for d in dias.values() if sinal_dia(d, z) is not None)
        print(f"  z>={z:.1f}  dias com sinal = {n:>4}  "
              f"({100.0*n/len(dias):.1f}% dos dias)")

    print("\n--- (a) extremos reais: fade normal, slip 1.0 ---")
    print(f"  {'z':>4} {'kSL':>4} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} "
          f"{'OOS exp':>7} {'OOS PF':>5}  gate")
    for z in Z_EXT:
        for k in K_EXT:
            tr = coletar(dias, z, k, 1.0)
            v, vis, voos = avaliar(tr, "x")
            print(f"  {z:>4.1f} {k:>4.1f} {v.get('n',0):>4} "
                  f"{v.get('win%',0):>5.1f} {v.get('exp_rs',0):>7.2f} "
                  f"{v.get('pf',0):>5.2f} {v.get('total_rs',0):>7.0f} | "
                  f"{vis.get('exp_rs',0):>7.2f} {vis.get('pf',0):>5.2f} "
                  f"{voos.get('n',0):>5} {voos.get('exp_rs',0):>7.2f} "
                  f"{voos.get('pf',0):>5.2f}  {'PASSA' if gate(vis, voos) else 'nao'}")

    print("\n--- (b) mirror (momentum) na grade pre-registrada, slip 1.0 ---")
    print(f"  {'z':>4} {'kSL':>4} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} "
          f"{'OOS exp':>7} {'OOS PF':>5}  gate")
    for z in (1.5, 2.0, 2.5):
        for k in (1.0, 1.5, 2.0):
            tr = coletar(dias, z, k, 1.0, side_mode="mirror")
            v, vis, voos = avaliar(tr, "x")
            print(f"  {z:>4.1f} {k:>4.1f} {v.get('n',0):>4} "
                  f"{v.get('win%',0):>5.1f} {v.get('exp_rs',0):>7.2f} "
                  f"{v.get('pf',0):>5.2f} {v.get('total_rs',0):>7.0f} | "
                  f"{vis.get('exp_rs',0):>7.2f} {vis.get('pf',0):>5.2f} "
                  f"{voos.get('n',0):>5} {voos.get('exp_rs',0):>7.2f} "
                  f"{voos.get('pf',0):>5.2f}  {'PASSA' if gate(vis, voos) else 'nao'}")

    print("\n--- (c) saida so por tempo (kSL=8 ~ sem stop), slip 1.0 ---")
    print(f"  {'z':>4} {'lado':>7} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} "
          f"{'OOS exp':>7} {'OOS PF':>5}")
    for z in (1.5, 2.0, 3.0, 4.0):
        for mode, lbl in (("normal", "fade"), ("mirror", "moment")):
            tr = coletar(dias, z, 8.0, 1.0, side_mode=mode)
            v, vis, voos = avaliar(tr, "x")
            print(f"  {z:>4.1f} {lbl:>7} {v.get('n',0):>4} "
                  f"{v.get('win%',0):>5.1f} {v.get('exp_rs',0):>7.2f} "
                  f"{v.get('pf',0):>5.2f} {v.get('total_rs',0):>7.0f} | "
                  f"{vis.get('exp_rs',0):>7.2f} {vis.get('pf',0):>5.2f} "
                  f"{voos.get('n',0):>5} {voos.get('exp_rs',0):>7.2f} "
                  f"{voos.get('pf',0):>5.2f}")

    # detalhe dos melhores esforcos (so para leitura, nao promocao)
    print("\n--- detalhe por ano: melhores esforcos (slip 1.0) ---")
    for z, k, mode, lbl in ((2.0, 1.5, "mirror", "mirror z2.0 k1.5"),
                            (2.5, 2.0, "mirror", "mirror z2.5 k2.0"),
                            (4.0, 3.0, "normal", "fade z4.0 k3.0")):
        tr = coletar(dias, z, k, 1.0, side_mode=mode)
        print(f"\n  [{lbl}]")
        by = {}
        for t in tr:
            by.setdefault(t["year"], []).append(t)
        for y in sorted(by):
            print("    " + linha(stats(by[y], str(y))))
        print("    " + linha(stats(tr, "FULL")))


if __name__ == "__main__":
    main()
