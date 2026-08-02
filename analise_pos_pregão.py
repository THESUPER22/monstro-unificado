import csv, json
from collections import Counter

print('='*70)
print('ANALISE POS-PREGAO 29/07/2026')
print('='*70)

# ===== 1. historico_contexto_wdo.csv =====
print('\n[1] HISTORICO_CONTEXTO_WDO.CSV (trades reais)')
trades = []
with open('C:\\AIOFEN\\historico_contexto_wdo.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['action'] in ('BUY','SELL'):
            trades.append(row)
total_rows = sum(1 for _ in open('C:\\AIOFEN\\historico_contexto_wdo.csv')) - 1
print(f'  Registros totais: {total_rows}')
print(f'  Trades identificados: {len(trades)}')
actions = Counter(t['action'] for t in trades)
print(f'  Acoes: {dict(actions)}')
rewards = [float(t['reward']) for t in trades]
print(f'  Rewards individuais (pts): {rewards}')
total_pl = sum(rewards)
wins = sum(1 for r in rewards if r > 0)
losses = sum(1 for r in rewards if r < 0)
evens = sum(1 for r in rewards if r == 0)
print(f'  Total P&L: {total_pl:.1f} pts = R$ {total_pl*10:.2f}')
print(f'  Wins: {wins} | Losses: {losses} | Even: {evens}')
wr = wins/(wins+losses)*100 if (wins+losses)>0 else 0
print(f'  Winrate: {wr:.1f}%')
print(f'  Avg Win: {sum(r for r in rewards if r>0)/wins:.1f}' if wins>0 else '', end='')
print(f'  Avg Loss: {sum(r for r in rewards if r<0)/losses:.1f}' if losses>0 else '')
print()

# Trade-a-trade
print('--- TRADE-A-TRADE ---')
for i, t in enumerate(trades):
    print(f'\nTrade #{i+1}: {t["action"]} reward={t["reward"]}pts')
    print(f'  RSI_14: {float(t["rsi_14"]):.1f} | Volatilidade: {float(t["volatility"]):.2f}')
    print(f'  Candle: {t["candle_type"]} | Spread: {t["spread"]}')
    print(f'  Entropia Book: {float(t["entropia_book"]):.2f}')
    print(f'  Liquidez BID top5: {t["liquidez_top5_bid"]} | ASK top5: {t["liquidez_top5_ask"]}')
    print(f'  Escora BID: {t["preco_maior_escora_bid"]} vol={t["volume_maior_escora_bid"]} dist={t["distancia_maior_escora_bid"]}')
    print(f'  Escora ASK: {t["preco_maior_escora_ask"]} vol={t["volume_maior_escora_ask"]} dist={t["distancia_maior_escora_ask"]}')

# ===== 2. experiencias_wdo.json =====
print('\n[2] EXPERIENCIAS_WDO.JSON (ML experiences)')
with open('C:\\AIOFEN\\experiencias_wdo.json') as f:
    exp = json.load(f)
print(f'  Total experiencias: {len(exp)}')
if exp:
    print(f'  Keys do primeiro registro: {list(exp[0].keys())}')
    reward_exp = [e.get('reward', 0) for e in exp]
    pos_exp = sum(1 for r in reward_exp if r > 0)
    neg_exp = sum(1 for r in reward_exp if r < 0)
    zero_exp = sum(1 for r in reward_exp if r == 0)
    print(f'  Positivas: {pos_exp} | Negativas: {neg_exp} | Neutras: {zero_exp}')
    # Check status distribution
    status_exp = Counter(e.get('status', 'N/A') for e in exp)
    print(f'  Status: {dict(status_exp)}')

# ===== 3. sniper_supermo_historico.csv =====
print('\n[3] SNIPER_SUPERMO_HISTORICO.CSV')
try:
    with open('C:\\AIOFEN\\sniper_supermo_historico.csv') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f'  Total registros: {len(rows)}')
    if rows:
        print(f'  Colunas: {list(rows[0].keys())}')
        # Show last 10
        print(f'  Ultimos 5 registros:')
        for r in rows[-5:]:
            print(f'    {r}')
except Exception as e:
    print(f'  ERRO: {e}')

# ===== 4. williams_r_historico.csv =====
print('\n[4] WILLIAMS_R_HISTORICO.CSV')
try:
    with open('C:\\AIOFEN\\williams_r_historico.csv') as f:
        reader = csv.DictReader(f)
        rows_wr = list(reader)
    print(f'  Total registros: {len(rows_wr)}')
    if rows_wr:
        print(f'  Colunas: {list(rows_wr[0].keys())}')
        # Show last 10
        print(f'  Ultimos 5 registros:')
        for r in rows_wr[-5:]:
            print(f'    {r}')
        # Analyse WR values
        wr_vals = [float(r.get('williams_r', r.get('wr', 0))) for r in rows_wr if r.get('williams_r', r.get('wr', 'N/A')) != 'N/A']
        if wr_vals:
            oversold = sum(1 for v in wr_vals if v <= -80)
            overbought = sum(1 for v in wr_vals if v >= -20)
            print(f'  Oversold (WR <= -80): {oversold}')
            print(f'  Overbought (WR >= -20): {overbought}')
            print(f'  Media WR: {sum(wr_vals)/len(wr_vals):.1f}')
except Exception as e:
    print(f'  ERRO: {e}')

# ===== 5. decisions_wdo.csv =====
print('\n[5] DECISIONS_WDO.CSV')
try:
    with open('C:\\AIOFEN\\decisions_wdo.csv') as f:
        reader = csv.DictReader(f)
        dec = list(reader)
    print(f'  Total registros: {len(dec)}')
    dec_actions = Counter(d['acao'] for d in dec)
    print(f'  Decisoes: {dict(dec_actions)}')
except Exception as e:
    print(f'  ERRO: {e}')

print('\n' + '='*70)
print('FIM DA ANALISE')
