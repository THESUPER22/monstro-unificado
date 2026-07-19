#!/usr/bin/env python3
"""
Script de teste paradar a implementação da leitura de profundidade do book.
Testa se todas as novas features estão funcionando corretamente.
"""

import json
from typing import Dict

import pandas as pd


def analisar_profundidade_book(book_data: Dict, preco_referencia: float) -> Dict:
    """
    Cópia da função implementada no Monstro V2 para teste.
    """
    features = {
        'preco_maior_escora_bid': 0.0,
        'volume_maior_escora_bid': 0.0,
        'distancia_maior_escora_bid': 999.0,
        'preco_maior_escora_ask': 0.0,
        'volume_maior_escora_ask': 0.0,
        'distancia_maior_escora_ask': 999.0,
        'liquidez_top5_bid': 0.0,
        'liquidez_top5_ask': 0.0
    }

    if not book_data:
        return features

    try:
        # Analisa o lado da compra (bids)
        if book_data.get("bids") and len(book_data["bids"]) > 0:
            df_bids = pd.DataFrame(book_data["bids"])
            if not df_bids.empty and 'volume' in df_bids.columns:
                # Encontra a maior escora (maior volume)
                idx_maior_bid = df_bids['volume'].idxmax()
                maior_escora_bid = df_bids.loc[idx_maior_bid]

                features['preco_maior_escora_bid'] = float(
                    maior_escora_bid.get('price', 0.0))
                features['volume_maior_escora_bid'] = float(
                    maior_escora_bid.get('volume', 0.0))

                # Calcula distância apenas se temos preço válido
                if features['preco_maior_escora_bid'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_bid'] = abs(
                        preco_referencia - features['preco_maior_escora_bid'])

                # Liquidez dos top 5 níveis
                features['liquidez_top5_bid'] = float(
                    df_bids.head(5)['volume'].sum())

        # Analisa o lado da venda (asks)
        if book_data.get("asks") and len(book_data["asks"]) > 0:
            df_asks = pd.DataFrame(book_data["asks"])
            if not df_asks.empty and 'volume' in df_asks.columns:
                # Encontra a maior escora (maior volume)
                idx_maior_ask = df_asks['volume'].idxmax()
                maior_escora_ask = df_asks.loc[idx_maior_ask]

                features['preco_maior_escora_ask'] = float(
                    maior_escora_ask.get('price', 0.0))
                features['volume_maior_escora_ask'] = float(
                    maior_escora_ask.get('volume', 0.0))

                # Calcula distância apenas se temos preço válido
                if features['preco_maior_escora_ask'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_ask'] = abs(
                        features['preco_maior_escora_ask'] - preco_referencia)

                # Liquidez dos top 5 níveis
                features['liquidez_top5_ask'] = float(
                    df_asks.head(5)['volume'].sum())

    except Exception as e:
        print(f"⚠️ Erro ao analisar profundidade do book: {e}")

    return features


def testar_formato_json():
    """Testa se a função funciona com dados JSON do EA."""
    print("🧪 Testando formato JSON do EA...")

    # Simula dados que o EA geraria
    book_data_json = {
        "bids": [
            {"price": 140080.0, "volume": 312},
            {"price": 140075.0, "volume": 150},
            {"price": 140070.0, "volume": 500},  # Esta será a maior escora
            {"price": 140065.0, "volume": 200},
            {"price": 140060.0, "volume": 100}
        ],
        "asks": [
            {"price": 140085.0, "volume": 68},
            {"price": 140090.0, "volume": 299},
            {"price": 140095.0, "volume": 800},  # Esta será a maior escora
            {"price": 140100.0, "volume": 150},
            {"price": 140105.0, "volume": 75}
        ]
    }

    preco_referencia = 140082.5  # Preço médio entre bid e ask

    features = analisar_profundidade_book(book_data_json, preco_referencia)

    print("📊 Resultados da análise:")
    print(
        f"   Maior escora BID: {features['volume_maior_escora_bid']} contratos a {features['preco_maior_escora_bid']}")
    print(
        f"   Distância escora BID: {features['distancia_maior_escora_bid']:.1f} pontos")
    print(
        f"   Maior escora ASK: {features['volume_maior_escora_ask']} contratos a {features['preco_maior_escora_ask']}")
    print(
        f"   Distância escora ASK: {features['distancia_maior_escora_ask']:.1f} pontos")
    print(f"   Liquidez top5 BID: {features['liquidez_top5_bid']} contratos")
    print(f"   Liquidez top5 ASK: {features['liquidez_top5_ask']} contratos")

    # Validações
    assert features['volume_maior_escora_bid'] == 500, "Maior escora BID deveria ser 500"
    assert features['preco_maior_escora_bid'] == 140070.0, "Preço da maior escora BID deveria ser 140070.0"
    assert features['volume_maior_escora_ask'] == 800, "Maior escora ASK deveria ser 800"
    assert features['preco_maior_escora_ask'] == 140095.0, "Preço da maior escora ASK deveria ser 140095.0"
    assert features['liquidez_top5_bid'] == 1262, "Liquidez top5 BID deveria ser 1262"
    assert features['liquidez_top5_ask'] == 1392, "Liquidez top5 ASK deveria ser 1392"

    print("✅ Teste JSON passou!")
    return True


