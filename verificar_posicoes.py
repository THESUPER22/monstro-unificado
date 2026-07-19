import sys

import MetaTrader5 as mt5

print("🔍 Verificando posições abertas...")

# Inicializa MT5
if not mt5.initialize():
    print("❌ Erro ao conectar MT5")
    sys.exit(1)

# Verifica posições
positions = mt5.positions_get()
num_positions = len(positions) if positions else 0

print(f"📊 POSIÇÕES ABERTAS: {num_positions}")

if positions:
    print("\n🚨 ATENÇÃO - POSIÇÕES ENCONTRADAS:")
    for pos in positions:
        tipo = "COMPRA" if pos.type == 0 else "VENDA"
        print(f"  Ticket: {pos.ticket}")
        print(f"  Tipo: {tipo}")
        print(f"  Volume: {pos.volume}")
        print(f"  Símbolo: {pos.symbol}")
        print(f"  Lucro: R$ {pos.profit:.2f}")
        print(f"  Magic: {pos.magic}")
        print("-" * 30)
else:
    print("✅ Nenhuma posição aberta - SEGURO PARA FECHAR")

mt5.shutdown()
mt5.shutdown()
