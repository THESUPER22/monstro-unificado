#!/usr/bion3
"""
Debug da leitura do book para identificar problemas específicos.
"""

import json
import os
import sys

def debug_arquivo_book():
    """Faz debug completo do arquivo de book."""

    arquivo = "book_data_win.csv"

    print("🔍 DEBUG COMPLETO DO ARQUIVO DE BOOK")
    print("=" * 50)

    # Verifica se arquivo existe
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não existe: {arquivo}")
        return False

    print(f"✅ Arquivo existe: {arquivo}")

    # Verifica tamanho
    tamanho = os.path.getsize(arquivo)
    print(f"📏 Tamanho: {tamanho} bytes")

    if tamanho < 4:
        print("⚠️ Arquivo muito pequeno (< 4 bytes)")
        return False

    # Tenta ler como texto
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        print(f"📄 Conteúdo bruto ({len(conteudo)} chars):")
        print(f"'{conteudo}'")
        print()

        # Mostra linhas
        linhas = conteudo.strip().split('\n')
        print(f"📋 Linhas ({len(linhas)}):")
        for i, linha in enumerate(linhas, 1):
            print(f"   {i}: '{linha}' ({len(linha)} chars)")
        print()

    except Exception as e:
        print(f"❌ Erro ao ler como texto: {e}")
        return False

    # Tenta interpretar como JSON
    print("🧪 Testando formato JSON...")
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados_json = json.load(f)

        print("✅ É um JSON válido!")
        print(f"   🔑 Chaves: {list(dados_json.keys())}")

        if "bids" in dados_json:
            print(f"   📊 BIDs: {len(dados_json['bids'])} níveis")
            if dados_json['bids']:
                print(f"       Primeiro: {dados_json['bids'][0]}")

        if "asks" in dados_json:
            print(f"   📊 ASKs: {len(dados_json['asks'])} níveis")
     if dados_json['asks']:
                print(f"       Primeiro: {dados_json['asks'][0]}")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Não é JSON válido: {e}")
    except Exception as e:
        print(f"❌ Erro ao ler JSON: {e}")

    # Tenta interpretar como CSV
    print("\n🧪 Testando formato CSV...")
    try:
        linhas = conteudo.strip().split('\n')

        if len(linhas) >= 2:
            linha_bid = linhas[0].strip()
            linha_ask = linhas[1].strip()

            volumes_bid = [int(x.strip()) for x in linha_bid.split(',') if x.strip()]
            volumes_ask = [int(x.strip()) for x in linha_ask.split(',') if x.strip()]

            print("✅ É um CSV válido!")
            print(f"   📊 Volumes BID: {volumes_bid} (total: {sum(volumes_bid)})")
            print(f"   📊 Volumes ASK: {volumes_ask} (total: {sum(volumes_ask)})")

            # Simula conversão para formato JSON
            dados_convertidos = {
                "bids": [{"price": 0.0, "volume": vol} for vol in volumes_bid],
                "asks": [{"price": 0.0, "volume": vol} for vol in volumes_ask]
            }

            print(f"   🔄 Convertido: {len(dados_convertidos['bids'])} BIDs, {len(dados_convertidos['asks'])} ASKs")

            return True
        else:
            print(f"❌ CSV inválido: precisa de pelo men linhas, tem {len(linhas)}")

    except ValueError as e:
        print(f"❌ Erro ao converter números: {e}")
    except Exception as e:
        print(f"❌ Erro ao processar CSV: {e}")

    return False

def testar_funcao_analisar_profundidade():
    """Testa a função de análise de profundidade com dados do arquivo atual."""

    print("\n🧪 TESTANDO FUNÇÃO DE ANÁLISE DE PROFUNDIDADE")
    print("=" * 50)

    # Importa a função do arquivo principal (se possível)
    try:
        sys.path.append('.')
        # Não vamos importar o arquivo completo para evitar inicialização
        # Vamos recriar a função aqui

        def analisar_profundidade_book_local(book_data, preco_referencia=140000.0):
            """Versão local da função para teste."""

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
                import pandas as pd

                # Analisa BIDs
                if book_data.get("bids") and len(book_data["bids"]) > 0:
                    df_bids = pd.DataFrame(book_data["bids"])
                    if not df_bids.empty and 'volume' in df_bids.columns:
                        idx_= df_bids['volume'].idxmax()
                        maior_escora]
