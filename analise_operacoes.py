# Análise des de 04/08/2025
lucros_brutos = [
    -80, 35, 35, 35, 30, -90, 35, 35, 35, 35, 30, 35, 35, 35, 35, 35, 35,
    35, 35, -85, 35, -90, 35, 35, 35, -90, -90, 30, 35, 30, 35, -90, -90,
    -90, 5, 35, 35, 35, 35, -90, -90, 35, 35, 35, 35, 35, -90, -90, 35, 35, 30,
    10, -90, 35, 35, 35, 10, 5, 35, -90, 35, 35, 30, 35, 35, 5, 35, 35, 10,
    5, 5, 35, -90, 55, 35, 35, 35, 35, 10, 35, 10, 10, 35, 35, 35, 35, 35,
    10, 10, 35, 35, 35, -90, 5, -90, -90, 35, -30, 35, -90, 10, 35, -5, 35,
    35, -90, 10, 5, 35, -50, 35, 35, -90, 10, -90, 35, -45, 35, -55, 35, 35,
    -10, 35, 5, 35, 5, -90, -85, -90, 5, 35, 35, 35, -90, 35, -90, 35, 35,
    35, 5, 35, 35, 35, 0, 35, 35, 35, -45, 0, -25, 35, 35, 35, -90, 5, -95,
    -25, 5, -20, 35, -10, -90, 35, 35, 35, 35, 5, 35, 35, -50, -65, 35, 5,
    35, -50, -90, 35, 35, -90, -90, 35, -90, 35, -90, 35
]

total_ops = len(lucros_brutos)
lucro_bruto_total = sum(lucros_brutos)
custo_total = total_ops * 5  # R$ 5 por operação
lucro_liquido = lucro_bruto_total - custo_total

ops_positivas = len([l for l in lucros_brutos if l > 0])
ops_negativas = len([l for l in lucros_brutos if l < 0])
ops_zero = len([l for l in lucros_brutos if l == 0])

taxa_acerto = (ops_positivas / total_ops) * 100

print('🔥 ANÁLISE DEVASTADORA - OPERAÇÕES 04/08/2025')
print('=' * 50)
print(f'📊 Total de operações: {total_ops}')
print(
    f'✅ Operações positivas: {ops_positivas} ({ops_positivas/total_ops*100:.1f}%)')
print(
    f'❌ Operações negativas: {ops_negativas} ({ops_negativas/total_ops*100:.1f}%)')
print(f'⚪ Operações zero: {ops_zero}')
print(f'🎯 Taxa de acerto: {taxa_acerto:.1f}%')
print()
print('💰 RESULTADO FINANCEIRO:')
print(f'💵 Lucro bruto total: R$ {lucro_bruto_total:.2f}')
print(f'💸 Custo total ({total_ops} × R$ 5): R$ {custo_total:.2f}')
print(f'💀 LUCRO LÍQUIDO FINAL: R$ {lucro_liquido:.2f}')
print()
print('🔍 ANÁLISE DETALHADA:')
ops_35 = len([l for l in lucros_brutos if l == 35])
ops_30 = len([l for l in lucros_brutos if l == 30])
ops_10 = len([l for l in lucros_brutos if l == 10])
ops_5 = len([l for l in lucros_brutos if l == 5])
ops_90_neg = len([l for l in lucros_brutos if l == -90])

print(f'🎯 Operações R$ 35: {ops_35} ({ops_35/total_ops*100:.1f}%)')
print(f'🎯 Operações R$ 30: {ops_30} ({ops_30/total_ops*100:.1f}%)')
print(f'🎯 Operações R$ 10: {ops_10} ({ops_10/total_ops*100:.1f}%)')
print(f'🎯 Operações R$ 5: {ops_5} ({ops_5/total_ops*100:.1f}%)')
print(f'💀 Operações -R$ 90: {ops_90_neg} ({ops_90_neg/total_ops*100:.1f}%)')
print()
print('🚨 IMPACTO DOS CUSTOS:')
ops_que_viram_prejuizo = len([l for l in lucros_brutos if 0 < l < 5])
ops_lucro_liquido_positivo = len([l for l in lucros_brutos if l >= 5])
print(f'💀 Ops que viraram prejuízo: {ops_que_viram_prejuizo}')
print(f'✅ Ops com lucro líquido: {ops_lucro_liquido_positivo}')
print()
print('📈 LUCRO MÉDIO POR TRADE:')
print(f'Bruto: R$ {lucro_bruto_total/total_ops:.2f}')
print(f'Líquido: R$ {lucro_liquido/total_ops:.2f}')
print()
print('🎯 ANÁLISE APÓS CUSTOS:')
lucros_liquidos = [l - 5 for l in lucros_brutos]
ops_liquidas_positivas = len([l for l in lucros_liquidos if l > 0])
ops_liquidas_negativas = len([l for l in lucros_liquidos if l < 0])
ops_liquidas_zero = len([l for l in lucros_liquidos if l == 0])
taxa_acerto_liquida = (ops_liquidas_positivas / total_ops) * 100

print(
    f'✅ Operações líquidas positivas: {ops_liquidas_positivas} ({taxa_acerto_liquida:.1f}%)')
print(f'❌ Operações líquidas negativas: {ops_liquidas_negativas}')
print(f'⚪ Operações líquidas zero: {ops_liquidas_zero}')
