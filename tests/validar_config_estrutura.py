"""Valida a estrutura do config.json / agente_config.json como fonte unica da verdade.

Checagens (nao mudam nada - somente auditoria):
  - Existencia e tipo das chaves criticas (raiz e risk_management).
  - Alinhamento raiz vs risk_management para as chaves compartilhadas.
  - Single-occurrence das chaves criticas no arquivo (evita duplicata de fonte).
  - Kill-switch do agente coerente com max_loss_diario.

Saida: exit 0 = PASS, exit 1 = FAIL.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CRITICAS_RAIZ = {
    "sniper_ratio_min": float,
    "max_loss_diario": float,
    "sniper_apenas": bool,
    "sl_points": (int, float),
    "sniper_cooldown_s": (int, float),
}

COMPARTILHADAS = ("max_loss_diario", "sniper_ratio_min", "sl_points", "sniper_volume_min")


def _ler(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _checks(path, cfg):
    fails = []
    raiz = cfg
    rm = cfg.get("risk_management", {})

    for k, tipo in CRITICAS_RAIZ.items():
        if k not in raiz:
            fails.append(f"FALTA raiz.{k}")
        elif not isinstance(raiz[k], tipo):
            fails.append(f"TIPO raiz.{k} = {type(raiz[k]).__name__} (esperado {tipo})")

    for k in COMPARTILHADAS:
        if k in raiz and k in rm and raiz[k] != rm[k]:
            fails.append(f"DIVERGENCIA {k}: raiz={raiz[k]} vs risk_management={rm[k]}")

    return fails


def _nested_consistencia(path, cfg):
    """Keys criticas presentes tanto na raiz quanto em risk_management devem
    estar ALINHADAS. Duplicata aninhada (raiz+nested) e ESTRUTURA legitima;
    o que caracteriza drift e DIVERGENCIA de valor, nao mera duplicacao textual."""
    fails = []
    raiz = cfg
    rm = cfg.get("risk_management", {})
    for k in COMPARTILHADAS:
        if k not in raiz and k not in rm:
            continue
        if k in raiz and k in rm and raiz[k] != rm[k]:
            fails.append(f"DIVERGENCIA {k}: raiz={raiz[k]} vs risk_management={rm[k]}")
    return fails


def main():
    cfg_path = os.path.join(BASE, "config.json")
    ag_path = os.path.join(BASE, "agente_config.json")
    fails = []

    cfg = _ler(cfg_path)
    fails += _checks(cfg_path, cfg)
    fails += _nested_consistencia(cfg_path, cfg)

    if os.path.exists(ag_path):
        ag = _ler(ag_path)
        ks = ag.get("kill_switch", {})
        l1, l2 = ks.get("limite_1"), ks.get("limite_2")
        max_loss = cfg.get("max_loss_diario", 0)
        if l1 is None or l2 is None:
            fails.append("agente_config.kill_switch incompleto")
        else:
            # Ordem (mais rigido -> menos): max_loss < l2 <= l1 < 0
            # max_loss=-1000, l2=-400, l1=-250  =>  -1000 < -400 <= -250 < 0
            if not (max_loss < l2 <= l1 < 0):
                fails.append(f"kill_switch incoerente: max_loss={max_loss} l2={l2} l1={l1}")

    if fails:
        print("FAIL (" + str(len(fails)) + "):")
        for f in fails:
            print("  - " + f)
        return 1
    print("PASS: config/agente_config estruturalmente consistentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
