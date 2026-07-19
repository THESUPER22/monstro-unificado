def test_indentation_error():
    try:
        # Simulando o bloco de código que causa o erro de indentação
        colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book']
    except IndentationError:
        assert True
    else:
        assert False