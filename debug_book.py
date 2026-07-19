import os


def debug_book():
    arquivo = "book_data_win.csv"

    print("DEBUG DO ARQUIVO DE BOOK")
    print("=" * 40)

    if not os.path.exists(arquivo):
        print(f"ERRO: Arquivo nao existe: {arquivo}")
        return

    tamanho = os.path.getsize(arquivo)
    print(f"Tamanho: {tamanho} bytes")

    with open(arquivo, 'r') as f:
        conteudo = f.read()

    print(f"Conteudo:")
    print(repr(conteudo))

    linhas = conteudo.strip().split('\n')
    print(f"\n{len(linhas)} linhas:")
    for i, linha in enumerate(linhas, 1):
        print(f"   {i}: {repr(linha)}")

    # Testa como CSV
    try:
        if len(linhas) >= 2:
            volumes_bid = [int(x) for x in linhas[0].split(',') if x.strip()]
            volumes_ask = [int(x) for x in linhas[1].split(',') if x.strip()]

            print(f"\nCSV valido:")
            print(f"   BID: {volumes_bid} (soma: {sum(volumes_bid)})")
            print(f"   ASK: {volumes_ask} (soma: {sum(volumes_ask)})")

    except Exception as e:
   print(f"Erro CSV: {e}")

if __name__ == "__main__":
    debug_book()
