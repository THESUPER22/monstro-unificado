#!/usr/bin/env python3
import os
import MetaTrader5 as mt5

# Inicializa MT5
mt5.initialize()
terminal_info = mt5.terminal_info()
csv_path = os.path.join(terminal_info.data_path, 'MQL5', 'Files', 'book_data.csv')

print(f"📁 Caminho: {csv_path}")
print(f"📊 Existe: {os.path.exists(csv_path)}")

if os.path.exists(csv_path):
    size = os.path.getsize(csv_path)
    print(f"📏 Tamanho: {size} bytes")
    
    print("\n🔍 TESTANDO CODIFICAÇÕES:")
    for encoding in ['utf-16', 'utf-8', 'ascii', 'latin-1']:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            print(f"✅ {encoding}: {len(lines)} linhas")
            if len(lines) >= 2:
                print(f"   BID: {lines[0].strip()[:50]}...")
                print(f"   ASK: {lines[1].strip()[:50]}...")
                
                # Testa parsing
                bids_str = lines[0].strip()
                bids = [int(v) for v in bids_str.split(',') if v and v.strip().isdigit()]
                print(f"   BIDs válidos: {len(bids)}, Total: {sum(bids)}")
                break
        except Exception as e:
            print(f"❌ {encoding}: {e}")

mt5.shutdown() 