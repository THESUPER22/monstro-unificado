#!/usr/bin/env python3
"""
Corre para o problema de book vazio quando mercado está fechado.
Modifica a função verificar_estado_book para aceitar dados do CSV quando mercado fechado.
"""

import re

def corrigir_verificacao_book():
    """Corrige a função verificar_estado_book no arquivo principal."""

    arquivo = "monstro_unificado_v2.py"

    print("🔧 CORRIGINDO VERIFICAÇÃO DE BOOK PARA MERCADO FECHADO")
 print("=" * 60)

    # Lê o arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Locação verificar_estado_book
    padrao_funcao = r'def verificar_estado_book\(symbol: str = SYMBOL\) -> bool:(.*?)(?=\n\ndef|\nclass|\Z)'

    match = re.search(padrao_funcao, conteudo, re.L)

    if not m
     print("❌ Função verificar_estado_bookencontrada")
        return False

    print("✅ Função verificar_estado_book encontrada")

    # Nova implementação da função
    nova_funcao = '''def verificar_estado_book(symbol: = SYMBOL) -> bool:
    """Verifica se o book está ativo e funcionando corretamente."""
    try:
        # Verifica se é fim de semana
        if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
            logging.info(
                "📅 Fim de semana: book não disponível (comportamento normal)")
turn True  # Retorna True para evitar tentativas de reinicialização

        # Verifica se é horário de mercado fechado (fora do pregão)
        agora = datetime.now().time()
        inicio_pregao = datetime.strptime("09:00", "%H:%M").time()
        fim_pregao = datetime.strptime("18:30", "%H:%M").time()

        if agora < inicio_pregao or agora > fim_pregao:
            logging.info(
                f"🕐 Mercado fechado ({agora.strfH:%M')}): usando dados do arquivo CSV")
            # Quando mercado fechado, verifica se consegue ler o arquivo CSV
            try:
                book_csv = ler_book_csv()
                if book_csv and book_csv.get('bids') and book_csv.get('asks'):
                    return True
lse:
                    logging.warning("⚠️ Arquivo CSV do EA não disponível ou vazio")
                    return False
            except Exception as e:
ing.warning(f"⚠️ Erro ao ler CSV do EA: {e}")
                return False

        # Garante que o símbolo esteja selecionado
        mt5.symbol_select(symbol, True)

Verifica se o book está ativo
        if not mt5.market_book_add(symbol):
            logging.error(f"❌ Erro ao ativar book: {mt5.last_error()}")
urn False

        # Tenta obter dados do book
        book = mt5.market_book_get(symbol)
        if book is None:
            logging.error("❌ Book retornou None")
            return False

        # Verifica se há dados no book
        if len(book) == 0:
            logging.error("❌ Book vazio")
            return False

        # Verifica tipos de ordem no book
        tipos_ordem = set(level.type for level in book)
        if len(tipos_ordem) < 2:
            logging.error(f"❌ Book com apenas um tipo de ordem: {tipos_ordem}")
            return False

        return True

    except Exception as e:
        logging.error(f"❌ Erro ao verificar estado do book: {e}")
        return False'''

    # Substitui a função
    conteudo_nb(padrao_funcao, nova_funcao, conteudo, flags=re.DOTALL)

    # Verifica se a substituição foi feita
    if conteudo_novo == conteudo:
        print("❌ N"i feitafolteração
te")anualmenvo m o arqui🔧 Verifiqueprint(")
        ÇÃO!"RE NA CORFALHA"\n❌      print( else:
   )
   ado"do fechercaom mo mesmo cMonstrtestar o ocê pode "💡 Agora vnt(pri   )
     O!"M SUCESSADA COÇÃO APLICn🎯 CORREint("\
        pracao_book():erificf corrigir_v_":
    i== "__main_f __name__ rn True

i
    retu
    cadoo mero CSV quanda dados da aceitsistemora o t("📝 Ag)
    princesso!"gida com suook corrir_estado_bficação verint("✅ Fun   prio)

 nteudo_nov.write(co       ff:
 s -8') aoding='utf encrquipen(ath o wiquivo
    o arva  # Sal
      se
 Fal return
