//+------------------------------------------------------------------+
//| EA_BookData_Sniper_V5.mq5                                        |
//| Monstro das Negociações — Versão Sniper Seletiva                 |
//| Filtros: Volume Mínimo, Desequilíbrio (Imbalance), Escrita por Evento|
//+------------------------------------------------------------------+
#property copyright "Monstro das Negociações"
#property version   "5.0"
#property description "EA Sniper — Só envia dados de alta relevância"

//--- Parâmetros de entrada
input int    InpMinVolumeTrigger = 1500;     // Volume total mínimo para disparar (cc)
input double InpMinImbalanceRatio = 1.5;     // Desequilíbrio mínimo (ex: 1.5 = 50% a mais de um lado)
input int    InpMaxLevels = 10;              // Máximo de níveis do book
input bool   InpDebugMode = true;            // Modo debug
input string InpSymbolPrefix = "WIN";        // Prefixo do símbolo

//--- Variáveis globais
string   g_symbol      = "";
bool     g_bookActive  = false;
ulong    g_updateCount = 0;
datetime g_lastUpdate  = 0;
string   g_fileName    = "book_data_win.csv";

//+------------------------------------------------------------------+
//| Inicialização                                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("🚀 EA Sniper V5 iniciando... Foco em Big Players (> ", InpMinVolumeTrigger, "cc)");
    g_symbol = Symbol(); // Usa o símbolo do gráfico atual
    
    if(!MarketBookAdd(g_symbol)) 
    {
        Print("❌ Falha ao ativar Book para ", g_symbol);
        return INIT_FAILED;
    }

    g_bookActive = true;
    Print("✅ EA Sniper Ativado para: ", g_symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Finalização                                                      |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(g_bookActive) MarketBookRelease(g_symbol);
    Print("🏁 EA Sniper finalizado. Sinais Relevantes Enviados: ", g_updateCount);
}

//+------------------------------------------------------------------+
//| OnBookEvent — Onde a mágica acontece                             |
//+------------------------------------------------------------------+
void OnBookEvent(const string& symbol)
{
    if(symbol != g_symbol) return;
    
    MqlBookInfo book[];
    if(!MarketBookGet(g_symbol, book)) return;
    
    long totalBidVol = 0;
    long totalAskVol = 0;
    
    // Calcula volumes totais do book atual
    for(int i = 0; i < ArraySize(book); i++)
    {
        long vol = (book[i].volume_real > 0) ? (long)book[i].volume_real : book[i].volume;
        if(book[i].type == BOOK_TYPE_BUY) totalBidVol += vol;
        else if(book[i].type == BOOK_TYPE_SELL) totalAskVol += vol;
    }
    
    // --- FILTRO SNIPER 1: VOLUME MÍNIMO ---
    if(totalBidVol < InpMinVolumeTrigger && totalAskVol < InpMinVolumeTrigger) return;
    
    // --- FILTRO SNIPER 2: DESEQUILÍBRIO (IMBALANCE) ---
    double ratio = 0;
    if(totalBidVol > 0 && totalAskVol > 0)
    {
        ratio = (totalBidVol > totalAskVol) ? (double)totalBidVol/totalAskVol : (double)totalAskVol/totalBidVol;
    }
    
    if(ratio < InpMinImbalanceRatio) return; // Ignora se o mercado estiver equilibrado (sardinhas brigando)

    // Se passou nos filtros, envia para o Python
    UpdateBookData(book, totalBidVol, totalAskVol);
}

//+------------------------------------------------------------------+
//| Escrita dos dados filtrados                                      |
//+------------------------------------------------------------------+
void UpdateBookData(MqlBookInfo &book[], long totalBidVolume, long totalAskVolume)
{
    string bids = "";
    string asks = "";
    int bidCount = 0;
    int askCount = 0;

    for(int i = 0; i < ArraySize(book); i++)
    {
        long vol = (book[i].volume_real > 0) ? (long)book[i].volume_real : book[i].volume;
        string priceStr = DoubleToString(book[i].price, _Digits);

        if(book[i].type == BOOK_TYPE_BUY && bidCount < InpMaxLevels)
        {
            if(bidCount > 0) bids += ",";
            bids += "{\"price\":" + priceStr + ",\"volume\":" + (string)vol + "}";
            bidCount++;
        }
        else if(book[i].type == BOOK_TYPE_SELL && askCount < InpMaxLevels)
        {
            if(askCount > 0) asks += ",";
            asks += "{\"price\":" + priceStr + ",\"volume\":" + (string)vol + "}";
            askCount++;
        }
    }

    string json = "{";
    json += "\"timestamp\":" + (string)TimeCurrent() + ",";
    json += "\"symbol\":\"" + g_symbol + "\",";
    json += "\"bids\":[" + bids + "],";
    json += "\"asks\":[" + asks + "],";
    json += "\"total_bid_volume\":" + (string)totalBidVolume + ",";
    json += "\"total_ask_volume\":" + (string)totalAskVolume + ",";
    json += "\"relevancia\":true"; // Flag para o Python saber que é um sinal forte
    json += "}";

    string tempFileName = g_fileName + ".tmp";
    int handle = FileOpen(tempFileName, FILE_WRITE|FILE_TXT|FILE_UNICODE);
    
    if(handle != INVALID_HANDLE)
    {
        FileWriteString(handle, json);
        FileClose(handle);
        FileDelete(g_fileName);
        if(FileMove(tempFileName, 0, g_fileName, 0))
        {
            g_updateCount++;
            if(InpDebugMode) Print("🎯 SINAL SNIPER ENVIADO! Vol: ", totalBidVolume + totalAskVolume, " | Ratio: ", DoubleToString(totalBidVolume > totalAskVolume ? (double)totalBidVolume/totalAskVolume : (double)totalAskVolume/totalBidVolume, 2));
        }
    }
}
