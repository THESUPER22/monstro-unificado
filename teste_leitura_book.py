#!/usr/bin/env python3
"""
Teste específico para verificar se o Monstro consegue ler o arquivo book_data_win.csv atual
"""

import os
import sys

sys.path.append('.')


def testar_leitura_atual():
    """Testa a leitura do arquivo atual do EA"""

    # Verifica se arquivo existe
    if not os.path.exists('book_data_win.csv'):
        print("❌ Arquivo book_data_win.csv não encontrado")
        return False

    print("📁 Arquivo encontrado, testando leitura...")

    # Tenta diferentes encodings
    encodings = ['utf-8', 'utf-16-le', 'utf-16', 'latin1', 'cp1252']

    for encoding in encodings:
        try:
            with open('book_data_win.csv', 'r', encoding=encoding) as f:
                content = f.read()

            print(f"✅ Sucesso com encoding {encoding}")
            print(f"   Conteúdo: {repr(content[:100])}")

            lines = content.strip().split('\n')
            print(f"   Linhas: {len(lines)}")

            if len(lines) >= 1:
                # Testa o parsing da primeira linha
                line1 = lines[0].strip()
                line1_clean = ''.join(
                    c for c in line1 if c.isprintable() or c == ',')

                values = []
                for v in line1_clean.split(','):
                    v_clean = v.strip()
                    if v_clean and v_clean.replace('.', '').replace('-', '').isdigit():
                        try:
                            values.append(int(float(v_clean)))
                        except:
                            continue

                print(f"   Valores extraídos: {values}")
                print(f"   Total valores: {len(values)}")

                if len(values) > 0:
                    print(
                        f"🎉 SUCESSO! Conseguiu extrair {len(values)} valores")
                    return True

            break

        except Exception as e:
            print(f"❌ Falha com encoding {encoding}: {e}")
            continue

    return False


if __name__ == "__main__":
    print("🧪 TESTE DE LEITURA DO BOOK_DATA_WIN.CSV")
    print("=" * 50)

    sucesso = testar_leitura_atual()

    if sucesso:
        print("\n✅ TESTE PASSOU - O Monstro deve conseguir ler o arquivo!")
    else:
        print("\n❌ TESTE FALHOU - Precisa investigar mais")
