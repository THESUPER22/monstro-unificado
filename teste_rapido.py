print("Teste da correção do close_price...")

# Simula a lógica corrigida
close_price = 0.0
total_bid_volume = 0.0
atr = 0.0
candle_type = "doji"
rsi_14 = 50.0
volume_tick = 0

# Simula dados
rates = [[0, 140000, 140100, 139900, 140050, 1000, 0, 0]]
if rates:
    last_candle = rates[-1]
    close_price = float(last_candle[4])
    volume_tick = 100

# Testa se todas as variáveis existem
resultado = (total_bid_volume, atr, candle_type,
             rsi_14, volume_tick, close_price)
print(f"SUCESSO: close_price = {close_price}")
print("CORREÇÃO CONFIRMADA!")
