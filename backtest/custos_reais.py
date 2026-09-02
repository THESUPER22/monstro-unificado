"""
Custos reais XP NOMOS com RLP ativo (5 contratos)
Valores validados em 01/09/2026 com assessoria NOMOS.
"""

# Custo por trade completo (entrada + saída), 5 contratos
CUSTO_TRADE_WIN_5CT = 1.25    # R$ 0,25/contrato (emolumentos B3 + RLP)
CUSTO_TRADE_WDO_5CT = 4.00    # R$ 0,80/contrato (emolumentos B3 + RLP)

# Valor por ponto (5 contratos)
VALOR_PONTO_WIN_5CT = 5.0     # R$ 1,00/pt * 5 = R$ 5,00/pt
VALOR_PONTO_WDO_5CT = 50.0    # R$ 10,00/pt * 5 = R$ 50,00/pt

# Slippage estimado com RLP ativo (pontos)
SLIPPAGE_PTS_WIN = 1.0       # 1-2 pts em condições normais
SLIPPAGE_PTS_WDO = 0.5       # 0.5-1 pts com RLP

# Fatores de conversão
TICK_SIZE_WIN = 0.5          # WIN: 0,5 pts = 1 tick
TICK_SIZE_WDO = 0.5          # WDO: 0,5 pts = 1 tick
TICKS_POR_PONTO_WIN = 2      # 1 ponto = 2 ticks (WIN)
TICKS_POR_PONTO_WDO = 2000   # WDO: 1 ponto = 2000 ticks

# Custos por ponto (para cálculos de P&L líquido)
CUSTO_POR_PONTO_WIN = CUSTO_TRADE_WIN_5CT / 1.0  # custo fixo por trade
CUSTO_POR_PONTO_WDO = CUSTO_TRADE_WDO_5CT / 1.0