e()undidadalisar_prof_anuncaostar_f    teo_book()
ug_arquiv    deb
__":main ==name__
if __")
ste: {e} Erro no te  print(f"❌
      ption as e:cept Exce
    ex      mente!")ndo corretancionaidade fue de profundis"\n✅ Anál print(       se:
     el      ")
 ema}obl• {prprint(f"                  as:
 roblemma in p proble   for
  DOS:")DETECTAAS ⚠️ PROBLEM print("\n          s:
 f problema
        i        zero")
  édez top5 ASKLiquiend("pplemas.a      prob     0:
  ==] sk'ez_top5_aquides['li  if featur")
      5 BID é zero topquidezend("Lis.appemabl    pro         0:
==bid'] p5__to['liquidezf features   io")
     ercora AS maior esume da"Volas.append(blem         pro
 == 0:ra_ask'] come_maior_esures['voluif feat    ")
    D é zeroora BIescmaior Volume da s.append("    problema        = 0:
'] =escora_bidaior_es['volume_mif featur]
        emas = [obl        prtido
es fazem senaturerifica s# V
            lue}")
y}: {vake"   {rint(f       ps():
     tematures.iin fealue  for key, v     SE:")
  DA ANÁLIO LTADRESU"\n📊   print(

0000.0)a, 14(book_dat_localdidade_bookfunro= analisar_p   features dade
      profundi deta análise  # Tes
      )
    ', []))}"('askseta.gk_dat{len(booSKs: t(f"   📊 Arin
        p[]))}")et('bids', ta.g_dan(book BIDs: {le"   📊 print(f
       rmato}")focomo {s  Dados lido"✅int(f    pr
turn
            re
       : {e}") arquivoler"❌ Erro ao   print(f              ion as e:
cept Except      ex
      eturn    r              o")
  nválidV i CS Arquivo   print("❌
              else:       "
   VCSrmato = "     fo       }
                          s_ask]
   in volumevol} for vol: e"volum 0.0, "ce":{"pri": [    "asks                _bid],
     volumes vol inforol} lume": v"vo: 0.0,  [{"price" "bids":
      ok_data = {        bo

      ip()].strt(',') if xip().splistrn linhas[1].) for x itrip() = [int(x.s volumes_ask                 trip()]
  ',') if x.st(ip().spli0].strn linhas[ for x ip())ri(x.st= [intolumes_bid   v                   >= 2:
n(linhas)   if le

   nes()adlinhas = f.re li                   as f:
='utf-8') ding'r', encoarquivo,  with open(         :
        try         SV
 omo Centa ler c T        #:
      except"
      to = "JSONma for         .load(f)
  = jsonk_data   boo
      f:tf-8') asing='uodr', encn(arquivo, 'pe  with o        try:
       imeiro
   o JSON prta ler com     # Ten
 n
          retur
     ivo}")qu {arrado:contuivo não ennt(f"❌ Arq   pri
         ):quivots(arxish.eatf not os.p     i

  sv"_win.c"book_dataquivo =    arl
     uivo atuaos do arq  # Lê dad
     features
 eturn      r
          ")
   nálise: {e} Erro na a⚠️(f"print              e:
   tion ascept Excep         ex
                     ))
  um(.s5)['volume']ks.head(oat(df_as = flz_top5_ask']res['liquide   featu
                       ia)
       erencreco_refa_ask'] - pmaior_escoreco_atures['pr   fe                          = abs(
   ask'] escora_or_aiia_mes['distancfeatur                        :
    encia > 0o_refer0 and prec > ask']ora_or_escs['preco_maieature       if f
                    )
', 0.0)get('volumea_ask.orescfloat(maior_= ] ra_ask'maior_escoolume_ures['v feat
    )) 0.0rice',t('pcora_ask.geior_es float(ma] =a_ask'_escorco_maioratures['pre   fe
                       or_ask]
   maix_loc[id df_asks.ask =_escora_maior                      x()
  idxmae'].sks['volum df_aior_ask =   idx_ma                     lumns:
n df_asks.co id 'volume' ans.emptynot df_ask
      "])ksasook_data["ataFrame(b = pd.D  df_asks                 0:
  s"]) >k_data[" and len(boosks")("ak_data.get if boo            Ks
   alisa AS An           #
               um())
  .s'])['volume_bids.head(5oat(df5_bid'] = flliquidez_top  features['

      id'])escora_bpreco_maior_atures['a - feeferenci   preco_r
     id'] = abs(ra_br_escostancia_maios['dire  featu                          cia > 0:
co_referen0 and preid'] > a_b_maior_escors['precourefeat          i

         )), 0.0get('volume'ora_bid.t(maior_esc floa_bid'] =r_escora_maio['volume   features                     .0))
', 0ce.get('pribidcora_maior_es] = float(escora_bid'maior_res['preco_       fea
                                  r_bidioc[idx_mabids.lo_bid = df_
