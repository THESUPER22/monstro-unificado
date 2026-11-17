"""Le os logs de 17/11/2026 e resume: clipping, modelo, execucao, startup oculto.

SOMENTE LEITURA. Nao escreve em nada alem do JSON de saida em logs/.
"""
from __future__ import annotations

import io
import json
import os
import re
from collections import Counter

BASE = r"C:\AIOFEN"
LOG = os.path.join(BASE, "monstro_wdo.log")
HOJE = "2026-11-17"
ONTEM = "2026-11-16"

res = {"log": LOG, "existe": os.path.exists(LOG)}

# ---------- varredura principal ----------
pat_data = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")
clip_novo = re.compile(r"(\d+) valores fora de \[0,1\] clipped nos ultimos")
clip_velho = re.compile(r"(\d+) valores fora de \[0,1\] foram clipped")
feat = re.compile(r"\(features: ([^)]*)\)")

hoje = {
    "linhas": 0, "clip_warnings": 0, "clip_total": 0, "clip_por_feature": Counter(),
    "clip_velho": 0, "clip_velho_total": 0,
    "invalid_stops": 0, "erros": 0, "warnings": 0,
    "modelo_ok": 0, "modelo_falhou": 0, "modelo_novo": 0,
    "scaler_ok": 0, "scaler_dummy": 0, "migrar_l2": 0,
    "primeiro": None, "ultimo": None,
}
ontem = {"clip_velho": 0, "clip_velho_total": 0}

for linha in io.open(LOG, encoding="utf-8", errors="replace"):
    m = pat_data.match(linha)
    dia = m.group(1) if m else None
    if dia == ONTEM:
        mm = clip_velho.search(linha)
        if mm:
            ontem["clip_velho"] += 1
            ontem["clip_velho_total"] += int(mm.group(1))
        continue
    if dia != HOJE:
        continue

    hoje["linhas"] += 1
    hhmmss = m.group(2)
    if hoje["primeiro"] is None:
        hoje["primeiro"] = hhmmss
    hoje["ultimo"] = hhmmss

    mm = clip_novo.search(linha)
    if mm:
        hoje["clip_warnings"] += 1
        hoje["clip_total"] += int(mm.group(1))
        mf = feat.search(linha)
        if mf:
            for par in mf.group(1).split(","):
                if "=" in par:
                    k, v = par.strip().split("=", 1)
                    hoje["clip_por_feature"][k] += int(v)
        continue
    mm = clip_velho.search(linha)
    if mm:
        hoje["clip_velho"] += 1
        hoje["clip_velho_total"] += int(mm.group(1))

    if "10016" in linha or "Invalid stops" in linha:
        hoje["invalid_stops"] += 1
    if "[carregar_modelo] Modelo carregado" in linha:
        hoje["modelo_ok"] += 1
    if "[carregar_modelo] Erro" in linha or "Artefato preservado" in linha:
        hoje["modelo_falhou"] += 1
    if "Modelo nao encontrado" in linha or "Modelo n\u00e3o encontrado" in linha:
        hoje["modelo_novo"] += 1
    if "Scaler carregado do treinamento offline" in linha:
        hoje["scaler_ok"] += 1
    if "Scaler global recriado" in linha or "usando dados dummy" in linha:
        hoje["scaler_dummy"] += 1
    if "_migrar_modelo_l2" in linha or "migrar_modelo_l2" in linha:
        hoje["migrar_l2"] += 1
    if " - ERROR - " in linha or " ERROR " in linha:
        hoje["erros"] += 1
    if " - WARNING - " in linha or " WARNING " in linha:
        hoje["warnings"] += 1

hoje["clip_por_feature"] = dict(hoje["clip_por_feature"].most_common())
res["hoje"] = hoje
res["ontem"] = ontem

# ---------- arquivos de console das tarefas ----------
consoles = {}
for nome in ("start_all_console.log", "monstro_console.log", "watchdog_console.log",
             "fecho_console.log", "herman_console.log"):
    p = os.path.join(BASE, "logs", nome)
    if not os.path.exists(p):
        consoles[nome] = {"existe": False}
        continue
    st = os.stat(p)
    import datetime as _dt
    linhas = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    consoles[nome] = {
        "existe": True,
        "bytes": st.st_size,
        "modificado": _dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "n_linhas": len(linhas),
        "primeiras": linhas[:6],
        "ultimas": linhas[-8:],
    }
res["consoles"] = consoles

with open(os.path.join(BASE, "logs", "_autopsia_17_11_logs.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=True, indent=1, default=str)

print(json.dumps(res["hoje"], ensure_ascii=True, indent=1))
print("ontem:", json.dumps(res["ontem"], ensure_ascii=True))
print("consoles:", {k: {kk: vv for kk, vv in v.items() if kk in ("existe", "bytes", "n_linhas", "modificado")}
                    for k, v in consoles.items()})