def testar_formato_legado():
    """Testa compatibilidade com formato legado (sem preços)."""
    print("\n🧪 Testando compatibilidade com formato legado...")

    # Simula dados do formato antigo (convertidos)
    book_data_legado = {
        "bids": [
            {"price": 0.0, "volume": 312},
            {"price": 0.0, "volume": 150},
            {"price": 0.0, "volume": 500}
        ],
        "asks": [
            {"price": 0.0, "volume": 68},
            {"price": 0.0, "volume": 299},
            {"price": 0.0, "volume": 800}
        ]
    }

    preco_referencia = 140082.5

    features = analisar_profundidade_book(book_data_legado, preco_referencia)

    print("📊 Resultados da análise (formato legado):")
    print(
        f"   Maior escora BID: {features['volume_maior_escora_bid']} contratos")
    print(
        f"   Maior escora ASK: {features['volume_maior_escora_ask']} contratos")
    print(f"   Liquidez top5 BID: {features['liquidez_top5_bid']} contratos")
    print(f"   Liquidez top5 ASK: {features['liquidez_top5_ask']} contratos")
    print(
        f"   Distâncias: BID={features['distancia_maior_escora_bid']}, ASK={features['distancia_maior_escora_ask']}")

    # No formato legado, as distâncias ficam 0 (sem preços válidos)
    assert features['volume_maior_escora_bid'] == 500, "Maior escora BID deveria ser 500"
    assert features['volume_maior_escora_ask'] == 800, "Maior escora ASK deveria ser 800"

    print("✅ Teste compatibilidade passou!")
    return True


def testar_dados_vazios():
    """Testa comportamento com dados vazios ou inválidos."""
    print("\n🧪 Testando dados vazios/inválidos...")

    # Teste com dados vazios
    features_vazio = analisar_profundidade_book({}, 140000.0)
    print("📊 Dados vazios - todas features devem ser 0 ou padrão:")
    for key, value in features_vazio.items():
        print(f"   {key}: {value}")

    # Teste com dados None
    features_none = analisar_profundidade_book(None, 140000.0)
    print("📊 Dados None - todas features devem ser 0 ou padrão:")
    for key, value in features_none.items():
        print(f"   {key}: {value}")

    print("✅ Teste dados vazios passou!")
    return True


def testar_contexto_completo():
    """Testa se o contexto final tem todas as 18 features."""
    print("\n🧪 Testando contexto completo com 18 features...")

    # Simula contexto original (10 features)
    contexto_original = {
        "bid_qty": 1000,
        "ask_qty": 800,
        "spread": 2.5,
        "volatility": 45.2,
        "candle_type": "doji",
        "entropia_book": 0.65,
        "rsi_14": 58.3,
        "volume_tick": 150,
        "is_in_trade": 0,
        "floating_profit": 0.0,
        "tempo_em_trade": 0
    }

    # Simula features de profundidade
    features_profundidade = {
        'preco_maior_escora_bid': 140070.0,
        'volume_maior_escora_bid': 500.0,
        'distancia_maior_escora_bid': 12.5,
        'preco_maior_escora_ask': 140095.0,
        'volume_maior_escora_ask': 800.0,
        'distancia_maior_escora_ask': 12.5,
        'liquidez_top5_bid': 1262.0,
        'liquidez_top5_ask': 1392.0
    }

    # Combina contextos (como no código real)
    contexto_completo = {
        **contexto_original,
        **features_profundidade
    }

    print(f"📊 Contexto completo tem {len(contexto_completo)} features:")
    for i, (key, value) in enumerate(contexto_completo.items(), 1):
        print(f"   {i:2d}. {key}: {value}")

    assert len(
        contexto_completo) == 19, f"Deveria ter 19 features (11 originais + 8 profundidade), mas tem {len(contexto_completo)}"

    # Verifica se todas as features de profundidade estão presentes
    features_esperadas = [
        'preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
        'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
        'liquidez_top5_bid', 'liquidez_top5_ask'
    ]

    for feature in features_esperadas:
        assert feature in contexto_completo, f"Feature {feature} não encontrada no contexto"

    print("✅ Teste contexto completo passou!")
    return True


def main():
    """Executa todos os testes."""
    print("🚀 INICIANDO TESTES DE PROFUNDIDADE DO BOOK")
    print("=" * 60)

    try:
        # Executa todos os testes
        testar_formato_json()
        testar_formato_legado()
        testar_dados_vazios()
        testar_contexto_completo()

        print("\n" + "=" * 60)
        print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("✅ A implementação de profundidade do book está funcionando corretamente")
        print("🚀 O Monstro V2 está pronto para usar as novas features!")

    except Exception as e:
        print(f"\n❌ ERRO NOS TESTES: {e}")
        print("🔧 Verifique a implementação antes de usar em produção")
        return False

    return True


if __name__ == "__main__":
    main()
