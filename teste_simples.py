print("Testando contagem de acoes...")

# Simula o dicionario
contagem_acoes = {"BUY": 0, "SELL": 0, "NADA": 0, "NAO_AGIU": 0}

# Simula adicionar experiencias
acoes_teste = ["BUY", "BUY", "SELL", "SELL", "SELL", "NAO_AGIU", "NAO_AGIU"]

for acao in acoes_teste:
    if acao in contagem_acoes:
        contagem_acoes[acao] += 1
    else:
        contagem_acoes[acao] = 1

print(f"BUY: {contagem_acoes['BUY']}")
print(f"SELL: {contagem_acoes['SELL']}")
print(f"NAO_AGIU: {contagem_acoes['NAO_AGIU']}")

total_operacoes = contagem_acoes["BUY"] + contagem_acoes["SELL"]
if total_operacoes > 0:
    razao = contagem_acoes["BUY"] / total_operacoes
    print(f"Razao BUY/SELL: {razao:.3f}")
else:
    print("Razao BUY/SELL: 0.000")
