"""Fase 0 - Item 1: Popular experiencias_wdo.json com trades reais do CSV."""
import csv
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE, "experiencias_wdo.json")
CSV_PATH = os.path.join(BASE, "historico_contexto_wdo.csv")

# Carregar experiencias existentes
existing = []
if os.path.exists(JSON_PATH):
    with open(JSON_PATH, encoding="utf-8-sig") as f:
        existing = json.load(f)

# Chave de dedup: (timestamp aproximado, acao, lucro)
def chave(exp):
    return (exp.get("acao"), exp.get("lucro"), exp.get("contexto", {}).get("bid_qty"),
            exp.get("contexto", {}).get("ask_qty"))

existing_keys = {chave(e) for e in existing}

# Ler trades reais do CSV
with open(CSV_PATH, encoding="utf-8-sig") as f:
    trades = [r for r in csv.DictReader(f)
              if r.get("reward") not in (None, "", "0", "0.0")]

def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

novos = 0
for t in trades:
    ctx = {
        "bid_qty": to_float(t["bid_qty"]),
        "ask_qty": to_float(t["ask_qty"]),
        "spread": to_float(t["spread"]),
        "volatility": to_float(t["volatility"]),
        "candle_type": t.get("candle_type", "desconhecido"),
        "entropia_book": to_float(t["entropia_book"]),
        "rsi_14": to_float(t["rsi_14"]),
        "volume_tick": to_float(t["volume_tick"]),
        "is_in_trade": 0,
        "floating_profit": 0.0,
        "tempo_em_trade": 0,
        "preco": 0.0,
        "williams_r": -50.0,
        "wr_zona": "NEUTRO",
        "wr_divergencia": "NEUTRO",
        "dol_ratio": 1.0,
        "dol_lado": "NEUTRO",
        "dol_confianca": 0.0,
        "dol_presente": 0,
        "ptax": 0.0,
        "dolar_casado": 0.0,
        "em_janela_ptax": 0,
        "minutos_para_ptax": 60,
        "dia_ptax": 0,
        "payroll_ativado": 0,
        "sniper_bloqueado": 0,
        "tendencia_m1": "LATERAL",
        "preco_maior_escora_bid": to_float(t.get("preco_maior_escora_bid")),
        "volume_maior_escora_bid": to_float(t.get("volume_maior_escora_bid")),
        "distancia_maior_escora_bid": to_float(t.get("distancia_maior_escora_bid")),
        "preco_maior_escora_ask": to_float(t.get("preco_maior_escora_ask")),
        "volume_maior_escora_ask": to_float(t.get("volume_maior_escora_ask")),
        "distancia_maior_escora_ask": to_float(t.get("distancia_maior_escora_ask")),
        "liquidez_top5_bid": to_float(t.get("liquidez_top5_bid")),
        "liquidez_top5_ask": to_float(t.get("liquidez_top5_ask")),
        "m5_rsi": 50.0,
        "m5_atr": 0.0,
        "m5_wr": -50.0,
        "m15_rsi": 50.0,
        "m15_atr": 0.0,
        "m15_wr": -50.0,
        "m30_rsi": 50.0,
        "m30_atr": 0.0,
        "m30_wr": -50.0,
        "tendencia_veto_buy": False,
        "tendencia_veto_sell": False,
        "tendencia_motivo": "",
        "sniper_wr": 0,
        "sniper_sl_points": 8.0,
        "sniper_tp_points": 0.0,
    }
    exp = {
        "contexto": ctx,
        "acao": t["action"],
        "lucro": to_float(t["reward"]),  # reward ja em R$
        "score_dist": 0.0,
        "timestamp": t["timestamp"],
    }
    if chave(exp) in existing_keys:
        print(f"  SKIP (dup): {t['timestamp']} {t['action']} {t['reward']}")
        continue
    existing.append(exp)
    existing_keys.add(chave(exp))
    novos += 1
    print(f"  ADD: {t['timestamp']} {t['action']} {t['reward']}")

# Backup
backup = JSON_PATH + ".backup_pre_fase0"
if os.path.exists(JSON_PATH) and not os.path.exists(backup):
    import shutil
    shutil.copy2(JSON_PATH, backup)
    print(f"Backup criado: {backup}")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)

print(f"\nTOTAL: {len(existing)} experiencias ({novos} novas)")